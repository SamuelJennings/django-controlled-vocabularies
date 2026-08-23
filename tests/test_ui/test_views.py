"""Tests for :mod:`controlled_vocabularies.ui.views` (T006-T009, T011-T013)."""

import pytest
from bs4 import BeautifulSoup
from django.db import connection
from django.template.loader import render_to_string
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import translation

from controlled_vocabularies.models import ConceptLabel
from controlled_vocabularies.ui.views import VocabularyDetailView, VocabularyListView
from tests.factories import ConceptFactory, ConceptNoteFactory, ConceptSchemeFactory

ROW_TEMPLATE = "controlled_vocabularies/ui/conceptscheme_list_item.html"
CONCEPT_ROW_TEMPLATE = "controlled_vocabularies/ui/concept_list_item.html"


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


class TestVocabularyListEntry:
    """An entry's description, size and origin (FR-002, FR-003, User Story 1 scenarios 2-5).

    The row partial's own rendering is exercised directly, through the same template it is
    rendered from on the page (``render_to_string``, matching what ``{% render_list_item %}``
    does), so an assertion about one row is never confused by the page's own chrome — the
    pagination summary line and the empty-state component are also ``<c-text>``/``<p>`` output
    and would otherwise be indistinguishable from the row's.
    """

    def test_an_entry_names_and_describes_its_vocabulary(self):
        # The two things every entry must carry (FR-002, User Story 1 scenario 4) and the
        # two nothing else asserts: every other case here builds a factory scheme whose
        # description is blank, so the description branch is never taken and deleting
        # either the title or the description from the partial would leave them all green.
        # Line coverage does not stand in for this — templates are not measured.
        scheme = ConceptSchemeFactory.build(
            name="Geological Time Scale",
            description="Periods, epochs and ages of the geological record.",
        )
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert scheme.name in html
        assert scheme.description in html

    def test_an_entry_leads_to_the_vocabularys_own_page(self):
        # T004, FR-013: the list finally leads somewhere. #140 shipped these entries
        # unlinked because no address served a vocabulary yet; T001 gives them one, and
        # the name is what carries it.
        scheme = ConceptSchemeFactory.build(name="Geological Time Scale")
        scheme.concept_count = 0
        detail_url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})
        anchor = BeautifulSoup(html, "html.parser").find("a", href=detail_url)

        assert anchor is not None
        assert anchor.text.strip() == scheme.name

    def test_a_description_running_to_several_paragraphs_is_shortened(self):
        # An entry stays scannable however long its description is (spec.md Edge Cases).
        # The assertion is on the rendered text rather than on a class name deliberately:
        # a CSS clamp cannot be relied on here (decisions.md D14), so what is checked is
        # that the entry does not carry the whole description, not how it avoids doing so.
        description = " ".join(f"word{index}" for index in range(400))
        scheme = ConceptSchemeFactory.build(name="Verbose", description=description)
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})

        assert "word0" in html
        assert "word399" not in html
        assert len(BeautifulSoup(html, "html.parser").get_text()) < len(description)

    @pytest.mark.django_db
    def test_get_queryset_annotates_the_real_concept_count(self, client):
        populated = ConceptSchemeFactory()
        ConceptFactory.create_batch(3, scheme=populated)
        empty = ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))

        counts = {vocabulary.pk: vocabulary.concept_count for vocabulary in response.context["object_list"]}
        assert counts[populated.pk] == 3
        assert counts[empty.pk] == 0

    def test_imported_vocabulary_shows_its_publisher_identifier_as_a_link_and_reads_as_imported(self):
        # T003: the identifier is a link now, not plain text (#140's D6 reversed) — the
        # anchor's href and text are both the publisher's identifier, unrewritten, and it
        # carries rel="noopener" since it points at an address this site does not control.
        scheme = ConceptSchemeFactory.build(external=True)
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})
        soup = BeautifulSoup(html, "html.parser")
        anchor = soup.find("a", href=scheme.static_uri)

        assert anchor is not None
        assert anchor.text == scheme.static_uri
        assert anchor.get("rel") == ["noopener"]
        assert "Imported" in html

    def test_a_locally_authored_vocabulary_still_shows_no_identifier(self):
        # decisions.md D8: T003 makes an existing identifier display a link, but which
        # vocabularies show one at all on this page is unchanged from #140 — none for a
        # vocabulary held here. That case gains a link only on the vocabulary's own page.
        scheme = ConceptSchemeFactory.build()
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})
        soup = BeautifulSoup(html, "html.parser")

        assert soup.find("a", href=scheme.local_url) is None

    def test_a_urn_identifier_is_still_rendered_as_a_link_unrewritten(self):
        scheme = ConceptSchemeFactory.build(static_uri="urn:nbn:example:vocab-1")
        scheme.concept_count = 0

        html = render_to_string(ROW_TEMPLATE, {"object": scheme})
        soup = BeautifulSoup(html, "html.parser")
        anchor = soup.find("a", href="urn:nbn:example:vocab-1")

        assert anchor is not None
        assert anchor.text == "urn:nbn:example:vocab-1"

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


