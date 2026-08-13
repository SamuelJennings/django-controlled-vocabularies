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
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import translation
from django_tomselect.middleware import TomSelectMiddleware

from tests.factories import ConceptFactory, ConceptSchemeFactory
from tests.testapp.models import Borehole, Sketch, Specimen


def _field_reference(model, field_name):
    """The ``<app_label>.<model>.<field_name>`` reference the control's
    widget sends (decisions.md D11), built the same way for a test as
    ``_ConceptWidgetReferenceMixin.get_autocomplete_params()`` builds it."""
    return f"{model._meta.app_label}.{model._meta.model_name}.{field_name}"


class SpecimenForm(forms.ModelForm):
    class Meta:
        model = Specimen
        fields = ["name", "rock_type"]


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
    match was made on (FR-005).

    Each search fragment is one no other clause of the filter can match: a
    fragment that is also a substring of the default-language ``label``
    column passes whether or not the label kind under test is searched at
    all, which is a test that asserts nothing about its own scenario."""

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
        concept.add_label(language="en", kind="hidden", text="granyte")
        ConceptFactory(label="Basalt")

        response = Client().get(reverse("controlled_vocabularies:concept-autocomplete"), {"q": "granyte"})

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [concept.pk]
        assert body["results"][0]["display_label"] == "Granite"

    @pytest.mark.django_db
    def test_a_fragment_of_either_the_active_or_default_language_preferred_label_finds_the_concept_by_the_active_one(
        self,
    ):
        concept = ConceptFactory(label="Granite", multilingual=True, german_label__text="Granitgestein")
        ConceptFactory(label="Basalt", multilingual=True, german_label__text="Basalt")

        with translation.override("de"):
            by_active_language = Client().get(
                reverse("controlled_vocabularies:concept-autocomplete"), {"q": "gestein"}
            )
            by_default_language = Client().get(
                reverse("controlled_vocabularies:concept-autocomplete"), {"q": "Granite"}
            )

        for response in (by_active_language, by_default_language):
            body = json.loads(response.content)
            assert [result["id"] for result in body["results"]] == [concept.pk]
            assert body["results"][0]["display_label"] == "Granitgestein"

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


@pytest.mark.django_db
class TestConceptAutocompleteRestrictionFromDeclaration:
    """FR-006, plan.md A6 path one, decisions.md D11: the endpoint derives
    what a search may return from the field declaration a ``field=``
    reference names, resolved through Django's app registry — never from
    anything else the request carries (T006)."""

    def test_a_field_declared_against_one_vocabulary_returns_only_that_vocabularys_concepts(self):
        rock_scheme = ConceptSchemeFactory(name="Rock type")
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        fossil_scheme = ConceptSchemeFactory(name="Fossil")
        rock_concept = ConceptFactory(scheme=rock_scheme, label="Granite rock")
        ConceptFactory(scheme=mineral_scheme, label="Granite ore")
        ConceptFactory(scheme=fossil_scheme, label="Granite fossil")

        response = Client().get(
            reverse("controlled_vocabularies:concept-autocomplete"),
            {"q": "Granite", "field": _field_reference(Specimen, "rock_type")},
        )

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [rock_concept.pk]

    def test_the_request_naming_a_different_vocabulary_directly_is_ignored(self):
        rock_scheme = ConceptSchemeFactory(name="Rock type")
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        rock_concept = ConceptFactory(scheme=rock_scheme, label="Granite rock")
        ConceptFactory(scheme=mineral_scheme, label="Granite ore")

        response = Client().get(
            reverse("controlled_vocabularies:concept-autocomplete"),
            {
                "q": "Granite",
                "field": _field_reference(Specimen, "rock_type"),
                # Names a vocabulary directly, through a parameter the
                # endpoint never reads. FR-006 says the restriction comes
                # from the declaration alone; this is the case that proves
                # it (prohibitions).
                "vocabulary": mineral_scheme.slug,
            },
        )

        body = json.loads(response.content)
        assert [result["id"] for result in body["results"]] == [rock_concept.pk]

    def test_a_field_declared_against_several_vocabularies_returns_exactly_those(self):
        rock_scheme = ConceptSchemeFactory(name="Rock type")
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        fossil_scheme = ConceptSchemeFactory(name="Fossil")
        rock_concept = ConceptFactory(scheme=rock_scheme, label="Basalt rock")
        mineral_concept = ConceptFactory(scheme=mineral_scheme, label="Basalt ore")
        ConceptFactory(scheme=fossil_scheme, label="Basalt fossil")

        response = Client().get(
            reverse("controlled_vocabularies:concept-autocomplete"),
            {"q": "Basalt", "field": _field_reference(Borehole, "dominant_material")},
        )

        body = json.loads(response.content)
        assert {result["id"] for result in body["results"]} == {rock_concept.pk, mineral_concept.pk}

    def test_a_field_declared_against_no_vocabulary_makes_every_concept_eligible(self):
        rock_scheme = ConceptSchemeFactory(name="Rock type")
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        fossil_scheme = ConceptSchemeFactory(name="Fossil")
        rock_concept = ConceptFactory(scheme=rock_scheme, label="Quartz rock")
        mineral_concept = ConceptFactory(scheme=mineral_scheme, label="Quartz ore")
        fossil_concept = ConceptFactory(scheme=fossil_scheme, label="Quartz fossil")

        response = Client().get(
            reverse("controlled_vocabularies:concept-autocomplete"),
            {"q": "Quartz", "field": _field_reference(Sketch, "subject")},
        )

        body = json.loads(response.content)
        assert {result["id"] for result in body["results"]} == {
            rock_concept.pk,
            mineral_concept.pk,
            fossil_concept.pk,
        }

    def test_the_rendered_widget_carries_the_reference(self):
        # The widget's full context — including autocompleteParams — only
        # builds with a live request in django_tomselect's thread-local
        # storage (widgets.py:610-628), the way TomSelectMiddleware provides
        # it on a real request/response cycle. A bare `str(SpecimenForm())`
        # falls back to the base context, which carries no reference at all,
        # and would pass this assertion vacuously by asserting on nothing.
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        rendered = {}

        def get_response(inner_request):
            rendered["html"] = str(SpecimenForm())
            return HttpResponse()

        TomSelectMiddleware(get_response)(request)

        # The template renders autocompleteParams through Django's `escapejs`
        # filter, which escapes "=" to the literal six characters
        # backslash-u-0-0-3-D — verified against the actual rendered output,
        # not assumed from the raw parameter string.
        escaped_equals = "\\u003D"
        assert f"autocompleteParams: 'field{escaped_equals}testapp.specimen.rock_type'" in rendered["html"]

