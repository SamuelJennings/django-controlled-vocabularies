"""US-2 — Define a concept (Concept).

Covers FR-003 (add/relabel/delete), FR-004 (slug derived from label, synced,
unique within a scheme not app-wide), FR-006 (concept URI composed from the
scheme URI and slug), FR-007 (empty labels and within-scheme collisions
refused), and cascade delete of a scheme's concepts.
"""

import pytest
from django.core.exceptions import ValidationError

from controlled_vocabularies.models import Concept, ConceptScheme


@pytest.mark.django_db
def test_add_derives_slug_from_label():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    assert concept.slug == "heat-flow"


@pytest.mark.django_db
def test_get_concept_by_scheme_and_slug():
    # FR-006's second retrieval mode: a concept is retrievable by its
    # vocabulary-plus-slug pair, as a first-class query, not only via get_by_uri.
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    assert Concept.objects.get(scheme=scheme, slug="heat-flow") == concept


@pytest.mark.django_db
def test_list_concepts_of_a_scheme():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    Concept.objects.create(scheme=scheme, label="Heat Flow")
    Concept.objects.create(scheme=scheme, label="Gradient")
    assert scheme.concepts.count() == 2


@pytest.mark.django_db
def test_relabel_updates_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    concept.label = "Surface Heat Flow"
    concept.save()
    assert concept.slug == "surface-heat-flow"


@pytest.mark.django_db
def test_empty_label_is_rejected():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    with pytest.raises(ValidationError):
        Concept.objects.create(scheme=scheme, label="")


@pytest.mark.django_db
def test_whitespace_only_label_is_rejected():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    with pytest.raises(ValidationError):
        Concept.objects.create(scheme=scheme, label="   ")


@pytest.mark.django_db
def test_non_latin_label_yields_nonempty_unicode_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Wärmefluss")
    assert concept.slug
    assert concept.slug == "wärmefluss"


@pytest.mark.django_db
def test_colliding_slug_within_scheme_is_refused_not_suffixed():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    Concept.objects.create(scheme=scheme, label="Heat Flow")
    with pytest.raises(ValidationError):
        # A different label that slugifies to the same value within the same
        # scheme must be refused, never silently auto-suffixed to "heat-flow-2".
        Concept.objects.create(scheme=scheme, label="HEAT FLOW")
    assert scheme.concepts.filter(slug="heat-flow").count() == 1
    assert not scheme.concepts.filter(slug="heat-flow-2").exists()


@pytest.mark.django_db
def test_same_slug_allowed_across_different_schemes():
    scheme_a = ConceptScheme.objects.create(name="Geothermics")
    scheme_b = ConceptScheme.objects.create(name="Hydrology")
    concept_a = Concept.objects.create(scheme=scheme_a, label="Heat Flow")
    concept_b = Concept.objects.create(scheme=scheme_b, label="Heat Flow")
    assert concept_a.slug == concept_b.slug == "heat-flow"
    assert Concept.objects.filter(slug="heat-flow").count() == 2


@pytest.mark.django_db
def test_uri_composes_from_scheme_uri_and_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    assert concept.uri == f"{scheme.uri}/heat-flow"
    assert concept.uri == "https://example.org/vocabularies/geothermics/heat-flow"


@pytest.mark.django_db
def test_uri_reflects_relabel():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    concept.label = "Surface Heat Flow"
    concept.save()
    assert concept.uri == "https://example.org/vocabularies/geothermics/surface-heat-flow"


@pytest.mark.django_db
def test_str_is_the_label():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    assert str(concept) == "Heat Flow"


@pytest.mark.django_db
def test_delete_removes_concept():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    concept = Concept.objects.create(scheme=scheme, label="Heat Flow")
    pk = concept.pk
    concept.delete()
    assert not Concept.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_deleting_scheme_cascades_to_its_concepts():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    Concept.objects.create(scheme=scheme, label="Heat Flow")
    Concept.objects.create(scheme=scheme, label="Gradient")
    scheme.delete()
    assert Concept.objects.count() == 0
