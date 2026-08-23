# Tasks: Look inside a vocabulary

**Feature**: `014-look-inside-a-vocabulary` · **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Every task is test-first per Article I: the test is written and seen to fail before the production
change that makes it pass. Test scope per task is one class or one file; the full suite runs once per
story, at the story's report.

`[P]` marks tasks that could run in parallel with their siblings. There is no Phase 1 of the kind
#140 needed — the app, its extra, its packaging and its test scaffolding all exist and are unchanged
by this feature.

**Nothing in this feature changes a model, adds a migration, or touches the `exchange` package.** A
task that finds itself editing `controlled_vocabularies/models.py` has gone wrong.

---

## Story US-1 — Open a vocabulary and know what it is (P1)

### T001 — A vocabulary's address serves a page, and an unknown one does not

**Files**: `controlled_vocabularies/ui/views.py`, `controlled_vocabularies/ui/urls.py`,
`tests/test_ui/test_views.py`, `tests/test_ui/test_urls.py`

Add `VocabularyDetailView(MVPListView)` with `model = Concept`, resolving the vocabulary from the
URL slug in `setup()` and raising `Http404` when nothing has it. Route it as
`path("<str:slug>/", …, name="vocabulary-detail")` in the `ui` app's `urlpatterns`, **after** the
list route.

`<str:slug>` and not `<slug:slug>`: the models slugify with `allow_unicode=True` and Django's `slug`
converter is ASCII-only, so a vocabulary named in a non-Latin script would 404 on its own page under
the obvious converter. Assert that directly — a vocabulary whose name is not Latin script serves.

The page's title is the vocabulary's name, set through `get_page_title()`; without that override the
title reads as the concept model's plural, because the view's `model` is `Concept`.

**Proves**: FR-001, FR-017 · US-1 scenarios 1, 7, 8.
**Verify**: the new test module passes; a request to an unknown slug returns 404; an anonymous
request to a known one returns 200.
**Depends on**: nothing.

---

### T002 — The page describes the vocabulary and says where it came from

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

Add the page template, extending django-mvp's `list_view.html` and overriding `page.content` to put
the vocabulary's description and provenance above `{{ block.super }}`. Point the view at it with
`template_name`.

Provenance is the same distinction the list row already draws and must read the same way: a
vocabulary with a fixed identifier is shown as published elsewhere, one without as held here. Where
it was published elsewhere, the publisher's identifier is shown. **The page names no publisher** —
nothing records one, and a heading saying "Publisher" above an identifier would claim one.

A missing description renders nothing at all — no heading, no empty element. Assert on the absence,
not on the page merely still returning 200.

A description of several paragraphs is truncated with `truncatewords`, matching the list row and for
the same reason recorded there: this package ships no stylesheet, and a CSS clamp would rely on a
utility class absent from django-mvp's prebuilt build.

**Proves**: FR-002, FR-003 · US-1 scenarios 1, 2, 3, 5.
**Verify**: the view test module passes, including a vocabulary with no description.
**Depends on**: T001.

---

### T003 — The identifier is a link, on this page and on the list

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_list_item.html`,
`tests/test_ui/test_views.py`

Render the vocabulary's identifier as an anchor on both pages: `href` is the identifier, the link
text is the identifier, and the anchor carries `rel="noopener"`. Nothing is marked safe and nothing
is interpolated into any attribute other than `href`.

Both cases are asserted, because they are different strings: a vocabulary published elsewhere links
to its publisher's address, and one held here links to the address this site composes — which, when
the project is configured consistently, is the page the reader is already on.

Assert too that an identifier which is not a web address — a `urn:` or a `doi:` — is still rendered
as a link and is not silently dropped or rewritten.

**Proves**: FR-004, and the identifier half of FR-013 · US-1 scenario 4.
**Verify**: both test modules pass. The existing list-view assertions about a plain-text identifier
are updated in place, not deleted — this task changes what the list shows and must say so.
**Depends on**: T002.

---

### T004 — The list of vocabularies finally leads somewhere

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_list_item.html`,
`tests/test_ui/test_views.py`

Make each entry's name a link to that vocabulary's page.

