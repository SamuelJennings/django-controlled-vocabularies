"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

Filled in one view per story: ``VocabularyListView`` (US-1). User Story 2's search
narrows the same view rather than adding another (T011-T014, dispatched separately).
"""

from mvp.views import MVPListView

from controlled_vocabularies.models import ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds — FR-001, FR-012, User Story 1 scenario 1."""

    model = ConceptScheme
    list_item_template = "controlled_vocabularies/ui/conceptscheme_list_item.html"
    template_name = "controlled_vocabularies/ui/conceptscheme_list.html"
