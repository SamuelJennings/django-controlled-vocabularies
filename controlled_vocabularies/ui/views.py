"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

Filled in one view per story: ``VocabularyListView`` (US-1). User Story 2's search
narrows the same view rather than adding another (T011-T014, dispatched separately).
"""

from django.db.models import Count
from mvp.views import MVPListView

from controlled_vocabularies.models import ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds — FR-001 through FR-003, FR-012, User Story 1 scenarios 1-5."""

    model = ConceptScheme
    list_item_template = "controlled_vocabularies/ui/conceptscheme_list_item.html"
    template_name = "controlled_vocabularies/ui/conceptscheme_list.html"

    def get_queryset(self):
        # Collections are not counted (decisions.md D3) — Count("concepts") reaches the
        # concepts related_name only, never collection_members or any other relation.
        return super().get_queryset().annotate(concept_count=Count("concepts"))
