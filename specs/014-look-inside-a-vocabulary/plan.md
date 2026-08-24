# Implementation Plan: Look inside a vocabulary

**Branch**: `014-look-inside-a-vocabulary` | **Date**: 2026-08-20 | **Spec**: [`spec.md`](spec.md)

**Input**: Feature specification from `specs/014-look-inside-a-vocabulary/spec.md`

## Summary

A vocabulary's own address serves a page describing it and listing every concept it holds, narrowed
by a search, with its collections named alongside. The page is the second surface in the `ui` app
#140 created, and it reuses that app's machinery rather than adding any: one more view, one more
row partial, one page template, one more route, and edits to the existing list row so its entries
finally lead somewhere.

The one decision with reach beyond this feature is that **the page is a list of concepts, not a
detail page for a vocabulary** — django-mvp's `MVPDetailView` is deliberately empty below its
heading (its own ADR 0001), so building on it would mean re-implementing search, pagination and the
empty states that `MVPListView` already supplies and that #140 has already proved in this codebase.

## Technical Context

**Language/Version**: Python 3.11 floor for the package; the `ui` extra requires 3.12. Unchanged.

**Primary Dependencies**: none added. django-mvp `>=0.19,<1.0` in the existing `ui` extra.

**Storage**: none. Reads `ConceptScheme`, `Concept`, `ConceptLabel` and `Collection`. **No model
change and no migration** — every field this feature reads already exists.

**Testing**: pytest + pytest-django, extending `tests/test_ui/` and `tests/test_demo/`.

**Target Platform**: any Django project mounting the package's `ui` routes.

**Project Type**: installable Django package (single project, library layout).

**Performance Goals**: the number of queries the page runs does not grow with the number of
concepts shown (SC-005). This is the requirement that decides how a concept's displayed label is
resolved — see Key design decision 3.

**Constraints**: no JavaScript requirement. No access rule of the package's own. No link to any
individual concept or collection. No model change.

**Scale/Scope**: four user stories, one new view, two new templates, one edited template, one new
route, one new system check, seed-data additions, and documentation. **The stories run in sequence,
not in parallel** — US-2, US-3 and US-4 all write into the same view class and the same page
template, so parallel worktrees would collide at every convergence.

## Constitution Check

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I — Test-First | Every task writes its test before its code; the acceptance scenarios are the test names | Complies |
| II — Simplicity | One view class, no new abstraction layer, no model change. The alternative considered and rejected (a detail view composed with `MultipleObjectMixin` and the search and order mixins) is strictly more machinery for the same page | Complies |
| III — Anti-Abstraction | The view subclasses `MVPListView` directly and sets attributes; nothing is wrapped | Complies |
| IV — Integration-First | The page is exercised through the test client against real URLs, and through the demonstration project | Complies |
| V — Security & data-safety | No write path, no user input reaching the ORM except a search term the ORM parameterises. A vocabulary's identifier becomes an outbound link — see Key design decision 6 | Complies, with one deliberate change noted |
| VI — Documentation | The README's browsing section and the demonstration walk both change in this branch, alongside the code | Complies |
| VII — Dependency discipline | Nothing added | Complies |
| IX — URI identity | The page must be served at the address a vocabulary's identifier composes, or FR-004's link is a lie. This is the feature's sharpest constraint — see Key design decision 2 | Complies via a new system check |
| XII — Internationalization | Every string translatable; a concept is named in the reading language | Complies, see Key design decision 3 |
| XIII — Data-model conventions | No model change, so nothing to conform to | Not applicable |
| XIV — Test structure | `tests/test_ui/` mirrors the source tree. The new view is added to `controlled_vocabularies/ui/views.py`, so its tests join the existing `tests/test_ui/test_views.py` as new classes rather than a second module for the same source file | Complies |

## Key design decisions

### 1. The page is a list view over concepts, with the vocabulary resolved once in `setup()`

`VocabularyDetailView(MVPListView)` with `model = Concept`. The vocabulary is resolved from the
URL's slug in `setup()`, raising `Http404` when no vocabulary has it, and put in the template
context. The page's title is the vocabulary's name.

Two alternatives were weighed and rejected:

- **`MVPDetailView` with the concepts rendered by hand.** django-mvp's detail template is
  deliberately empty below the heading and its ADR 0001 states that is finished behaviour, not a
  placeholder. Search, pagination, the two empty states and the paging controls would all have to be
  re-implemented, having already been implemented once in this codebase by #140.
