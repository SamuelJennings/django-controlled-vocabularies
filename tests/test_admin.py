"""Tests for the Django admin's rendering of the concept fields (US-1, T002-T004).

The registrations in ``tests/testapp/admin.py`` are deliberately bare — no
``ModelAdmin`` here declares anything about ``Specimen.rock_type`` or
``Outcrop.minerals``. What these tests prove is FR-001, FR-002 and SC-001
together: the control the forms feature already renders reaches the admin
unchanged, through nothing more than ``db_field.formfield()``, and the bare
registration itself is scenario 6's proof that nothing further is configured
for the admin specifically. This story builds no production code — it pins
behaviour that is currently true by accident, so the next stories cannot
quietly break it (plan.md, US-1).

``TestConceptControlRendersOnAdminPages`` (T002) covers scenarios 1-3 and 6:
the add and change pages of both field kinds render the control, and the
change page shows what the record already holds, under its preferred label.

``TestAdminPageRenderingIsBoundedByVocabularySize`` (T003) mirrors
``tests/test_forms.py::TestConceptFieldRenderingIsBoundedByVocabularySize``
so the two read the same — FR-009, SC-006, scenario 4.

``TestAdminSubmissionSavesAndFieldRulesStillBite`` (T004) covers scenario 5:
a POST from the add page saves the chosen concept, one naming a concept
outside the field's declared vocabulary is refused by the field's own
validation, and a concept referenced through the admin is still protected
from deletion — both field kinds.
"""

import pytest
from django.db.models import ProtectedError
from django.urls import reverse

from tests.factories import ConceptFactory, ConceptSchemeFactory, OutcropFactory, SpecimenFactory
from tests.testapp.models import Outcrop, Specimen


def _field_reference(model, field_name):
    """The ``<app_label>.<model>.<field_name>`` reference the control's widget
    sends, spelled the same way ``tests/test_views.py::_field_reference`` is —
    duplicated per module rather than imported, per DAMP."""
    return f"{model._meta.app_label}.{model._meta.model_name}.{field_name}"


def _assert_control_rendered(content, model, field_name):
    """T002's three-part acceptance, factored out because every test in this
    module asserts it: the select carries ``data-tomselect``, the page
    carries the widget's own configuration script, and the autocomplete
    reference for this field is present — escaped the way Django's
    ``escapejs`` filter renders it (``tests/test_views.py`` proves the
    escaping against the same template; this asserts against the admin's
    rendering of it)."""
    assert f'id="id_{field_name}"' in content
    assert "data-tomselect" in content
    assert "window.djangoTomSelect.initialize(element, config);" in content
    escaped_equals = "\\u003D"
    assert f"autocompleteParams: 'field{escaped_equals}{_field_reference(model, field_name)}'" in content


@pytest.mark.django_db
class TestConceptControlRendersOnAdminPages:
    """T002: FR-001, FR-002, SC-001, US-1 scenarios 1-3 and 6."""

    def test_add_page_renders_the_control_for_a_concept_field(self, admin_client):
        response = admin_client.get(reverse("admin:testapp_specimen_add"))

        assert response.status_code == 200
        _assert_control_rendered(response.content.decode(), Specimen, "rock_type")

    def test_add_page_renders_the_control_for_a_concepts_field(self, admin_client):
        response = admin_client.get(reverse("admin:testapp_outcrop_add"))

        assert response.status_code == 200
        _assert_control_rendered(response.content.decode(), Outcrop, "minerals")

    def test_change_page_renders_the_control_and_shows_the_held_concept_under_its_preferred_label(self, admin_client):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme, label="Granite")
        specimen = SpecimenFactory(rock_type=concept)

        response = admin_client.get(reverse("admin:testapp_specimen_change", args=[specimen.pk]))
        content = response.content.decode()

        assert response.status_code == 200
        _assert_control_rendered(content, Specimen, "rock_type")
        assert concept.label in content

    def test_change_page_shows_every_concept_a_concepts_field_holds(self, admin_client):
        scheme = ConceptSchemeFactory(name="Mineral")
        concepts = [ConceptFactory(scheme=scheme, label=f"Mineral concept {i}") for i in range(3)]
        outcrop = OutcropFactory()
        outcrop.minerals.add(*concepts)

        response = admin_client.get(reverse("admin:testapp_outcrop_change", args=[outcrop.pk]))
        content = response.content.decode()

        assert response.status_code == 200
        _assert_control_rendered(content, Outcrop, "minerals")
        for concept in concepts:
            assert concept.label in content


