"""Tests for :mod:`controlled_vocabularies.checks` (T008, T009)."""

import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from django import forms
from django.core import checks as django_checks
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from controlled_vocabularies.checks import CHECK_ID, check_concept_field_vocabularies
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

    def test_costs_one_query_however_many_fields_are_declared(self):
        # The test app declares three ConceptFields (Specimen.rock_type,
        # Sample.mineral, Artifact.mineral) across two distinct vocabularies.
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
        stdout = io.StringIO()
        call_command("check", stdout=stdout)
        assert CHECK_ID in stdout.getvalue()

        stdout = io.StringIO()
        with override_settings(SILENCED_SYSTEM_CHECKS=[CHECK_ID]):
            call_command("check", stdout=stdout)
        assert CHECK_ID not in stdout.getvalue()

    @pytest.mark.django_db
    def test_form_offers_no_choices_and_does_not_raise_when_vocabulary_absent(self):
        class SpecimenForm(forms.ModelForm):
            class Meta:
                model = Specimen
                fields = ["name", "rock_type"]

        form = SpecimenForm()

        assert list(form.fields["rock_type"].queryset) == []
