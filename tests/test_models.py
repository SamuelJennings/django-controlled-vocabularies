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
from django.core.exceptions import ValidationError
from django.db.models import Model, UniqueConstraint
from django.utils.functional import Promise

from controlled_vocabularies import conf
from controlled_vocabularies.models import Concept, ConceptScheme
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
