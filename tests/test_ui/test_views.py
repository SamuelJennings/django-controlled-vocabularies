"""Tests for :mod:`controlled_vocabularies.ui.views` (T006-T009)."""

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from tests.factories import ConceptFactory, ConceptSchemeFactory

ROW_TEMPLATE = "controlled_vocabularies/ui/conceptscheme_list_item.html"


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


class TestVocabularyListEntry:
    """An entry's description, size and origin (FR-002, FR-003, User Story 1 scenarios 2-5).

    The row partial's own rendering is exercised directly, through the same template it is
    rendered from on the page (``render_to_string``, matching what ``{% render_list_item %}``
    does), so an assertion about one row is never confused by the page's own chrome — the
    pagination summary line and the empty-state component are also ``<c-text>``/``<p>`` output
    and would otherwise be indistinguishable from the row's.
    """

    @pytest.mark.django_db
    def test_get_queryset_annotates_the_real_concept_count(self, client):
        populated = ConceptSchemeFactory()
        ConceptFactory.create_batch(3, scheme=populated)
        empty = ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))

        counts = {vocabulary.pk: vocabulary.concept_count for vocabulary in response.context["object_list"]}
        assert counts[populated.pk] == 3
        assert counts[empty.pk] == 0

    def test_imported_vocabulary_shows_its_publisher_identifier_and_reads_as_imported(self):
        scheme = ConceptSchemeFactory.build(external=True)
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert scheme.static_uri in html
        assert "Imported" in html

    def test_locally_authored_vocabulary_shows_neither_identifier_nor_imported_wording(self):
        scheme = ConceptSchemeFactory.build()
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert "Imported" not in html
        assert "Held here" in html

    def test_reports_the_number_of_concepts_it_holds(self):
        scheme = ConceptSchemeFactory.build()
        scheme.concept_count = 3

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert "3 concepts" in html

    def test_a_vocabulary_with_no_concepts_reports_none_rather_than_blank(self):
        scheme = ConceptSchemeFactory.build()
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert "0 concepts" in html

    def test_a_vocabulary_with_no_description_renders_without_a_stray_label_or_punctuation(self):
        scheme = ConceptSchemeFactory.build(description="")
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        # Only the concept-count line renders as a <p> — nothing stands in for the
        # missing description, no empty label and no trailing punctuation.
        assert html.count("<p") == 1
