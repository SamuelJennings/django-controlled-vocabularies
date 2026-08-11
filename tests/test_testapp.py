"""Tests for :mod:`tests.testapp` — the consuming test app T002 builds.

Not a test of application logic: the models carry none beyond ``__str__`` and
``Artifact.get_mineral_label()``, which exists solely as T011's collision
target. These prove the app's own two acceptance criteria — it migrates
cleanly from zero, and stays ``makemigrations --check`` clean — plus that the
three model factories and the two vocabulary fixtures ``conftest.py`` now
carries for #87, #88 and #89 build correctly. The field's *bound* runtime
behaviour (declaring, saving, reading back, the reverse accessor) is US-1's
(T004) and is not exercised here.

- ``TestMigrations`` — the app migrates from zero; ``makemigrations --check``
  stays clean.
- ``TestFactories`` — the three model factories build valid, saved records.
- ``TestVocabularyFixtures`` — the two scheme fixtures build the shape their
  docstrings promise.
"""

import pytest
from django.core.management import call_command

from tests.factories import ArtifactFactory, SampleFactory, SpecimenFactory
from tests.testapp.models import Artifact, Sample, Specimen


class TestMigrations:
    """T002 — the app migrates from zero, and stays ``makemigrations --check`` clean."""

    @pytest.mark.django_db
    def test_models_are_queryable(self):
        """Tables exist and are queryable — proof the app's own migration
        applied. pytest-django builds the test database from every installed
        app's migrations, run from zero, for the whole session; a query
        against any of these three tables fails outright if it did not."""
        assert Specimen.objects.count() == 0
        assert Sample.objects.count() == 0
        assert Artifact.objects.count() == 0

    @pytest.mark.django_db
    def test_makemigrations_check_is_clean(self):
        """No undeclared model changes: exits normally rather than raising
        ``SystemExit(1)``, which is ``makemigrations --check``'s failure mode
        when it detects an unmade migration."""
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)


class TestFactories:
    """The three model factories T002 adds build valid, saved records."""

    @pytest.mark.django_db
    def test_specimen_factory_builds_a_required_concept(self):
        specimen = SpecimenFactory()
        assert specimen.pk is not None
        assert specimen.rock_type is not None

    @pytest.mark.django_db
    def test_sample_factory_leaves_the_optional_field_unset_by_default(self):
        sample = SampleFactory()
        assert sample.pk is not None
        assert sample.mineral is None

    @pytest.mark.django_db
    def test_artifact_factory_leaves_the_optional_field_unset_by_default(self):
        artifact = ArtifactFactory()
        assert artifact.pk is not None
        assert artifact.mineral is None

    @pytest.mark.django_db
    def test_artifact_keeps_its_own_get_mineral_label(self):
        """The pre-existing definition T011's collision guard must leave alone."""
        artifact = ArtifactFactory()
        assert artifact.get_mineral_label() == "this artifact's own label, not the field's"


class TestVocabularyFixtures:
    """The scheme/concept fixtures ``conftest.py`` now carries for #87, #88, #89."""

    @pytest.mark.django_db
    def test_multilingual_scheme_has_one_concept_with_a_second_language_label(self, multilingual_scheme):
        assert multilingual_scheme.concepts.count() == 2
        labelled = [c for c in multilingual_scheme.concepts.all() if c.labels.exists()]
        assert len(labelled) == 1
        assert labelled[0].labels.filter(language="de").exists()

    @pytest.mark.django_db
    def test_single_language_scheme_has_no_extra_labels(self, single_language_scheme):
        assert single_language_scheme.concepts.count() == 2
        assert not any(c.labels.exists() for c in single_language_scheme.concepts.all())

    @pytest.mark.django_db
    def test_the_two_schemes_are_distinct(self, multilingual_scheme, single_language_scheme):
        assert multilingual_scheme.pk != single_language_scheme.pk
