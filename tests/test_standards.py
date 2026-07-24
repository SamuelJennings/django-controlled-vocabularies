"""US-7 — Translatable, self-documenting field metadata + deliberate indexing.

FS-002 extends the vocabulary to four models (``ConceptScheme``, ``Concept``,
``ConceptLabel``, ``ConceptNote``). This suite holds every one of them to the
same standard #15 set for the first two:

- Article XII: every editable field carries a lazily-translatable ``verbose_name``
  and a non-empty, lazily-translatable ``help_text``; user-facing validation
  messages are translatable with *named* placeholders (the
  ``ValidationError(msgid, params=…)`` form — #15 ``decisions.md`` §9).
- Article XIII: indexing is deliberate. ``ConceptLabel`` is indexed on its
  ``(language, kind, text)`` lookup path and enforces one preferred label per
  language; ``ConceptNote.value`` is free prose and stays unindexed (FS-002
  ``decisions.md`` §20).

It walks ``_meta`` rather than a hand-listed field set, so a future field is
held to the same standard automatically.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Model, UniqueConstraint
from django.utils.functional import Promise

from controlled_vocabularies.models import (
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptScheme,
)

ALL_MODELS = [ConceptScheme, Concept, ConceptLabel, ConceptNote]


def _editable_fields(model: type[Model]):
    """The model's own, user-editable, concrete fields (excludes the auto pk
    and reverse relations) — every one must meet the metadata standard."""
    return [
        field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and getattr(field, "editable", False) and not field.auto_created
    ]


# --- Article XII: every editable field carries lazy verbose_name + non-empty help_text ---


@pytest.mark.parametrize("model", ALL_MODELS)
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


@pytest.mark.parametrize("model", ALL_MODELS)
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


# --- Article XII: the new FS-002 validation messages are translatable, with named placeholders ---


def _inner_error(exc: ValidationError, field: str) -> ValidationError:
    """The single field-scoped ValidationError carrying the lazy message."""
    return exc.error_dict[field][0]


@pytest.mark.django_db
def test_missing_default_language_label_message_uses_named_placeholder(scheme):
    # FR-002: a concept needs a preferred label in the scheme's effective default
    # language. The refusal names that language through a *named* placeholder, so the
    # translatable msgid stays static and the language is supplied via params.
    with pytest.raises(ValidationError) as excinfo:
        Concept.objects.create(scheme=scheme, label="")
    err = _inner_error(excinfo.value, "label")
    assert isinstance(err.message, Promise), "missing-default-language-label message is not lazily translatable"
    assert "%(language)s" in str(err.message), "message lacks a named %(language)s placeholder"
    assert err.params == {"language": scheme.effective_default_language}
    # ...and it still renders with the real language substituted in.
    assert scheme.effective_default_language in excinfo.value.messages[0]


@pytest.mark.django_db
def test_duplicate_preferred_label_message_uses_named_placeholder(scheme):
    # FR-001: at most one preferred label per language. The second is refused with a
    # translatable, curator-facing message that names the language via a placeholder.
    concept = Concept.objects.create(scheme=scheme, label="Heat flow")
    concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
    with pytest.raises(ValidationError) as excinfo:
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Terrestrischer Wärmefluss")
    err = _inner_error(excinfo.value, "language")
    assert isinstance(err.message, Promise), "duplicate-preferred-label message is not lazily translatable"
    assert "%(language)s" in str(err.message), "message lacks a named %(language)s placeholder"
    assert err.params == {"language": "de"}
    assert "de" in excinfo.value.messages[0]


# --- Article XIII: indexing is deliberate on the two new models ---


def test_concept_label_lookup_path_is_indexed():
    # FR-015: the (language, kind, text) lookup/search path is indexed.
    indexed = [tuple(index.fields) for index in ConceptLabel._meta.indexes]
    assert ("language", "kind", "text") in indexed, (
        f"ConceptLabel is missing a (language, kind, text) index; has {indexed}"
    )


def test_concept_label_has_one_preferred_per_language_constraint():
    constraint = next(
        (
            c
            for c in ConceptLabel._meta.constraints
            if isinstance(c, UniqueConstraint) and c.name == "one_preferred_label_per_language"
        ),
        None,
    )
    assert constraint is not None, "missing one_preferred_label_per_language partial unique constraint"
    assert tuple(constraint.fields) == ("concept", "language")
    assert constraint.condition is not None, "the preferred-label uniqueness must be a *partial* constraint"


def test_concept_note_value_is_unindexed():
    # decisions.md §20: value is free documentary prose with no lookup path this
    # slice, so it carries no db_index and appears in no explicit index.
    assert ConceptNote._meta.get_field("value").db_index is False, "ConceptNote.value must stay unindexed"
    for index in ConceptNote._meta.indexes:
        assert "value" not in index.fields, "ConceptNote.value must not be part of any index"


def test_concept_note_and_label_fks_are_indexed():
    # FKs are auto-indexed; assert it holds for the two new child models.
    assert ConceptLabel._meta.get_field("concept").db_index is True
    assert ConceptNote._meta.get_field("concept").db_index is True
