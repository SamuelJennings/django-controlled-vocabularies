"""Tests for ``controlled_vocabularies.views`` (T003, T005, FR-005, FR-012, FR-004).

``TestConceptAutocompleteResults`` — a result carries exactly the identifier, the
preferred label and the vocabulary a concept belongs to (FR-005, FR-012): not the
editorial notes, hidden labels or anything else the concept holds, and not merely
those three among others — the exact key set. A second test bounds the query cost
of a full page under ``django_assert_num_queries`` (R5): ``display_label()`` walks
each concept's ``labels.all()``, so ``hook_queryset()``'s ``prefetch_related`` is
what keeps that from costing a query per row.

``TestConceptAutocompleteSearch`` — a typed string matches a concept by any of its
three kinds of label in the active language, or by the default-language preferred
label every concept carries (FR-004, User Story 2). Every case is displayed under
the concept's preferred label, whichever label matched (FR-005).
"""

import json

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from tests.factories import ConceptFactory, ConceptSchemeFactory


class TestConceptAutocompleteResults:
    """The endpoint's JSON results carry exactly what FR-012 permits."""

    @pytest.mark.django_db
    def test_a_result_carries_exactly_the_id_display_label_and_vocabulary(self):
        scheme = ConceptSchemeFactory(name="Rock types")
        concept = ConceptFactory(scheme=scheme, label="Granite")
        concept.add_note(language="en", kind="definition", value="An igneous rock.")
        concept.add_label(language="en", kind="alternative", text="granitic rock")
        concept.add_label(language="en", kind="hidden", text="granit")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"))

        body = json.loads(response.content)
        assert len(body["results"]) == 1
        result = body["results"][0]
        assert set(result.keys()) == {"id", "display_label", "vocabulary"}
        assert result["id"] == concept.pk
        assert result["display_label"] == "Granite"
        assert result["vocabulary"] == "Rock types"

    @pytest.mark.django_db
    def test_a_full_page_of_concepts_with_labels_and_notes_costs_a_bounded_query_count(
        self, django_assert_num_queries
    ):
        scheme = ConceptSchemeFactory()
        for _ in range(20):
            concept = ConceptFactory(scheme=scheme)
            concept.add_label(language="de", kind="alternative", text="alt")
            concept.add_note(language="en", kind="definition", value="A definition.")

        with django_assert_num_queries(3):
            response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"))

        body = json.loads(response.content)
        assert len(body["results"]) == 20


class TestConceptAutocompleteSearch:
    """A typed string matches a concept by any of its labels, in the active
    language (FR-004, User Story 2). Every case is displayed under the
    concept's preferred label for the active language, whichever label the
    match was made on (FR-005)."""

    @pytest.mark.django_db
    def test_a_fragment_of_an_alternative_label_finds_the_concept_by_its_preferred_label(self):
        concept = ConceptFactory(label="Granite")
        concept.add_label(language="en", kind="alternative", text="granitic rock")
        ConceptFactory(label="Basalt")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "granitic"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]
        assert body["results"][0]["display_label"] == "Granite"

    @pytest.mark.django_db
    def test_a_fragment_of_a_hidden_label_finds_the_concept_by_its_preferred_label(self):
        concept = ConceptFactory(label="Granite")
        concept.add_label(language="en", kind="hidden", text="granit")
        ConceptFactory(label="Basalt")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "granit"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]
        assert body["results"][0]["display_label"] == "Granite"

    @pytest.mark.django_db
    def test_a_fragment_of_either_the_active_or_default_language_preferred_label_finds_the_concept_by_the_active_one(
        self,
    ):
        concept = ConceptFactory(label="Granite", multilingual=True, german_label__text="Granit")
        ConceptFactory(label="Basalt", multilingual=True, german_label__text="Basalt")

        with translation.override("de"):
            by_active_language = Client().get(
                reverse("controlled_vocabularies:concept-autocomplete"), {"q": "Granit"}
            )
            by_default_language = Client().get(
                reverse("controlled_vocabularies:concept-autocomplete"), {"q": "Granite"}
            )

        for response in (by_active_language, by_default_language):
            body = json.loads(response.content)
            assert [result["id"] for result in body["results"]] == [concept.pk]
            assert body["results"][0]["display_label"] == "Granit"

    @pytest.mark.django_db
    def test_a_concept_with_no_active_language_labels_is_found_and_shown_by_its_default_label(self):
        concept = ConceptFactory(label="Granite")
        ConceptFactory(label="Basalt")

        with translation.override("de"):
            response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "Granite"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]
        assert body["results"][0]["display_label"] == "Granite"

    @pytest.mark.django_db
    def test_a_concept_matching_on_two_of_its_labels_appears_once(self):
        concept = ConceptFactory(label="Granite")
        concept.add_label(language="en", kind="alternative", text="Granite rock")
        concept.add_label(language="en", kind="hidden", text="Granites")
        ConceptFactory(label="Basalt")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "Granit"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]

    @pytest.mark.django_db
    def test_a_search_differing_only_in_case_from_a_label_still_matches(self):
        concept = ConceptFactory(label="Granite")
        ConceptFactory(label="Basalt")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "GRANITE"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]
        assert body["results"][0]["display_label"] == "Granite"
