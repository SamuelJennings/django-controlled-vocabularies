"""US-3 — Every concept carries a stable identifier.

Covers the URI identity guarantees: the full URI composes from the base address,
scheme slug and concept slug (FR-005/FR-006); ``Concept.objects.get_by_uri`` round-
trips a URI back to exactly its concept (FR-006); no two concepts across different
schemes ever compose the same URI (SC-002); a non-Latin label yields a URI that
still resolves; and renaming the scheme or the label recomposes the URI so the new
one resolves (unpublished slice, research R5). A URI with no matching concept raises
``Concept.DoesNotExist``.
"""

import pytest

from controlled_vocabularies import conf
from controlled_vocabularies.models import Concept, ConceptScheme


@pytest.mark.django_db
def test_full_uri_is_base_plus_scheme_slug_plus_concept_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    assert concept.uri == f"{conf.get_base_uri()}/{scheme.slug}/{concept.slug}"
    assert concept.uri == "https://example.org/vocabularies/geothermics/heat-flow"


@pytest.mark.django_db
def test_get_by_uri_returns_exactly_that_concept():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    resolved = Concept.objects.get_by_uri(concept.uri)
    assert resolved == concept
    assert resolved.pk == concept.pk


@pytest.mark.django_db
def test_no_two_concepts_across_schemes_share_a_uri():
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
def test_non_latin_label_yields_resolvable_uri():
    scheme = ConceptScheme.objects.create(name="Geothermik")
    concept = Concept.objects.create(scheme=scheme, label="Wärmefluss")
    assert concept.uri == f"{conf.get_base_uri()}/geothermik/wärmefluss"
    assert Concept.objects.get_by_uri(concept.uri) == concept


@pytest.mark.django_db
def test_renaming_scheme_recomposes_uri_and_still_resolves():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    scheme.name = "Geothermal Science"
    scheme.save()
    concept.refresh_from_db()
    assert concept.uri == "https://example.org/vocabularies/geothermal-science/heat-flow"
    assert Concept.objects.get_by_uri(concept.uri) == concept


@pytest.mark.django_db
def test_renaming_label_recomposes_uri_and_still_resolves():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    concept.label = "Surface Heat Flow"
    concept.save()
    assert concept.uri == "https://example.org/vocabularies/geothermics/surface-heat-flow"
    assert Concept.objects.get_by_uri(concept.uri) == concept


@pytest.mark.django_db
def test_get_by_uri_unknown_uri_raises_does_not_exist():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    Concept.objects.create(scheme=scheme, label="Heat Flow")
    with pytest.raises(Concept.DoesNotExist):
        Concept.objects.get_by_uri(f"{conf.get_base_uri()}/geothermics/no-such-concept")