class TestVocabularyListEmptyState:
    """A site holding no vocabularies says so (FR-011, SC-006, User Story 1 scenario 7).

    US-2's second empty state (a search matching nothing) does not exist yet — this story
    has no search — so both hooks return the empty-site wording unconditionally for now.
    """

    @pytest.mark.django_db
    def test_an_empty_site_returns_200_with_wording_that_says_the_site_holds_no_vocabularies(self, client):
        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))

        assert response.status_code == 200
        assert "no vocabularies" in response.content.decode()

    @pytest.mark.django_db
    def test_get_empty_state_heading_names_the_site_as_holding_none(self, rf):
        view = VocabularyListView()
        view.request = rf.get("/")

        assert "no vocabularies" in str(view.get_empty_state_heading())


class TestVocabularySearch:
    """A search narrows the list by name and by description (FR-006, SC-006, User Story 2
    scenarios 1-3 and 7).
    """

    @pytest.mark.django_db
    def test_a_word_from_the_name_narrows_to_that_vocabulary(self, client):
        match = ConceptSchemeFactory(name="Geological Time Scale")
        ConceptSchemeFactory(name="Soil Classification")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "Geological"})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    def test_a_word_appearing_only_in_the_description_narrows_too(self, client):
        match = ConceptSchemeFactory(name="Alpha", description="Covers stratigraphy and rock units")
        ConceptSchemeFactory(name="Beta", description="Covers something else entirely")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "stratigraphy"})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    def test_matching_ignores_case(self, client):
        match = ConceptSchemeFactory(name="Geological Time Scale")
        ConceptSchemeFactory(name="Soil Classification")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "geological"})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    @pytest.mark.parametrize("term", ["%", "_", "'"])
    def test_a_term_containing_a_like_wildcard_or_a_quote_is_looked_for_literally(self, client, term):
        # icontains escapes %, _ and the backslash before building the LIKE pattern, so none
        # of these terms are wildcards here — none of the seeded names or descriptions
        # contain the literal character, so a correct implementation matches nothing.
        ConceptSchemeFactory.create_batch(3)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": term})

        assert list(response.context["object_list"]) == []

    @pytest.mark.django_db
    def test_a_non_latin_term_matches_its_vocabulary(self, client):
        match = ConceptSchemeFactory(name="地質年代")
        ConceptSchemeFactory(name="Soil Classification")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "地質"})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    @pytest.mark.skipif(connection.vendor != "sqlite", reason="the limitation under test is SQLite's")
    @pytest.mark.parametrize(
        ("name", "term", "matches"),
        [
            ("Ecology", "ECOLOGY", True),
            ("Ökologie", "ÖKOLOGIE", True),
            ("Ökologie", "ökologie", False),
            ("Гидрология", "гидрология", False),
        ],
    )
    def test_case_insensitive_matching_covers_ascii_letters_only_on_sqlite(self, client, name, term, matches):
        # The case half of the non-Latin edge case, which the test above cannot reach:
        # Japanese has no case, so it passes whether or not case folding works. On SQLite
        # `LIKE` folds ASCII letters and nothing else, so a vocabulary named `Ökologie` is
        # not found by `ökologie` — a documented Django limitation with no ORM-level repair
        # (`Lower()` compiles to the same ASCII-only `LOWER()`). PostgreSQL folds the whole
        # of Unicode and matches. Pinned rather than left implicit so the day it changes is
        # a failing test rather than a silent difference between two supported backends;
        # disclosed in the README, and FR-006 is written against it.
        scheme = ConceptSchemeFactory(name=name)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": term})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert (listed == {scheme.pk}) is matches

    @pytest.mark.django_db
    def test_a_search_far_longer_than_any_real_one_still_answers(self, client):
        # Unbounded, the upstream mixin ORs one condition per word per field, and past
        # roughly 400 words the query exceeds SQLite's parser depth limit and the page 500s
        # for anyone who can reach it (django-mvp#281). 600 words fits an ordinary request
        # line, so nothing stands in the way of sending it.
        ConceptSchemeFactory(name="Geology")
        term = " ".join(f"word{index}" for index in range(600))

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": term})

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_a_search_past_the_bound_keeps_its_first_words_and_drops_the_rest(self, client):
        # The cost of the bound above, pinned rather than left implicit. Matching is OR, so
        # dropping words drops matches — a term long enough to be truncated is answered on
        # its first 100 words alone. The bound sits far above any search a person means, so
        # this is reachable only by a term nobody typed on purpose.
        # Zero-padded so no word is a substring of another: unpadded, `word5` matches
        # `word500` and the late vocabulary would be found through a word that survived
        # truncation, which would pass the assertion below for the wrong reason.
        early = ConceptSchemeFactory(name="word003 vocabulary")
        late = ConceptSchemeFactory(name="word500 vocabulary")
        term = " ".join(f"word{index:03d}" for index in range(600))

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": term})

        listed = {vocabulary.pk for vocabulary in response.context["object_list"]}
        assert early.pk in listed
        assert late.pk not in listed

    @pytest.mark.django_db
    def test_a_search_of_nothing_but_whitespace_is_not_a_search(self, client):
        # It filters nothing (the search mixin strips before testing for a term), so the
        # page must not read as searched either: no prefilled box, no offer of a way back
        # from a search that never happened.
        ConceptSchemeFactory.create_batch(2)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "   "})
        content = response.content.decode()

        assert len(response.context["object_list"]) == 2
        assert "Show all vocabularies" not in content

    @pytest.mark.skip(
        reason=(
            "Waiting on django-mvp/django-mvp#282 (tracked here as #147). The search box prefills itself from the raw "
            "?q= value rather than the stripped one, so a whitespace-only query comes back in the "
            "box as whitespace while filtering nothing — the page reads as searched when it is "
            "not. The prefill belongs to django-mvp's own search component, and correcting it "
            "here would mean overriding the page template. Filtering is unaffected and is "
            "asserted above."
        )
    )
    @pytest.mark.django_db
    def test_a_whitespace_only_search_does_not_come_back_in_the_box(self, client):
        ConceptSchemeFactory.create_batch(2)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "   "})
        soup = BeautifulSoup(response.content, "html.parser")

        assert soup.find("input", attrs={"name": "q"}).get("value", "") == ""

    @pytest.mark.django_db
    def test_the_rendered_page_carries_a_search_input_and_nothing_else(self, client):
        # The actions block holds search and only search. Sort, filter and create are all
        # part of the toolbar django-mvp renders by default, and all three are out of scope
        # (spec.md scope note): sorting is not asked for, filtering was ruled out for want
        # of an axis, and nothing here creates a vocabulary.
        ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))
        content = response.content.decode()

        assert 'name="q"' in content
        assert 'name="o"' not in content
        assert "filterModal" not in content
        assert "Add new" not in content

    @pytest.mark.skip(
        reason=(
            "Waiting on django-mvp/django-mvp#282 (tracked here as #147): the shipped search control's input and button "
            "carry form=\"filterForm\", and the only element with that id lives inside the filter "
            "action, so a page rendering search alone has a box wired to nothing. Fixing it here "
            "would mean overriding django-mvp's page template, which is the thing django-mvp exists "
            "to make unnecessary and which would outlive the upstream fix. Unskip when a released "
            "django-mvp puts the form element in the actions wrapper."
        )
    )
    @pytest.mark.django_db
    def test_the_search_input_belongs_to_a_get_form_that_actually_exists(self, client):
        # The shipped search action's input and button both carry a hard-coded
        # form="filterForm" attribute, and upstream only defines an element with that id
        # inside the *filter* action (research R4) — render search alone and the box is
        # wired to nothing. A query-string assertion alone would not catch this: it builds
        # the URL directly and never touches the box's own wiring. Parsing the markup and
        # confirming a real <form id="filterForm"> nests the input is what proves the box
        # itself would submit.
        ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))
        soup = BeautifulSoup(response.content, "html.parser")

        form = soup.find("form", id="filterForm")
        assert form is not None
        assert form.get("method", "").lower() == "get"
        assert form.find("input", attrs={"name": "q"}) is not None
        assert form.find(attrs={"type": "submit"}) is not None


