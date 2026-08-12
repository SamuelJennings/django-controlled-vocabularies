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
- ``TestConceptFieldRoundTrip`` — T004 (US-1): declaring the field on a real
  model, saving, and reading back a concept survives a save/reload; the
  optional field validates and saves with nothing attached; and using the
  field this way stays ``makemigrations --check`` clean, the regression guard
  against ``deconstruct()`` rotting.
- ``TestConceptFieldOrdinaryOptions`` — T004 (US-1): the field's ordinary
  ``ForeignKey`` options — ``related_name``, ``null``/``blank``,
  ``verbose_name``, ``help_text``, the automatic index — behave exactly as
  they would on a plain ``ForeignKey``, asserted directly on the bound field
  rather than only through a save/reload round trip.
- ``TestConceptFieldValidation`` — T005 (US-2): ``full_clean()`` on a record
  holding a concept from another vocabulary raises ``ValidationError``, and
  *reading* ``.messages`` shows the vocabulary named — the behavioural proof
  T001's ``validate()`` override exists for, only reachable against a real,
  bound model. A concept from the correct vocabulary passes; an optional
  field with nothing attached passes.
- ``TestConceptFieldFormChoices`` — T006 (US-2): a ``ModelForm`` generated
  from a consuming model offers only the named vocabulary's concepts as
  choices, and a submission carrying another vocabulary's concept is
  rejected rather than saved — proof that ``ForeignKey.formfield()`` passes
  ``limit_choices_to`` through, since nothing in this package's own source
  states that guarantee.
- ``TestConceptFieldDeleteGuard`` — T007 (US-3): no new code — ``PROTECT``
  was fixed on the field in T001. This class is the proof FR-007 needs: a
  referenced concept survives both a single-instance and a bulk queryset
  delete, the scheme holding it survives too (the cascade from scheme to
  concept meets the protection on the way down), an unreferenced concept
  deletes normally, and deleting the referencing record leaves the concept
  in place.
