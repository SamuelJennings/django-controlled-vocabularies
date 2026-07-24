"""US-5 — Translatable, self-documenting field metadata + deliberate indexing.

Covers FR-009 (every field: translatable ``verbose_name`` + non-empty
``help_text``), FR-010 (all user-facing strings — including validation messages
— translatable, with named placeholders), FR-011 (indexing is deliberate).
This suite walks the models' metadata rather than exercising a UI (SC-006), and
iterates ``_meta`` fields so a future field is automatically held to the same
standard.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Model, UniqueConstraint
from django.utils.functional import Promise

from controlled_vocabularies.models import Concept, ConceptScheme


def _editable_fields(model: type[Model]):
    """The model's own, user-editable, concrete fields (excludes the auto pk
    and reverse relations) — every one must meet the metadata standard."""
    return [
        field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and getattr(field, "editable", False) and not field.auto_created
    ]


# --- FR-009: every editable field carries lazy verbose_name + non-empty help_text ---


@pytest.mark.parametrize("model", [ConceptScheme, Concept])
def test_every_editable_field_has_metadata(model):
    fields = _editable_fields(model)
    assert fields, f"{model.__name__} exposes no editable fields to check"
    for field in fields:
        # help_text: present, non-empty, and a lazy translation proxy.
        assert field.help_text, f"{model.__name__}.{field.name} has no help_text"
        assert isinstance(field.help_text, Promise), (
            f"{model.__name__}.{field.name}.help_text is not lazily translatable"
        )
        # verbose_name: a lazy translation proxy (Django defaults it to a plain
        # str derived from the attribute name, which is not translatable).
        assert isinstance(field.verbose_name, Promise), (
            f"{model.__name__}.{field.name}.verbose_name is not lazily translatable"
        )


@pytest.mark.parametrize("model", [ConceptScheme, Concept])
def test_meta_verbose_names_are_lazy(model):
    assert isinstance(model._meta.verbose_name, Promise), (
        f"{model.__name__} Meta.verbose_name is not lazily translatable"
    )
    assert isinstance(model._meta.verbose_name_plural, Promise), (
        f"{model.__name__} Meta.verbose_name_plural is not lazily translatable"
    )


def test_app_config_verbose_name_is_lazy():
    from django.apps import apps

    verbose_name = apps.get_app_config("controlled_vocabularies").verbose_name
    assert isinstance(verbose_name, Promise), "AppConfig.verbose_name is not lazily translatable"


# --- FR-010: validation messages are translatable, with named placeholders ---


def _inner_error(exc: ValidationError, field: str) -> ValidationError:
    """The single field-scoped ValidationError carrying the lazy message."""
    return exc.error_dict[field][0]


@pytest.mark.django_db
def test_empty_name_message_is_translatable():
    with pytest.raises(ValidationError) as excinfo:
        ConceptScheme.objects.create(name="   ")
    err = _inner_error(excinfo.value, "name")
    assert isinstance(err.message, Promise), "empty-name message is not lazily translatable"


@pytest.mark.django_db
def test_empty_label_message_is_translatable():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    with pytest.raises(ValidationError) as excinfo:
        Concept.objects.create(scheme=scheme, label="   ")
    err = _inner_error(excinfo.value, "label")
    assert isinstance(err.message, Promise), "empty-label message is not lazily translatable"


@pytest.mark.django_db
def test_scheme_slug_collision_message_uses_named_placeholder():
    ConceptScheme.objects.create(name="Geothermics")
    with pytest.raises(ValidationError) as excinfo:
        ConceptScheme.objects.create(name="GEOTHERMICS")
    err = _inner_error(excinfo.value, "slug")
    # The translatable msgid is lazy and carries a *named* placeholder — the slug
    # value is supplied via params, never baked into the translatable string.
    assert isinstance(err.message, Promise), "collision message is not lazily translatable"
    assert "%(slug)s" in str(err.message), "collision msgid lacks a named %(slug)s placeholder"
    assert err.params == {"slug": "geothermics"}
    # ...and it still renders with the real value substituted in.
    assert "geothermics" in excinfo.value.messages[0]


@pytest.mark.django_db
def test_concept_slug_collision_message_uses_named_placeholder():
    scheme = ConceptScheme.objects.create(name="Geothermics")
    Concept.objects.create(scheme=scheme, label="Heat Flow")
    with pytest.raises(ValidationError) as excinfo:
        Concept.objects.create(scheme=scheme, label="HEAT FLOW")
    err = _inner_error(excinfo.value, "slug")
    assert isinstance(err.message, Promise), "collision message is not lazily translatable"
    assert "%(slug)s" in str(err.message), "collision msgid lacks a named %(slug)s placeholder"
    assert err.params == {"slug": "heat-flow"}
    assert "heat-flow" in excinfo.value.messages[0]


# --- FR-011: indexing is deliberate ---


def test_scheme_slug_is_uniquely_indexed():
    assert ConceptScheme._meta.get_field("slug").unique is True


def test_concept_scheme_fk_is_indexed():
    assert Concept._meta.get_field("scheme").db_index is True


def test_concept_has_composite_unique_constraint():
    constraint = next(
        (
            c
            for c in Concept._meta.constraints
            if isinstance(c, UniqueConstraint) and c.name == "unique_concept_slug_per_scheme"
        ),
        None,
    )
    assert constraint is not None, "missing (scheme, slug) UniqueConstraint"
    assert tuple(constraint.fields) == ("scheme", "slug")
