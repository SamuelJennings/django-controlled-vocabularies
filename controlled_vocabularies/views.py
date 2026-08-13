"""Views for :mod:`controlled_vocabularies` (T002, FR-002).

One route serves both the FK and M2M concept fields, since both target the same
``Concept`` model. The view answers with the library's own behaviour and nothing
more; result shaping (``virtual_fields``, ``prepare_results()``), the multi-name
search, and the allowlists that close the filter/order surface are later tasks.
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
