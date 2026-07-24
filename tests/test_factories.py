"""US-4 — Ready-made test scaffolding (factories).

Covers the test factories that downstream stories build their fixtures on:
``ConceptSchemeFactory`` and ``ConceptFactory``. The factories must produce
valid, saved objects with derived slugs/URIs, ``ConceptFactory`` must
auto-create its owning scheme, and repeated calls must not collide on the
app-wide-unique scheme slug or the per-scheme-unique concept slug.
"""

import pytest

from controlled_vocabularies.models import Concept, ConceptScheme
from tests.factories import ConceptFactory, ConceptSchemeFactory


@pytest.mark.django_db
def test_scheme_factory_produces_saved_valid_object():
    scheme = ConceptSchemeFactory()
    assert isinstance(scheme, ConceptScheme)
    assert scheme.pk is not None
    assert scheme.name
    assert scheme.slug
    assert scheme.uri == f"https://example.org/vocabularies/{scheme.slug}"


@pytest.mark.django_db
def test_concept_factory_produces_saved_valid_object():
    concept = ConceptFactory()
    assert isinstance(concept, Concept)
    assert concept.pk is not None
    assert concept.label
    assert concept.slug
    assert concept.uri == f"{concept.scheme.uri}/{concept.slug}"


@pytest.mark.django_db
def test_concept_factory_auto_creates_its_scheme():
    concept = ConceptFactory()
    assert concept.scheme is not None
    assert concept.scheme.pk is not None
    assert ConceptScheme.objects.filter(pk=concept.scheme.pk).exists()


@pytest.mark.django_db
def test_scheme_factory_sequence_avoids_slug_collisions():
    first = ConceptSchemeFactory()
    second = ConceptSchemeFactory()
    assert first.slug != second.slug
    assert ConceptScheme.objects.count() == 2


@pytest.mark.django_db
def test_concept_factory_repeated_calls_do_not_collide():
    # Each ConceptFactory() call mints a fresh scheme *and* a fresh label via
    # sequences, so a second call never trips the collision guards in save().
    first = ConceptFactory()
    second = ConceptFactory()
    assert first.slug != second.slug or first.scheme_id != second.scheme_id
    assert first.scheme_id != second.scheme_id
    assert Concept.objects.count() == 2


@pytest.mark.django_db
def test_concept_factory_accepts_an_explicit_scheme():
    scheme = ConceptSchemeFactory()
    concept = ConceptFactory(scheme=scheme)
    assert concept.scheme_id == scheme.pk
