"""Views for the opt-in vocabulary-browsing front end (013-find-a-vocabulary).

One view: ``VocabularyListView``. Search narrows that same view rather than adding
another, so both user stories land here.
"""

from django.db.models import Count, F, OuterRef, Subquery
from django.db.models.functions import Coalesce, Lower
from django.http import Http404
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from mvp.views import MVPListView

from controlled_vocabularies.models import Concept, ConceptLabel, ConceptScheme


class VocabularyListView(MVPListView):
    """Every vocabulary the site holds, narrowed by an optional search — FR-001 through
    FR-013, User Story 1 scenarios 1-7 and User Story 2 scenarios 1-6.
    """

    model = ConceptScheme
    list_item_template = "controlled_vocabularies/ui/conceptscheme_list_item.html"

    # No page template of our own: the page is django-mvp's `list_view.html`, reached through
    # the base class's own fallback. This package supplies the row and nothing else, which is
    # the extension point django-mvp documents. An earlier revision overrode the page to work
    # around two faults in the shipped search control (django-mvp/django-mvp#282); the override
    # was removed on the maintainer's instruction. A template override in a consumer outlives
    # the upstream fix that made it unnecessary, and a shell package whose consumers all carry
    # overrides has stopped being a shell. The tests those faults block are skipped, naming the
    # issue they wait on (decisions.md D23).

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

    # A search longer than this many words keeps its first this-many and drops the rest.
    max_search_words = 100

    def setup(self, request, *args, **kwargs):
        # django-mvp's search mixin ORs one condition per word per search field with no
        # bound, and reads `?q=` from the request itself rather than through a method a
        # subclass could override (`mvp/views/list.py`). Past roughly 400 words the resulting
        # expression exceeds SQLite's parser depth limit and the page raises OperationalError
        # — a 500 on a page anyone can reach, from a query string short enough to fit an
        # ordinary request line. Bounding the term once, here, before anything has read it,
        # is what keeps the queryset, the page's own context and the empty states agreeing on
        # what was searched for. Filed upstream as django-mvp#281; this stays correct whether
        # or not upstream grows a bound of its own.
        #
        # The bound is set far above any search a person means and far below where the
        # database gives out, because dropping words from an OR search drops matches: a bound
        # tight enough to trim a real search would answer a different question in silence.
        super().setup(request, *args, **kwargs)
        words = request.GET.get("q", "").split()
        if len(words) > self.max_search_words:
            bounded = request.GET.copy()
            bounded["q"] = " ".join(words[: self.max_search_words])
            request.GET = bounded

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

    def get_context_data(self, **kwargs):
        # The template needs the same stripped term the queryset was filtered on. Branching
        # the page on the raw `search_query` put `?q=%20%20` into a half-searched state: the
        # unfiltered list, but with the box prefilled with whitespace and the way-back link
        # offering to undo a search that never happened.
        context = super().get_context_data(**kwargs)
        context["search_term"] = self.get_search_term()
        return context

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


class VocabularyDetailView(MVPListView):
    """A single vocabulary's own page: its description, provenance and the concepts it
    holds (014-look-inside-a-vocabulary, US-1).

    A list view over ``Concept``, not a detail view over ``ConceptScheme`` — plan.md Key
    design decision #1. django-mvp's ``MVPDetailView`` is deliberately empty below its
    heading (its own ADR 0001), so building on it would mean re-implementing search,
    pagination and the empty states ``MVPListView`` already supplies. The vocabulary
    itself is resolved once, in ``setup()``, and carried on ``self.vocabulary`` for every
    hook that needs it.
    """

    model = Concept
    template_name = "controlled_vocabularies/ui/conceptscheme_detail.html"
    list_item_template = "controlled_vocabularies/ui/concept_list_item.html"

    # T010: by the label actually shown, not the stored default-language one — Django
    # applies this innermost (D11), ahead of self.queryset's own annotation being
    # consulted by anything downstream. `pk` is not decoration: without a total order,
    # two identically labelled concepts could land on either of two pages, or on
    # neither, once pagination is in play (#140 makes the same point for vocabularies).
    ordering = [Lower("resolved_label"), "pk"]

    # django-mvp's SearchMixin reads ?q=, strips it, and applies case-insensitive
    # substring matching across these fields with OR semantics, joined with `.distinct()`
    # (T013, FR-008, FR-009, decisions.md D4/plan.md item 4). `label` is the preferred
    # label in the vocabulary's own default language; `labels__text` reaches every
    # ConceptLabel row in one traversal — preferred labels in other languages,
    # alternative labels, and hidden labels. Definitions and notes live on ConceptNote
    # and are deliberately absent, so they are never matched. A hidden label is matched
    # here and never displayed: display comes from `resolved_label`, which only ever
    # reads preferred labels.
    search_fields = ["label", "labels__text"]

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.vocabulary = ConceptScheme.objects.get(slug=kwargs["slug"])
        except ConceptScheme.DoesNotExist as exc:
            raise Http404(_("No vocabulary matches this address.")) from exc
        # US-2 T009, decisions.md D11: assigned to self.queryset here, never built by
        # annotating the result of super().get_queryset() — Django applies
        # self.ordering innermost, ahead of both django-mvp's search and order mixins'
        # own get_queryset() overrides, so an annotation added on the way out would not
        # exist yet when the ordering (T010) is applied. The active language is matched
        # exactly, not by base language (D11) — labels are stored under the site's own
        # configured languages, which is exactly what get_language() returns one of.
        preferred_in_active_language = ConceptLabel.objects.filter(
            concept=OuterRef("pk"),
            language=get_language(),
            kind=ConceptLabel.Kind.PREFERRED,
        ).values("text")[:1]
        # Every concept this vocabulary holds, and only this vocabulary's. No relation
        # is consulted, so the list is flat by construction — a concept three levels
        # down a broader/narrower chain is a plain sibling of one at the top, never
        # rendered nested beneath it (T008, FR-006, FR-012).
        self.queryset = Concept.objects.filter(scheme=self.vocabulary).annotate(
            resolved_label=Coalesce(Subquery(preferred_in_active_language), F("label"))
        )

    def get_page_title(self):
        # Without this override the title reads as the concept model's plural, because
        # the view's `model` is `Concept` — the page describes the vocabulary, not concepts.
        return self.vocabulary.name

    def get_search_term(self):
        # Read and stripped exactly as django-mvp's own search mixin does it before
        # filtering (`mvp/views/list.py`), so "a search is in force" means the same
        # thing to the empty states and the "back to the whole vocabulary" link as it
        # does to the queryset (T015, #140's own `?q=%20%20` trap restated here).
        return self.request.GET.get("q", "").strip()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vocabulary"] = self.vocabulary
        context["search_term"] = self.get_search_term()
        return context

    def get_empty_state_heading(self):
        # T015, decisions.md D7: two distinct empty states, never one — a search
        # matching nothing says so and repeats the term; a genuinely empty vocabulary
        # keeps T011's own wording. Never mark_safe, never format_html.
        search_term = self.get_search_term()
        if search_term:
            return _("Nothing matches “%(term)s”") % {"term": search_term}
        return _("This vocabulary holds no concepts")

    def get_empty_state_message(self):
        if self.get_search_term():
            return _("Try a different search term.")
        return None