class TestVocabularySearchAcrossRequestsAndPages:
    """A search survives being linked to, and being paged through (FR-007, FR-008, FR-010,
    User Story 2 scenarios 5 and 6). No production change expected: django-mvp builds
    pagination links with Django's ``{% querystring %}`` tag, which keeps every parameter but
    ``page`` — this proves that rather than assuming it.
    """

    @pytest.mark.django_db
    def test_requesting_the_same_search_address_twice_returns_the_same_set_in_the_same_order(self, client):
        ConceptSchemeFactory(name="Stratigraphy Unit A")
        ConceptSchemeFactory(name="Stratigraphy Unit B")
        ConceptSchemeFactory(name="Soil Classification")
        url = reverse("controlled_vocabularies_ui:vocabulary-list")

        first = [vocabulary.pk for vocabulary in client.get(url, {"q": "Stratigraphy"}).context["object_list"]]
        second = [vocabulary.pk for vocabulary in client.get(url, {"q": "Stratigraphy"}).context["object_list"]]

        assert first == second
        assert len(first) == 2

    @pytest.mark.django_db
    def test_following_the_rendered_link_to_page_two_keeps_the_search_applied(self, client):
        matching = [ConceptSchemeFactory(name=f"Stratigraphy Unit {i:02d}") for i in range(30)]
        ConceptSchemeFactory.create_batch(5)
        url = reverse("controlled_vocabularies_ui:vocabulary-list")

        first_page = client.get(url, {"q": "Stratigraphy"})
        first_page_pks = {vocabulary.pk for vocabulary in first_page.context["object_list"]}
        assert len(first_page_pks) == first_page.context["paginator"].per_page

        # Read the link out of the markup rather than constructing ?page=2 by hand — that
        # is the only way a broken query-string tag on the pagination link would show up.
        soup = BeautifulSoup(first_page.content, "html.parser")
        page_two_href = next(
            a["href"] for a in soup.find_all("a", href=True) if "page=2" in a["href"] and "q=" in a["href"]
        )

        second_page = client.get(url + page_two_href)

        assert second_page.status_code == 200
        second_page_pks = {vocabulary.pk for vocabulary in second_page.context["object_list"]}
        matching_pks = {vocabulary.pk for vocabulary in matching}
        # The second page continues the narrowed (30-vocabulary) set, not the full one —
        # no overlap with page one, entirely inside the matched set, and together the two
        # pages account for every matching vocabulary and nothing else.
        assert second_page_pks.isdisjoint(first_page_pks)
        assert second_page_pks <= matching_pks
        assert first_page_pks | second_page_pks == matching_pks


