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
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, override_settings
from django.utils import translation
from django_tomselect.middleware import TomSelectMiddleware

from controlled_vocabularies.forms import ConceptChoiceField, ConceptsChoiceField
from tests.factories import ConceptFactory, ConceptSchemeFactory, OutcropFactory, SampleFactory
from tests.testapp.models import Deposit, Outcrop, Sample


def _rendered_under_an_ambient_request(build):
    """Render ``build()`` (a callable returning the string to render) under an
    ambient request, the way ``TomSelectMiddleware`` supplies one for every real
    HTTP response. ``tests/settings.py`` installs no middleware, so nothing else
    sets ``django_tomselect``'s thread-local request — without one,
    ``TomSelectModelWidget.get_context()`` returns its base context before ever
    reaching ``_get_selected_options()``: it requires ``request`` truthy and
    ``validate_request(request)``, and the latter requires ``request.user``
    (confirmed against the installed wheel, ``2026.6.2``, ``widgets.py:619-633``
    and ``widgets.py:1093-1116``, not against the README).
    """
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    return TomSelectMiddleware(lambda r: build())(request)


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
    is on the message, not the exception type alone.

    Both widgets carry the mixin, so both are asserted: the single-valued and the
    many-valued field reach the render through different widget classes, and one
    covered on its own leaves the other free to raise the library's own error."""

    @override_settings(ROOT_URLCONF=())
    @pytest.mark.parametrize("form_class", [SampleForm, DepositForm])
    def test_rendering_raises_improperlyconfigured_naming_both_steps(self, form_class):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            str(form_class())

        message = str(exc_info.value)
        assert "controlled_vocabularies.urls" in message
        assert "INSTALLED_APPS" in message


@pytest.mark.django_db
class TestConceptFieldShowsWhatARecordAlreadyHolds:
    """T009, FR-008, plan.md A8, decisions.md D12: an existing record's attached
    concept renders unrestricted, because A6 path two narrows
    ``_ConceptWidgetValidationMixin.get_queryset()`` to the field's current
    declaration and the library resolves already-selected values through that
    same method (``widgets.py:965``). What a record already holds is displayed
    unrestricted; what a submission newly contains is still validated against
    the declaration — the validation path (T004) is untouched, and its own
    refusal tests above still pass.

    Both fields' shapes are covered independently: :class:`Sample`'s
    ``mineral`` (the single-valued ``ConceptField``, ``ConceptWidget``) and
    :class:`Outcrop`'s ``minerals`` (the multiple-valued ``ConceptsField``,
    ``ConceptsWidget``). Each reaches the render through a different widget
    class, so a property proved for one alone would leave the other free to
    regress — the exact gap T008 found and repaired.
    """

    def test_a_concept_field_shows_the_attached_concept_under_its_active_language_label(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=scheme, multilingual=True, label="Quartz")
        sample = SampleFactory(mineral=concept)

        with translation.override("de"):
            rendered = _rendered_under_an_ambient_request(lambda: str(SampleForm(instance=sample)))

        assert concept.preferred_label("de") in rendered
        assert "Quartz" not in rendered

    def test_a_concepts_field_shows_every_attached_concept_under_its_active_language_label(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        concepts = [ConceptFactory(scheme=scheme, multilingual=True, label=f"Concept {i}") for i in range(3)]
        outcrop = OutcropFactory()
        outcrop.minerals.add(*concepts)

        with translation.override("de"):
            rendered = _rendered_under_an_ambient_request(lambda: str(OutcropForm(instance=outcrop)))

        for concept in concepts:
            assert concept.preferred_label("de") in rendered

    def test_submitting_the_concepts_field_form_untouched_leaves_all_three_attached(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        concepts = [ConceptFactory(scheme=scheme, label=f"Concept {i}") for i in range(3)]
        outcrop = OutcropFactory()
        outcrop.minerals.add(*concepts)

        form = OutcropForm(
            data={"name": outcrop.name, "minerals": [concept.pk for concept in concepts]},
            instance=outcrop,
        )

        assert form.is_valid(), form.errors
        instance = form.save()
        assert set(instance.minerals.values_list("pk", flat=True)) == {concept.pk for concept in concepts}

    def test_removing_one_attached_concept_and_saving_removes_exactly_that_one(self):
        scheme = ConceptSchemeFactory(name="Mineral")
        concepts = [ConceptFactory(scheme=scheme, label=f"Concept {i}") for i in range(3)]
        outcrop = OutcropFactory()
        outcrop.minerals.add(*concepts)
        kept = concepts[:2]

        form = OutcropForm(
            data={"name": outcrop.name, "minerals": [concept.pk for concept in kept]},
            instance=outcrop,
        )

        assert form.is_valid(), form.errors
        instance = form.save()
        assert set(instance.minerals.values_list("pk", flat=True)) == {concept.pk for concept in kept}

    def test_a_concept_field_still_shows_an_attached_concept_outside_the_current_vocabulary(self):
        """The un-overridden widget drops this concept (plan.md A8, R1): the
        record already holds it, but ``_get_selected_options()`` resolves it
        through the same narrowed ``get_queryset()`` the validation path uses,
        and this concept's scheme is not the field's declared vocabulary."""
        outside_scheme = ConceptSchemeFactory(name="Rock Type")
        outside_concept = ConceptFactory(scheme=outside_scheme, label="Basalt")
        sample = SampleFactory(mineral=outside_concept)

        rendered = _rendered_under_an_ambient_request(lambda: str(SampleForm(instance=sample)))

        assert "Basalt" in rendered

    def test_a_concepts_field_still_shows_an_attached_concept_outside_the_current_vocabulary(self):
        """The multiple-valued field's own widget class, proved independently
        (see the single-valued case above for why the un-overridden widget
        drops it).

        ``fields.py``'s ``_refuse_concepts_outside_vocabulary`` (an
        ``m2m_changed`` receiver) refuses ``.add()``ing a concept outside the
        vocabulary outright, by design (D2) — so unlike the single-valued
        case above, a concept cannot be attached directly from a foreign
        scheme. The realistic route to the same state is the one that
        receiver does not — and, by its own docstring, is not meant to —
        guard against: the concept is attached while still in-vocabulary,
        then its *own* scheme is reassigned afterwards, exactly as an editor
        recategorising a concept would leave it.
        """
        mineral_scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=mineral_scheme, label="Basalt")
        outcrop = OutcropFactory()
        outcrop.minerals.add(concept)

        other_scheme = ConceptSchemeFactory(name="Rock Type")
        concept.scheme = other_scheme
        concept.save()

        rendered = _rendered_under_an_ambient_request(lambda: str(OutcropForm(instance=outcrop)))

        assert "Basalt" in rendered
