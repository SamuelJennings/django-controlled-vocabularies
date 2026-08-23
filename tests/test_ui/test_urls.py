"""Tests for :mod:`controlled_vocabularies.ui.urls` (T006, FR-012; T001)."""

from django.urls import reverse


class TestVocabularyListUrl:
    """The route reverses by name, under its own namespace and the project's chosen prefix."""

    def test_reverses_by_name_under_its_own_namespace(self):
        assert reverse("controlled_vocabularies_ui:vocabulary-list") == "/browse/"


class TestVocabularyDetailUrl:
    """The detail route reverses by name and slug, mounted after the list route."""

    def test_reverses_by_name_and_slug(self):
        assert reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": "geology"}) == "/browse/geology/"
