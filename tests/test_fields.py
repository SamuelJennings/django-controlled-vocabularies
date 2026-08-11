"""Tests for ``controlled_vocabularies.fields``.

Phase F covers ``ConceptField`` construction and ``deconstruct()``, unbound to
any consuming model — no model declares the field yet, so every test here
builds the field directly rather than through a model instance. The bound
behaviour (declaring it on a model, saving, reading back) is US-1's (T004),
and the ``validate()`` override's behavioural proof — raise, then read
``.messages`` and find the vocabulary named — is US-2's T005, against a real
test-app model. Neither is in scope here: with ``to`` the string
``"controlled_vocabularies.Concept"`` (not the imported class — see
``fields.py``'s module docstring for why), ``remote_field.model`` only
resolves once the field is attached to a model class, so an unbound field
cannot run ``validate()`` at all.

- ``TestConceptFieldConstruction`` — the fixed kwargs, the two construction-time
  rejections, that building the field issues no query (FR-003's mechanism),
  and that ``error_messages["invalid"]`` carries the named placeholder
  ``validate()`` needs (proved bound in T005).
- ``TestConceptFieldMigrations`` — a model carrying the field migrates from
  zero and stays ``makemigrations --check`` clean, which is what the string
  ``to`` and ``deconstruct()`` together exist to make possible.
- ``TestConceptFieldFactories`` and ``TestConceptVocabularyFixtures`` — the
  test-app factories and the two scheme fixtures ``conftest.py`` carries for
  #87, #88 and #89 build the shape their docstrings promise.
- ``TestConceptFieldDeconstruct`` — ``deconstruct()`` strips the three kwargs
  this field fixes and adds ``vocabulary``, so a field built from the emitted
  path/kwargs round-trips (T003, moved into Phase F because
  ``ModelState.from_model()`` clones every field through ``deconstruct()``,
  so T002's test app cannot migrate without it).
"""

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.models import PROTECT, Q
from django.test.utils import CaptureQueriesContext
from django.utils.functional import Promise
from django.utils.module_loading import import_string

from controlled_vocabularies.fields import ConceptField
from tests.factories import ArtifactFactory, SampleFactory, SpecimenFactory
from tests.testapp.models import Artifact, Sample, Specimen


class TestConceptFieldConstruction:
    """FR-001, FR-002, FR-007, FR-010 — the kwargs a consumer does not supply."""

    def test_fixes_to_concept(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.remote_field.model == "controlled_vocabularies.Concept"

    def test_fixes_on_delete_to_protect(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.remote_field.on_delete is PROTECT

    def test_fixes_limit_choices_to_the_named_vocabulary(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.get_limit_choices_to() == Q(scheme__slug="rock-type")

    @pytest.mark.django_db
    def test_construction_issues_no_queries(self):
        """FR-003's mechanism: the ``Q`` is constructed, never evaluated."""
        with CaptureQueriesContext(connection) as ctx:
            ConceptField(vocabulary="rock-type")
        assert len(ctx.captured_queries) == 0

    def test_rejects_consumer_supplied_on_delete(self):
        with pytest.raises(TypeError, match="on_delete"):
            ConceptField(vocabulary="rock-type", on_delete=PROTECT)

    def test_rejects_missing_vocabulary(self):
        with pytest.raises(TypeError, match="vocabulary"):
            ConceptField()

    def test_rejects_empty_vocabulary(self):
        with pytest.raises(TypeError, match="vocabulary"):
            ConceptField(vocabulary="")

    def test_help_text_has_a_translatable_default(self):
        field = ConceptField(vocabulary="rock-type")
        assert isinstance(field.help_text, Promise)
        assert str(field.help_text)

    def test_help_text_default_is_overridable(self):
        field = ConceptField(vocabulary="rock-type", help_text="Pick a rock type.")
        assert field.help_text == "Pick a rock type."

    def test_error_messages_invalid_carries_named_vocabulary_placeholder(self):
        field = ConceptField(vocabulary="rock-type")
        assert "%(vocabulary)s" in field.error_messages["invalid"]


class TestConceptFieldDeconstruct:
    """T003 — without this, ``Field.clone()`` (``db/models/fields/__init__.py``,
    ``self.__class__(*args, **kwargs)`` built from ``self.deconstruct()``) cannot
    rebuild the field: ``ForeignKey``/``RelatedField.deconstruct()`` would emit
    ``to``, ``on_delete`` and ``limit_choices_to`` but never ``vocabulary``, and
    ``__init__`` requires the latter and rejects the former. ``ModelState.from_model()``
    calls ``clone()`` on every local field, so every one of ``makemigrations``,
    ``makemigrations --check``, ``migrate`` and pytest-django's own test-database
    build would raise before writing anything — precisely what T002 hit.
    """

    def test_deconstruct_omits_the_three_fixed_kwargs(self):
        field = ConceptField(vocabulary="rock-type")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "to" not in kwargs
        assert "on_delete" not in kwargs
        assert "limit_choices_to" not in kwargs

    def test_deconstruct_adds_vocabulary(self):
        field = ConceptField(vocabulary="rock-type")
        _name, _path, _args, kwargs = field.deconstruct()
        assert kwargs["vocabulary"] == "rock-type"

    def test_round_trip_rebuilds_an_equivalent_field(self):
        """Deconstruct, rebuild from the emitted path and kwargs — exactly what
        ``Field.clone()`` and a replayed migration file both do — and the
        rebuilt field carries the same vocabulary, the same ``limit_choices_to``,
        and ``PROTECT``."""
        field = ConceptField(vocabulary="rock-type")
        _name, path, args, kwargs = field.deconstruct()
        field_class = import_string(path)
        rebuilt = field_class(*args, **kwargs)
        assert rebuilt.vocabulary == "rock-type"
        assert rebuilt.get_limit_choices_to() == Q(scheme__slug="rock-type")
        assert rebuilt.remote_field.on_delete is PROTECT

    def test_clone_rebuilds_without_error(self):
        """``clone()`` is exactly what ``ModelState.from_model()`` calls on every
        local field (``db/migrations/state.py``) — the failure T002 actually hit."""
        field = ConceptField(vocabulary="rock-type")
        cloned = field.clone()
        assert cloned.vocabulary == "rock-type"


class TestConceptFieldMigrations:
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


class TestConceptFieldFactories:
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


class TestConceptVocabularyFixtures:
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