class TestVocabularySearchEmptyState:
    """A search matching nothing says so, in its own words (FR-009, FR-011, User Story 2
    scenario 4, decisions.md D4) — distinct from T009's site-empty wording.
    """

    @pytest.mark.django_db
    def test_a_search_matching_nothing_returns_200_with_no_match_wording_and_the_term_echoed(self, client):
        ConceptSchemeFactory(name="Soil Classification")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"), {"q": "Stratigraphy"})
        content = response.content.decode()

        assert response.status_code == 200
        assert "Stratigraphy" in content
        # The exact site-empty string, not a loose substring — "no vocabularies" itself
        # is not a safe check here since it is also a substring of some plausible
        # no-match wordings.
        assert "This site holds no vocabularies" not in content

    @pytest.mark.skip(
        reason=(
            "Waiting on django-mvp/django-mvp#282 (tracked here as #147). The way back to the unsearched list has to be a "
            "link in the page's actions area: django-mvp renders the empty-state heading and message "
            "as autoescaped strings with no slot, so an anchor inside the message would render as "
            "literal text, and mark_safe over a string that also carries the search term would emit "
            "that term unescaped. Placing the link needs the page template, and this package no longer "
            "overrides it. The no-match message still names the term (test above); only the link is "
            "absent. Unskip when the actions area is reachable without an override."
        )
    )
    @pytest.mark.django_db
    def test_a_search_matching_nothing_offers_a_link_back_to_the_unsearched_list(self, client):
        ConceptSchemeFactory(name="Soil Classification")
        list_url = reverse("controlled_vocabularies_ui:vocabulary-list")

        response = client.get(list_url, {"q": "Stratigraphy"})
        soup = BeautifulSoup(response.content, "html.parser")

        hrefs = {a["href"] for a in soup.find_all("a", href=True)}
        assert list_url in hrefs

    @pytest.mark.django_db
    def test_an_empty_site_with_no_search_keeps_t009s_wording_and_shows_no_such_link(self, client):
        list_url = reverse("controlled_vocabularies_ui:vocabulary-list")

        response = client.get(list_url)
        soup = BeautifulSoup(response.content, "html.parser")
        content = response.content.decode()

        assert "no vocabularies" in content.lower()
        hrefs = {a["href"] for a in soup.find_all("a", href=True)}
        assert list_url not in hrefs

    def test_the_no_match_and_site_empty_headings_are_different_strings(self, rf):
        no_match_view = VocabularyListView()
        no_match_view.request = rf.get("/", {"q": "Stratigraphy"})

        site_empty_view = VocabularyListView()
        site_empty_view.request = rf.get("/")

        assert str(no_match_view.get_empty_state_heading()) != str(site_empty_view.get_empty_state_heading())

    @pytest.mark.django_db
    def test_a_term_containing_markup_is_escaped_in_the_response(self, client):
        # Scoped to the empty-state heading itself, not a blanket "no <script> in the
        # page" check — the page's own theme-toggle script legitimately has one. If the
        # term were rendered through mark_safe (the repair T013 explicitly rejects), an
        # HTML parser would read it as a real <script> element nested inside the
        # heading; a substring check on the raw response would not catch that, since the
        # unescaped term is also a byte-for-byte substring of the correctly escaped one.
        ConceptSchemeFactory(name="Soil Classification")
        list_url = reverse("controlled_vocabularies_ui:vocabulary-list")

        response = client.get(list_url, {"q": "<script>alert(1)</script>"})
        soup = BeautifulSoup(response.content, "html.parser")
        heading = soup.find("h3")

        assert heading.find("script") is None
        assert "<script>alert(1)</script>" in heading.get_text()


class TestVocabularyDetail:
    """A vocabulary's own address serves a page, and an unknown one does not (FR-001,
    FR-017, User Story 1 scenarios 1, 7, 8).
    """

    @pytest.mark.django_db
    def test_a_known_vocabulary_serves_its_page_anonymously(self, client):
        scheme = ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_a_slug_nothing_has_returns_404(self, client):
        response = client.get(
            reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": "no-such-vocabulary"})
        )

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_the_page_title_is_the_vocabularys_name(self, client):
        scheme = ConceptSchemeFactory(name="Geological Time Scale")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))

        assert response.context["page"]["title"] == scheme.name

    @pytest.mark.django_db
    def test_a_vocabulary_named_in_a_non_latin_script_still_serves_its_own_page(self, client):
        # <str:slug>, not <slug:slug>: the model slugifies with allow_unicode=True, and
        # Django's slug converter matches ASCII only. A vocabulary named this way would
        # 404 on its own page under the obvious converter.
        scheme = ConceptSchemeFactory(name="地質年代")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))

        assert response.status_code == 200


