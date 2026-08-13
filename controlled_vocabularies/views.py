"""Views for :mod:`controlled_vocabularies` (T002, T003, FR-002, FR-005, FR-012).

One route serves both the FK and M2M concept fields, since both target the same
``Concept`` model. The multi-name search and the allowlists that close the
filter/order surface are later tasks. Result shaping is this task's: a result
carries exactly the identifier, the preferred label and the vocabulary a concept
belongs to (FR-005, FR-012) — not the editorial notes or hidden/alternative
labels the concept also holds.
"""

from django_tomselect.autocompletes import AutocompleteModelView

from .models import Concept


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

    def hook_queryset(self, queryset):
        """Attach what ``prepare_results()`` needs before filtering, searching and
        ordering run (plan.md A5) — the library's documented extension point, not
        an override of ``get_queryset()`` (plan.md A6): ``select_related("scheme")``
        for the vocabulary name, ``prefetch_related("labels")`` because
        ``display_label()`` walks ``self.labels.all()`` and a bounded page would
        otherwise cost a query per row (R5).
        """
        return queryset.select_related("scheme").prefetch_related("labels")

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
