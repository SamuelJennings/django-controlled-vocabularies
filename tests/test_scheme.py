"""US-1 — Define a vocabulary (ConceptScheme).

Covers FR-001 (create/rename/delete), FR-002 (slug derived, synced, unique
app-wide), FR-005 (scheme URI), FR-007 (non-ASCII slugs, collisions refused).
"""

import pytest
from django.core.exceptions import ValidationError

from controlled_vocabularies.models import ConceptScheme


@pytest.mark.django_db
def test_create_derives_slug_from_name():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    assert scheme.slug == "geothermics"


@pytest.mark.django_db
def test_create_accepts_optional_description():
    scheme = ConceptScheme.objects.create(name="Geothermics", description="Study of Earth's heat.")
    fetched = ConceptScheme.objects.get(pk=scheme.pk)
    assert fetched.description == "Study of Earth's heat."


@pytest.mark.django_db
def test_rename_updates_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    scheme.name = "Geothermal Science"
    scheme.save()
    assert scheme.slug == "geothermal-science"


@pytest.mark.django_db
def test_empty_name_is_rejected():
    with pytest.raises(ValidationError):
        ConceptScheme.objects.create(name="")


@pytest.mark.django_db
def test_whitespace_only_name_is_rejected():
    with pytest.raises(ValidationError):
        ConceptScheme.objects.create(name="   ")


@pytest.mark.django_db
def test_non_latin_name_yields_nonempty_unicode_slug():
    scheme = ConceptScheme.objects.create(name="Wärmefluss")
    assert scheme.slug
    assert scheme.slug == "wärmefluss"


@pytest.mark.django_db
def test_colliding_slug_is_refused_not_suffixed():
    ConceptScheme.objects.create(name="Geothermics")
    with pytest.raises(ValidationError):
        # A different name that slugifies to the same value must be refused,
        # never silently auto-suffixed to "geothermics-2".
        ConceptScheme.objects.create(name="GEOTHERMICS")
    assert ConceptScheme.objects.filter(slug="geothermics").count() == 1
    assert not ConceptScheme.objects.filter(slug="geothermics-2").exists()


@pytest.mark.django_db
def test_uri_composes_from_base_and_slug():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    assert scheme.uri == "https://example.org/vocabularies/geothermics"


@pytest.mark.django_db
def test_uri_reflects_rename():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    scheme.name = "Geothermal Science"
    scheme.save()
    assert scheme.uri == "https://example.org/vocabularies/geothermal-science"


@pytest.mark.django_db
def test_str_is_the_name():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    assert str(scheme) == "Geothermics"


@pytest.mark.django_db
def test_delete_removes_scheme():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    pk = scheme.pk
    scheme.delete()
    assert not ConceptScheme.objects.filter(pk=pk).exists()
