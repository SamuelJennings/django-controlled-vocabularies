"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

Filled in one view per story: ``VocabularyListView`` (US-1). User Story 2's search
narrows the same view rather than adding another (T011-T014, dispatched separately).
"""

from django.db.models import Count
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from mvp.views import MVPListView

from controlled_vocabularies.models import ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds — FR-001 through FR-004, FR-011 through FR-013,
    User Story 1 scenarios 1-7.
    """

    model = ConceptScheme
    list_item_template = "controlled_vocabularies/ui/conceptscheme_list_item.html"
    template_name = "controlled_vocabularies/ui/conceptscheme_list.html"

    # django-mvp's SearchMixin reads ?q=, strips it, and applies case-insensitive
    # substring matching across these fields with OR semantics (T011, FR-006).
    search_fields = ["name", "description"]

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

    def get_empty_state_heading(self):
        # This story has no search yet (T011-T014, User Story 2), so there is only one
        # empty state to report — the site itself holds nothing. Once search exists, the
        # second state (a search matching nothing, distinct wording — decisions.md D4)
        # branches here on the ``?q=`` value.
        return _("This site holds no vocabularies")

    def get_empty_state_message(self):
        # No message: the base class's own default points at a create button this page
        # does not show (show_create_action is never set), and this empty state has
        # nothing else useful to add beyond the heading.
        return None
