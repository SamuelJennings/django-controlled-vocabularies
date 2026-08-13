"""Tests for ``controlled_vocabularies.forms`` (T004, FR-001, FR-003, FR-009).

``TestConceptFieldRendersAsTheControl`` — an ordinary ``ModelForm`` built from a
consuming model, with no widget declared and no form field declared, gets this
package's control from ``ConceptFieldMixin.formfield()`` alone (FR-001).

``TestConceptFieldRenderingIsBoundedByVocabularySize`` — FR-003 properly: the
control renders no concept into the page, so the rendered length and the absence
of any concept's label hold identically whether the vocabulary is five concepts
or several thousand.

``TestConceptFieldSubmissionSurvives`` — decisions.md D12 is the point of this
task: the widget's own ``get_queryset()`` builds the validation queryset from the
model field instance directly, with no request consulted, so a legitimate
submission does not fail with ``invalid_choice`` the way it would if validation
fell back to the library's default (an ambient request whose ``GET`` is empty
during a POST). Both the single- (``ConceptField``) and multiple-valued
(``ConceptsField``) fields are proved, and a foreign concept is still refused —
FR-009 promises nothing already guaranteed was taken away.
"""

import pytest
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from controlled_vocabularies.forms import ConceptChoiceField, ConceptsChoiceField
from tests.factories import ConceptFactory, ConceptSchemeFactory, OutcropFactory
from tests.testapp.models import Deposit, Outcrop, Sample


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ["name", "mineral"]


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ["name", "rock_types"]


class OutcropForm(forms.ModelForm):
    class Meta:
        model = Outcrop
        fields = ["name", "minerals"]


class TestConceptFieldRendersAsTheControl:
    """No widget declared, no form field declared — the field alone is enough (FR-001)."""

    def test_a_concept_field_binds_this_packages_form_field_and_widget(self):
        bound_field = SampleForm().fields["mineral"]

        assert isinstance(bound_field, ConceptChoiceField)

    def test_a_concepts_field_binds_this_packages_form_field_and_widget(self):
        bound_field = DepositForm().fields["rock_types"]

        assert isinstance(bound_field, ConceptsChoiceField)


@pytest.mark.django_db
class TestConceptFieldRenderingIsBoundedByVocabularySize:
    """FR-003: rendering never loads the vocabulary into the page."""

    def test_rendered_length_and_absence_of_labels_hold_for_a_small_vocabulary(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        concepts = [ConceptFactory(scheme=scheme, label=f"Small vocab concept {i}") for i in range(5)]

        rendered = str(SampleForm())

        assert not any(concept.label in rendered for concept in concepts)

    def test_rendered_length_is_identical_for_a_large_vocabulary(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        for i in range(5):
            ConceptFactory(scheme=scheme, label=f"Small vocab concept {i}")
        small_rendered = str(SampleForm())

        large_concepts = [ConceptFactory(scheme=scheme, label=f"Large vocab concept {i}") for i in range(2000)]
        large_rendered = str(SampleForm())

        assert len(large_rendered) == len(small_rendered)
        assert not any(concept.label in large_rendered for concept in large_concepts)


@pytest.mark.django_db
class TestConceptFieldSubmissionSurvives:
    """decisions.md D12: the widget's own get_queryset() is what makes a submission
    of a legitimate concept survive validation, on both fields' shapes.

    The ``ConceptsField`` half uses :class:`Outcrop` (``minerals``, ``blank=True``)
    rather than :class:`Deposit`, to keep the assertions on D12 alone. A *required*
    ``ConceptsField`` has one submission path of its own that fails for an unrelated,
    pre-existing reason (#124): editing a saved record whose relation is still empty.
    ``_post_clean()`` runs model-level ``full_clean()`` — and so FS-010's
    ``_install_required_set_check`` — before ``save_m2m()`` has attached anything, so
    the submission that would populate the relation is the one refused. Creating a
    record is unaffected: the check skips an instance with no primary key. Nothing
    here is D12's widget queryset.
    """

    def test_a_legitimate_concept_is_valid_and_saves_for_a_concept_field(self):
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=mineral_scheme)

        form = SampleForm(data={"name": "Sample A", "mineral": concept.pk})

        assert form.is_valid(), form.errors
        instance = form.save()
        assert instance.mineral_id == concept.pk

    def test_a_foreign_concept_is_still_refused_for_a_concept_field(self):
        other_scheme = ConceptSchemeFactory(name="Rock Type")
        foreign_concept = ConceptFactory(scheme=other_scheme)

        form = SampleForm(data={"name": "Sample B", "mineral": foreign_concept.pk})

        assert not form.is_valid()
        assert "mineral" in form.errors

    def test_a_legitimate_concept_is_valid_and_saves_for_a_concepts_field(self):
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=mineral_scheme)
        outcrop = OutcropFactory()

        form = OutcropForm(data={"name": "Outcrop A", "minerals": [concept.pk]}, instance=outcrop)

        assert form.is_valid(), form.errors
        instance = form.save()
        assert list(instance.minerals.values_list("pk", flat=True)) == [concept.pk]

    def test_a_foreign_concept_is_still_refused_for_a_concepts_field(self):
        other_scheme = ConceptSchemeFactory(name="Rock Type")
        foreign_concept = ConceptFactory(scheme=other_scheme)
        outcrop = OutcropFactory()

        form = OutcropForm(data={"name": "Outcrop B", "minerals": [foreign_concept.pk]}, instance=outcrop)

        assert not form.is_valid()
        assert "minerals" in form.errors


class TestConceptFieldRenderingWithoutTheRouteIncluded:
    """T008, decisions.md D14: a project that ignores the system check's warning
    still reaches a render. The library's own ``get_autocomplete_url()`` would
    re-raise ``NoReverseMatch`` verbatim there — a message naming a URL pattern
    the developer never wrote. This widget catches it and raises
    ``ImproperlyConfigured`` naming both wiring steps instead, so the assertion
    is on the message, not the exception type alone."""

    @override_settings(ROOT_URLCONF=())
    def test_rendering_raises_improperlyconfigured_naming_both_steps(self):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            str(SampleForm())

        message = str(exc_info.value)
        assert "controlled_vocabularies.urls" in message
        assert "INSTALLED_APPS" in message
