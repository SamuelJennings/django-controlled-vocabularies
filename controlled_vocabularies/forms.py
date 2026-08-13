"""Form fields for :mod:`controlled_vocabularies` (T004, FR-001, FR-003, FR-009).

``ConceptFieldMixin.formfield()`` (``fields.py``) returns ``ConceptChoiceField``
for a ``ConceptField`` and ``ConceptsChoiceField`` for a ``ConceptsField``, so an
ordinary ``ModelForm`` built from a consuming model gets the search-as-you-type
control from the model declaration alone — a project never names a widget or
declares a form field (FR-001, plan.md A3).

Both fields' widgets carry the load-bearing part of this task (decisions.md D12,
plan.md A6 path two). The library's own ``TomSelectModelWidget.get_queryset()``
walks back to the autocomplete endpoint through an *ambient* request; during a
form POST that request is the page's own submission, whose ``GET`` carries no
``field=`` reference, so the endpoint's fail-closed refusal (a missing/invalid
reference) would be the guaranteed state on every submission and
``ModelChoiceField.to_python()`` would raise ``invalid_choice`` for a legitimate
concept. This module's widgets override ``get_queryset()`` to build the
restriction directly from the model field instance ``formfield()`` already holds
— ``Concept.objects.complex_filter(field.get_limit_choices_to())`` — with no
request consulted, restoring what an unmodified ``ModelChoiceField`` already does
with ``limit_choices_to``.
"""

from urllib.parse import urlencode

from django_tomselect.app_settings import AllowedCSSFrameworks, TomSelectConfig
from django_tomselect.forms import TomSelectModelChoiceField, TomSelectModelMultipleChoiceField
from django_tomselect.widgets import TomSelectModelMultipleWidget, TomSelectModelWidget

from .models import Concept


def _config() -> TomSelectConfig:
    """The one configuration both concept widgets render with.

    ``css_framework`` is pinned to the framework-free default explicitly
    (plan.md A3) rather than left to whatever a project's own
    ``PROJECT_TOMSELECT`` setting configures — this package imposes no
    Bootstrap on a project that uses none, regardless of that project's other
    TomSelect widgets. ``label_field`` names ``display_label``, the virtual
    field T003's view exposes; ``value_field`` stays the default ``"id"``.

    ``css_framework`` takes the enum's *value*, not the member: the wheel's
    own ``TomSelectConfig.validate()`` checks membership against
    ``{f.value for f in AllowedCSSFrameworks}``, so the member itself fails
    validation despite the field's type annotation naming the enum (verified
    against ``django_tomselect`` ``2026.6.2``, not the annotation).
    """
    return TomSelectConfig(
        url="controlled_vocabularies:concept-autocomplete",
        value_field="id",
        label_field="display_label",
        css_framework=AllowedCSSFrameworks.DEFAULT.value,  # type: ignore[arg-type]
    )


class _ConceptWidgetValidationMixin:
    """The ``get_queryset()`` override decisions.md D12 exists for.

    ``model_field`` is set by the owning form field's ``__init__`` (below), from
    the model field instance ``ConceptFieldMixin.formfield()`` passes through.
    Absent — a widget built without going through ``formfield()`` — refuses
    outright rather than falling back to the library's request-derived default,
    the same fail-closed shape ``get_limit_choices_to()`` itself takes when a
    declaration names no vocabulary (an empty ``Q`` matches everything; a
    genuinely absent field reference should not).
    """

    model_field = None

    def get_queryset(self):
        if self.model_field is None:
            return Concept.objects.none()
        return Concept.objects.complex_filter(self.model_field.get_limit_choices_to())


class _ConceptWidgetReferenceMixin:
    """The ``get_autocomplete_params()`` override T006 exists for (plan.md
    A6 path one, decisions.md D11).

    Appends ``field=<app_label>.<model>.<field_name>`` — a reference to this
    widget's own declaration, read from the same ``model_field`` attribute
    :class:`_ConceptWidgetValidationMixin` reads — to every autocomplete
    request the control's browser plugin makes. It identifies which
    declaration is searching and carries no restriction of its own: the
    restriction is read from that declaration on the server (T006), never
    from this parameter's value.

    Absent — a widget built without going through ``formfield()`` — sends no
    reference, which the endpoint's own fail-closed refusal already covers.
    """

    model_field = None

    def get_autocomplete_params(self) -> str:
        if self.model_field is None:
            return ""
        meta = self.model_field.model._meta
        return urlencode({"field": f"{meta.app_label}.{meta.model_name}.{self.model_field.name}"})


class ConceptWidget(_ConceptWidgetReferenceMixin, _ConceptWidgetValidationMixin, TomSelectModelWidget):
    """The control :class:`ConceptChoiceField` renders (FR-001)."""


class ConceptsWidget(_ConceptWidgetReferenceMixin, _ConceptWidgetValidationMixin, TomSelectModelMultipleWidget):
    """The control :class:`ConceptsChoiceField` renders (FR-001)."""


class ConceptChoiceField(TomSelectModelChoiceField):
    """The form field :class:`~controlled_vocabularies.fields.ConceptField`
    renders as, through ``ConceptFieldMixin.formfield()``.

    ``model_field`` is the model field instance ``formfield()`` was called on
    — popped here rather than left in ``kwargs``, since neither
    :class:`~django_tomselect.forms.TomSelectModelChoiceField` nor Django's own
    ``ModelChoiceField`` accepts it — and handed to the widget after
    construction for its own ``get_queryset()`` (decisions.md D12).
    """

    widget_class = ConceptWidget

    def __init__(self, *args, model_field=None, **kwargs):
        kwargs.setdefault("config", _config())
        super().__init__(*args, **kwargs)
        self.widget.model_field = model_field


class ConceptsChoiceField(TomSelectModelMultipleChoiceField):
    """The form field :class:`~controlled_vocabularies.fields.ConceptsField`
    renders as, through ``ConceptFieldMixin.formfield()``. See
    :class:`ConceptChoiceField` for ``model_field``.
    """

    widget_class = ConceptsWidget

    def __init__(self, *args, model_field=None, **kwargs):
        kwargs.setdefault("config", _config())
        super().__init__(*args, **kwargs)
        self.widget.model_field = model_field
