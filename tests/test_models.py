"""Tests for ``controlled_vocabularies.models``.

One module mirrors the single ``models.py``. The per-story suites — US-1 (the
vocabulary scheme), US-2 (the concept), US-3 (stable URI identity), and US-5
(translatable, self-documenting field metadata and deliberate indexing) — are
folded here and grouped by subject into classes:

- ``TestConceptScheme`` — create, rename, slug derivation and app-wide uniqueness, URI, delete.
- ``TestConcept`` — add, relabel, per-scheme slug uniqueness, cascade delete, URI.
- ``TestConceptIdentity`` — the URI identity guarantees and ``get_by_uri`` round-trips.
- ``TestFieldMetadata`` — every editable field carries a lazy ``verbose_name`` + non-empty ``help_text``.
- ``TestValidationMessages`` — validation messages are lazily translatable, with named placeholders.
- ``TestIndexing`` — indexing and the composite uniqueness constraint are deliberate.
"""

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Model, UniqueConstraint
from django.utils.functional import Promise

from controlled_vocabularies import conf
from controlled_vocabularies.models import (
    Collection,
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptScheme,
    validate_permanent_uri,
)
from tests.factories import ConceptSchemeFactory


class TestConceptScheme:
    """US-1 — Define a vocabulary. FR-001 (create/rename/delete), FR-002 (slug
    derived, synced, unique app-wide), FR-005 (scheme URI), FR-007 (non-ASCII
    slugs, collisions refused)."""

    @pytest.mark.django_db
    def test_create_derives_slug_from_name(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        assert scheme.slug == "geothermics"

    @pytest.mark.django_db
    def test_create_accepts_optional_description(self):
        scheme = ConceptScheme.objects.create(name="Geothermics", description="Study of Earth's heat.")
        fetched = ConceptScheme.objects.get(pk=scheme.pk)
        assert fetched.description == "Study of Earth's heat."

    @pytest.mark.django_db
    def test_rename_updates_slug(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        scheme.name = "Geothermal Science"
        scheme.save()
        assert scheme.slug == "geothermal-science"

    @pytest.mark.django_db
    def test_empty_name_is_rejected(self):
        with pytest.raises(ValidationError):
            ConceptScheme.objects.create(name="")

    @pytest.mark.django_db
    def test_whitespace_only_name_is_rejected(self):
        with pytest.raises(ValidationError):
            ConceptScheme.objects.create(name="   ")

    @pytest.mark.django_db
    def test_non_latin_name_yields_nonempty_unicode_slug(self):
        scheme = ConceptScheme.objects.create(name="Wärmefluss")
        assert scheme.slug
        assert scheme.slug == "wärmefluss"

    @pytest.mark.django_db
    def test_colliding_slug_is_refused_not_suffixed(self):
        ConceptScheme.objects.create(name="Geothermics")
        with pytest.raises(ValidationError):
            # A different name that slugifies to the same value must be refused,
            # never silently auto-suffixed to "geothermics-2".
            ConceptScheme.objects.create(name="GEOTHERMICS")
        assert ConceptScheme.objects.filter(slug="geothermics").count() == 1
        assert not ConceptScheme.objects.filter(slug="geothermics-2").exists()

    @pytest.mark.django_db
    def test_uri_composes_from_base_and_slug(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        assert scheme.uri == "https://example.org/vocabularies/geothermics"

    @pytest.mark.django_db
    def test_uri_reflects_rename(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        scheme.name = "Geothermal Science"
        scheme.save()
        assert scheme.uri == "https://example.org/vocabularies/geothermal-science"

    @pytest.mark.django_db
    def test_str_is_the_name(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        assert str(scheme) == "Geothermics"

    @pytest.mark.django_db
    def test_delete_removes_scheme(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        pk = scheme.pk
        scheme.delete()
        assert not ConceptScheme.objects.filter(pk=pk).exists()


class TestConcept:
    """US-2 — Populate a vocabulary with concepts. FR-003 (add/relabel/delete),
    FR-004 (slug derived from label, synced, unique within a scheme not app-wide),
    FR-006 (concept URI composed from the scheme URI and slug), FR-007 (empty
    labels and within-scheme collisions refused), and cascade delete."""

    @pytest.mark.django_db
    def test_add_derives_slug_from_label(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert concept.slug == "heat-flow"

    @pytest.mark.django_db
    def test_get_concept_by_scheme_and_slug(self, scheme):
        # FR-006's second retrieval mode: a concept is retrievable by its
        # vocabulary-plus-slug pair, as a first-class query, not only via get_by_uri.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert Concept.objects.get(scheme=scheme, slug="heat-flow") == concept

    @pytest.mark.django_db
    def test_list_concepts_of_a_scheme(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        Concept.objects.create(scheme=scheme, label="Gradient")
        assert scheme.concepts.count() == 2

    @pytest.mark.django_db
    def test_relabel_updates_slug(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.slug == "surface-heat-flow"

    @pytest.mark.django_db
    def test_empty_label_is_rejected(self, scheme):
        with pytest.raises(ValidationError):
            Concept.objects.create(scheme=scheme, label="")

    @pytest.mark.django_db
    def test_whitespace_only_label_is_rejected(self, scheme):
        with pytest.raises(ValidationError):
            Concept.objects.create(scheme=scheme, label="   ")

    @pytest.mark.django_db
    def test_non_latin_label_yields_nonempty_unicode_slug(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Wärmefluss")
        assert concept.slug
        assert concept.slug == "wärmefluss"

    @pytest.mark.django_db
    def test_colliding_slug_within_scheme_is_refused_not_suffixed(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(ValidationError):
            # A different label that slugifies to the same value within the same
            # scheme must be refused, never silently auto-suffixed to "heat-flow-2".
            Concept.objects.create(scheme=scheme, label="HEAT FLOW")
        assert scheme.concepts.filter(slug="heat-flow").count() == 1
        assert not scheme.concepts.filter(slug="heat-flow-2").exists()

    @pytest.mark.django_db
    def test_same_slug_allowed_across_different_schemes(self):
        scheme_a = ConceptSchemeFactory()
        scheme_b = ConceptSchemeFactory()
        concept_a = Concept.objects.create(scheme=scheme_a, label="Heat Flow")
        concept_b = Concept.objects.create(scheme=scheme_b, label="Heat Flow")
        assert concept_a.slug == concept_b.slug == "heat-flow"
        assert Concept.objects.filter(slug="heat-flow").count() == 2

    @pytest.mark.django_db
    def test_uri_composes_from_scheme_uri_and_slug(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert concept.uri == f"{scheme.uri}/heat-flow"
        assert concept.uri == "https://example.org/vocabularies/geothermics/heat-flow"

    @pytest.mark.django_db
    def test_uri_reflects_relabel(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.uri == "https://example.org/vocabularies/geothermics/surface-heat-flow"

    @pytest.mark.django_db
    def test_str_is_the_label(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert str(concept) == "Heat Flow"

    @pytest.mark.django_db
    def test_delete_removes_concept(self, concept):
        pk = concept.pk
        concept.delete()
        assert not Concept.objects.filter(pk=pk).exists()

    @pytest.mark.django_db
    def test_deleting_scheme_cascades_to_its_concepts(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        Concept.objects.create(scheme=scheme, label="Gradient")
        scheme.delete()
        assert Concept.objects.count() == 0


class TestConceptIdentity:
    """US-3 — Every concept carries a stable identifier. The URI composes from the
    base address, scheme slug and concept slug (FR-005/FR-006); ``get_by_uri``
    round-trips a URI back to exactly its concept (FR-006); no two concepts across
    schemes compose the same URI (SC-002); non-Latin labels stay resolvable; and a
    rename recomposes the URI so the new one resolves. An unmatched URI raises
    ``Concept.DoesNotExist``."""

    @pytest.mark.django_db
    def test_full_uri_is_base_plus_scheme_slug_plus_concept_slug(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert concept.uri == f"{conf.get_base_uri()}/{scheme.slug}/{concept.slug}"
        assert concept.uri == "https://example.org/vocabularies/geothermics/heat-flow"

    @pytest.mark.django_db
    def test_get_by_uri_returns_exactly_that_concept(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        resolved = Concept.objects.get_by_uri(concept.uri)
        assert resolved == concept
        assert resolved.pk == concept.pk

    @pytest.mark.django_db
    def test_no_two_concepts_across_schemes_share_a_uri(self):
        scheme_a = ConceptScheme.objects.create(name="Geothermics")
        scheme_b = ConceptScheme.objects.create(name="Hydrology")
        concept_a = Concept.objects.create(scheme=scheme_a, label="Heat Flow")
        concept_b = Concept.objects.create(scheme=scheme_b, label="Heat Flow")
        # Same concept slug, but the scheme slug disambiguates: distinct URIs, and each
        # resolves back to its own concept.
        assert concept_a.slug == concept_b.slug
        assert concept_a.uri != concept_b.uri
        assert Concept.objects.get_by_uri(concept_a.uri) == concept_a
        assert Concept.objects.get_by_uri(concept_b.uri) == concept_b

    @pytest.mark.django_db
    def test_non_latin_label_yields_resolvable_uri(self):
        scheme = ConceptScheme.objects.create(name="Geothermik")
        concept = Concept.objects.create(scheme=scheme, label="Wärmefluss")
        assert concept.uri == f"{conf.get_base_uri()}/geothermik/wärmefluss"
        assert Concept.objects.get_by_uri(concept.uri) == concept

    @pytest.mark.django_db
    def test_renaming_scheme_recomposes_uri_and_still_resolves(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        scheme.name = "Geothermal Science"
        scheme.save()
        concept.refresh_from_db()
        assert concept.uri == "https://example.org/vocabularies/geothermal-science/heat-flow"
        assert Concept.objects.get_by_uri(concept.uri) == concept

    @pytest.mark.django_db
    def test_renaming_label_recomposes_uri_and_still_resolves(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.uri == "https://example.org/vocabularies/geothermics/surface-heat-flow"
        assert Concept.objects.get_by_uri(concept.uri) == concept

    @pytest.mark.django_db
    def test_get_by_uri_unknown_uri_raises_does_not_exist(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(f"{conf.get_base_uri()}/geothermics/no-such-concept")

    @pytest.mark.django_db
    def test_get_by_uri_requires_the_configured_base(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        # A bare relative path (no base) must not resolve: get_by_uri means "by URI",
        # so a string outside the configured base is not an identity.
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(f"{scheme.slug}/{concept.slug}")


class TestPermanentUri:
    """US-1 — a record keeps the identifier it arrived with (FR-001/FR-002/FR-003/
    FR-004/FR-006/FR-013). An externally assigned ``permanent_uri`` is read back
    verbatim from ``uri``, survives a rename and a configured-base-address change,
    is never derived from another record's, and is refused up front when
    malformed, unsafe, too long, or already held by a record of another model."""

    @pytest.mark.django_db
    def test_permanent_uri_reads_back_verbatim_from_uri(self, scheme):
        concept = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        assert concept.uri == "http://vocabs.example.org/rock/granite"
        assert concept.has_permanent_uri is True

    @pytest.mark.django_db
    def test_permanent_uri_survives_a_rename(self, scheme):
        concept = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        concept.label = "Granite (coarse-grained)"
        concept.save()
        assert concept.uri == "http://vocabs.example.org/rock/granite"

    @pytest.mark.django_db
    def test_permanent_uri_survives_a_base_address_change(self, scheme, settings):
        concept = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        settings.CONTROLLED_VOCABULARIES_BASE_URI = "https://elsewhere.example.org/vocab"
        assert concept.uri == "http://vocabs.example.org/rock/granite"

    @pytest.mark.django_db
    def test_scheme_and_collection_keep_their_own_permanent_uri(self):
        scheme = ConceptScheme.objects.create(name="Rocks", permanent_uri="http://vocabs.example.org/rocks")
        collection = Collection.objects.create(
            scheme=scheme, name="Igneous", permanent_uri="http://vocabs.example.org/rocks/igneous"
        )
        assert scheme.uri == "http://vocabs.example.org/rocks"
        assert scheme.has_permanent_uri is True
        assert collection.uri == "http://vocabs.example.org/rocks/igneous"
        assert collection.has_permanent_uri is True

    @pytest.mark.django_db
    def test_concepts_permanent_uri_is_not_derived_from_its_schemes(self):
        scheme = ConceptScheme.objects.create(name="Rocks", permanent_uri="http://vocabs.example.org/rocks")
        concept = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        assert concept.uri == "http://vocabs.example.org/rock/granite"
        assert concept.uri != scheme.uri

    @pytest.mark.django_db
    def test_has_permanent_uri_false_while_provisional(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Basalt")
        assert concept.permanent_uri is None
        assert concept.has_permanent_uri is False
        assert concept.uri == f"{conf.get_base_uri()}/{scheme.slug}/{concept.slug}"

    @pytest.mark.parametrize(
        "value",
        [
            "not-absolute",
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "data:text/html,x",
            "vbscript:msgbox(1)",
        ],
    )
    def test_refuses_non_absolute_and_script_bearing_schemes(self, value):
        with pytest.raises(ValidationError):
            validate_permanent_uri(value)

    def test_refuses_overlong_identifier(self):
        with pytest.raises(ValidationError):
            validate_permanent_uri("http://example.org/" + "x" * 500)

    def test_accepts_urn_identifier(self):
        validate_permanent_uri("urn:uuid:9f6c1e2a-1234-4a12-9abc-1234567890ab")

    @pytest.mark.django_db
    def test_bare_create_with_bad_permanent_uri_raises_and_does_not_store(self, scheme):
        with pytest.raises(ValidationError):
            Concept.objects.create(scheme=scheme, label="Granite", permanent_uri="not-absolute")
        assert not Concept.objects.filter(label="Granite").exists()

    @pytest.mark.django_db
    def test_concept_and_collection_cannot_share_a_permanent_uri(self, scheme):
        Concept.objects.create(scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/shared")
        with pytest.raises(ValidationError):
            Collection.objects.create(scheme=scheme, name="Igneous", permanent_uri="http://vocabs.example.org/shared")


def _create_with_permanent_uri(model: type[Model], scheme: ConceptScheme, uri: str):
    """Create a saved record of ``model`` carrying ``uri`` as its ``permanent_uri``."""
    if model is ConceptScheme:
        return ConceptScheme.objects.create(name=f"External scheme {uri}", permanent_uri=uri)
    if model is Concept:
        return Concept.objects.create(scheme=scheme, label=f"External concept {uri}", permanent_uri=uri)
    return Collection.objects.create(scheme=scheme, name=f"External collection {uri}", permanent_uri=uri)


def _create_without_permanent_uri(model: type[Model], scheme: ConceptScheme):
    """Create a saved, provisional (no ``permanent_uri``) record of ``model``."""
    if model is ConceptScheme:
        return ConceptScheme.objects.create(name="Provisional scheme")
    if model is Concept:
        return Concept.objects.create(scheme=scheme, label="Provisional concept")
    return Collection.objects.create(scheme=scheme, name="Provisional collection")


class TestPermanentUriIsFixed:
    """US-1 — a stored permanent URI can never be rewritten or cleared (FR-002,
    FR-013). Fixedness moves one way only: a record loaded from the database
    refuses a save that changes or clears its stored ``permanent_uri``, the
    refusal is a translatable ``ValidationError`` on the ``permanent_uri`` key,
    and re-saving with the identifier unchanged still succeeds. Fixedness starts
    at the save that first stores an identifier, and a deferred load is no way
    around it. Only a record with nothing stored is unconstrained, so setting an
    identifier for the first time (the path R4's publish action will use) is
    allowed."""

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_loaded_record_refuses_a_save_that_changes_the_stored_uri(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        reloaded = model.objects.get(pk=record.pk)
        reloaded.permanent_uri = "http://vocabs.example.org/rewritten"
        with pytest.raises(ValidationError) as excinfo:
            reloaded.save()
        err = _inner_error(excinfo.value, "permanent_uri")
        assert isinstance(err.message, Promise), "rewrite-refusal message is not lazily translatable"
        assert "%(uri)s" in str(err.message), "rewrite-refusal msgid lacks a named %(uri)s placeholder"
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_loaded_record_refuses_a_save_that_clears_the_stored_uri(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        reloaded = model.objects.get(pk=record.pk)
        reloaded.permanent_uri = None
        with pytest.raises(ValidationError) as excinfo:
            reloaded.save()
        err = _inner_error(excinfo.value, "permanent_uri")
        assert isinstance(err.message, Promise), "clear-refusal message is not lazily translatable"
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_full_clean_also_refuses_a_rewrite(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        reloaded = model.objects.get(pk=record.pk)
        reloaded.permanent_uri = "http://vocabs.example.org/rewritten"
        with pytest.raises(ValidationError):
            reloaded.full_clean()

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_loaded_record_may_be_resaved_with_the_identifier_unchanged(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        reloaded = model.objects.get(pk=record.pk)
        reloaded.save()
        reloaded.refresh_from_db()
        assert reloaded.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_record_created_with_an_identifier_keeps_it(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_record_created_without_an_identifier_may_have_one_set_once(self, model, scheme):
        record = _create_without_permanent_uri(model, scheme)
        assert record.permanent_uri is None
        record.permanent_uri = "http://vocabs.example.org/published"
        record.save()
        assert record.permanent_uri == "http://vocabs.example.org/published"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_a_deferred_load_still_refuses_a_rewrite(self, model, scheme):
        """`.only()`/`.defer()` is an ordinary query idiom, not an escape hatch.

        The instance carries no snapshot because the column was never fetched,
        so the stored identifier is read back before the save is allowed
        through.
        """
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        deferred = model.objects.only("id").get(pk=record.pk)
        deferred.permanent_uri = "http://vocabs.example.org/rewritten"
        with pytest.raises(ValidationError):
            deferred.save()
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_a_deferred_load_still_refuses_a_clear(self, model, scheme):
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        deferred = model.objects.only("id").get(pk=record.pk)
        deferred.permanent_uri = None
        with pytest.raises(ValidationError):
            deferred.save()
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_a_deferred_load_that_leaves_the_identifier_alone_never_fetches_it(self, model, scheme):
        """The read-back is paid for only when the deferred column is assigned.

        A record loaded without ``permanent_uri`` and saved untouched must not
        fetch it, or every deferred save in the app pays for this guard. The
        column staying deferred afterwards is the evidence it was never read.
        """
        record = _create_with_permanent_uri(model, scheme, "http://vocabs.example.org/original")
        deferred = model.objects.only("id").get(pk=record.pk)
        deferred.save()
        assert "permanent_uri" in deferred.get_deferred_fields()
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/original"

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    @pytest.mark.django_db
    def test_a_provisional_record_may_be_given_an_identifier_only_once(self, model, scheme):
        """Fixedness starts at the save that stores the identifier, not at the
        next load — otherwise the instance R4's publish action holds could
        publish the same record twice under different identifiers."""
        record = _create_without_permanent_uri(model, scheme)
        record.permanent_uri = "http://vocabs.example.org/published"
        record.save()
        record.permanent_uri = "http://vocabs.example.org/published-again"
        with pytest.raises(ValidationError):
            record.save()
        record.refresh_from_db()
        assert record.permanent_uri == "http://vocabs.example.org/published"


class TestGetByUri:
    """US-2 — a record is found by its identifier wherever it points (FR-007).
    ``get_by_uri`` tries an exact match on the stored ``permanent_uri`` first,
    falling back to the model's base-relative parse (R1's behaviour, unchanged)
    for a provisional identifier, and raises the model's ``DoesNotExist`` when
    neither resolves. ``ConceptScheme`` and ``Collection`` gain the method for
    the first time; ``Concept.objects.get_by_uri`` keeps its existing name and
    exact local behaviour (FR-014)."""

    @pytest.mark.django_db
    def test_concept_resolves_by_external_permanent_uri(self, scheme):
        concept = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        assert Concept.objects.get_by_uri("http://vocabs.example.org/rock/granite") == concept

    @pytest.mark.django_db
    def test_concept_resolves_by_its_own_local_identifier(self, scheme):
        # FR-014: unchanged from R1 — a locally authored concept still resolves
        # by the identifier composed from the configured base and its slugs.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert Concept.objects.get_by_uri(concept.uri) == concept

    @pytest.mark.django_db
    def test_concept_unheld_identifier_raises_does_not_exist(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri("http://vocabs.example.org/nothing")
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(f"{conf.get_base_uri()}/{scheme.slug}/no-such-concept")

    @pytest.mark.django_db
    def test_imported_and_local_concept_do_not_answer_to_each_others_identifier(self, scheme):
        imported = Concept.objects.create(
            scheme=scheme, label="Granite", permanent_uri="http://vocabs.example.org/rock/granite"
        )
        local = Concept.objects.create(scheme=scheme, label="Basalt")
        # Each is found by its own identifier — the imported concept's external
        # permanent_uri, the local concept's composed base-relative one — and not
        # by an identifier held by neither.
        assert Concept.objects.get_by_uri(imported.uri) == imported
        assert Concept.objects.get_by_uri(local.uri) == local
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri("http://vocabs.example.org/rock/nothing-here")

    @pytest.mark.django_db
    def test_scheme_resolves_by_external_permanent_uri(self):
        scheme = ConceptScheme.objects.create(name="Rocks", permanent_uri="http://vocabs.example.org/rocks")
        assert ConceptScheme.objects.get_by_uri("http://vocabs.example.org/rocks") == scheme

    @pytest.mark.django_db
    def test_scheme_resolves_by_its_own_local_identifier(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        assert ConceptScheme.objects.get_by_uri(scheme.uri) == scheme

    @pytest.mark.django_db
    def test_scheme_unheld_identifier_raises_does_not_exist(self):
        ConceptScheme.objects.create(name="Geothermics")
        with pytest.raises(ConceptScheme.DoesNotExist):
            ConceptScheme.objects.get_by_uri("http://vocabs.example.org/nothing")
        with pytest.raises(ConceptScheme.DoesNotExist):
            ConceptScheme.objects.get_by_uri(f"{conf.get_base_uri()}/no-such-scheme")

    @pytest.mark.django_db
    def test_scheme_does_not_resolve_a_concepts_identifier(self, scheme):
        # A concept's local identifier has two path segments below the base; a
        # scheme's has one — the scheme parse must not mistake one for the other.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(ConceptScheme.DoesNotExist):
            ConceptScheme.objects.get_by_uri(concept.uri)

    @pytest.mark.django_db
    def test_concept_does_not_resolve_a_schemes_identifier(self, scheme):
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(scheme.uri)

    @pytest.mark.django_db
    def test_collection_resolves_by_external_permanent_uri(self, scheme):
        collection = Collection.objects.create(
            scheme=scheme, name="Igneous", permanent_uri="http://vocabs.example.org/rocks/igneous"
        )
        assert Collection.objects.get_by_uri("http://vocabs.example.org/rocks/igneous") == collection

    @pytest.mark.django_db
    def test_collection_resolves_by_its_own_local_identifier(self, scheme):
        collection = Collection.objects.create(scheme=scheme, name="Igneous")
        assert Collection.objects.get_by_uri(collection.uri) == collection

    @pytest.mark.django_db
    def test_collection_unheld_identifier_raises_does_not_exist(self, scheme):
        Collection.objects.create(scheme=scheme, name="Igneous")
        with pytest.raises(Collection.DoesNotExist):
            Collection.objects.get_by_uri("http://vocabs.example.org/nothing")

    @pytest.mark.django_db
    def test_collection_does_not_resolve_a_concepts_identifier(self, scheme):
        # A collection's local identifier carries a literal "collection" segment
        # that a concept's never does — the collection parse must require it.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(Collection.DoesNotExist):
            Collection.objects.get_by_uri(concept.uri)

    @pytest.mark.django_db
    def test_concept_does_not_resolve_a_collections_identifier(self, scheme):
        collection = Collection.objects.create(scheme=scheme, name="Igneous")
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(collection.uri)


class TestProvisionalUri:
    """US-3 — a record authored here shows the identifier it will publish under
    (FR-005). A record with no ``permanent_uri`` reports the value R1's
    composition produces; that value follows a rename and a change to the
    configured base address; ``permanent_uri`` stays ``None`` and
    ``has_permanent_uri`` is ``False`` throughout."""

    @pytest.mark.django_db
    def test_scheme_with_no_permanent_uri_reports_the_composed_value(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        assert scheme.permanent_uri is None
        assert scheme.has_permanent_uri is False
        assert scheme.uri == f"{conf.get_base_uri()}/{scheme.slug}"

    @pytest.mark.django_db
    def test_scheme_provisional_uri_follows_a_rename(self):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        scheme.name = "Geothermal Science"
        scheme.save()
        assert scheme.uri == f"{conf.get_base_uri()}/geothermal-science"

    @pytest.mark.django_db
    def test_scheme_provisional_uri_follows_a_base_address_change(self, settings):
        scheme = ConceptScheme.objects.create(name="Geothermics")
        settings.CONTROLLED_VOCABULARIES_BASE_URI = "https://elsewhere.example.org/vocab"
        assert scheme.uri == "https://elsewhere.example.org/vocab/geothermics"

    @pytest.mark.django_db
    def test_concept_with_no_permanent_uri_reports_the_composed_value(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert concept.permanent_uri is None
        assert concept.has_permanent_uri is False
        assert concept.uri == f"{conf.get_base_uri()}/{scheme.slug}/{concept.slug}"

    @pytest.mark.django_db
    def test_concept_provisional_uri_follows_a_rename(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.uri == f"{conf.get_base_uri()}/{scheme.slug}/surface-heat-flow"

    @pytest.mark.django_db
    def test_concept_provisional_uri_follows_a_base_address_change(self, scheme, settings):
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        settings.CONTROLLED_VOCABULARIES_BASE_URI = "https://elsewhere.example.org/vocab"
        assert concept.uri == f"https://elsewhere.example.org/vocab/{scheme.slug}/{concept.slug}"

    @pytest.mark.django_db
    def test_collection_with_no_permanent_uri_reports_the_composed_value(self, scheme):
        collection = Collection.objects.create(scheme=scheme, name="Igneous")
        assert collection.permanent_uri is None
        assert collection.has_permanent_uri is False
        assert collection.uri == f"{conf.get_base_uri()}/{scheme.slug}/collection/{collection.slug}"

    @pytest.mark.django_db
    def test_collection_provisional_uri_follows_a_rename(self, scheme):
        collection = Collection.objects.create(scheme=scheme, name="Igneous")
        collection.name = "Igneous Rocks"
        collection.save()
        assert collection.uri == f"{conf.get_base_uri()}/{scheme.slug}/collection/igneous-rocks"

    @pytest.mark.django_db
    def test_collection_provisional_uri_follows_a_base_address_change(self, scheme, settings):
        collection = Collection.objects.create(scheme=scheme, name="Igneous")
        settings.CONTROLLED_VOCABULARIES_BASE_URI = "https://elsewhere.example.org/vocab"
        assert collection.uri == f"https://elsewhere.example.org/vocab/{scheme.slug}/collection/{collection.slug}"


def _editable_fields(model: type[Model]):
    """The model's own, user-editable, concrete fields (excludes the auto pk
    and reverse relations) — every one must meet the metadata standard."""
    return [
        field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and getattr(field, "editable", False) and not field.auto_created
    ]


class TestFieldMetadata:
    """US-5 / FR-009 — every editable field carries a lazy ``verbose_name`` and a
    non-empty ``help_text``, and the model Meta names are lazy too. This walks
    ``_meta`` rather than exercising a UI (SC-006), so a future field is held to the
    same standard automatically."""

    @pytest.mark.parametrize("model", [ConceptScheme, Concept])
    def test_every_editable_field_has_metadata(self, model):
        fields = _editable_fields(model)
        assert fields, f"{model.__name__} exposes no editable fields to check"
        for field in fields:
            # help_text: present, non-empty, and a lazy translation proxy.
            assert field.help_text, f"{model.__name__}.{field.name} has no help_text"
            assert isinstance(field.help_text, Promise), (
                f"{model.__name__}.{field.name}.help_text is not lazily translatable"
            )
            # verbose_name: a lazy translation proxy (Django defaults it to a plain
            # str derived from the attribute name, which is not translatable).
            assert isinstance(field.verbose_name, Promise), (
                f"{model.__name__}.{field.name}.verbose_name is not lazily translatable"
            )

    @pytest.mark.parametrize("model", [ConceptScheme, Concept])
    def test_meta_verbose_names_are_lazy(self, model):
        assert isinstance(model._meta.verbose_name, Promise), (
            f"{model.__name__} Meta.verbose_name is not lazily translatable"
        )
        assert isinstance(model._meta.verbose_name_plural, Promise), (
            f"{model.__name__} Meta.verbose_name_plural is not lazily translatable"
        )


def _inner_error(exc: ValidationError, field: str) -> ValidationError:
    """The single field-scoped ValidationError carrying the lazy message."""
    return exc.error_dict[field][0]


class TestValidationMessages:
    """US-5 / FR-010 — all user-facing validation messages are lazily translatable,
    and collision messages carry the offending value through a *named* placeholder
    rather than baked into the translatable string."""

    @pytest.mark.django_db
    def test_empty_name_message_is_translatable(self):
        with pytest.raises(ValidationError) as excinfo:
            ConceptScheme.objects.create(name="   ")
        err = _inner_error(excinfo.value, "name")
        assert isinstance(err.message, Promise), "empty-name message is not lazily translatable"

    @pytest.mark.django_db
    def test_empty_label_message_is_translatable(self, scheme):
        with pytest.raises(ValidationError) as excinfo:
            Concept.objects.create(scheme=scheme, label="   ")
        err = _inner_error(excinfo.value, "label")
        assert isinstance(err.message, Promise), "empty-label message is not lazily translatable"

    @pytest.mark.django_db
    def test_scheme_slug_collision_message_uses_named_placeholder(self):
        ConceptScheme.objects.create(name="Geothermics")
        with pytest.raises(ValidationError) as excinfo:
            ConceptScheme.objects.create(name="GEOTHERMICS")
        err = _inner_error(excinfo.value, "slug")
        # The translatable msgid is lazy and carries a *named* placeholder — the slug
        # value is supplied via params, never baked into the translatable string.
        assert isinstance(err.message, Promise), "collision message is not lazily translatable"
        assert "%(slug)s" in str(err.message), "collision msgid lacks a named %(slug)s placeholder"
        assert err.params == {"slug": "geothermics"}
        # ...and it still renders with the real value substituted in.
        assert "geothermics" in excinfo.value.messages[0]

    @pytest.mark.django_db
    def test_concept_slug_collision_message_uses_named_placeholder(self, scheme):
        Concept.objects.create(scheme=scheme, label="Heat Flow")
        with pytest.raises(ValidationError) as excinfo:
            Concept.objects.create(scheme=scheme, label="HEAT FLOW")
        err = _inner_error(excinfo.value, "slug")
        assert isinstance(err.message, Promise), "collision message is not lazily translatable"
        assert "%(slug)s" in str(err.message), "collision msgid lacks a named %(slug)s placeholder"
        assert err.params == {"slug": "heat-flow"}
        assert "heat-flow" in excinfo.value.messages[0]


class TestIndexing:
    """US-5 / FR-011 — indexing is deliberate: the scheme slug is uniquely indexed,
    the concept's scheme FK is indexed, and per-scheme slug uniqueness is a named
    composite constraint."""

    def test_scheme_slug_is_uniquely_indexed(self):
        assert ConceptScheme._meta.get_field("slug").unique is True

    def test_concept_scheme_fk_is_indexed(self):
        assert Concept._meta.get_field("scheme").db_index is True

    def test_concept_has_composite_unique_constraint(self):
        constraint = next(
            (
                c
                for c in Concept._meta.constraints
                if isinstance(c, UniqueConstraint) and c.name == "unique_concept_slug_per_scheme"
            ),
            None,
        )
        assert constraint is not None, "missing (scheme, slug) UniqueConstraint"
        assert tuple(constraint.fields) == ("scheme", "slug")


class TestConceptSchemeDefaultLanguage:
    """US-1 / FR-011 — a vocabulary's effective default language falls back to the
    application's configured default when no per-vocabulary override is set (the
    override itself is US-4 and is deliberately absent from this slice)."""

    def test_effective_default_language_is_the_app_default(self):
        # No override in this slice: the effective default is settings.LANGUAGE_CODE.
        assert ConceptScheme().effective_default_language == settings.LANGUAGE_CODE


class TestConceptPreferredLabels:
    """US-1 — Preferred labels in several languages, identity preserved. FR-001 (one
    preferred label per language), FR-002 (a default-language preferred label is
    required and anchors identity), FR-003 (slug derives from the default-language
    label), FR-004/SC-003 (a non-default-language label never disturbs slug or URI),
    FR-007 (read a preferred label back by language)."""

    @pytest.mark.django_db
    def test_preferred_labels_readable_in_each_language(self, scheme):
        # The default-language preferred label lives on Concept.label; other
        # languages are ConceptLabel PREFERRED rows. Both read back via preferred_label.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        assert concept.preferred_label("en") == "Heat flow"
        assert concept.preferred_label("de") == "Wärmefluss"
        # language=None means the scheme's effective default language.
        assert concept.preferred_label() == "Heat flow"

    @pytest.mark.django_db
    def test_preferred_label_absent_language_returns_none(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        assert concept.preferred_label("fr") is None

    @pytest.mark.django_db
    def test_slug_derives_from_default_language_label(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        # Identity anchors to the default-language (English) label, not the German one.
        assert concept.slug == "heat-flow"

    @pytest.mark.django_db
    def test_second_preferred_label_in_a_language_is_refused(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        with pytest.raises(ValidationError):
            # At most one preferred label per language (FR-001).
            concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Terrestrischer Wärmefluss")

    @pytest.mark.django_db
    def test_concept_without_default_language_label_is_refused(self, scheme):
        # The default-language preferred label is the required identity anchor (FR-002).
        with pytest.raises(ValidationError):
            Concept.objects.create(scheme=scheme, label="")

    @pytest.mark.django_db
    def test_preferred_label_row_in_default_language_is_refused(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        with pytest.raises(ValidationError):
            # The default language's preferred label belongs on Concept.label, not
            # as a separate ConceptLabel row.
            concept.add_label(language="en", kind=ConceptLabel.Kind.PREFERRED, text="Heat flow")

    @pytest.mark.django_db
    def test_uri_and_slug_unchanged_by_non_default_label_lifecycle(self, scheme):
        # SC-003: mutating a non-default-language label — add, edit, remove — never
        # disturbs the concept's slug or URI.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        original_slug = concept.slug
        original_uri = concept.uri

        german = concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri

        german.text = "Terrestrischer Wärmefluss"
        german.save()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.preferred_label("de") == "Terrestrischer Wärmefluss"

        german.delete()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.preferred_label("de") is None


class TestConceptAlternativeAndHiddenLabels:
    """US-2 — Alternative and hidden labels in several languages, identity preserved.
    FR-005 (any number of alternative/hidden labels per language), FR-007 (read them
    back filtered by language), FR-004/SC-003 (an alternative or hidden label never
    disturbs the concept's slug or URI)."""

    @pytest.mark.django_db
    def test_alt_labels_filtered_by_language(self, scheme):
        # Two English alternatives plus a German one: alt_labels("en") returns the two
        # English texts and nothing else (many-per-language, filtered by language).
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="Terrestrial heat flow")
        concept.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="Geothermal heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.ALTERNATIVE, text="Terrestrischer Wärmefluss")
        assert sorted(concept.alt_labels("en")) == ["Geothermal heat flow", "Terrestrial heat flow"]
        assert concept.alt_labels("de") == ["Terrestrischer Wärmefluss"]

    @pytest.mark.django_db
    def test_alt_labels_absent_language_returns_empty_list(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        assert concept.alt_labels("fr") == []

    @pytest.mark.django_db
    def test_hidden_labels_stored_and_read_per_language(self, scheme):
        # Hidden labels read back by language, and are held separately from
        # alternatives — one kind never leaks into the other's reader (FR-005/FR-007).
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="en", kind=ConceptLabel.Kind.HIDDEN, text="heatflow")
        concept.add_label(language="en", kind=ConceptLabel.Kind.HIDDEN, text="heet flow")
        concept.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="Terrestrial heat flow")
        assert sorted(concept.hidden_labels("en")) == ["heatflow", "heet flow"]
        assert concept.hidden_labels("de") == []
        # The two readers do not bleed into each other.
        assert concept.alt_labels("en") == ["Terrestrial heat flow"]

    @pytest.mark.django_db
    def test_uri_and_slug_unchanged_by_alt_and_hidden_label_lifecycle(self, scheme):
        # SC-003: mutating an alternative or hidden label — add, edit, remove — never
        # disturbs the concept's slug or URI, in any language including the default one.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        original_slug = concept.slug
        original_uri = concept.uri

        alt = concept.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="Terrestrial heat flow")
        hidden = concept.add_label(language="de", kind=ConceptLabel.Kind.HIDDEN, text="waermefluss")
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri

        alt.text = "Geothermal heat flow"
        alt.save()
        hidden.text = "wärmefluss"
        hidden.save()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.alt_labels("en") == ["Geothermal heat flow"]
        assert concept.hidden_labels("de") == ["wärmefluss"]

        alt.delete()
        hidden.delete()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.alt_labels("en") == []
        assert concept.hidden_labels("de") == []


class TestConceptDefinitionsAndNotes:
    """US-3 — Definitions and the SKOS documentary notes, per language, repeatable,
    identity preserved. FR-006 (a definition plus the six documentary note kinds —
    scope/example/editorial/history/change/note — each language-tagged and repeatable),
    FR-007 (read them back filtered by language and optionally kind), FR-004/SC-003 (a
    note in any language, including the default one, never disturbs slug or URI).

    Kinds are passed as their plain choice values (``"definition"``, ``"scope"``, …);
    this keeps the test module importable while ``ConceptNote`` is being built, so only
    these new tests go red — on the missing ``Concept`` methods — and the prior suites
    stay green. The SKOS CURIE each kind carries is model metadata, exercised by US-7.
    """

    @pytest.mark.django_db
    def test_definitions_readable_in_each_language(self, scheme):
        # The definition is a ConceptNote of kind "definition"; definition(lang) reads
        # back the value for that language (FR-006/FR-007).
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_note(language="en", kind="definition", value="Heat energy moving through rock.")
        concept.add_note(language="de", kind="definition", value="Wärme, die durch Gestein strömt.")
        assert concept.definition("en") == "Heat energy moving through rock."
        assert concept.definition("de") == "Wärme, die durch Gestein strömt."

    @pytest.mark.django_db
    def test_definition_absent_language_returns_none(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        assert concept.definition("fr") is None

    @pytest.mark.django_db
    def test_each_documentary_note_kind_stored_and_read_by_kind(self, scheme):
        # Every documentary note kind is stored under its own kind and reads back only
        # under that kind, in its own language (FR-006/FR-007).
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        by_kind = {
            "scope": "Use for terrestrial heat only.",
            "example": "Continental crust ~65 mW/m².",
            "editorial": "Check the unit convention before publishing.",
            "history": "Coined in mid-20th-century geophysics.",
            "change": "Broadened from 'surface heat flow' in 2020.",
            "note": "See also thermal gradient.",
        }
        for kind, value in by_kind.items():
            concept.add_note(language="en", kind=kind, value=value)
        for kind, value in by_kind.items():
            assert concept.notes("en", kind=kind) == [value]
            # A note reads back only in its own language.
            assert concept.notes("de", kind=kind) == []

    @pytest.mark.django_db
    def test_notes_without_kind_returns_all_values_for_language(self, scheme):
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_note(language="en", kind="definition", value="A definition.")
        concept.add_note(language="en", kind="scope", value="A scope note.")
        concept.add_note(language="de", kind="note", value="Eine Notiz.")
        assert sorted(concept.notes("en")) == ["A definition.", "A scope note."]
        assert concept.notes("de") == ["Eine Notiz."]

    @pytest.mark.django_db
    def test_repeated_notes_of_a_kind_allowed(self, scheme):
        # SKOS permits repeated notes of a kind per language; no uniqueness refuses them.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_note(language="en", kind="example", value="Continental crust ~65 mW/m².")
        concept.add_note(language="en", kind="example", value="Oceanic crust ~100 mW/m².")
        assert sorted(concept.notes("en", kind="example")) == [
            "Continental crust ~65 mW/m².",
            "Oceanic crust ~100 mW/m².",
        ]

    @pytest.mark.django_db
    def test_uri_and_slug_unchanged_by_note_lifecycle(self, scheme):
        # SC-003: adding, changing, or removing a note — even in the default language —
        # never disturbs the concept's slug or URI.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        original_slug = concept.slug
        original_uri = concept.uri

        note = concept.add_note(language="en", kind="definition", value="Heat energy moving through rock.")
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri

        note.value = "Heat energy conducted through rock."
        note.save()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.definition("en") == "Heat energy conducted through rock."

        note.delete()
        concept.refresh_from_db()
        assert concept.slug == original_slug
        assert concept.uri == original_uri
        assert concept.definition("en") is None


class TestConceptSchemePerVocabularyDefaultLanguage:
    """US-4 — Per-vocabulary default language. FR-009 (each vocabulary has a default
    language that defaults to the app default and may be overridden per vocabulary),
    FR-011 (the effective default language is the app default unless the vocabulary
    overrides it), and the identity consequence: the vocabulary's effective default
    language decides which preferred label — held on ``Concept.label`` — anchors its
    concepts' slugs.

    The override field (``ConceptScheme.default_language``) does not exist before
    US-4, so these tests fail precisely on that missing field (an ``AttributeError``
    reading it, a ``TypeError`` passing it) while every prior suite stays green — the
    module still imports.
    """

    @pytest.mark.django_db
    def test_no_override_anchors_identity_in_app_default(self, scheme):
        # A vocabulary with no explicit override carries an empty default_language and
        # falls back to the application's configured default (FR-009/FR-011).
        assert scheme.default_language == ""
        assert scheme.effective_default_language == settings.LANGUAGE_CODE

        # Identity therefore anchors in the app default (English): Concept.label is the
        # English preferred label and the slug derives from it; a German preferred label
        # is an additive ConceptLabel row that never moves identity.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        assert concept.slug == "heat-flow"
        assert concept.preferred_label("en") == "Heat flow"
        assert concept.preferred_label("de") == "Wärmefluss"

    @pytest.mark.django_db
    def test_override_to_de_derives_slug_from_de_label(self, db):
        # A vocabulary overridden to German anchors identity in German: Concept.label
        # now holds the German preferred label and the slug derives from it, while the
        # English preferred label becomes the additive ConceptLabel row (FR-009 identity
        # consequence, US-4 acceptance scenario 2).
        scheme = ConceptScheme.objects.create(name="Geothermik", default_language="de")
        assert scheme.effective_default_language == "de"

        concept = Concept.objects.create(scheme=scheme, label="Wärmefluss")
        concept.add_label(language="en", kind=ConceptLabel.Kind.PREFERRED, text="Heat flow")
        assert concept.slug == "wärmefluss"
        assert concept.uri == f"{scheme.uri}/wärmefluss"
        assert concept.preferred_label("de") == "Wärmefluss"
        assert concept.preferred_label("en") == "Heat flow"

    @pytest.mark.django_db
    def test_effective_default_language_returns_override_or_app_default(self, db):
        # Reading the effective default language reports the explicit override when set,
        # and the application default otherwise (US-4 acceptance scenario 3, FR-011).
        overridden = ConceptScheme.objects.create(name="Geothermik", default_language="de")
        assert overridden.default_language == "de"
        assert overridden.effective_default_language == "de"

        plain = ConceptScheme.objects.create(name="Geothermics")
        assert plain.default_language == ""
        assert plain.effective_default_language == settings.LANGUAGE_CODE

    @pytest.mark.django_db
    def test_default_language_is_freely_changeable_before_concepts_exist(self):
        # While a vocabulary is still empty, its default language may be changed at
        # will — nothing anchors to it yet, so there is no identity to disturb.
        scheme = ConceptScheme.objects.create(name="Geothermik", default_language="de")
        scheme.default_language = "fr"
        scheme.save()
        scheme.refresh_from_db()
        assert scheme.default_language == "fr"
        assert scheme.effective_default_language == "fr"

    @pytest.mark.django_db
    def test_default_language_is_frozen_once_concepts_exist(self):
        # Once a concept exists, its identity anchor (Concept.label) is the preferred
        # label in the vocabulary's effective default language. Changing the default
        # language afterwards would silently reinterpret every anchor, so it is refused.
        scheme = ConceptScheme.objects.create(name="Geothermics")  # effective default = en
        Concept.objects.create(scheme=scheme, label="Heat flow")
        scheme.default_language = "de"
        with pytest.raises(ValidationError):
            scheme.save()
        # The stored value is unchanged.
        scheme.refresh_from_db()
        assert scheme.default_language == ""
        assert scheme.effective_default_language == settings.LANGUAGE_CODE

    @pytest.mark.django_db
    def test_setting_default_language_to_the_same_value_is_allowed_with_concepts(self):
        # Re-saving a scheme without actually changing its default language must not
        # trip the freeze — the guard fires only on a genuine change.
        scheme = ConceptScheme.objects.create(name="Geothermik", default_language="de")
        Concept.objects.create(scheme=scheme, label="Wärmefluss")
        scheme.name = "Geothermik (rev.)"  # an unrelated edit, same default_language
        scheme.save()  # must not raise
        scheme.refresh_from_db()
        assert scheme.default_language == "de"


class TestConceptOverridableSlug:
    """US-5 — Overridable concept slug. FR-010 (a slug set explicitly is not
    re-derived when the preferred label later changes, while a concept with no
    explicit slug keeps tracking its default-language label), FR-012 (uniqueness
    within a scheme holds for both derived and explicit slugs, collisions refused)."""

    @pytest.mark.django_db
    def test_explicit_slug_is_exactly_the_value_set_not_derived(self, scheme):
        # Acceptance 1: an explicitly set slug is exactly the value given and is not
        # derived from the preferred label (which would slugify to "heat-flow").
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.set_slug("custom-identifier")
        assert concept.slug == "custom-identifier"
        assert concept.slug_is_manual is True
        concept.refresh_from_db()
        assert concept.slug == "custom-identifier"
        assert concept.slug != "heat-flow"

    @pytest.mark.django_db
    def test_explicit_slug_survives_a_default_language_relabel(self, scheme):
        # Acceptance 2: once set explicitly, changing the default-language preferred
        # label does not move the slug.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        concept.set_slug("hf")
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.slug == "hf"
        concept.refresh_from_db()
        assert concept.slug == "hf"

    @pytest.mark.django_db
    def test_slug_without_override_still_derives_from_label(self, scheme):
        # Acceptance 3: a concept with no explicit slug derives it from the
        # default-language label and keeps tracking it, exactly as in #15.
        concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
        assert concept.slug == "heat-flow"
        assert concept.slug_is_manual is False
        concept.label = "Surface Heat Flow"
        concept.save()
        assert concept.slug == "surface-heat-flow"

    @pytest.mark.django_db
    def test_explicit_slug_colliding_within_scheme_is_refused(self, scheme):
        # Acceptance 4: an explicit slug that collides with another concept's slug in
        # the same scheme is refused, per the uniqueness rule inherited from #15.
        Concept.objects.create(scheme=scheme, label="Heat Flow")  # slug "heat-flow"
        other = Concept.objects.create(scheme=scheme, label="Gradient")
        with pytest.raises(ValidationError):
            other.set_slug("heat-flow")
        assert scheme.concepts.filter(slug="heat-flow").count() == 1


class TestReviewHardening:
    """Fixes from the FS-002 review panel: manual-slug validation, the default-language
    preferred backstop at ``save()``, runtime language validation (no settings-frozen
    ``choices``), prefetch-friendly read helpers, and boundary-safe ``get_by_uri``."""

    @pytest.mark.django_db
    def test_explicit_slug_with_invalid_characters_is_refused(self, scheme):
        # A manual slug is stored verbatim but must still be a well-formed single-segment
        # slug: a '/' or whitespace would corrupt the composed URI and break get_by_uri.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        with pytest.raises(ValidationError):
            concept.set_slug("foo/bar")
        with pytest.raises(ValidationError):
            concept.set_slug("has spaces")
        # A valid explicit slug still works (regression guard).
        concept.set_slug("hf-1")
        assert concept.slug == "hf-1"

    @pytest.mark.django_db
    def test_default_language_preferred_row_is_refused_even_via_create(self, scheme):
        # The default-language-preferred rule is backstopped at save(), so even
        # .objects.create() (which bypasses full_clean) cannot plant a second identity
        # anchor alongside Concept.label.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")  # 'en' anchor
        with pytest.raises(ValidationError):
            ConceptLabel.objects.create(
                concept=concept, language="en", kind=ConceptLabel.Kind.PREFERRED, text="Heat flow (dup)"
            )

    @pytest.mark.django_db
    def test_language_outside_the_configured_set_is_refused(self, scheme):
        # choices=settings.LANGUAGES was dropped (so the migration does not freeze the
        # maintainer's LANGUAGES); an unconfigured language is still refused at runtime.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        with pytest.raises(ValidationError):
            concept.add_label(language="xx", kind=ConceptLabel.Kind.ALTERNATIVE, text="nope")
        with pytest.raises(ValidationError):
            concept.add_note(language="xx", kind=ConceptNote.Kind.NOTE, value="nope")

    @pytest.mark.django_db
    def test_scheme_default_language_rejects_an_unconfigured_language(self):
        with pytest.raises(ValidationError):
            ConceptScheme.objects.create(name="Bad", default_language="xx")

    @pytest.mark.django_db
    def test_read_helpers_stay_cheap_under_prefetch_related(self, django_assert_num_queries, scheme):
        # The read helpers iterate the cached related set, so prefetch_related collapses
        # the FR-007 read-by-language path to zero extra queries per concept (a .filter()
        # would bypass the cache and re-hit the DB per call).
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
        concept.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="terrestrial heat flow")
        concept.add_note(language="de", kind=ConceptNote.Kind.DEFINITION, value="Wärmestromdichte.")

        # A bulk caller select_relates the scheme (preferred_label consults its effective
        # default language) and prefetches the label/note sets; the helpers then add no
        # queries of their own.
        prefetched = (
            Concept.objects.select_related("scheme").prefetch_related("labels", "concept_notes").get(pk=concept.pk)
        )
        with django_assert_num_queries(0):
            assert prefetched.preferred_label("de") == "Wärmefluss"
            assert prefetched.alt_labels("en") == ["terrestrial heat flow"]
            assert prefetched.hidden_labels("en") == []
            assert prefetched.definition("de") == "Wärmestromdichte."
            assert prefetched.notes("de") == ["Wärmestromdichte."]

    @pytest.mark.django_db
    def test_get_by_uri_rejects_a_sibling_prefix_path(self, scheme):
        # A URI that merely shares the base as a raw prefix ('<base>X/...') must not be
        # treated as in-base — the match is on a '/'-terminated base.
        concept = Concept.objects.create(scheme=scheme, label="Heat flow")
        base = conf.get_base_uri()
        sibling = f"{base}X/{scheme.slug}/{concept.slug}"
        with pytest.raises(Concept.DoesNotExist):
            Concept.objects.get_by_uri(sibling)
        # The genuine URI still resolves (regression guard).
        assert Concept.objects.get_by_uri(concept.uri) == concept


class TestBroaderNarrower:
    """US-1 (FS-003) — a broader/narrower hierarchy, navigable both ways.

    ``add_broader`` asserts one direction; ``narrower`` is derived from it, never
    asserted separately. A concept may sit under several broader concepts
    (polyhierarchy). Adding or removing a link never moves a concept's identity
    (FR-004). Self, duplicate, and cross-vocabulary edges are refused.
    """

    @pytest.mark.django_db
    def test_broader_readable_and_narrower_derived(self, scheme):
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        granite.add_broader(igneous)
        # one assertion, both directions
        assert igneous in granite.broader()
        assert granite in igneous.narrower()
        # nothing spurious in the empty directions
        assert list(granite.narrower()) == []
        assert list(igneous.broader()) == []

    @pytest.mark.django_db
    def test_polyhierarchy_several_broader(self, scheme):
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        plutonic = Concept.objects.create(scheme=scheme, label="Plutonic rock")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        granite.add_broader(igneous)
        granite.add_broader(plutonic)
        assert set(granite.broader()) == {igneous, plutonic}

    @pytest.mark.django_db
    def test_remove_broader_clears_both_directions(self, scheme):
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        granite.add_broader(igneous)
        granite.remove_broader(igneous)
        assert list(granite.broader()) == []
        assert list(igneous.narrower()) == []
        # removing an absent edge is a no-op
        granite.remove_broader(igneous)

    @pytest.mark.django_db
    def test_self_broader_is_refused(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        with pytest.raises(ValidationError):
            granite.add_broader(granite)

    @pytest.mark.django_db
    def test_duplicate_broader_is_refused(self, scheme):
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        granite.add_broader(igneous)
        with pytest.raises(ValidationError):
            granite.add_broader(igneous)
        # the pair is held once
        assert list(granite.broader()) == [igneous]

    @pytest.mark.django_db
    def test_reverse_broader_is_a_distinct_edge(self, scheme):
        # a broader b and b broader a are different edges (a 2-cycle), permitted:
        # the cycle deferral means no traversal, and the ordered unique key differs.
        a = Concept.objects.create(scheme=scheme, label="A")
        b = Concept.objects.create(scheme=scheme, label="B")
        a.add_broader(b)
        b.add_broader(a)  # must not raise
        assert b in a.broader()
        assert a in b.broader()

    @pytest.mark.django_db
    def test_cross_scheme_broader_is_refused(self, scheme):
        other = ConceptSchemeFactory()
        here = Concept.objects.create(scheme=scheme, label="Granite")
        there = Concept.objects.create(scheme=other, label="Quartz")
        with pytest.raises(ValidationError):
            here.add_broader(there)

    @pytest.mark.django_db
    def test_adding_and_removing_broader_leaves_identity_unchanged(self, scheme):
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        uri_before, slug_before = granite.uri, granite.slug
        granite.add_broader(igneous)
        granite.refresh_from_db()
        assert (granite.uri, granite.slug) == (uri_before, slug_before)
        granite.remove_broader(igneous)
        granite.refresh_from_db()
        assert (granite.uri, granite.slug) == (uri_before, slug_before)


class TestRelated:
    """US-2 (FS-003) — the symmetric ``related`` association.

    ``add_related`` records a sideways link that reads the same from either concept
    and is stored once regardless of the order asserted (research R2). Self and
    duplicate (either order) are refused; removal clears both sides; identity is
    untouched.
    """

    @pytest.mark.django_db
    def test_related_is_symmetric(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        granite.add_related(quartz)
        assert quartz in granite.related()
        assert granite in quartz.related()

    @pytest.mark.django_db
    def test_related_stored_once_mirror_refused(self, scheme):
        from controlled_vocabularies.models import ConceptRelation

        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        granite.add_related(quartz)
        # the same association asserted in the mirror order is the one that exists
        with pytest.raises(ValidationError):
            quartz.add_related(granite)
        assert ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).count() == 1
        assert list(granite.related()) == [quartz]

    @pytest.mark.django_db
    def test_same_order_related_duplicate_is_refused(self, scheme):
        # the exact same assertion (not just the mirror) is also refused — the pair is held once
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        granite.add_related(quartz)
        with pytest.raises(ValidationError):
            granite.add_related(quartz)

    @pytest.mark.django_db
    def test_self_related_is_refused(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        with pytest.raises(ValidationError):
            granite.add_related(granite)

    @pytest.mark.django_db
    def test_remove_related_clears_both_sides(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        granite.add_related(quartz)
        # removal works from either side regardless of stored order
        quartz.remove_related(granite)
        assert list(granite.related()) == []
        assert list(quartz.related()) == []
        quartz.remove_related(granite)  # no-op

    @pytest.mark.django_db
    def test_cross_scheme_related_is_refused(self, scheme):
        other = ConceptSchemeFactory()
        here = Concept.objects.create(scheme=scheme, label="Granite")
        there = Concept.objects.create(scheme=other, label="Quartz")
        with pytest.raises(ValidationError):
            here.add_related(there)

    @pytest.mark.django_db
    def test_adding_related_leaves_identity_unchanged(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        uri_before, slug_before = granite.uri, granite.slug
        granite.add_related(quartz)
        granite.refresh_from_db()
        assert (granite.uri, granite.slug) == (uri_before, slug_before)


class TestGraphIntegrity:
    """US-3 (FS-003) — the graph cannot enter a SKOS-contradictory state.

    A pair joined by a direct broader/narrower link cannot also be ``related``
    (disjointness), checked at direct adjacency only. Cycles in the hierarchy and
    a related link between only-transitively-hierarchical concepts are *accepted* —
    both are recorded non-guarantees this slice (no hierarchy traversal is performed).
    """

    @pytest.mark.django_db
    def test_hierarchical_pair_cannot_also_be_related(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite.add_broader(igneous)
        # refused in either order of attempt
        with pytest.raises(ValidationError):
            granite.add_related(igneous)
        with pytest.raises(ValidationError):
            igneous.add_related(granite)

    @pytest.mark.django_db
    def test_related_pair_cannot_be_given_a_broader_link(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        granite.add_related(quartz)
        with pytest.raises(ValidationError):
            granite.add_broader(quartz)
        with pytest.raises(ValidationError):
            quartz.add_broader(granite)

    @pytest.mark.django_db
    def test_disjointness_constrains_a_pair_not_the_vocabulary(self, scheme):
        a = Concept.objects.create(scheme=scheme, label="A")
        b = Concept.objects.create(scheme=scheme, label="B")
        c = Concept.objects.create(scheme=scheme, label="C")
        d = Concept.objects.create(scheme=scheme, label="D")
        a.add_broader(b)  # one pair hierarchical
        c.add_related(d)  # a different pair related
        assert b in a.broader()
        assert d in c.related()

    @pytest.mark.django_db
    def test_transitively_hierarchical_pair_can_be_related(self, scheme):
        # a -> b -> c (broader). a and c are only *transitively* hierarchical, so relating
        # them is accepted — disjointness is checked at direct adjacency only.
        a = Concept.objects.create(scheme=scheme, label="A")
        b = Concept.objects.create(scheme=scheme, label="B")
        c = Concept.objects.create(scheme=scheme, label="C")
        a.add_broader(b)
        b.add_broader(c)
        a.add_related(c)  # must not raise
        assert c in a.related()

    @pytest.mark.django_db
    def test_cyclic_broader_chain_is_accepted(self, scheme):
        # a -> b -> c -> a. No cycle prevention this slice (recorded non-guarantee); the
        # inserts must succeed and perform no hierarchy traversal.
        a = Concept.objects.create(scheme=scheme, label="A")
        b = Concept.objects.create(scheme=scheme, label="B")
        c = Concept.objects.create(scheme=scheme, label="C")
        a.add_broader(b)
        b.add_broader(c)
        c.add_broader(a)  # closes the loop; must not raise
        assert a in c.broader()


class TestCollectionMembership:
    """US-1 — Gather concepts into a named collection.

    A ``Collection`` groups concepts of one vocabulary; members are added and read
    back, a concept may sit in several collections, and a member is held once.
    """

    @pytest.mark.django_db
    def test_add_and_read_members(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        igneous = Collection.objects.create(scheme=scheme, name="Common igneous rocks")
        igneous.add(granite)
        igneous.add(basalt)
        assert set(igneous.members()) == {granite, basalt}
        assert quartz not in igneous.members()

    @pytest.mark.django_db
    def test_new_collection_has_no_members(self, scheme):
        empty = Collection.objects.create(scheme=scheme, name="Empty")
        assert list(empty.members()) == []

    @pytest.mark.django_db
    def test_adding_same_concept_twice_holds_it_once(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        igneous.add(granite)
        igneous.add(granite)  # must not raise, must not duplicate
        assert list(igneous.members()).count(granite) == 1
        assert igneous.memberships.count() == 1

    @pytest.mark.django_db
    def test_a_concept_can_belong_to_several_collections(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        field_guide = Collection.objects.create(scheme=scheme, name="Field-guide rocks")
        igneous.add(granite)
        field_guide.add(granite)
        assert granite in igneous.members()
        assert granite in field_guide.members()
        # removing from one leaves the other intact
        igneous.remove(granite)
        assert granite not in igneous.members()
        assert granite in field_guide.members()

    @pytest.mark.django_db
    def test_remove_member_leaves_others_untouched(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        igneous.add(granite)
        igneous.add(basalt)
        igneous.remove(granite)
        assert granite not in igneous.members()
        assert basalt in igneous.members()

    @pytest.mark.django_db
    def test_remove_a_non_member_is_a_no_op(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        igneous.remove(granite)  # not a member; must not raise
        assert list(igneous.members()) == []

    @pytest.mark.django_db
    def test_concept_reports_its_collections(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        field_guide = Collection.objects.create(scheme=scheme, name="Field-guide rocks")
        igneous.add(granite)
        field_guide.add(granite)
        assert set(granite.collections()) == {igneous, field_guide}

    @pytest.mark.django_db
    def test_colliding_collection_slug_in_one_scheme_is_refused(self, scheme):
        Collection.objects.create(scheme=scheme, name="Igneous rocks")
        with pytest.raises(ValidationError):
            Collection.objects.create(scheme=scheme, name="Igneous rocks")

    @pytest.mark.django_db
    def test_same_collection_name_allowed_across_schemes(self):
        a = ConceptScheme.objects.create(name="Rocks")
        b = ConceptScheme.objects.create(name="Minerals")
        first = Collection.objects.create(scheme=a, name="Common")
        second = Collection.objects.create(scheme=b, name="Common")
        assert first.slug == second.slug
        assert first.scheme_id != second.scheme_id

    @pytest.mark.django_db
    def test_name_that_slugifies_to_empty_is_refused(self, scheme):
        # A name with no slug-able characters would mint an empty identifier; refuse it
        # rather than store an unidentifiable collection (the scheme/concept rule).
        with pytest.raises(ValidationError):
            Collection.objects.create(scheme=scheme, name="***")

    @pytest.mark.django_db
    def test_membership_str_names_the_concept_and_collection(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        member = igneous.add(granite)
        assert str(member) == "Granite in Igneous"

    @pytest.mark.django_db
    def test_membership_leaves_concept_identity_unchanged(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        uri_before, slug_before = granite.uri, granite.slug
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        igneous.add(granite)
        igneous.remove(granite)
        granite.refresh_from_db()
        assert granite.uri == uri_before
        assert granite.slug == slug_before

    @pytest.mark.django_db
    def test_uri_composes_under_a_collection_segment(self):
        vocab = ConceptScheme.objects.create(name="Rocks")
        coll = Collection.objects.create(scheme=vocab, name="Common igneous rocks")
        assert coll.uri == f"{vocab.uri}/collection/{coll.slug}"

    @pytest.mark.django_db
    def test_str_is_the_name(self, scheme):
        coll = Collection.objects.create(scheme=scheme, name="Common igneous rocks")
        assert str(coll) == "Common igneous rocks"


class TestOrderedCollection:
    """US-2 — A collection with a deliberate order.

    An ``ordered`` collection reads its members in the sequence they were arranged;
    an unordered one is a set and refuses ordering operations.
    """

    @pytest.mark.django_db
    def test_ordered_members_read_in_add_sequence(self, scheme):
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        gabbro = Concept.objects.create(scheme=scheme, label="Gabbro")
        reading = Collection.objects.create(scheme=scheme, name="Reading order", ordered=True)
        reading.add(basalt)
        reading.add(granite)
        reading.add(gabbro)
        assert list(reading.members()) == [basalt, granite, gabbro]

    @pytest.mark.django_db
    def test_set_member_order_rearranges(self, scheme):
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        gabbro = Concept.objects.create(scheme=scheme, label="Gabbro")
        reading = Collection.objects.create(scheme=scheme, name="Reading order", ordered=True)
        for c in (basalt, granite, gabbro):
            reading.add(c)
        reading.set_member_order([gabbro, basalt, granite])
        assert list(reading.members()) == [gabbro, basalt, granite]

    @pytest.mark.django_db
    def test_removing_a_member_keeps_relative_order(self, scheme):
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        gabbro = Concept.objects.create(scheme=scheme, label="Gabbro")
        reading = Collection.objects.create(scheme=scheme, name="Reading order", ordered=True)
        for c in (basalt, granite, gabbro):
            reading.add(c)
        reading.remove(granite)  # remove the middle member
        assert list(reading.members()) == [basalt, gabbro]

    @pytest.mark.django_db
    def test_set_member_order_on_unordered_collection_is_refused(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        plain = Collection.objects.create(scheme=scheme, name="A set")
        plain.add(granite)
        plain.add(basalt)
        with pytest.raises(ValidationError):
            plain.set_member_order([basalt, granite])

    @pytest.mark.django_db
    def test_set_member_order_with_a_different_set_is_refused(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        quartz = Concept.objects.create(scheme=scheme, label="Quartz")
        reading = Collection.objects.create(scheme=scheme, name="Reading order", ordered=True)
        reading.add(granite)
        reading.add(basalt)
        with pytest.raises(ValidationError):
            reading.set_member_order([granite, basalt, quartz])  # quartz is not a member

    @pytest.mark.django_db
    def test_unordered_collection_returns_its_members_as_a_set(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        plain = Collection.objects.create(scheme=scheme, name="A set")
        plain.add(granite)
        plain.add(basalt)
        assert set(plain.members()) == {granite, basalt}


class TestMembershipIntegrity:
    """US-3 — Membership stays inside the vocabulary and clear of the hierarchy."""

    @pytest.mark.django_db
    def test_cross_vocabulary_member_is_refused(self):
        rocks = ConceptScheme.objects.create(name="Rocks")
        minerals = ConceptScheme.objects.create(name="Minerals")
        igneous = Collection.objects.create(scheme=rocks, name="Igneous")
        mica = Concept.objects.create(scheme=minerals, label="Mica")
        with pytest.raises(ValidationError):
            igneous.add(mica)
        assert list(igneous.members()) == []

    @pytest.mark.django_db
    def test_membership_asserts_no_relation(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        basalt = Concept.objects.create(scheme=scheme, label="Basalt")
        igneous = Collection.objects.create(scheme=scheme, name="Igneous")
        igneous.add(granite)
        igneous.add(basalt)
        assert basalt not in granite.related()
        assert basalt not in granite.broader()
        assert basalt not in granite.narrower()

    @pytest.mark.django_db
    def test_existing_relation_is_unchanged_by_shared_membership(self, scheme):
        granite = Concept.objects.create(scheme=scheme, label="Granite")
        igneous_rock = Concept.objects.create(scheme=scheme, label="Igneous rock")
        granite.add_broader(igneous_rock)
        coll = Collection.objects.create(scheme=scheme, name="Igneous")
        coll.add(granite)
        coll.add(igneous_rock)
        # the pre-existing broader/narrower link is untouched
        assert igneous_rock in granite.broader()
        assert granite in igneous_rock.narrower()