class TestVocabularyDetailDescriptionAndProvenance:
    """The page describes the vocabulary and says where it came from (FR-002, FR-003,
    User Story 1 scenarios 1, 2, 3, 5).
    """

    @pytest.mark.django_db
    def test_a_vocabulary_with_a_description_shows_it_and_reads_as_held_here(self, client):
        scheme = ConceptSchemeFactory(description="Periods, epochs and ages of the geological record.")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        content = response.content.decode()

        assert scheme.description in content
        assert "Held here" in content

    @pytest.mark.django_db
    def test_a_vocabulary_with_no_description_renders_no_heading_or_empty_element(self, client):
        scheme = ConceptSchemeFactory(description="")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        soup = BeautifulSoup(response.content, "html.parser")

        assert soup.find(class_="vocabulary-description") is None

    @pytest.mark.django_db
    def test_a_vocabulary_published_elsewhere_shows_its_publisher_identifier_and_names_no_publisher(self, client):
        scheme = ConceptSchemeFactory(external=True)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        content = response.content.decode()

        assert scheme.static_uri in content
        assert "Held here" not in content
        assert "Publisher" not in content

    @pytest.mark.django_db
    def test_a_description_running_to_several_paragraphs_is_shortened(self, client):
        description = " ".join(f"word{index}" for index in range(400))
        scheme = ConceptSchemeFactory(description=description)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        content = response.content.decode()

        assert "word0" in content
        assert "word399" not in content


class TestVocabularyDetailIdentifierLink:
    """The identifier is a link on this page too (FR-004, identifier half of FR-013,
    User Story 1 scenario 4).
    """

    @pytest.mark.django_db
    def test_a_vocabulary_published_elsewhere_links_to_its_publisher_address(self, client):
        scheme = ConceptSchemeFactory(external=True)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        soup = BeautifulSoup(response.content, "html.parser")
        anchor = soup.find("a", href=scheme.static_uri)

        assert anchor is not None
        assert anchor.text == scheme.static_uri
        assert anchor.get("rel") == ["noopener"]

    @pytest.mark.django_db
    def test_a_vocabulary_held_here_links_to_the_address_this_site_composes(self, client):
        scheme = ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        soup = BeautifulSoup(response.content, "html.parser")
        anchor = soup.find("a", href=scheme.uri)

        assert anchor is not None
        assert anchor.text == scheme.uri
        assert anchor.get("rel") == ["noopener"]

    @pytest.mark.django_db
    def test_a_urn_identifier_is_still_rendered_as_a_link_unrewritten(self, client):
        scheme = ConceptSchemeFactory(static_uri="urn:nbn:example:vocab-1")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        soup = BeautifulSoup(response.content, "html.parser")
        anchor = soup.find("a", href="urn:nbn:example:vocab-1")

        assert anchor is not None
        assert anchor.text == "urn:nbn:example:vocab-1"


class TestVocabularyDetailConceptList:
    """Every concept the vocabulary holds appears, flat, and only this vocabulary's
    (FR-006, FR-012, User Story 2 scenarios 1, 2, 3, 9).
    """

    @pytest.mark.django_db
    def test_a_multi_level_hierarchy_renders_flat_with_every_concept_exactly_once(self, client):
        scheme = ConceptSchemeFactory()
        top = ConceptFactory(scheme=scheme, label="Top Concept")
        middle = ConceptFactory(scheme=scheme, label="Middle Concept")
        bottom = ConceptFactory(scheme=scheme, label="Bottom Concept")
        middle.add_broader(top)
        bottom.add_broader(middle)

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        soup = BeautifulSoup(response.content, "html.parser")

        listed = list(response.context["object_list"])
        assert len(listed) == 3
        assert {concept.pk for concept in listed} == {top.pk, middle.pk, bottom.pk}

        # Flatness asserted on structure, not a row count: a card for the concept three
        # levels down (`bottom`) must not be nested inside the card for one at the top
        # (`top`) — a tree-shaped rendering could total three cards too and still pass
        # a count-only assertion.
        cards = soup.find_all(class_="card")
        assert len(cards) == 3
        for card in cards:
            assert card.find(class_="card") is None

    @pytest.mark.django_db
    def test_a_concepts_row_carries_only_its_label(self):
        # A fully decorated concept — an alternative label, a note, a static
        # identifier and a relation to another concept — rendered through the row
        # partial alone. None of that belongs on the row (T008): no definition, no
        # note, no identifier, no relation, and nothing to follow.
        concept = ConceptFactory(label="Granite", external=True)
        concept.resolved_label = concept.label  # what T009's annotation carries in real use
        ConceptNoteFactory(concept=concept, value="A coarse-grained igneous rock.")
        concept.add_label(language="en", kind="alternative", text="granitic rock")
        other = ConceptFactory(scheme=concept.scheme, label="Basalt")
        concept.add_broader(other)

        html = render_to_string(CONCEPT_ROW_TEMPLATE, {"object": concept})
        soup = BeautifulSoup(html, "html.parser")

        assert concept.label in html
        assert "A coarse-grained igneous rock." not in html
        assert "granitic rock" not in html
        assert concept.static_uri not in html
        assert "Basalt" not in html
        assert soup.find("a") is None

    @pytest.mark.django_db
    def test_a_concept_belonging_to_another_vocabulary_does_not_appear(self, client):
        scheme = ConceptSchemeFactory()
        other_scheme = ConceptSchemeFactory()
        concept = ConceptFactory(scheme=scheme, label="Granite")
        foreign = ConceptFactory(scheme=other_scheme, label="Basalt")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {concept.pk}
        assert foreign.pk not in listed