"""

import warnings

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, models
from django.db.models import CASCADE, PROTECT, ProtectedError, Q
from django.test.utils import CaptureQueriesContext, isolate_apps
from django.utils import translation
from django.utils.functional import Promise
from django.utils.module_loading import import_string

from controlled_vocabularies.fields import ConceptField, ConceptsField
from controlled_vocabularies.models import Concept, ConceptLabel, ConceptScheme
from tests.factories import (
    ArtifactFactory,
    ConceptFactory,
    ConceptSchemeFactory,
    DepositFactory,
    FieldNoteFactory,
    OutcropFactory,
    PhotographFactory,
    RockSampleFactory,
    SampleFactory,
    SpecimenFactory,
    SurveyFactory,
)
from tests.testapp.models import (
    Artifact,
    Deposit,
    FieldNote,
    Outcrop,
    Photograph,
    RockSample,
    Sample,
    Specimen,
    Survey,
)


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

    def test_rejects_consumer_supplied_limit_choices_to(self):
        # The vocabulary constraint IS limit_choices_to, so accepting a
        # consumer's would silently discard either theirs or the constraint.
        # Refused loudly, the same way on_delete is.
        with pytest.raises(TypeError, match="limit_choices_to"):
            ConceptField(vocabulary="rock-type", limit_choices_to=Q(label="Granite"))

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


class TestConceptsFieldConstruction:
    """FS-010 T002 (FR-001, FR-002, FR-003, FR-011) — ``vocabulary`` is optional
    and takes three shapes, normalised once in ``__init__`` to a tuple of
    slugs; the two kwargs a consumer does not supply (``limit_choices_to``,
    ``through``); construction issues no query."""

    def test_single_slug_normalises_to_a_one_element_tuple(self):
        field = ConceptsField(vocabulary="rock-type")
        assert field.vocabulary == ("rock-type",)
        assert field.get_limit_choices_to() == Q(scheme__slug__in=("rock-type",))

    def test_list_normalises_with_duplicates_collapsed_and_order_not_significant(self):
        field = ConceptsField(vocabulary=["gcmd", "agu-index", "gcmd"])
        assert set(field.vocabulary) == {"gcmd", "agu-index"}
        assert len(field.vocabulary) == 2
        assert field.get_limit_choices_to() == Q(scheme__slug__in=field.vocabulary)

    def test_omitted_vocabulary_normalises_to_empty_and_sets_no_restriction(self):
        field = ConceptsField()
        assert field.vocabulary == ()
        assert field.get_limit_choices_to() == {}

    def test_fixes_to_concept(self):
        field = ConceptsField(vocabulary="rock-type")
        assert field.remote_field.model == "controlled_vocabularies.Concept"

    @pytest.mark.django_db
    def test_construction_issues_no_queries(self):
        """FR-003's mechanism, for all three shapes: the ``Q`` is constructed,
        never evaluated, and an omitted vocabulary sets nothing to evaluate."""
        with CaptureQueriesContext(connection) as ctx:
            ConceptsField(vocabulary="rock-type")
            ConceptsField(vocabulary=["gcmd", "agu-index"])
            ConceptsField()
        assert len(ctx.captured_queries) == 0

    def test_rejects_consumer_supplied_limit_choices_to(self):
        with pytest.raises(TypeError, match="limit_choices_to"):
            ConceptsField(vocabulary="rock-type", limit_choices_to=Q(label="Granite"))

    def test_rejects_consumer_supplied_through(self):
        # A consumer-supplied through model would silently drop T003's delete
        # guarantee, the same reasoning that refuses on_delete on ConceptField.
        with pytest.raises(TypeError, match="through"):
            ConceptsField(vocabulary="rock-type", through="controlled_vocabularies.Concept")

    def test_rejects_non_string_vocabulary_element(self):
        with pytest.raises(TypeError, match="vocabulary"):
            ConceptsField(vocabulary=["mineral", 42])

    def test_help_text_has_a_translatable_default(self):
        field = ConceptsField(vocabulary="rock-type")
        assert isinstance(field.help_text, Promise)
        assert str(field.help_text)

    def test_help_text_default_is_overridable(self):
        field = ConceptsField(vocabulary="rock-type", help_text="Pick some rock types.")
        assert field.help_text == "Pick some rock types."


class TestConceptsFieldDeconstruct:
    """FS-010 T002 — ``deconstruct()`` strips ``to`` and ``limit_choices_to``
    and records ``vocabulary`` instead, for the same ``Field.clone()`` reason
    documented on :class:`~controlled_vocabularies.fields.ConceptField`.
    ``through`` is never emitted (T003) so there is nothing to strip."""

    def test_deconstruct_omits_to_and_limit_choices_to(self):
        field = ConceptsField(vocabulary="rock-type")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "to" not in kwargs
        assert "limit_choices_to" not in kwargs
        assert "through" not in kwargs

    def test_deconstruct_adds_vocabulary(self):
        field = ConceptsField(vocabulary=["gcmd", "agu-index"])
        _name, _path, _args, kwargs = field.deconstruct()
        assert set(kwargs["vocabulary"]) == {"gcmd", "agu-index"}

    @pytest.mark.parametrize("vocabulary", ["rock-type", ["gcmd", "agu-index"], None])
    def test_round_trip_rebuilds_an_equivalent_field(self, vocabulary):
        """Deconstruct, rebuild from the emitted path and kwargs — exactly what
        ``Field.clone()`` and a replayed migration file both do — for each of
        the three shapes."""
        field = ConceptsField(vocabulary=vocabulary)
        _name, path, args, kwargs = field.deconstruct()
        field_class = import_string(path)
        rebuilt = field_class(*args, **kwargs)
        assert rebuilt.vocabulary == field.vocabulary
        assert rebuilt.get_limit_choices_to() == field.get_limit_choices_to()

    def test_clone_rebuilds_without_error(self):
        field = ConceptsField(vocabulary="rock-type")
        cloned = field.clone()
        assert cloned.vocabulary == ("rock-type",)


class TestConceptsFieldMembershipModel:
    """FS-010 T003 (FR-007, FR-011, US-3, R4, R6) — ``contribute_to_class``
    skips ``ManyToManyField``'s own through generation and substitutes one
    whose foreign key to ``Concept`` is ``PROTECT`` rather than ``CASCADE``,
    following Django's own ``create_many_to_many_intermediary_model`` closely
    otherwise. Against :class:`~tests.testapp.models.Deposit` (one
    ``ConceptsField``) and :class:`~tests.testapp.models.Survey` (two, both
    ``related_name="+"``), never against the generation helper in isolation.
    """

    def test_membership_model_is_named_owner_fieldname(self):
        field = Deposit._meta.get_field("rock_types")
        assert field.remote_field.through._meta.object_name == "Deposit_rock_types"

    def test_membership_models_concept_fk_is_protect(self):
        field = Deposit._meta.get_field("rock_types")
        concept_fk = field.remote_field.through._meta.get_field("concept")
        assert concept_fk.remote_field.on_delete is PROTECT

    def test_membership_models_owner_fk_is_cascade(self):
        field = Deposit._meta.get_field("rock_types")
        owner_fk = field.remote_field.through._meta.get_field("deposit")
        assert owner_fk.remote_field.on_delete is CASCADE

    def test_deconstruct_still_emits_no_through_once_bound(self):
        """Unbound, T002 already proves this by never setting ``through`` at
        all. Bound, ``through`` is real and ``Meta.auto_created`` is what
        keeps ``ManyToManyField.deconstruct()`` from emitting it — this is
        the test that would fail if that attribute were ever dropped."""
        field = Deposit._meta.get_field("rock_types")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "through" not in kwargs

    def test_two_declarations_on_one_model_produce_two_distinct_tables(self):
        primary = Survey._meta.get_field("primary_minerals")
        secondary = Survey._meta.get_field("secondary_minerals")
        assert primary.remote_field.through is not secondary.remote_field.through
        assert primary.remote_field.through._meta.db_table != secondary.remote_field.through._meta.db_table

    def test_two_hidden_related_names_are_rewritten_distinctly(self):
        """Without the hidden ``related_name`` rewrite this task replicates
        before its ``super(ManyToManyField, self).contribute_to_class()``
        call, both fields would keep the literal ``related_name="+"`` — proved
        failing directly below by the reverse-query-name-clash check."""
        primary = Survey._meta.get_field("primary_minerals")
        secondary = Survey._meta.get_field("secondary_minerals")
        assert primary.remote_field.related_name != "+"
        assert secondary.remote_field.related_name != "+"
        assert primary.remote_field.related_name != secondary.remote_field.related_name

    def test_two_declarations_on_one_model_do_not_clash_reverse_accessors(self):
        errors = Survey.check()
        assert not any(error.id in {"fields.E304", "fields.E305"} for error in errors)

    @isolate_apps("tests.testapp")
    def test_declaring_two_concepts_fields_on_one_model_warns_of_nothing(self):
        """ARC-001 (design review) — the MRO skip
        (``super(ManyToManyField, self).contribute_to_class(...)``) must skip
        ``ManyToManyField``'s own through generation, not merely call it and
        then generate again: doing both registers the through model under the
        same name twice and Django warns ``Model ... was already
        registered``, on every consuming declaration."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            class DoubleConceptsField(models.Model):
                a = ConceptsField(vocabulary="mineral", related_name="+")
                b = ConceptsField(vocabulary="mineral", related_name="+")

                class Meta:
                    app_label = "testapp"

        assert not any("was already registered" in str(warning.message) for warning in caught)


