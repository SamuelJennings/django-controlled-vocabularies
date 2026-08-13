"""Views for :mod:`controlled_vocabularies` (T002, T003, FR-002, FR-005, FR-012).

One route serves both the FK and M2M concept fields, since both target the same
``Concept`` model. The multi-name search and the allowlists that close the
filter/order surface are later tasks. Result shaping is this task's: a result
carries exactly the identifier, the preferred label and the vocabulary a concept
belongs to (FR-005, FR-012) — not the editorial notes or hidden/alternative
labels the concept also holds.
"""

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q, QuerySet
from django.utils.translation import get_language
from django_tomselect.autocompletes import AutocompleteModelView

from .fields import ConceptFieldMixin
from .models import Concept, ConceptLabel

#: The label kinds a typed string matches against, in the active language
#: (FR-004, plan.md A4). The default-language preferred label — every
#: concept's own ``label`` column — is matched separately, unconditional on
#: the active language.
_SEARCHED_LABEL_KINDS = [ConceptLabel.Kind.PREFERRED, ConceptLabel.Kind.ALTERNATIVE, ConceptLabel.Kind.HIDDEN]


class ConceptAutocompleteView(AutocompleteModelView):
    """Search-as-you-type endpoint for :class:`~controlled_vocabularies.models.Concept`."""

    model = Concept
    page_size = 20
    ordering = ("label", "pk")
    allow_anonymous = True
    allowed_filter_fields = []
    allowed_ordering_fields = []
    value_fields = ["id"]
    virtual_fields = ["display_label", "vocabulary"]

    def search(self, queryset: QuerySet, query: str) -> QuerySet:
        """Match ``query`` against a concept's names (FR-004, plan.md A4).

        Replaces the base ``search_lookups`` mechanism, left empty because it
        expresses one flat list of ORM lookups and cannot express "the active
        language's labels, of three kinds, or the default-language column".
        ``query`` is exactly what the base view's ``get_queryset()`` already
        extracted from the request (``autocompletes.py:396``) — nothing else
        is read off the request here (decisions.md D8). ``icontains`` gives
        case-insensitivity portably and folds no accents (decisions.md D4).
        ``.distinct()`` is what makes a concept matching on several of its
        labels appear once (FR-004).
        """
        if not query:
            return queryset
        active_language = get_language() or settings.LANGUAGE_CODE
        return queryset.filter(
            Q(label__icontains=query)
            | Q(labels__language=active_language, labels__kind__in=_SEARCHED_LABEL_KINDS, labels__text__icontains=query)
        ).distinct()

    def hook_queryset(self, queryset):
        """Attach what ``prepare_results()`` needs, then narrow to what the
        requested field declaration allows (T006, FR-006, plan.md A6 path
        one) — both before filtering, searching and ordering run, at the
        library's documented extension point rather than an override of
        ``get_queryset()``: ``select_related("scheme")`` for the vocabulary
        name, ``prefetch_related("labels")`` because ``display_label()``
        walks ``self.labels.all()`` and a bounded page would otherwise cost a
        query per row (R5).
        """
        queryset = queryset.select_related("scheme").prefetch_related("labels")
        return self._restrict_to_declaration(queryset)

    def _restrict_to_declaration(self, queryset: QuerySet) -> QuerySet:
        """Derive the restriction from the field declaration the request
        names, never from the request itself (FR-006, decisions.md D11).

        ``field`` is a ``<app_label>.<model>.<field_name>`` reference the
        control's widget appends (plan.md A6 path one); it identifies which
        declaration is searching and carries no restriction of its own —
        altering it can only name a different declaration, whose own
        restriction then applies. Resolution happens through Django's app
        registry, exactly as it does when Django itself loads a string
        ``to``; nothing here reads a vocabulary, a scheme, or anything else
        directly off the request.

        A reference that fails to resolve, names a field that is not one of
        this package's concept fields, or is absent, returns
        ``Concept.objects.none()`` — an ordinary empty page, HTTP 200,
        identical in shape to a search that matched nothing. No exception
        escapes, so a missing model and an existing-but-wrong field are
        indistinguishable from outside (plan.md A6 point 3).
        """
        reference = self.request.GET.get("field")
        if not reference:
            return queryset.none()
        try:
            app_label, model_name, field_name = reference.split(".", 2)
            model = apps.get_model(app_label, model_name)
            field = model._meta.get_field(field_name)
        except (ValueError, LookupError, FieldDoesNotExist):
            return queryset.none()
        if not isinstance(field, ConceptFieldMixin):
            return queryset.none()
        # ConceptFieldMixin is a plain mixin, not itself a RelatedField, so
        # get_limit_choices_to() (from ForeignKey/ManyToManyField, which
        # ConceptField/ConceptsField also inherit) is invisible to mypy after
        # narrowing on the mixin alone.
        return queryset.complex_filter(field.get_limit_choices_to())  # type: ignore[attr-defined]

    def prepare_results(self, results):
        """Shape each result down to exactly what FR-012 permits (FR-005): the
        identifier, the preferred label — ``display_label()``, active-language
        with default-language fallback — and the vocabulary's name. Overridden
        outright rather than through ``hook_prepare_results()``: ``display_label``
        and ``vocabulary`` are ``virtual_fields`` with no queryset annotation
        behind them, so the base implementation's ``.values()`` field extraction
        has nothing to build on here, and letting it run first would put
        permission/URL keys in a response FR-012 says must carry only these three.
        """
        return [
            {
                "id": concept.pk,
                "display_label": concept.display_label(),
                "vocabulary": concept.scheme.name,
            }
            for concept in results
        ]
