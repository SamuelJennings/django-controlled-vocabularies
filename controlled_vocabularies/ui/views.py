"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

Filled in one view per story: ``VocabularyListView`` (US-1). User Story 2's search
narrows the same view rather than adding another (T011-T014, dispatched separately).
"""

from django.db.models import Count
from django.db.models.functions import Lower
from mvp.views import MVPListView

from controlled_vocabularies.models import ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds — FR-001 through FR-004, FR-012, User Story 1 scenarios 1-6."""

    model = ConceptScheme
    list_item_template = "controlled_vocabularies/ui/conceptscheme_list_item.html"
    template_name = "controlled_vocabularies/ui/conceptscheme_list.html"

    # A class attribute, not an `.order_by()` call inside get_queryset() — Django applies
    # `self.ordering` innermost, ahead of both django-mvp's search and order mixins; ordering
    # from our own get_queryset() would land after the search mixin's `.distinct()`, the
    # operand order upstream's own docstring says its mixin order exists to avoid (plan.md
    # Key design decisions #1, decisions.md D2). `pk` is not decoration: without a total
    # order, two same-named vocabularies could land on either of two pages, or on neither,
    # once pagination is in play.
    ordering = [Lower("name"), "pk"]

    def get_queryset(self):
        # Collections are not counted (decisions.md D3) — Count("concepts") reaches the
        # concepts related_name only, never collection_members or any other relation.
        return super().get_queryset().annotate(concept_count=Count("concepts"))
