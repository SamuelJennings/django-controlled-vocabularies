"""Tests for :mod:`controlled_vocabularies.checks` (T008, T009)."""

import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from django import forms
from django.conf import settings
from django.core import checks as django_checks
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from controlled_vocabularies.checks import (
    CHECK_ID,
    CHECK_ID_MISSING_INSTALLED_APP,
    CHECK_ID_MISSING_ROUTE,
    check_concept_autocomplete_route_included,
    check_concept_field_vocabularies,
    check_django_tomselect_installed,
)
from tests.factories import ConceptSchemeFactory
from tests.testapp.models import Specimen

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_django_admin(*args: str) -> subprocess.CompletedProcess:
    """Run ``django-admin`` in a fresh subprocess against a brand-new, never-migrated
    ``:memory:`` sqlite database (``tests/settings.py``'s ``DATABASES``) — the state
    the very first ``migrate`` on a real install runs the checks against (T009)."""
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"}
    poetry = shutil.which("poetry")
    assert poetry is not None, "poetry must be on PATH to run this test"
    return subprocess.run(  # noqa: S603 — fixed argv, no untrusted input
        [poetry, "run", "django-admin", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.django_db
class TestCheckConceptFieldVocabularies:
    """T008 — the check walks every declared ``ConceptField`` and warns about the
    ones naming a vocabulary absent from the database."""

    def test_warns_about_a_field_whose_vocabulary_is_absent(self):
        warnings = check_concept_field_vocabularies(None)
        by_field = {(w.obj.model._meta.label, w.obj.name): w for w in warnings}
        assert ("testapp.Specimen", "rock_type") in by_field
        message = str(by_field[("testapp.Specimen", "rock_type")].msg)
        assert "testapp.Specimen" in message
        assert "rock_type" in message
        assert "rock-type" in message

    def test_reports_nothing_once_every_named_vocabulary_exists(self):
        ConceptSchemeFactory(name="Rock Type")
        ConceptSchemeFactory(name="Mineral")

        warnings = check_concept_field_vocabularies(None)

        assert warnings == []

    def test_reported_objects_are_warnings_not_errors(self):
        warnings = check_concept_field_vocabularies(None)

        assert warnings
        for warning in warnings:
            assert isinstance(warning, django_checks.Warning)
            assert warning.id == CHECK_ID

    def test_reports_only_the_absent_vocabulary_when_a_concept_field_names_several(self):
        """#111 — the single-value field reaches the check the same way the
        many-valued one does, one warning per absent slug it names."""
        ConceptSchemeFactory(name="Rock Type")

        warnings = check_concept_field_vocabularies(None)

        matches = [
            w for w in warnings if w.obj.model._meta.label == "testapp.Borehole" and w.obj.name == "dominant_material"
        ]
        assert len(matches) == 1
        message = str(matches[0].msg)
        assert "mineral" in message
        assert "rock-type" not in message

    def test_never_reports_a_concept_field_naming_no_vocabulary(self):
        """#111 — a single-value field naming none names nothing that could be
        missing, so the check has nothing to say about it, before or after any
        vocabulary is imported."""
        assert [w for w in check_concept_field_vocabularies(None) if w.obj.model._meta.label == "testapp.Sketch"] == []

        ConceptSchemeFactory(name="Rock Type")
        ConceptSchemeFactory(name="Mineral")

        assert [w for w in check_concept_field_vocabularies(None) if w.obj.model._meta.label == "testapp.Sketch"] == []

    def test_costs_one_query_however_many_fields_are_declared(self):
        # The test app declares several ConceptField and ConceptsField
        # instances (T010 widens the check to cover both) across a handful
        # of distinct vocabularies. However many slugs those fields name
        # between them, the distinct set is still resolved in one query.
        with CaptureQueriesContext(connection) as ctx:
            check_concept_field_vocabularies(None)

        assert len(ctx.captured_queries) == 1


@pytest.mark.django_db
class TestCheckConceptsFieldVocabularies:
    """T010 — the check widens to cover ``ConceptsField`` too (US-6, FR-003,
    FR-004, D9): a field naming several vocabularies contributes each slug it
    names, and a field naming none contributes nothing and is never warned
    about."""

    def test_warns_about_a_concepts_field_whose_vocabulary_is_absent(self):
        warnings = check_concept_field_vocabularies(None)

        matches = [w for w in warnings if w.obj.model._meta.label == "testapp.Deposit" and w.obj.name == "rock_types"]
        assert len(matches) == 1
        message = str(matches[0].msg)
        assert "testapp.Deposit" in message
        assert "rock_types" in message
        assert "rock-type" in message

    def test_reports_nothing_once_the_concepts_fields_vocabulary_exists(self):
        ConceptSchemeFactory(name="Rock Type")

        warnings = check_concept_field_vocabularies(None)

        matches = [w for w in warnings if w.obj.model._meta.label == "testapp.Deposit" and w.obj.name == "rock_types"]
        assert matches == []

    def test_reports_both_field_types_when_one_model_declares_both_against_one_absent_vocabulary(self):
        warnings = check_concept_field_vocabularies(None)

        matches = {w.obj.name for w in warnings if w.obj.model._meta.label == "testapp.RockSample"}
        assert matches == {"primary_mineral", "associated_minerals"}

    def test_reports_only_the_absent_vocabulary_when_a_field_names_several(self):
        ConceptSchemeFactory(name="Rock Type")

        warnings = check_concept_field_vocabularies(None)

        matches = [w for w in warnings if w.obj.model._meta.label == "testapp.FieldNote" and w.obj.name == "keywords"]
        assert len(matches) == 1
        message = str(matches[0].msg)
        assert "mineral" in message
        assert "rock-type" not in message

    def test_never_reports_a_field_naming_no_vocabulary(self):
        warnings = check_concept_field_vocabularies(None)

        matches = [w for w in warnings if w.obj.model._meta.label == "testapp.Photograph"]
        assert matches == []

    def test_never_reports_a_field_naming_no_vocabulary_even_once_others_exist(self):
        ConceptSchemeFactory(name="Rock Type")
        ConceptSchemeFactory(name="Mineral")

        warnings = check_concept_field_vocabularies(None)

        matches = [w for w in warnings if w.obj.model._meta.label == "testapp.Photograph"]
        assert matches == []

    def test_costs_one_query_when_a_field_names_several_vocabularies(self):
        with CaptureQueriesContext(connection) as ctx:
            check_concept_field_vocabularies(None)

        assert len(ctx.captured_queries) == 1


class TestCheckSurvivesUnmigratedDatabase:
    """T009 — the check runs before ``migrate``, so it must survive a database with
    no tables rather than raising. Exercised against a genuinely unmigrated
    connection (a fresh subprocess, never-migrated ``:memory:`` database), not a
    mock of ``DatabaseError`` (`plan.md` Risks, `research.md` R3)."""

    def test_check_reports_nothing_against_an_unmigrated_connection(self):
        result = _run_django_admin("check")

        assert result.returncode == 0, result.stderr
        assert CHECK_ID not in result.stdout
        assert "System check identified no issues" in result.stdout

    def test_makemigrations_succeeds_against_an_unmigrated_connection(self):
        result = _run_django_admin("makemigrations", "--check", "--dry-run")

        assert result.returncode == 0, result.stderr

    def test_migrate_succeeds_against_an_unmigrated_connection(self):
        result = _run_django_admin("migrate", "--no-input")

        assert result.returncode == 0, result.stderr

    @pytest.mark.django_db
    def test_silencing_the_check_id_suppresses_it(self):
        stderr = io.StringIO()
        call_command("check", stderr=stderr)
        assert CHECK_ID in stderr.getvalue()

        stderr = io.StringIO()
        with override_settings(SILENCED_SYSTEM_CHECKS=[CHECK_ID]):
            call_command("check", stderr=stderr)
        assert CHECK_ID not in stderr.getvalue()

    @pytest.mark.django_db
    def test_form_offers_no_choices_and_does_not_raise_when_vocabulary_absent(self):
        class SpecimenForm(forms.ModelForm):
            class Meta:
                model = Specimen
                fields = ["name", "rock_type"]

        form = SpecimenForm()

        assert list(form.fields["rock_type"].queryset) == []


class TestCheckConceptAutocompleteRouteIncluded:
    """T008 — warns when the project has not included this package's URL
    configuration (FR-010, decisions.md D14). ``reverse()`` resolves entirely
    against the already-loaded URLconf, so this never touches the database."""

    def test_warns_when_the_route_is_not_included(self):
        with override_settings(ROOT_URLCONF=()):
            warnings = check_concept_autocomplete_route_included(None)

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.id == CHECK_ID_MISSING_ROUTE
        message = f"{warning.msg} {warning.hint}"
        assert "controlled_vocabularies.urls" in message

    def test_absent_when_the_route_is_included(self):
        warnings = check_concept_autocomplete_route_included(None)

        assert warnings == []

    def test_reported_objects_are_warnings_not_errors(self):
        with override_settings(ROOT_URLCONF=()):
            warnings = check_concept_autocomplete_route_included(None)

        assert warnings
        for warning in warnings:
            assert isinstance(warning, django_checks.Warning)

    @pytest.mark.django_db
    def test_runs_without_touching_the_database(self, django_assert_num_queries):
        with override_settings(ROOT_URLCONF=()), django_assert_num_queries(0):
            check_concept_autocomplete_route_included(None)


class TestCheckDjangoTomselectInstalled:
    """T008 — warns when ``django_tomselect`` is not among the project's
    installed applications (FR-010, decisions.md D10). ``apps.is_installed()``
    reads the already-loaded app registry, so this never touches the
    database."""

    def test_warns_when_django_tomselect_is_not_installed(self):
        installed = [app for app in settings.INSTALLED_APPS if app != "django_tomselect"]
        with override_settings(INSTALLED_APPS=installed):
            warnings = check_django_tomselect_installed(None)

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.id == CHECK_ID_MISSING_INSTALLED_APP
        message = f"{warning.msg} {warning.hint}"
        assert "django_tomselect" in message

    def test_absent_when_django_tomselect_is_installed(self):
        warnings = check_django_tomselect_installed(None)

        assert warnings == []

    def test_reported_objects_are_warnings_not_errors(self):
        installed = [app for app in settings.INSTALLED_APPS if app != "django_tomselect"]
        with override_settings(INSTALLED_APPS=installed):
            warnings = check_django_tomselect_installed(None)

        assert warnings
        for warning in warnings:
            assert isinstance(warning, django_checks.Warning)

    @pytest.mark.django_db
    def test_runs_without_touching_the_database(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            check_django_tomselect_installed(None)
