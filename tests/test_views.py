"""Tests for ``controlled_vocabularies.views`` (T003, FR-005, FR-012).

``TestConceptAutocompleteResults`` — a result carries exactly the identifier, the
preferred label and the vocabulary a concept belongs to (FR-005, FR-012): not the
editorial notes, hidden labels or anything else the concept holds, and not merely
those three among others — the exact key set. A second test bounds the query cost
of a full page under ``django_assert_num_queries`` (R5): ``display_label()`` walks
each concept's ``labels.all()``, so ``hook_queryset()``'s ``prefetch_related`` is
what keeps that from costing a query per row.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse

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