The row partial renders in an isolated context holding only the object — no `request`, no `user` —
so the link is built with `{% url %}` and must not reach for anything else.

#140's test asserting that no entry links to the vocabulary it names is now wrong and is replaced by
its inverse. Replace it; do not leave both.

**Proves**: the link half of FR-013 · US-1 scenario 6.
**Verify**: `tests/test_ui/test_views.py` passes; following the link from the list reaches the page.
**Depends on**: T001.

---

### T005 — A misconfigured project is told its identifiers lead nowhere

**Files**: `controlled_vocabularies/ui/checks.py`, `tests/test_ui/test_checks.py`

Add a system check that compares the path the `vocabulary-detail` route reverses to against the path
component of the configured base address, and emits a **warning** when they disagree, because a
vocabulary's identifier will then not lead to its page.

A warning and not an error: a project may resolve its identifiers through a reverse proxy the
package cannot see, so the check reports what it sees rather than refusing to boot. Give it its own
id alongside the existing `controlled_vocabularies.ui.E001`.

The check must not raise when the routes are not mounted at all — a project that installed the app
and has not yet wired its URLs gets silence from this check, not a traceback.

**Proves**: FR-004's precondition, Article IX.
**Verify**: `tests/test_ui/test_checks.py` passes for agreement, disagreement, and unmounted routes.
**Depends on**: T001.

---

### T006 — The demonstration is configured so its identifiers resolve

**Files**: `demo/settings.py`, `tests/test_demo/test_demo.py`

Set `CONTROLLED_VOCABULARIES_BASE_URI = "http://localhost:8000/browse"`, matching where the
demonstration mounts the browsing routes.

Without this the demonstration is exactly the misconfiguration T005 exists to report: its browsing
routes are at `/browse/` while identifiers are composed against `/vocabularies`.

Only the locally authored vocabulary's identifier moves. The imported one keeps its publisher's,
which is the whole point of the distinction — assert both.

**Proves**: US-1 scenario 4 in the demonstration; SC-007.
**Verify**: the demo test module passes; the new check reports no warning against the demo settings.
**Depends on**: T005.

---

### T007 — US-1 documentation

**Files**: `README.md`, `CHANGELOG.md`

Extend the browsing section: a vocabulary's page, what it shows, the route name a project reverses,
and the configuration rule the new check enforces — that the browsing routes must be mounted to match
the configured base address, with what goes wrong when they are not.

Every example is run against this branch before it is written down.

**Proves**: Article VI.
**Verify**: the documented commands and route names resolve against this branch.
**Depends on**: T006.

---

## Story US-2 — See every term the vocabulary holds (P1)