class TestConceptsFieldMigrations:
    """FS-010 T003 — ``Deposit`` and ``Survey`` migrate cleanly with the
    generated membership models, and stay ``makemigrations --check`` clean."""

    @pytest.mark.django_db
    def test_models_are_queryable(self):
        assert Deposit.objects.count() == 0
        assert Survey.objects.count() == 0

    @pytest.mark.django_db
    def test_makemigrations_check_is_clean(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)


class TestConceptsFieldConsumingModels:
    """FS-010 T001 (FR-001, US-1 through US-8) — the remaining four consuming
    models: optional with a ``related_name``, both field types on one model,
    two named vocabularies, and no vocabulary named. ``Deposit`` and
    ``Survey`` (T003) round out the six `tasks.md` T001 lists."""

    @pytest.mark.django_db
    def test_all_six_models_are_queryable(self):
        """Proof the extended migration applied — pytest-django builds the
        test database from every installed app's migrations, from zero, for
        the whole session."""
        assert Deposit.objects.count() == 0
        assert Survey.objects.count() == 0
        assert Outcrop.objects.count() == 0
        assert RockSample.objects.count() == 0
        assert FieldNote.objects.count() == 0
        assert Photograph.objects.count() == 0

    @pytest.mark.django_db
    def test_makemigrations_check_is_clean(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)

    @pytest.mark.django_db
    def test_all_six_factories_build_valid_saved_records(self):
        assert DepositFactory().pk is not None
        assert SurveyFactory().pk is not None
        assert OutcropFactory().pk is not None
        assert RockSampleFactory().pk is not None
        assert FieldNoteFactory().pk is not None
        assert PhotographFactory().pk is not None

    @pytest.mark.django_db
    def test_optional_field_with_related_name_reads_back_from_both_sides(self):
        outcrop = OutcropFactory()
        scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=scheme)

        outcrop.minerals.add(concept)

        assert concept in outcrop.minerals.all()
        assert outcrop in concept.outcrops.all()

    @pytest.mark.django_db
    def test_both_field_types_on_one_model_coexist_without_clashing(self):
        """The collision case `plan.md`'s Risks section refuses to assume
        away: a ``ConceptField`` and a ``ConceptsField`` against the same
        vocabulary, declared on the same model, read and write independently."""
        scheme = ConceptSchemeFactory(name="Mineral")
        primary = ConceptFactory(scheme=scheme)
        associated = ConceptFactory(scheme=scheme)
        sample = RockSampleFactory(primary_mineral=primary)

        sample.associated_minerals.add(associated)

        reloaded = RockSample.objects.get(pk=sample.pk)
        assert reloaded.primary_mineral == primary
        assert associated in reloaded.associated_minerals.all()

    def test_field_naming_two_vocabularies_restricts_to_their_union(self):
        field = FieldNote._meta.get_field("keywords")
        assert field.vocabulary == ("rock-type", "mineral")
        assert field.get_limit_choices_to() == Q(scheme__slug__in=("rock-type", "mineral"))

    def test_field_naming_no_vocabulary_sets_no_restriction(self):
        field = Photograph._meta.get_field("keywords")
        assert field.vocabulary == ()
        assert field.get_limit_choices_to() == {}

    @pytest.mark.django_db
    def test_field_naming_no_vocabulary_still_attaches_a_concept_from_any_scheme(self):
        photograph = PhotographFactory()
        scheme = ConceptSchemeFactory(name="Anything")
        concept = ConceptFactory(scheme=scheme)

        photograph.keywords.add(concept)

        assert concept in photograph.keywords.all()

    @pytest.mark.parametrize(
        ("model", "field_name"),
        [
            (Deposit, "rock_types"),
            (Survey, "primary_minerals"),
            (Survey, "secondary_minerals"),
            (Outcrop, "minerals"),
            (RockSample, "associated_minerals"),
            (FieldNote, "keywords"),
            (Photograph, "keywords"),
        ],
    )
    def test_every_concepts_field_has_translatable_help_text_and_a_verbose_name(self, model, field_name):
        """Article XII — ``help_text`` is mandatory and translatable; every
        declaration above also supplies an explicit ``verbose_name``."""
        field = model._meta.get_field(field_name)
        assert isinstance(field.help_text, Promise)
        assert str(field.help_text)
        assert field.verbose_name


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