- **`MVPDetailView` composed with `MultipleObjectMixin` and django-mvp's `SearchOrderMixin`.**
  Technically supported and more machinery than the page needs: a strict mixin ordering constraint,
  two paginators to reconcile, and a `directory` whose URL kwargs must branch per action. Article II
  settles it.

The cost of the chosen route is that the page's `model_info` describes concepts rather than the
vocabulary, so the page title and breadcrumbs are set explicitly rather than derived. That is two
method overrides.

### 2. The route must line up with the address a vocabulary's identifier composes

A vocabulary's `local_url` is `CONTROLLED_VOCABULARIES_BASE_URI` + `/` + its slug — a *setting*,
composed in `conf.get_base_uri()`, never a URL reversal. The `ui` app is mounted wherever the
project chooses. Nothing has ever made the two agree, and until now nothing needed to: no page was
served at that address.

FR-004 requires that following a locally held vocabulary's identifier lands back on its page. That
is false whenever the mount and the base address disagree — and it is false in the demonstration as
it stands today, which mounts the browsing routes at `/browse/` while the default base address is
`http://localhost:8000/vocabularies`.

Three parts, all in this branch:

1. **Route:** `path("<str:slug>/", VocabularyDetailView.as_view(), name="vocabulary-detail")` in
   `controlled_vocabularies/ui/urls.py`. **`<str:slug>`, not `<slug:slug>`** — the models slugify
   with `allow_unicode=True`, and Django's `slug` converter matches ASCII only, so a vocabulary
   named in a non-Latin script would 404 on its own page under the obvious converter.
2. **System check (warning, not error):** when the `ui` app is installed, compare the path the
   `vocabulary-detail` route reverses to against the path component of the configured base address,
   and warn when a vocabulary's identifier will therefore not lead to its page. A warning rather
   than an error because a project may serve its identifiers through a reverse proxy that resolves
   them correctly; the package cannot know, so it says what it sees and does not refuse to boot.
   It joins the existing check in `controlled_vocabularies/ui/checks.py`.
3. **Demonstration:** set `CONTROLLED_VOCABULARIES_BASE_URI = "http://localhost:8000/browse"` in
   `demo/settings.py`, so the demonstration models a correctly configured project rather than the
   misconfiguration the new check exists to report.

### 3. A concept's displayed label is annotated, never resolved per row

FR-010 names a concept in the reading language, falling back to the vocabulary's own default
language — which is exactly what `Concept.label` holds. Resolving that per row is a query per
concept, and SC-005 forbids it.

`setup()` assigns `self.queryset` to `Concept.objects.filter(scheme=…)` annotated with
`Coalesce(Subquery(<the preferred ConceptLabel in the active language>), F("label"))` as
`resolved_label`. **Assigning `self.queryset` in `setup()` rather than annotating inside
`get_queryset()` is deliberate and load-bearing**, and it is the same trap #140 documented: Django
applies `self.ordering` innermost, and django-mvp's search mixin applies `.distinct()` outermost.
An annotation added after `super().get_queryset()` would not exist when the ordering is applied.
Setting `self.queryset` puts the annotation underneath everything.

Ordering is `[Lower("resolved_label"), "pk"]` as a class attribute, for the same reason #140 gives:
`pk` is not decoration, it is what stops two identically labelled concepts landing on either of two
pages or on neither once pagination is in play.

The active language is matched exactly, not by base language. Labels are stored under the site's
configured languages and `get_language()` returns one of those same codes, so an exact match is
correct here; the base-language matching in `CONTEXT.md` belongs to import, where the incoming tag
comes from a publisher and is not drawn from that set.

### 4. Search matches two fields and nothing more

`search_fields = ["label", "labels__text"]`. The first is the default-language preferred label; the
second reaches every `ConceptLabel` row — preferred labels in other languages, alternative labels,
and hidden labels — in one traversal. django-mvp's search mixin applies `.distinct()`, which the
join makes necessary.

Hidden labels are matched and never displayed, which FR-009 requires and which this arrangement
gives for free: display comes from `resolved_label`, which only ever reads preferred labels.

Definitions and notes live on `ConceptNote` and are not in `search_fields`, so they are not matched.

### 5. The collections are rendered by hand, not through django-mvp's list component

django-mvp's `<c-page.list>` declares a `card` attribute and never reads it — it renders whatever
`list_item_template` is in the surrounding context. A second list on the page therefore cannot be
given its own row template through the component's own API, and passing one silently renders concept
rows for collections.