### T008 — Every concept appears, and only this vocabulary's

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_list_item.html`,
`tests/test_ui/test_views.py`

List the vocabulary's concepts through the view's own queryset, with a row partial showing the
concept's label and nothing else — no definition, no note, no identifier, no relation — and offering
nothing to follow.

Assert the flatness directly, on a vocabulary whose concepts form a broader/narrower hierarchy
several levels deep: every concept appears exactly once, and a concept three levels down appears
alongside one at the top rather than beneath it. A test that only counts rows would pass against a
nested rendering.

Assert that a concept of another vocabulary does not appear.

**Proves**: FR-006, FR-012 · US-2 scenarios 1, 2, 3, 9.
**Verify**: the view test module passes.
**Depends on**: T001.

---

### T009 — A concept is named in the reading language

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

Annotate the queryset with `resolved_label`: the preferred label in the active language where the
concept carries one, otherwise `Concept.label`, which is the preferred label in the vocabulary's own
default language.

Build the annotated queryset in `setup()` by assigning `self.queryset`, **not** by annotating the
result of `super().get_queryset()`. Django applies the view's ordering innermost and django-mvp's
search applies `.distinct()` outermost, so an annotation added on the way out does not exist when
the ordering is applied. #140 documents the same trap from the other direction.

One query for the page regardless of how many concepts it shows — assert the query count does not
change between a vocabulary of three concepts and one of thirty.

**Proves**: FR-010, SC-005 · US-2 scenarios 4, 5.
**Verify**: the view test module passes under at least two active languages, including a
concept carrying no label in the active one.
**Depends on**: T008.

---

### T010 — The order is alphabetical by the label shown, and stable

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

`ordering = [Lower("resolved_label"), "pk"]` as a class attribute, for the reason #140 records: `pk`
is what stops two identically labelled concepts landing on either of two pages or on neither once
pagination is in play.

The ordering test must use a vocabulary whose translated labels sort into a **different order** from
their stored ones, and assert the translated order. Ordering by the stored label while displaying
the translated one passes any test built on a vocabulary where the two agree, and that is the
failure this task exists to prevent.

**Proves**: FR-007 · US-2 scenario 6, SC-004.
**Verify**: the view test module passes; two requests return the same order.
**Depends on**: T009.

---

### T011 — A long list is paged, and an empty vocabulary says so

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`tests/test_ui/test_views.py`

Page the list at a fixed size, and give a vocabulary holding no concepts an empty state saying so,
with the rest of the page still rendered.

The paging controls are django-mvp's shipped component, which builds each link with Django's
`querystring` tag and therefore carries an active search across pages without anything being done
about it. Assert that rather than assuming it.

**Proves**: FR-014's first half, FR-016 · US-2 scenarios 7, 8.
**Verify**: the view test module passes; the second page of a long list renders.
**Depends on**: T010.

---

### T012 — US-2 documentation

**Files**: `README.md`, `CHANGELOG.md`

Describe what the page lists and in what order, and state plainly that how concepts relate to one
another is not shown here.

**Proves**: Article VI.
**Verify**: examples run against this branch.
**Depends on**: T011.

---

## Story US-3 — Find a term inside the vocabulary (P2)

### T013 — The search matches every name a term goes by

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

`search_fields = ["label", "labels__text"]`. The first is the default-language preferred label; the
second reaches every label row — preferred labels in other languages, alternative labels, and hidden
labels — in one traversal, which django-mvp's `.distinct()` makes safe.

Four assertions, each on its own concept so a pass cannot come from the wrong field:

- a word only in a preferred label finds it,
- a word only in an alternative label finds it,
- a word only in a hidden label finds it, **and the hidden label appears nowhere in the response**,
- a word only in a definition does **not** find it.

Also assert that a concept in another vocabulary matching the same word is not returned, and that
the search reaches every concept in the vocabulary rather than the page being viewed.

**Proves**: FR-008, FR-009 · US-3 scenarios 1, 2, 3, 4, 6, 9.
**Verify**: the view test module passes.
**Depends on**: T011.

---

### T014 — A search is carried in the address, and case is ignored

**Files**: `tests/test_ui/test_views.py`

The search term travels in `?q=`, so a narrowed list is linkable and returns the same concepts when
opened fresh. Letter case is ignored and the search string is treated as text: `%`, `_` and a quote
are looked for, not obeyed.

Letter case outside ASCII depends on the database, exactly as the list of vocabularies already
discloses (ADR 0014). Follow that precedent: pin the behaviour by test, skip what SQLite cannot do
with the reason named, and say so in the documentation rather than leaving it to be discovered.

**Proves**: FR-008 · US-3 scenarios 5, 8.
**Verify**: the view test module passes on the configured database.
**Depends on**: T013.

---

### T015 — Three empty states, told apart

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`tests/test_ui/test_views.py`

A search matching nothing says so, repeats what was searched for, and offers the way back to the
whole list. A vocabulary holding no concepts keeps its own wording from T011. The two must be
distinguishable in the response, not merely both non-empty.

Read the search term the way django-mvp's own mixin does before filtering — stripped — so the empty
state and the queryset agree on whether a search is in force. #140 records what happens otherwise:
`?q=%20%20` produced an unfiltered list with the box prefilled with whitespace and a link offering
to undo a search that never happened.

The way back is a link the page renders, never markup inside the empty-state heading — django-mvp's
empty-state component autoescapes that string with no slot, so an anchor there shows as literal text
and marking it safe would emit the search term unescaped.

**Proves**: FR-014 · US-3 scenario 7.
**Verify**: the view test module passes; the two states differ in the response body.
**Depends on**: T014.

---

### T016 — The demonstration carries labels a search can find but a reader cannot see

**Files**: `demo/seed/dcmi_types.ttl`, `demo/seed/research_methods.ttl`,
`tests/test_demo/test_seed.py`

Add `skos:altLabel` and `skos:hiddenLabel` values to seeded concepts, through the Turtle files so
they load by the package's own importer rather than a fixture behind it.

The hidden label is the sharper of the two and the reason this task exists: it is the one behaviour
on this page that cannot be confirmed by reading it, only by searching for something that is not
there. Choose a hidden label a reader would plausibly type — a common misspelling of a seeded term.

Seeding stays repeatable: running the command again returns the demonstration to the same state.

**Proves**: FR-018 · SC-007.
**Verify**: `tests/test_demo/test_seed.py` passes; re-seeding is idempotent.
**Depends on**: T015.

---

### T017 — The unattended walk opens a vocabulary and searches inside it

**Files**: `demo/smoke.py`, `tests/test_demo/test_smoke.py`

Extend the walk: after reading the list, follow it to a vocabulary's page, assert a seeded concept
is on it, then request that page with a search and assert the list narrowed — including the search
that matches only a hidden label.

Keep the existing separation: the assertions are functions the test module imports and exercises
directly, so a broken assertion fails in the suite rather than only in CI.

The walk requests addresses directly, so it exercises the search itself and not the search control,
which is what makes it unaffected by django-mvp/django-mvp#282.

**Proves**: FR-019 · SC-007.
**Verify**: `tests/test_demo/test_smoke.py` passes; the demonstration walk runs end to end.
**Depends on**: T016.

---

### T018 — US-3 documentation, and the two things that do not work

**Files**: `README.md`, `CHANGELOG.md`

Document what the search matches and what it does not, the database-dependent letter-case behaviour
outside ASCII, and — plainly — that the search box does not submit on a page without a filter, that
this is django-mvp/django-mvp#282, and that the search itself works through the address.

A reader finding a box that does nothing and no mention of it in the documentation concludes the
package is broken. Saying it is a known upstream defect being waited on costs two sentences.

**Proves**: Article VI, ADR 0015.
**Verify**: every documented example is run against this branch first.
**Depends on**: T017.

---

## Story US-4 — See the groupings a curator made (P3)

### T019 — The collections are named, and an ordered one says so

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`tests/test_ui/test_views.py`

Show the vocabulary's collections, each named, with an ordered one distinguishable from an unordered
one, presented separately from the list of concepts. A vocabulary holding none shows no section at
all — assert the section's absence, not merely that no collection name appears.

Render them with an ordinary template loop, not django-mvp's list component: that component declares
a row-template attribute it never reads and renders whatever row template is in the surrounding
context, so pointing it at a collection row would silently render concept rows instead.

Nothing links to a collection.

**Proves**: FR-011, FR-015 · US-4 scenarios 1, 2, 3, 4.
**Verify**: the view test module passes, including a vocabulary with no collections.
**Depends on**: T011.

---

### T020 — The demonstration carries an ordered and an unordered collection

**Files**: `demo/seed/dcmi_types.ttl`, `demo/seed/research_methods.ttl`,
`tests/test_demo/test_seed.py`

Add one `skos:Collection` and one `skos:OrderedCollection` to the seed, through the Turtle files, so
both render on a page anyone can open.

**Proves**: FR-018 · SC-007.
**Verify**: `tests/test_demo/test_seed.py` passes; re-seeding is idempotent.
**Depends on**: T019.

---

### T021 — US-4 documentation

**Files**: `README.md`, `CHANGELOG.md`

Say what a collection is, that the page names them without opening them, and why.

**Proves**: Article VI.
**Verify**: examples run against this branch.
**Depends on**: T020.

---

## Dependency summary

```
T001 ──┬── T002 ── T003
       ├── T004
       ├── T005 ── T006 ── T007
       └── T008 ── T009 ── T010 ── T011 ──┬── T012
                                          ├── T013 ── T014 ── T015 ── T016 ── T017 ── T018
                                          └── T019 ── T020 ── T021
```

Story order: US-1 → US-2 → US-3 → US-4. Sequential throughout — US-1, US-2 and US-4 all write the
same page template, and US-2 and US-3 both write the view's queryset behaviour.