class TestConceptFieldRoundTrip:
    """T004 (US-1) — end-to-end usage of the field the way a consuming project
    would use it: a concept from the named vocabulary survives a save/reload,
    an optional field with nothing attached validates and saves, and using the
    field this way stays ``makemigrations --check`` clean."""

    @pytest.mark.django_db
    def test_saving_and_reloading_returns_the_same_concept(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = SpecimenFactory(rock_type=concept)

        reloaded = Specimen.objects.get(pk=specimen.pk)

        assert reloaded.rock_type == concept

    @pytest.mark.django_db
    def test_optional_field_with_nothing_attached_validates_and_saves(self):
        sample = Sample(name="Unclassified sample")

        sample.full_clean()
        sample.save()

        assert sample.pk is not None
        assert sample.mineral is None

    @pytest.mark.django_db
    def test_makemigrations_check_stays_clean_after_declaring_and_saving(self):
        """Regression guard for ``deconstruct()`` (T003): using the field
        end-to-end must not surface an undeclared model change beyond what
        Phase F already committed."""
        ConceptFactory()
        SpecimenFactory()

        call_command("makemigrations", "--check", "--dry-run", verbosity=0)


class TestConceptFieldOrdinaryOptions:
    """T004 (US-1) — the field's ordinary ``ForeignKey`` options behave
    exactly as they would on a plain ``ForeignKey``, asserted directly on the
    bound field rather than only through a save/reload round trip."""

    def test_related_name_produces_the_reverse_accessor(self):
        field = Sample._meta.get_field("mineral")
        assert field.remote_field.get_accessor_name() == "samples"

    def test_required_field_is_not_null_or_blank(self):
        field = Specimen._meta.get_field("rock_type")
        assert field.null is False
        assert field.blank is False

    def test_optional_field_is_null_and_blank(self):
        field = Sample._meta.get_field("mineral")
        assert field.null is True
        assert field.blank is True

    def test_verbose_name_and_help_text_are_what_was_declared(self):
        field = Specimen._meta.get_field("rock_type")
        assert field.verbose_name == "rock type"
        assert str(field.help_text) == "The rock type this specimen is classified as."

    def test_the_fks_index_is_present(self):
        field = Specimen._meta.get_field("rock_type")
        assert field.db_index is True


class TestConceptFieldValidation:
    """T005 (US-2) — no new constraint code: ``ForeignKey.validate()`` already
    applies ``limit_choices_to`` before checking existence. What this class
    proves is the behavioural chain T001's ``validate()`` override exists
    for — raise, then *read* ``.messages`` and find the vocabulary named —
    which an unbound field (T001's own tests) cannot reach."""

    @pytest.mark.django_db
    def test_full_clean_rejects_a_concept_from_another_vocabulary(self):
        other_scheme = ConceptSchemeFactory(name="Mineral")
        other_concept = ConceptFactory(scheme=other_scheme)
        specimen = Specimen(name="Wrong vocabulary", rock_type=other_concept)

        with pytest.raises(ValidationError) as excinfo:
            specimen.full_clean()

        assert any("rock-type" in message for message in excinfo.value.messages)

    @pytest.mark.django_db
    def test_full_clean_accepts_a_concept_from_the_correct_vocabulary(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = Specimen(name="Correct vocabulary", rock_type=concept)

        specimen.full_clean()

    @pytest.mark.django_db
    def test_full_clean_accepts_an_optional_field_with_nothing_attached(self):
        sample = Sample(name="Unclassified sample")

        sample.full_clean()

    @pytest.mark.django_db
    def test_the_re_raise_keeps_the_foreign_keys_own_params(self):
        # error_messages is an ordinary field kwarg, and a consumer's message
        # may use any placeholder a plain ForeignKey supplies. The override
        # adds `vocabulary` to those params; it must not replace them, or
        # reading .messages raises KeyError at form-render time.
        field = Specimen._meta.get_field("rock_type")
        original = field.error_messages["invalid"]
        field.error_messages["invalid"] = "%(model)s pk=%(pk)s field=%(field)s in %(vocabulary)s"
        try:
            other_concept = ConceptFactory(scheme=ConceptSchemeFactory(name="Mineral"))
            specimen = Specimen(name="Wrong vocabulary", rock_type=other_concept)

            with pytest.raises(ValidationError) as excinfo:
                specimen.full_clean()

            assert any("rock-type" in message for message in excinfo.value.messages)
        finally:
            field.error_messages["invalid"] = original


class SpecimenForm(forms.ModelForm):
    """Test-only — the plain ``ModelForm`` Django would auto-generate from
    ``Specimen``, used by T006 to prove ``limit_choices_to`` reaches a form's
    field choices and submission validation without this package adding any
    form-layer code of its own."""

    class Meta:
        model = Specimen
        fields = ["name", "rock_type"]


class TestConceptFieldFormChoices:
    """T006 (US-2) — also no new code: ``ForeignKey.formfield()`` passes
    ``limit_choices_to`` through. This class is the proof FR-006 needs."""

    @pytest.mark.django_db
    def test_form_field_offers_only_the_named_vocabularys_concepts(self):
        rock_scheme = ConceptSchemeFactory(name="Rock Type")
        matching_concept = ConceptFactory(scheme=rock_scheme)
        other_scheme = ConceptSchemeFactory(name="Mineral")
        other_concept = ConceptFactory(scheme=other_scheme)

        form = SpecimenForm()
        choices = list(form.fields["rock_type"].queryset)

        assert matching_concept in choices
        assert other_concept not in choices

    @pytest.mark.django_db
    def test_form_submission_with_another_vocabularys_concept_is_rejected(self):
        other_scheme = ConceptSchemeFactory(name="Mineral")
        other_concept = ConceptFactory(scheme=other_scheme)

        form = SpecimenForm(data={"name": "Wrong vocabulary", "rock_type": other_concept.pk})

        assert not form.is_valid()
        assert "rock_type" in form.errors
        assert Specimen.objects.count() == 0


class TestConceptFieldDeleteGuard:
    """T007 (US-3) — no new code: ``on_delete=PROTECT`` (T001) already refuses
    any delete path that would strand a reference. This class is the proof
    FR-007 needs."""

    @pytest.mark.django_db
    def test_deleting_a_referenced_concept_is_refused(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = SpecimenFactory(rock_type=concept)

        with pytest.raises(ProtectedError):
            concept.delete()

        assert Concept.objects.filter(pk=concept.pk).exists()
        assert Specimen.objects.filter(pk=specimen.pk).exists()

    @pytest.mark.django_db
    def test_bulk_queryset_delete_of_a_referenced_concept_is_refused(self):
        """The protection lives in the relation rather than in model
        validation, so a bulk ``QuerySet.delete()`` is refused exactly like a
        single-instance delete."""
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = SpecimenFactory(rock_type=concept)

        with pytest.raises(ProtectedError):
            Concept.objects.filter(pk=concept.pk).delete()

        assert Concept.objects.filter(pk=concept.pk).exists()
        assert Specimen.objects.filter(pk=specimen.pk).exists()

    @pytest.mark.django_db
    def test_deleting_the_scheme_holding_a_referenced_concept_is_refused(self):
        """``Concept.scheme`` cascades, so deleting the scheme tries to
        cascade-delete the concept — and meets the same ``PROTECT`` on the
        way down. Nothing in the scheme is removed."""
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = SpecimenFactory(rock_type=concept)

        with pytest.raises(ProtectedError):
            scheme.delete()

        assert ConceptScheme.objects.filter(pk=scheme.pk).exists()
        assert Concept.objects.filter(pk=concept.pk).exists()
        assert Specimen.objects.filter(pk=specimen.pk).exists()

    @pytest.mark.django_db
    def test_an_unreferenced_concept_deletes_normally(self):
        concept = ConceptFactory()

        concept.delete()

        assert not Concept.objects.filter(pk=concept.pk).exists()

    @pytest.mark.django_db
    def test_deleting_the_consuming_record_leaves_the_concept_in_place(self):
        concept = ConceptFactory()
        specimen = SpecimenFactory(rock_type=concept)

        specimen.delete()

        assert not Specimen.objects.filter(pk=specimen.pk).exists()
        assert Concept.objects.filter(pk=concept.pk).exists()


class TestConceptFieldLabelAndUriAccessors:
    """T011 (US-5) — FR-008/FR-009: ``contribute_to_class()`` gives the
    consuming model ``get_<field>_label()`` and ``get_<field>_uri()``, named
    the way Django's own ``get_FOO_display()`` is. The label accessor
    delegates to T010's ``Concept.display_label()``; the URI accessor returns
    the concept's own ``uri`` unchanged. Both return ``None`` rather than
    raising when nothing is attached, and the ``setattr`` is guarded so a
    model that already defines one of these names keeps its own."""

    @pytest.mark.django_db
    def test_label_accessor_returns_the_active_languages_preferred_label(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme, label="Basalt")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Basalt (de)")
        specimen = SpecimenFactory(rock_type=concept)

        with translation.override("de"):
            assert specimen.get_rock_type_label() == "Basalt (de)"

    @pytest.mark.django_db
    def test_label_accessor_falls_back_to_the_vocabulary_default(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme, label="Basalt")
        specimen = SpecimenFactory(rock_type=concept)

        with translation.override("fr"):
            assert specimen.get_rock_type_label() == "Basalt"

    @pytest.mark.django_db
    def test_uri_accessor_returns_the_concepts_own_uri_unchanged(self):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        specimen = SpecimenFactory(rock_type=concept)

        assert specimen.get_rock_type_uri() == concept.uri

    @pytest.mark.django_db
    def test_both_accessors_return_none_when_nothing_is_attached(self):
        sample = SampleFactory()

        assert sample.get_mineral_label() is None
        assert sample.get_mineral_uri() is None

    def test_both_accessors_return_none_on_a_required_field_with_nothing_attached(self):
        # A required field's forward descriptor raises RelatedObjectDoesNotExist
        # rather than returning None, so the nullable case above does not cover
        # this one. Both accessors promise None, never a raise.
        specimen = Specimen(name="not yet classified")

        assert specimen.get_rock_type_label() is None
        assert specimen.get_rock_type_uri() is None

    @pytest.mark.django_db
    def test_a_models_own_definition_survives_the_contribution_guard(self):
        artifact = ArtifactFactory()

        assert artifact.get_mineral_label() == "this artifact's own label, not the field's"