Collections are a short, unpaginated list of names, so they are rendered with an ordinary template
loop in the page template. This is not a workaround for a defect to be reported: the component is
documented for the page's one list, and a second list was never in its contract.

### 6. The identifier becomes an outbound link, on both pages

FR-004 and FR-013. On a vocabulary published elsewhere the identifier points at a third-party
address the site does not control, so the anchor carries `rel="noopener"` and the identifier is
rendered as text inside the anchor rather than interpolated into any attribute besides `href`.
Django's autoescaping covers the rest; nothing here is marked safe.

This reverses #140's D6, which rendered the identifier as plain text on the grounds that a
publisher's identifier need not resolve. That reasoning still holds — a `urn:` or `doi:` identifier
will fail in the browser — and the maintainer's instruction is that a linked-data record presented
without its link makes less sense than a link that sometimes fails. An ADR records the reversal at
convergence.

### 7. The page template is this package's own, not an override of django-mvp's

`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
extending django-mvp's `list_view.html` and overriding `page.content` to put the vocabulary's
description, provenance, identifier and collections above `{{ block.super }}`'s concept list.

This is worth stating because #140 removed a page template on the maintainer's instruction and
recorded why (its D23): that template overrode *django-mvp's own* `list_view.html` to work around
two defects in the shipped search control, and an override in a consumer outlives the upstream fix
that made it unnecessary. Supplying a page template for a page this package owns is the extension
point django-mvp documents, and is the opposite case.

### 8. The search control still does not submit, and this feature does not fix it

django-mvp's shipped search box points at a form element that only its filter action defines, so on
a page with search and no filter the box renders and submits nothing
(**django-mvp/django-mvp#282**, open as of 2026-08-20). The search itself works: `?q=` filters
correctly, the narrowed address is linkable, and the unattended demonstration walk exercises it.

The standing decision is ADR 0015 — an upstream defect is waited on, not worked around — and #140
already ships this exact state on the list of vocabularies with its affected tests skipped and the
issue named. This feature does the same rather than diverging: the tests that need a submitting box
are skipped citing #282, and nothing is built around it.

## Story sequence and structure

| Story | Adds |
|---|---|
| **US-1** (P1) | The route, the view's resolution of the vocabulary, the page template's descriptive half, the system check, the demo's base-address setting, and the two link changes to the existing list row |
| **US-2** (P1) | The concept queryset: the `resolved_label` annotation, the ordering, pagination, the row partial, and the empty state for a vocabulary holding no concepts |
| **US-3** (P2) | `search_fields`, the two empty states told apart, the seed file's alternative and hidden labels, and the extension of the unattended walk |
| **US-4** (P3) | The collections section, the seed file's two collections |

Sequential. US-2 and US-3 both write the view's queryset behaviour and US-1, US-2 and US-4 all write
the same page template.

## Files this feature touches

**New**
- `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`
- `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_list_item.html`

**Changed**
- `controlled_vocabularies/ui/views.py` — one new class
- `controlled_vocabularies/ui/urls.py` — one route
- `controlled_vocabularies/ui/checks.py` — one check
- `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_list_item.html` — two links
- `demo/settings.py` — the base address
- `demo/seed/dcmi_types.ttl`, `demo/seed/research_methods.ttl` — collections, alternative and hidden labels
- `demo/smoke.py` — the extended walk
- `tests/test_ui/test_views.py`, `tests/test_ui/test_checks.py`, `tests/test_ui/test_urls.py`,
  `tests/test_demo/test_smoke.py`, `tests/test_demo/test_seed.py`
- `README.md` — the browsing section
- `CHANGELOG.md`

**Unchanged, deliberately**: every model, every migration, `controlled_vocabularies/urls.py`, and
the whole `exchange` package.

## Risks

- **The ordering-versus-annotation interaction** (decision 3) is the one place a plausible
  implementation is silently wrong: annotate in the wrong place and the page raises, or worse,
  orders by the stored label while displaying the translated one. The task that adds ordering asserts
  on a vocabulary whose translated labels sort differently from its stored ones, so the two cannot
  pass for each other.
- **`<str:slug>` will also match a slug containing characters a vocabulary can never have.** Those
  simply 404 at the lookup. The route must not be so loose that it shadows a future sibling route;
  it is declared after the list route and there is nothing else in this app's namespace.
- **The demonstration's base-address change moves every identifier in it.** The seeded imported
  vocabulary keeps its publisher's identifier, so only the locally authored one moves, which is the
  intended effect and is asserted rather than assumed.
