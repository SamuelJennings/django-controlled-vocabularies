"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

One view: ``VocabularyListView``. Search narrows that same view rather than adding
another, so both user stories land here.
"""

from django.db.models import Count
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from mvp.views import MVPListView

from controlled_vocabularies.models import ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds, narrowed by an optional search — FR-001 through
    FR-013, User Story 1 scenarios 1-7 and User Story 2 scenarios 1-6.
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

    def get_search_term(self):
        # Read and stripped exactly as django-mvp's own search mixin does it before
        # filtering (`mvp/views/list.py`), so "a search is in force" means the same thing
        # to the empty states as it does to the queryset. The `search_query` the mixin puts
        # in the context is the raw value, unstripped, and is not a substitute here.
        return self.request.GET.get("q", "").strip()

    def get_empty_state_heading(self):
        # Two distinct empty states, never one (decisions.md D4): a search matching
        # nothing says so and repeats the term; a genuinely empty site keeps its own
        # wording. Both branches return plain translatable text — never mark_safe, never
        # format_html. The way back to the full list is the link the actions block renders
        # (conceptscheme_list.html), not markup here — django-mvp's empty-state component
        # renders this string autoescaped with no slot, so an anchor here would show as
        # literal text, and marking it safe would emit the search term unescaped.
        search_term = self.get_search_term()
        if search_term:
            return _("Nothing matches “%(term)s”") % {"term": search_term}
        return _("This site holds no vocabularies")

    def get_empty_state_message(self):
        if self.get_search_term():
            return _("Try a different search term.")
        # No message: the base class's own default points at a create button this page
        # does not show (show_create_action is never set), and this empty state has
        # nothing else useful to add beyond the heading.
        return None
