"""Tests for :mod:`controlled_vocabularies.ui.views` (T006-T009)."""

import pytest
from django.db import connection
from django.template.loader import render_to_string
from django.test.utils import CaptureQueriesContext
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


class TestVocabularyListOrdering:
    """Alphabetical, stable order at a flat query cost (FR-004, SC-005, User Story 1 scenario 6).

    Every case here deliberately gives the vocabulary whose *name* should sort last a *slug*
    that would sort it first — ``ConceptScheme.slug`` is unique and Django's ``Count()``
    annotation forces a ``GROUP BY`` on every selected column including it, which this
    repo's SQLite test database satisfies through the unique index on ``slug`` when no
    explicit ordering says otherwise. A slugified name and its own name normally sort the
    same way, so a naive test would pass on that coincidence alone and prove nothing about
    the ordering this task adds — a manually diverging slug (``set_slug()``) is what makes
    the two cases distinguishable.
    """

    @pytest.mark.django_db
    def test_a_name_beginning_with_a_lowercase_letter_still_sorts_before_an_uppercase_one_later_in_the_alphabet(
        self, client
    ):
        zebra = ConceptSchemeFactory(name="Zebra")
        zebra.set_slug("aaa-sorts-first-by-slug")
        ConceptSchemeFactory(name="antelope")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))

        names = [vocabulary.name for vocabulary in response.context["object_list"]]
        # Byte order (capital Z = 0x5A, lowercase a = 0x61) would sort "Zebra" first, and
        # so would zebra's own (deliberately mis-set) slug; case-insensitive order by name
        # puts "antelope" first, as a reader expects.
        assert names == ["antelope", "Zebra"]

    @pytest.mark.django_db
    def test_two_requests_return_the_same_sequence(self, client):
        ConceptSchemeFactory.create_batch(5)
        url = reverse("controlled_vocabularies_ui:vocabulary-list")

        first = [vocabulary.pk for vocabulary in client.get(url).context["object_list"]]
        second = [vocabulary.pk for vocabulary in client.get(url).context["object_list"]]

        assert first == second

    @pytest.mark.django_db
    def test_two_vocabularies_sharing_a_name_still_produce_a_deterministic_order(self, client):
        first = ConceptSchemeFactory(name="Duplicate")
        # The slug is derived from the name and is unique app-wide, so a second same-named
        # scheme needs its own explicit slug to save at all — set_slug() is the model's own
        # supported way to give it one without touching the name under test. Set to sort
        # first by slug (and so, by the class docstring's mechanism, first if the tiebreak
        # were accidentally slug-based) while its pk sorts second — only a real `pk`
        # tiebreak on identical names produces [first.pk, second.pk] here.
        second = ConceptSchemeFactory.build(name="Duplicate")
        second.set_slug("aaa-sorts-first-by-slug")
        url = reverse("controlled_vocabularies_ui:vocabulary-list")

        first_request = [vocabulary.pk for vocabulary in client.get(url).context["object_list"]]
        second_request = [vocabulary.pk for vocabulary in client.get(url).context["object_list"]]

        assert first_request == second_request == [first.pk, second.pk]

    @pytest.mark.django_db
    def test_query_count_is_flat_regardless_of_how_many_vocabularies_the_site_holds(
        self, client, django_assert_num_queries
    ):
        # Page size is django-mvp's own inherited default (24, not restated — plan.md item 1),
        # so this proves what SC-005 actually asks: the *annotation* costs a flat number of
        # queries as the source table grows, not a query per row (an N+1 the SQLite-only test
        # DB is otherwise too small to expose). It is not a claim that thirty rows render on
        # one page.
        ConceptSchemeFactory.create_batch(3)
        url = reverse("controlled_vocabularies_ui:vocabulary-list")

        with CaptureQueriesContext(connection) as captured:
            client.get(url)
        baseline = len(captured.captured_queries)

        ConceptSchemeFactory.create_batch(27)

        with django_assert_num_queries(baseline):
            client.get(url)
