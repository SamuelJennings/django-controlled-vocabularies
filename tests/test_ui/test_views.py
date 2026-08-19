"""Tests for :mod:`controlled_vocabularies.ui.views` (T006-T009)."""

import pytest
from django.urls import reverse

from tests.factories import ConceptSchemeFactory


class TestVocabularyList:
    """Every vocabulary the site holds appears exactly once (FR-001, FR-012, User Story 1 scenario 1)."""

    @pytest.mark.django_db
    def test_every_vocabulary_appears_exactly_once(self, client):
        schemes = ConceptSchemeFactory.create_batch(3)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))

        assert response.status_code == 200
        listed = list(response.context["object_list"])
        assert len(listed) == len(schemes)
        assert {vocabulary.pk for vocabulary in listed} == {scheme.pk for scheme in schemes}

    @pytest.mark.django_db
    def test_a_vocabulary_added_after_the_first_request_appears_on_the_next(self, client):
        url = reverse("controlled_vocabularies_ui:vocabulary-list")
        client.get(url)

        added = ConceptSchemeFactory()

        response = client.get(url)

        assert added.pk in {vocabulary.pk for vocabulary in response.context["object_list"]}

    @pytest.mark.django_db
    def test_page_renders_no_sort_filter_or_create_control(self, client):
        ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))
        content = response.content.decode()

        assert 'name="q"' not in content
        assert 'name="o"' not in content
        assert "Add new" not in content
