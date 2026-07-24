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
from controlled_vocabularies.models import Concept, ConceptLabel, ConceptScheme
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