class TestVocabularyDetailConceptLabel:
    """A concept is named in the reading language (FR-010, SC-005, User Story 2
    scenarios 4, 5).
    """

    @pytest.mark.django_db
    def test_a_concept_with_a_preferred_label_in_the_active_language_shows_it(self, client):
        # Deliberately not a substring of the default-language label ("Granite") —
        # a naive test built on "Granit" would pass whether the annotation resolved
        # the German label or merely truncated the English one.
        scheme = ConceptSchemeFactory()
        concept = ConceptFactory(scheme=scheme, label="Granite")
        concept.add_label(language="de", kind="preferred", text="Kristallgestein")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        with translation.override("de"):
            response = client.get(url)

        content = response.content.decode()
        assert "Kristallgestein" in content
        assert concept.label not in content

    @pytest.mark.django_db
    def test_a_concept_with_no_label_in_the_active_language_falls_back_to_its_default_one(self, client):
        # Concept.label *is* the preferred label in the vocabulary's own default
        # language (D11) — the fallback needs no separate ConceptLabel row.
        scheme = ConceptSchemeFactory()
        ConceptFactory(scheme=scheme, label="Granite")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        with translation.override("de"):
            response = client.get(url)

        assert "Granite" in response.content.decode()

    @pytest.mark.django_db
    def test_query_count_is_flat_regardless_of_how_many_concepts_the_vocabulary_holds(
        self, client, django_assert_num_queries
    ):
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(3, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        with CaptureQueriesContext(connection) as captured:
            client.get(url)
        baseline = len(captured.captured_queries)

        ConceptFactory.create_batch(27, scheme=scheme)

        with django_assert_num_queries(baseline):
            client.get(url)


class TestVocabularyDetailConceptOrder:
    """Order follows the label shown, not the one stored, and stays stable (FR-007,
    User Story 2 scenario 6, SC-004).
    """

    @pytest.mark.django_db
    def test_order_follows_the_label_shown_under_the_active_language_not_the_stored_one(self, client):
        scheme = ConceptSchemeFactory()
        # `zebra`'s own (default-language) label sorts last; its German preferred
        # label sorts first. `antelope` has no German label, so it falls back to its
        # own — the ordering must follow whichever label is actually resolved for the
        # active language, never the stored default-language one.
        zebra = ConceptFactory(scheme=scheme, label="Zebra")
        zebra.add_label(language="de", kind="preferred", text="Aardvark")
        antelope = ConceptFactory(scheme=scheme, label="Antelope")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        with translation.override("de"):
            german_order = [c.pk for c in client.get(url).context["object_list"]]
        default_order = [c.pk for c in client.get(url).context["object_list"]]

        assert german_order == [zebra.pk, antelope.pk]
        assert default_order == [antelope.pk, zebra.pk]

    @pytest.mark.django_db
    def test_two_identically_labelled_concepts_produce_a_deterministic_order(self, client):
        scheme = ConceptSchemeFactory()
        first = ConceptFactory(scheme=scheme, label="Duplicate")
        # A second concept with the same label would collide on its derived slug —
        # .build() plus set_slug() gives it a distinct one without touching the label
        # under test, exactly as ConceptSchemeFactory's own tiebreak tests do.
        second = ConceptFactory.build(scheme=scheme, label="Duplicate")
        second.set_slug("aaa-sorts-first-by-slug")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        first_request = [c.pk for c in client.get(url).context["object_list"]]
        second_request = [c.pk for c in client.get(url).context["object_list"]]

        assert first_request == second_request == [first.pk, second.pk]

    @pytest.mark.django_db
    def test_two_requests_return_the_same_order(self, client):
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(5, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        first = [c.pk for c in client.get(url).context["object_list"]]
        second = [c.pk for c in client.get(url).context["object_list"]]

        assert first == second


class TestVocabularyDetailConceptPaging:
    """A long list is paged, and an empty vocabulary says so (FR-014, FR-016, User
    Story 2 scenarios 7, 8).
    """

    @pytest.mark.django_db
    def test_a_long_list_is_paged_and_the_second_page_renders(self, client):
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(30, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        first_page = client.get(url)
        per_page = first_page.context["paginator"].per_page
        assert len(first_page.context["object_list"]) == per_page

        soup = BeautifulSoup(first_page.content, "html.parser")
        page_two_href = next(a["href"] for a in soup.find_all("a", href=True) if "page=2" in a["href"])

        second_page = client.get(url + page_two_href)

        assert second_page.status_code == 200
        assert len(second_page.context["object_list"]) == 30 - per_page

    @pytest.mark.django_db
    def test_a_paging_link_carries_forward_an_active_query_parameter(self, client):
        # django-mvp's paging component builds each link with Django's own
        # `{% querystring %}` tag, which keeps every parameter but `page` — nothing is
        # done here to make that so. Proven with a parameter this story gives no
        # filtering meaning to (search itself is US-3's, not this story's), so the
        # assertion is about the paging mechanism carrying a parameter forward, not
        # about a filter this view does not yet have. Read the link out of the markup
        # rather than constructing it by hand — that is the only way a broken
        # querystring tag would show up.
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(30, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(url, {"unrelated": "kept"})
        soup = BeautifulSoup(response.content, "html.parser")

        page_two_href = next(
            a["href"]
            for a in soup.find_all("a", href=True)
            if "page=2" in a["href"] and "unrelated=kept" in a["href"]
        )

        second_page = client.get(url + page_two_href)
        assert second_page.status_code == 200

    @pytest.mark.django_db
    def test_a_vocabulary_holding_no_concepts_says_so_and_the_rest_of_the_page_still_renders(self, client):
        scheme = ConceptSchemeFactory(description="Periods, epochs and ages of the geological record.")

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}))
        content = response.content.decode()

        assert response.status_code == 200
        assert "no concepts" in content.lower()
        assert scheme.name in content
        assert scheme.description in content


class TestVocabularyDetailConceptSearch:
    """The search matches every name a term goes by (FR-008, FR-009, User Story 3
    scenarios 1, 2, 3, 4, 6, 9). Each assertion below uses its own concept, so a pass
    cannot come from the wrong field matching instead (tasks.md T013).
    """

    @pytest.mark.django_db
    def test_a_word_only_in_the_preferred_label_finds_it(self, client):
        match = ConceptFactory(label="Granite")
        ConceptFactory(scheme=match.scheme, label="Basalt")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "Granite"})

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    def test_a_word_only_in_an_alternative_label_finds_it(self, client):
        match = ConceptFactory(label="Granite")
        match.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="granitic rock")
        ConceptFactory(scheme=match.scheme, label="Basalt")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "granitic"})

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    def test_a_word_only_in_a_hidden_label_finds_it_and_the_label_is_shown_nowhere(self, client):
        match = ConceptFactory(label="Granite")
        match.add_label(language="en", kind=ConceptLabel.Kind.HIDDEN, text="granate")
        ConceptFactory(scheme=match.scheme, label="Basalt")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "granate"})
        # The search box echoes back the raw ?q= value as an <input value="…"> attribute
        # — that is an echo of what was typed, not a display of the hidden label, and it
        # is not part of the rendered text a reader sees. get_text() reads only text
        # nodes, so the box's echo is excluded here the same way it is excluded from a
        # reader's view of the page.
        rendered_text = BeautifulSoup(response.content, "html.parser").get_text()

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {match.pk}
        assert "granate" not in rendered_text

    @pytest.mark.django_db
    def test_a_concept_matching_on_several_labels_at_once_is_listed_once(self, client):
        # Searching across a reverse relation joins one row per matching label, so a
        # concept whose preferred, alternative and hidden labels all match would appear
        # three times without the de-duplication the search applies. Asserted as a list,
        # not a set: every other assertion in this class compares sets, which cannot see
        # a repeat.
        match = ConceptFactory(label="Granite")
        match.add_label(language="en", kind=ConceptLabel.Kind.ALTERNATIVE, text="Granite rock")
        match.add_label(language="en", kind=ConceptLabel.Kind.HIDDEN, text="Granite stone")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "Granite"})

        assert [concept.pk for concept in response.context["object_list"]] == [match.pk]

    @pytest.mark.django_db
    def test_a_word_only_in_the_definition_does_not_find_the_concept(self, client):
        concept = ConceptFactory(label="Granite")
        ConceptNoteFactory(concept=concept, value="A coarse-grained igneous rock.")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": concept.scheme.slug})

        response = client.get(url, {"q": "igneous"})

        assert list(response.context["object_list"]) == []

    @pytest.mark.django_db
    def test_a_matching_concept_in_another_vocabulary_is_not_returned(self, client):
        match = ConceptFactory(label="Granite")
        other_scheme = ConceptSchemeFactory()
        foreign = ConceptFactory(scheme=other_scheme, label="Granite Boulder")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "Granite"})

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {match.pk}
        assert foreign.pk not in listed

    @pytest.mark.django_db
    def test_a_search_run_directly_from_the_second_page_still_reaches_every_concept(self, client):
        # Scenario 6: requested with page=2 up front, not reached by following a link
        # from page one — a search scoped to the page being viewed would filter only
        # whatever unfiltered page two happens to hold, which is a mix of matching and
        # non-matching concepts here, and would leak the non-matching ones through.
        scheme = ConceptSchemeFactory()
        matching = [ConceptFactory(scheme=scheme, label=f"Stratigraphy Unit {i:02d}") for i in range(30)]
        non_matching = ConceptFactory.create_batch(5, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(url, {"q": "Stratigraphy", "page": 2})

        assert response.status_code == 200
        listed = {c.pk for c in response.context["object_list"]}
        matching_pks = {c.pk for c in matching}
        non_matching_pks = {c.pk for c in non_matching}
        assert listed <= matching_pks
        assert listed.isdisjoint(non_matching_pks)
        assert response.context["paginator"].count == 30


class TestVocabularyDetailConceptSearchAddressAndCase:
    """A search is carried in the address, and case is ignored (FR-008, User Story 3
    scenarios 5, 8; tasks.md T014). ADR 0014 covers the letter-case limit outside ASCII.
    """

    @pytest.mark.django_db
    def test_a_narrowed_lists_address_opened_fresh_returns_the_same_concepts(self, client):
        scheme = ConceptSchemeFactory()
        match = ConceptFactory(scheme=scheme, label="Stratigraphy Unit")
        ConceptFactory(scheme=scheme, label="Soil Classification")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        first = {c.pk for c in client.get(url, {"q": "Stratigraphy"}).context["object_list"]}
        second = {c.pk for c in client.get(url, {"q": "Stratigraphy"}).context["object_list"]}

        assert first == second == {match.pk}

    @pytest.mark.django_db
    def test_matching_ignores_ascii_case(self, client):
        match = ConceptFactory(label="Granite")
        ConceptFactory(scheme=match.scheme, label="Basalt")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": match.scheme.slug})

        response = client.get(url, {"q": "granite"})

        listed = {c.pk for c in response.context["object_list"]}
        assert listed == {match.pk}

    @pytest.mark.django_db
    @pytest.mark.parametrize("term", ["%", "_", "'"])
    def test_a_term_containing_a_like_wildcard_or_a_quote_is_looked_for_literally(self, client, term):
        # icontains escapes %, _ and the backslash before building the LIKE pattern
        # (TestVocabularySearch's own precedent, #140) — none of these terms are
        # wildcards here, and none of the seeded labels contain the literal
        # character, so a correct implementation matches nothing.
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(3, scheme=scheme)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(url, {"q": term})

        assert list(response.context["object_list"]) == []

    @pytest.mark.django_db
    @pytest.mark.skipif(connection.vendor != "sqlite", reason="the limitation under test is SQLite's")
    @pytest.mark.parametrize(
        ("label", "term", "matches"),
        [
            ("Ecology", "ECOLOGY", True),
            ("Ökologie", "ÖKOLOGIE", True),
            ("Ökologie", "ökologie", False),
            ("Гидрология", "гидрология", False),
        ],
    )
    def test_case_insensitive_matching_covers_ascii_letters_only_on_sqlite(self, client, label, term, matches):
        # ADR 0014: SQLite's LIKE folds ASCII letters only, so a concept labelled
        # Ökologie is found by ÖKOLOGIE and not by ökologie; PostgreSQL folds the
        # whole of Unicode and matches either way. Pinned rather than left implicit,
        # per the precedent this ADR sets for every search surface that follows the
        # one it names — this is that surface.
        concept = ConceptFactory(label=label)
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": concept.scheme.slug})

        response = client.get(url, {"q": term})

        listed = {c.pk for c in response.context["object_list"]}
        assert (listed == {concept.pk}) is matches


class TestVocabularyDetailConceptSearchEmptyState:
    """Three empty states, told apart (FR-014, User Story 3 scenario 7; tasks.md T015,
    decisions.md D7). Read the search term stripped, the way django-mvp's own mixin
    reads it before filtering, so the empty state and the queryset agree on whether a
    search is in force — #140's own trap (``?q=%20%20``) restated one page down.
    """

    @pytest.mark.django_db
    def test_a_search_matching_nothing_returns_200_with_no_match_wording_and_the_term_echoed(self, client):
        scheme = ConceptSchemeFactory()
        ConceptFactory(scheme=scheme, label="Granite")
        url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(url, {"q": "Basalt"})
        content = response.content.decode()

        assert response.status_code == 200
        assert "Basalt" in content
        # The exact no-concepts string, not a loose substring — "no concepts" itself
        # would also match a plausible no-match wording.
        assert "This vocabulary holds no concepts" not in content

    @pytest.mark.django_db
    def test_a_search_matching_nothing_offers_a_link_back_to_the_unsearched_vocabulary(self, client):
        # Unlike the list of vocabularies (#140, skipped waiting on django-mvp/django-mvp#282),
        # this page has its own template (T007) and can render the link directly rather
        # than needing django-mvp's actions area, so this is not skipped.
        scheme = ConceptSchemeFactory()
        ConceptFactory(scheme=scheme, label="Granite")
        detail_url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(detail_url, {"q": "Basalt"})
        soup = BeautifulSoup(response.content, "html.parser")

        hrefs = {a["href"] for a in soup.find_all("a", href=True)}
        assert detail_url in hrefs

    @pytest.mark.django_db
    def test_a_vocabulary_holding_no_concepts_keeps_t011s_wording_and_shows_no_such_link(self, client):
        scheme = ConceptSchemeFactory()
        detail_url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(detail_url)
        soup = BeautifulSoup(response.content, "html.parser")
        content = response.content.decode()

        assert "no concepts" in content.lower()
        hrefs = {a["href"] for a in soup.find_all("a", href=True)}
        assert detail_url not in hrefs

    def test_the_no_match_and_no_concepts_headings_are_different_strings(self, rf):
        scheme = ConceptSchemeFactory.build()

        no_match_view = VocabularyDetailView()
        no_match_view.vocabulary = scheme
        no_match_view.request = rf.get("/", {"q": "Basalt"})

        empty_view = VocabularyDetailView()
        empty_view.vocabulary = scheme
        empty_view.request = rf.get("/")

        assert str(no_match_view.get_empty_state_heading()) != str(empty_view.get_empty_state_heading())

    @pytest.mark.django_db
    def test_a_whitespace_only_search_is_not_a_search(self, client):
        # #140's own trap restated one page down: a raw, unstripped `?q=%20%20` must not
        # half-search — the list stays unfiltered and no "back to the whole vocabulary"
        # link appears offering to undo a search that never happened.
        scheme = ConceptSchemeFactory()
        ConceptFactory.create_batch(2, scheme=scheme)
        detail_url = reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug})

        response = client.get(detail_url, {"q": "   "})
        soup = BeautifulSoup(response.content, "html.parser")

        assert len(response.context["object_list"]) == 2
        hrefs = {a["href"] for a in soup.find_all("a", href=True)}
        assert detail_url not in hrefs