@pytest.mark.django_db
class TestAdminPageRenderingIsBoundedByVocabularySize:
    """T003: FR-009, SC-006, US-1 scenario 4 — mirrors
    ``tests/test_forms.py::TestConceptFieldRenderingIsBoundedByVocabularySize``
    so the two read the same."""

    def test_rendered_length_is_identical_for_a_large_vocabulary(self, admin_client):
        scheme = ConceptSchemeFactory(name="Rock Type")
        for i in range(5):
            ConceptFactory(scheme=scheme, label=f"Small vocab concept {i}")
        small_rendered = admin_client.get(reverse("admin:testapp_specimen_add")).content.decode()

        large_concepts = [ConceptFactory(scheme=scheme, label=f"Large vocab concept {i}") for i in range(2000)]
        large_rendered = admin_client.get(reverse("admin:testapp_specimen_add")).content.decode()

        assert len(large_rendered) == len(small_rendered)
        assert not any(concept.label in large_rendered for concept in large_concepts)


@pytest.mark.django_db
class TestAdminSubmissionSavesAndFieldRulesStillBite:
    """T004: FR-010, US-1 scenario 5. A POST from the add page saves the
    chosen concept. A concept from outside the field's declared vocabulary is
    refused at the form field's own level: the widget's ``get_queryset()``
    (``tests/test_forms.py``'s ``TestConceptFieldSubmissionSurvives`` proves
    this is what a legitimate submission survives) is narrowed to the
    declaration, so ``ModelChoiceField.clean()`` rejects the foreign pk with
    Django's own "not one of the available choices" message before the
    model-level ``ConceptField.validate()`` custom message is ever reached —
    the same reason the existing form-level tests assert on the errored
    field, not on message text. And a concept referenced through the admin is
    still protected from deletion — both field kinds."""

    def test_a_legitimate_concept_saves_through_the_add_page_for_a_concept_field(self, admin_client):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)

        response = admin_client.post(
            reverse("admin:testapp_specimen_add"),
            {"name": "Granite sample", "rock_type": concept.pk, "_save": "Save"},
        )

        assert response.status_code == 302
        specimen = Specimen.objects.get(name="Granite sample")
        assert specimen.rock_type_id == concept.pk

    def test_a_foreign_concept_is_refused_by_the_add_page_for_a_concept_field(self, admin_client):
        other_scheme = ConceptSchemeFactory(name="Mineral")
        foreign_concept = ConceptFactory(scheme=other_scheme)

        response = admin_client.post(
            reverse("admin:testapp_specimen_add"),
            {"name": "Wrong vocabulary sample", "rock_type": foreign_concept.pk, "_save": "Save"},
        )
        content = response.content.decode()

        assert response.status_code == 200
        assert not Specimen.objects.filter(name="Wrong vocabulary sample").exists()
        assert 'id="id_rock_type_error"' in content

    def test_a_legitimate_concept_saves_through_the_add_page_for_a_concepts_field(self, admin_client):
        scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=scheme)

        response = admin_client.post(
            reverse("admin:testapp_outcrop_add"),
            {"name": "Basalt outcrop", "minerals": [concept.pk], "_save": "Save"},
        )

        assert response.status_code == 302
        outcrop = Outcrop.objects.get(name="Basalt outcrop")
        assert concept in outcrop.minerals.all()

    def test_a_foreign_concept_is_refused_by_the_add_page_for_a_concepts_field(self, admin_client):
        other_scheme = ConceptSchemeFactory(name="Rock Type")
        foreign_concept = ConceptFactory(scheme=other_scheme)

        response = admin_client.post(
            reverse("admin:testapp_outcrop_add"),
            {"name": "Wrong vocabulary outcrop", "minerals": [foreign_concept.pk], "_save": "Save"},
        )
        content = response.content.decode()

        assert response.status_code == 200
        assert not Outcrop.objects.filter(name="Wrong vocabulary outcrop").exists()
        assert 'id="id_minerals_error"' in content

    def test_a_concept_field_saved_through_the_admin_still_cannot_be_deleted(self, admin_client):
        scheme = ConceptSchemeFactory(name="Rock Type")
        concept = ConceptFactory(scheme=scheme)
        admin_client.post(
            reverse("admin:testapp_specimen_add"),
            {"name": "Protected sample", "rock_type": concept.pk, "_save": "Save"},
        )

        with pytest.raises(ProtectedError):
            concept.delete()

        assert Specimen.objects.filter(name="Protected sample", rock_type=concept).exists()

    def test_a_concepts_field_saved_through_the_admin_still_cannot_be_deleted(self, admin_client):
        scheme = ConceptSchemeFactory(name="Mineral")
        concept = ConceptFactory(scheme=scheme)
        admin_client.post(
            reverse("admin:testapp_outcrop_add"),
            {"name": "Protected outcrop", "minerals": [concept.pk], "_save": "Save"},
        )

        with pytest.raises(ProtectedError):
            concept.delete()

        outcrop = Outcrop.objects.get(name="Protected outcrop")
        assert concept in outcrop.minerals.all()
