# Progress — 014-look-inside-a-vocabulary

Append-only. Each entry is written at the moment the thing happened, not reconstructed afterwards.

---

## 2026-08-20 — Spec gate: APPROVED

Approved by SamuelJennings, in session, on the revised specification (the one with hierarchy
navigation removed).

The gate ran twice. The first request went out with four stories, the second of which navigated the
broader/narrower hierarchy one level at a time. The maintainer asked what "following a concept goes
to this page scoped under it" meant, and on reading the explanation removed hierarchy navigation from
the feature altogether: one flat, searchable list of every concept, and how concepts relate moves to
a concept's own page (#142). The specification, the four stories, the epic body and the pull request
description were re-synced before approval; `decisions.md` D2 and D3 are struck through in place
rather than deleted.

Approved scope, in one line: the page a vocabulary's address leads to — what it says about the
vocabulary, one flat list of every concept it holds, a search over that list, and the collections it
holds, with nothing on the page linking to an individual record.

Open at approval, and carried forward rather than resolved:

- A concept's notation cannot be searched, though the maintainer agreed at intake that it should be.
  Nothing stores one. Raised at the gate and approved with the gap.
- Rendering a vocabulary's identifier as a link is provisional and expected to be revisited once it
  has been seen working.

Surfaces: epic #141 · stories #150, #151, #152, #153 · pull request #154 · branch
`014-look-inside-a-vocabulary`.

---

## 2026-08-20 — Plan written (S3)

`plan.md`, `research.md` and `tasks.md` on the branch. 21 tasks across the four stories, run in
sequence: US-1, US-2 and US-4 all write the same page template, and US-2 and US-3 both write the
view's queryset behaviour, so parallel worktrees would collide at every convergence.

The two findings that shaped the plan and were not visible from the specification:

- **A vocabulary's address and the browsing app's mount have never been made to agree.** The address
  is composed from a setting; the mount is the project's choice; nothing compared them, because until
  now nothing served a page there. The demonstration is itself misconfigured today. The plan adds the
  route, a system check that reports the disagreement as a warning, and a corrected demonstration.
- **The search control still does not submit** on a page carrying search and no filter
  (django-mvp/django-mvp#282, open). The search itself works through the address. ADR 0015 governs:
  the defect is waited on, the affected tests are skipped naming the issue, and nothing is built
  around it — the same state #140 already ships.

No model change, no migration, and nothing in the `exchange` package is touched.

## Design review

Two findings, both verified against the code before being acted on, both applied to the plan and
the task graph:

- The queryset annotation naming a concept in the reading language was called `display_label`, which
  is already a public method on `Concept`. An annotation is set as a plain attribute, so a concept
  fetched through this view would carry a string where the rest of the package calls a method. The
  annotation is now `resolved_label` (D11).
- The new view was to be tested in a module of its own beside the existing one for the same source
  file. Its tests now join `tests/test_ui/test_views.py` as new classes (D12).

No task's scope changed. No change to the specification.

---

## 2026-08-24 · Implementer US-1 · T001

Did: added `VocabularyDetailView(MVPListView)` (model=`Concept`, vocabulary resolved from the
URL slug in `setup()`, `Http404` on no match), and the `<str:slug>/` route named
`vocabulary-detail`, mounted after the list route.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetail
tests/test_ui/test_urls.py -q` — 6 passed.
Next: T002. Watch: nothing outstanding.

## 2026-08-24 · Implementer US-1 · T002

Did: added `conceptscheme_detail.html` (extends django-mvp's `list_view.html`, overrides
`page.content`), pointed the view at it with `template_name`, added `vocabulary` to context.
Description truncated at 40 words; a missing description renders no heading and no empty
element (guarded by `{% if %}`).
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetail
tests/test_ui/test_views.py::TestVocabularyDetailDescriptionAndProvenance -q` — 8 passed.
Next: T003. Watch: nothing outstanding.

## 2026-08-24 · Implementer US-1 · T003

Did: the identifier is now an anchor (`href`/text both the identifier, `rel="noopener"`) on
the vocabulary's own page, in both cases (published elsewhere → publisher's address; held
here → the composed local address, i.e. the reader's current page). On the list row, decisions.md
D8 settles that only a published-elsewhere vocabulary shows an identifier at all — that stays
true; T003 only turns the existing plain-text identifier into a link there.
Updated in place (the named T003 exception): the row test asserting a plain-text identifier
(`test_imported_vocabulary_shows_its_publisher_identifier_and_reads_as_imported`) now asserts an
anchor. No other pre-existing test touched.
Watch: a Django `{# ... #}` comment containing the literal substring `<c-text>` breaks
django-cotton's tag compilation — the comment stops being stripped and an extra element leaks
into the render. Hit this twice (once with `<c-text>`, once with `{% url %}` inside a comment
in T004's attempt). Avoid writing a component or tag name literally inside a comment in these
templates; paraphrase instead.
Verified: `poetry run pytest tests/test_ui/ -q` — 98 passed, 3 skipped (all pre-existing,
tracked to django-mvp#282).
Next: T004.

## 2026-08-24 · Implementer US-1 · T004 — BLOCKED

Did: implemented the row's name as an anchor built with `{% url 'controlled_vocabularies_ui:
vocabulary-detail' slug=object.slug %}` inside a `<c-slot name="title">` (django-cotton does
carry HTML through a named slot unescaped, confirmed by a scratch render before committing to
the approach).
Found: this makes 6 pre-existing tests in `TestVocabularyListEntry` raise `NoReverseMatch`
(`slug=''`), because they build an unsaved `ConceptScheme` via `.build()` with no explicit
`slug`, and the model only derives a slug in `save()`. These tests assert nothing about the
name or a link (concept counts, description handling, the imported/held-here badge) — the
failure is `{% url %}` requiring a resolvable slug to render at all, not a semantic conflict
with what they check.
Not attempted: adding `slug=...` to those `.build()` calls, or giving `ConceptSchemeFactory` a
non-persisted default slug. Both would touch tests or shared fixtures I'm not authorized to
touch this story — none of the six is the one named T004 exception (`#140`'s "no row link"
test), and `tests/factories.py` is outside every task's file list in this story.
Reverted the row template and my new test back to the T003 commit; the tree is green.
Verified: `poetry run pytest tests/test_ui/ -q` — 98 passed, 3 skipped, after the revert.
Next: T005 (does not depend on T004 — see tasks.md's dependency summary). Watch: T004 needs
either explicit authorization to add a `slug` to the six affected `.build()` calls, or a
factory change, before it can land.

## 2026-08-24 · Implementer US-1 · T005

Did: added `check_vocabulary_detail_route` to `controlled_vocabularies/ui/checks.py`
(`controlled_vocabularies.ui.W001`), registered from `ControlledVocabulariesUIConfig.ready()`.
Reverses `vocabulary-detail` with a placeholder slug, strips it back off to get the mount
prefix, compares against `urlparse(conf.get_base_uri()).path`. Silent (`NoReverseMatch`) when
the routes are not mounted at all.
Verified: `poetry run pytest tests/test_ui/ -q` — 101 passed, 3 skipped.
Next: T006.

## 2026-08-24 · Implementer US-1 · T006

Did: set `CONTROLLED_VOCABULARIES_BASE_URI = "http://localhost:8000/browse"` in
`demo/settings.py`, matching where `demo/urls.py` mounts the browsing routes. Extended
`tests/test_demo/test_demo.py` with a subprocess boot that migrates, seeds, and asserts the
locally authored vocabulary's identifier now starts with the configured base address while the
imported one still equals its own `static_uri`.
Verified: `poetry run pytest tests/test_demo/ tests/test_ui/ -q` — 122 passed, 3 skipped.
Next: T007.

## 2026-08-24 · Implementer US-1 · T007

Did: extended README.md's "Finding a vocabulary" section with "A vocabulary's own page" —
what it shows, the `vocabulary-detail` route name (verified reversing against this branch),
and the `CONTROLLED_VOCABULARIES_BASE_URI`/mount-agreement rule `controlled_vocabularies.ui.W001`
enforces. Added the matching CHANGELOG entry.
Verified: `poetry run pytest tests/test_ui/ tests/test_demo/ -q` — 122 passed, 3 skipped.
Next: the story's mandatory full verify.

## 2026-08-24 · Implementer US-1 · Full verify (final ritual)

Ran `poetry run pytest -q` (the full suite, once, per the brief's ritual) and
`/home/sam/.openclaw/workspaces/forge/engineering-org/kit/forge verify --repo
/home/sam/projects/samueljennings/dcv-014-us1`.

Found one pre-existing test newly red:
`tests/test_checks.py::TestCheckSurvivesUnmigratedDatabase::test_check_reports_nothing_against_an_unmigrated_connection`.
`tests.settings` inherits `CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"`
from `tests.settings_core` unchanged, while also mounting `controlled_vocabularies.ui`'s routes
at `/browse/` — the same class of mismatch T005's new check exists to report, now on the
project's own test settings.

Tried and reverted: overriding the setting in `tests/settings.py` to agree with `/browse/`.
Broke eleven pre-existing tests in `tests/test_models.py` and `tests/test_factories.py` that
assert `.uri`/`.local_url` against the literal `https://example.org/vocabularies/...` string
rather than through `conf.get_base_uri()`. Moving the ui app's mount in `tests/urls.py` instead
was not attempted: it would collide with the core app's own `/vocabularies/` mount and undo the
file's own deliberate two-different-prefixes design. Full reasoning in decisions.md D13.

Left `tests/settings.py`, `tests/urls.py` and `tests/test_checks.py` untouched — none is inside
this story's scope, and both available fixes ripple into tests this story does not own.
Reported as a concern rather than patched.

Final state: `poetry run pytest -q` — 1476 passed, 3 skipped, 1 failed (the one above).
`forge verify`: conformance passed, poetry:lint passed, poetry:typecheck passed, poetry:test
failed (the same test), poetry:build passed, docs skipped (needs --base).

## Convergence — T004 unblocked, and the test project's own wiring corrected

T004 landed. The row's name is now an anchor to the vocabulary's page, given through the card's
`title` slot rather than its `title` attribute, which renders as escaped text and so cannot carry
one. `ConceptSchemeFactory` derives the slug `save()` would derive (decisions.md D14), so the nine
built, unsaved fixtures that render the row partial directly no longer raise `NoReverseMatch` — the
blocker reported against this task.

#140's two assertions that no entry links to a vocabulary were replaced by their inverse, in
`tests/test_ui/test_templates.py`: the partial's source must reverse the vocabulary's route, and
every entry on the rendered page must carry an anchor to its own page. The second assertion of the
source-level pair is kept as it was — the in-site link is reversed from the route's name, never
composed from the identifier base address.

The `tests.settings` mismatch left red at the end of the story is fixed by moving the mounts rather
than the base address (decisions.md D13, rewritten): browsing is mounted at `vocabularies/`, the path
`CONTROLLED_VOCABULARIES_BASE_URI` already names, and the core app's autocomplete route moves to
`widget/`. None of the eleven `test_models.py`/`test_factories.py` identifier literals change. The
check's agreeing case in `tests/test_ui/test_checks.py` now needs no `override_settings` at all: it
asserts silence against the project's own correctly wired configuration.

Final state: `poetry run pytest -q` — 1478 passed, 3 skipped, 0 failed. `forge verify`: conformance,
lint, typecheck, test and build all passed; docs skipped (needs `--base`).

## 2026-08-24 · Implementer US-2 · T008

Did: `VocabularyDetailView.get_queryset()` filters `Concept.objects` to `scheme=self.vocabulary`
— nothing else, no relation consulted. Added `concept_list_item.html` (a bare `<c-card
title="{{ object.label }}">`, nothing else) and pointed `list_item_template` at it. Three new
tests in `TestVocabularyDetailConceptList`: a broader/narrower chain three levels deep renders
flat (asserted on DOM nesting — no `.card` contains another `.card` — not on a row count alone),
a fully decorated concept's row carries only its label (note, alternative label, identifier and
relation all attached, none of it leaking into the row's own markup), and a concept in another
scheme does not appear.
RED observed first: stashed the production changes, ran the new class, watched it fail on
`TemplateDoesNotExist: controlled_vocabularies/concept_list_item.html` (the auto-derived path,
since no explicit template existed yet) and on `RuntimeError: Database access not allowed` until
the missing `@pytest.mark.django_db` was added — both for the right reason, then restored.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptList
tests/test_ui/test_views.py::TestVocabularyDetail
tests/test_ui/test_views.py::TestVocabularyDetailDescriptionAndProvenance
tests/test_ui/test_views.py::TestVocabularyDetailIdentifierLink -q` — 14 passed.

## 2026-08-24 · Implementer US-2 · T009

Did: moved queryset construction from `get_queryset()` into `setup()`, assigned to
`self.queryset` (decisions.md D11) — `Concept.objects.filter(scheme=self.vocabulary)` annotated
with `resolved_label = Coalesce(Subquery(<preferred ConceptLabel in get_language()>), F("label"))`.
The subquery matches `language` exactly against `get_language()`, never by base language (D11).
Template now reads `object.resolved_label`. Three new tests in `TestVocabularyDetailConceptLabel`:
a German preferred label shows under `translation.override("de")` (using a label deliberately not
a substring of the English one, so the assertion cannot pass by truncation coincidence), a concept
with no German label falls back to `Concept.label`, and query count stays flat between 3 and 30
concepts (`django_assert_num_queries`).
RED observed first: the German-label test initially used "Granit" against the stored "Granite" —
passed against the unmodified view because "Granit" is a substring of "Granite", a tautological
pass. Replaced with "Kristallgestein" (no relation to the stored label) and re-ran against the
unmodified view: failed with the string absent from the response body, the correct reason. Also
had to teach T008's `test_a_concepts_row_carries_only_its_label` to set
`concept.resolved_label = concept.label` by hand, since the row template now reads an attribute
a plain (unannotated) fixture does not carry.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptList
tests/test_ui/test_views.py::TestVocabularyDetailConceptLabel -q` — 6 passed.

## 2026-08-24 · Implementer US-2 · T010

Did: `ordering = [Lower("resolved_label"), "pk"]` as a class attribute on
`VocabularyDetailView`. Three new tests in `TestVocabularyDetailConceptOrder`: a concept whose
German preferred label sorts before another's under German, but whose own (default-language)
label sorts after it under no override — proving the order follows the *shown* label, not the
stored one; two identically labelled concepts (the second built via `.build()` +
`set_slug()` to dodge the derived-slug collision, mirroring `ConceptSchemeFactory`'s own
tiebreak tests) land in the same order on repeated requests; and two ordinary requests return
the same sequence.
RED observed first: ran the class before adding `ordering` — the language test failed (default
order came back as insertion order, `[zebra, antelope]`, not the alphabetical `[antelope,
zebra]` the assertion expects); the tiebreak and same-order tests already passed by coincidence
of SQLite's natural row order, which is expected — they are regression guards against the
*deterministic* half of FR-007, not proof the alphabetical ordering does not yet exist.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptOrder
tests/test_ui/test_views.py::TestVocabularyDetailConceptList
tests/test_ui/test_views.py::TestVocabularyDetailConceptLabel -q` — 9 passed.

## 2026-08-24 · Implementer US-2 · T011

Did: `get_empty_state_heading()`/`get_empty_state_message()` overrides on
`VocabularyDetailView` naming the vocabulary as holding no concepts, with no message (there is
no create action on this page to point at). No pagination override — `MVPListView`'s own
`paginate_by = 24` default already fixes the page size, matching `VocabularyListView`'s own
precedent. Three new tests in `TestVocabularyDetailConceptPaging`: a 30-concept vocabulary pages
at 24, and the link read out of the first page's own markup (never constructed by hand) reaches
a working second page; a paging link carries forward an arbitrary GET parameter this story gives
no meaning to (real search is US-3's — this proves django-mvp's own `{% querystring %}`
mechanism does the carrying, nothing built here); and an empty vocabulary says so while its
description and title still render.
RED observed first: the paging and querystring-carrying tests passed unmodified (django-mvp's
own defaults and pagination component already do this — no story-specific work needed, matching
the task's own "without anything being done about it" framing); the empty-state test failed
against the base class's generic "There's nothing here yet" heading, absent the word "concepts".
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptPaging -q`
— 3 passed, then the whole file: 63 passed, 3 skipped.

## 2026-08-24 · Implementer US-2 · T012

Did: extended README's "A vocabulary's own page" section — the concept list is flat and
alphabetical by the label shown (reader's language, falling back to the vocabulary's own
default), a row carries only a concept's label, and a bolded line states plainly that how
concepts relate is not shown here (#142). Replaced the stale "a later feature; there is nothing
to list yet" parenthetical the section carried since before T004 landed. Matching CHANGELOG
entry under `[Unreleased] / Added`. No new commands or reverse() calls introduced — nothing
further to verify against the branch beyond the existing example, unchanged.
Noticed but out of scope: "**An entry names a vocabulary — it does not yet link to it** ... a
later feature turns the name into a link" (README, just above "### A vocabulary's own page") is
itself stale — T004 landed the link, in this same story's own history, and the sentence was
never updated. Not touched: it belongs to US-1's T004/T007, not this story's files. Reported in
`concerns`.

## Full verify (final ritual)

`poetry run pytest -q` — 1491 passed, 3 skipped, 0 failed (baseline was 1478 passed, 3 skipped;
13 new tests added across T008-T011, T012 added none).

`forge verify --repo /home/sam/projects/samueljennings/dcv-014-us2`: conformance passed,
poetry:lint passed, poetry:typecheck passed, poetry:test passed, poetry:build passed, docs
skipped (needs `--base`).

## 2026-08-24 · Implementer US-3 · T013

Did: `search_fields = ["label", "labels__text"]` as a class attribute on
`VocabularyDetailView` (decisions.md D4, plan.md item 4). `label` is the preferred label in
the vocabulary's own default language; `labels__text` reaches every `ConceptLabel` row —
preferred labels in other languages, alternative labels, and hidden labels — in one traversal,
which django-mvp's search mixin's own `.distinct()` makes safe. Definitions live on
`ConceptNote`, outside `search_fields`, so they are never matched. Six new tests in a new
`TestVocabularyDetailConceptSearch` class: a word matching only the preferred label, only an
alternative label, and only a hidden label (each on its own concept), the last also asserting
the hidden label is absent from the rendered text — `BeautifulSoup(...).get_text()`, not the raw
response body, since the search box legitimately echoes the raw `?q=` value into an `<input
value="…">` attribute and `get_text()` reads only text nodes, excluding it, the same way a
reader's own view of the page excludes it. A word matching only a definition finds nothing. A
matching concept in another vocabulary is excluded. A search requested directly at `page=2`
(not reached by following a link from page one) still reaches every matching concept and none of
the non-matching ones mixed into what an unfiltered page two would hold — `paginator.count == 30`
pins the whole-vocabulary scope directly.
RED observed first: all six ran against the view before `search_fields` existed. Five failed for
the right reason — unfiltered results leaking through (`{1, 2} == {1}`, a definition match
present when it should be absent, a foreign-vocabulary concept and non-matching concepts leaking
into a 35-strong unfiltered set). The hidden-label test's first attempt asserted against the raw
decoded body and failed as a false positive (the echoed search box value, not a real display of
the label) — corrected to `get_text()` before it was ever run as a claimed pass.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptSearch -q`
— 6 passed. Then the file: 69 passed, 3 skipped (baseline 63 passed, 3 skipped).

## 2026-08-24 · Implementer US-3 · T014

Did: no production change — the brief lists only `tests/test_ui/test_views.py`, and the
behaviour pinned here (address-carried search, ASCII case-insensitivity, LIKE-wildcard/quote
escaping) already comes from django-mvp's own search mixin plus T013's `search_fields`. Nine new
tests in a new `TestVocabularyDetailConceptSearchAddressAndCase` class, mirroring
`TestVocabularySearch`'s own precedent for the list of vocabularies: the same `?q=` address
requested twice returns the same set (scenario 8); a term in one letter case matches a label in
another; `%`, `_` and `'` are looked for literally, not as LIKE syntax; and the ADR 0014
letter-case-outside-ASCII parametrize set (`Ecology`/`Ökologie`/`Гидрология`), skipped on any
non-SQLite backend with the reason named, exactly as the list search already discloses.
RED/characterization check, not RED-then-GREEN: since nothing here is new production code, the
usual RED step would prove nothing. Instead, ran the new class once with all nine passing
(behaviour already correct), then temporarily blanked `VocabularyDetailView.search_fields` to
confirm the tests are not tautological — 7 of 9 failed for the right reason (unfiltered results
leaking through). The 2 that still passed unfiltered are the address-carried-search-returns-
matching case and the true-going ASCII/Ökologie sub-cases of the case parametrize, which cannot
be broken by "no filtering" in a vocabulary holding only the one concept under test — the same
structural limit `TestVocabularySearch`'s own equivalent parametrize set already carries, not a
new weakness introduced here. Restored `search_fields` before re-running to confirm the whole
file was green again.
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptSearchAddressAndCase -q`
— 9 passed. Then the file: 78 passed, 3 skipped.

## 2026-08-24 · Implementer US-3 · T015

Did: `get_search_term()` on `VocabularyDetailView`, stripped exactly the way django-mvp's own
search mixin reads `?q=` before filtering — the same fix #140 made for the vocabulary list,
restated one page down so the empty state and the queryset never disagree about whether a
search is in force. `get_empty_state_heading()`/`get_empty_state_message()` now branch on it:
a search matching nothing repeats the term and offers a different-search hint; an empty
vocabulary keeps T011's own wording unchanged. `search_term` added to the context.
`conceptscheme_detail.html` renders a "Show every concept" link back to the vocabulary's own
(unsearched) address whenever `search_term` is truthy — in the page template itself, not inside
the empty-state heading or message (which django-mvp's own component autoescapes with no slot,
so an anchor there would render as literal text). Unlike #140's identical-shaped feature on the
list of vocabularies, this is not skipped: that page has no template of its own to add the link
to, and this one does (T007).
Five new tests in `TestVocabularyDetailConceptSearchEmptyState`: the no-match wording appears
and echoes the term (with the exact no-concepts string absent); the way-back link appears when
a search matches nothing; T011's own wording and the absence of the link hold for a genuinely
empty vocabulary; the two headings differ as plain strings (constructed directly, without a
request round-trip, mirroring `TestVocabularySearchEmptyState`'s own precedent); and a
whitespace-only `?q=` neither filters nor shows the link.
RED observed first: three of five failed before the change — the no-concepts heading rendered
for a search matching nothing (wrong branch), the way-back link was absent, and the two headings
compared equal as the same unconditional string. The other two already passed unmodified
(`MVPListView`'s own default empty state was already distinct enough from "no such link", and
the paginator already treats a stripped-empty term as no search).
Verified: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptSearchEmptyState -q`
— 5 passed. Then `tests/test_ui/test_views.py tests/test_ui/test_templates.py` together (the
latter mechanically checks every reader-visible template string carries a translation tag,
which the new "Show every concept" link must too): 89 passed, 3 skipped.

## 2026-08-24 · Implementer US-3 · T016

Did: added `skos:altLabel`/`skos:hiddenLabel` to one concept in each seed file — `Dataset`
(`demo/seed/dcmi_types.ttl`, the imported vocabulary) gains `"Data set"@en` (alternative) and
`"Datset"@en` (hidden); `Fieldwork` (`demo/seed/research_methods.ttl`, the authored one) gains
`"Field work"@en` and `"Feildwork"@en`. Both hidden labels are plausible typos of the seeded
term itself, not arbitrary strings — the reason FR-018/D9 call for one at all: a hidden label is
the one behaviour on the page that only a search can confirm, never a reading of it. Loaded
through `import_skos()` (`seed_demo.py`'s existing path), no fixture behind it — the mapping
from `skos:altLabel`/`skos:hiddenLabel` to `ConceptLabel.Kind.ALTERNATIVE`/`HIDDEN` already
existed in `controlled_vocabularies/exchange/mapping.py`, so no importer change was needed or
made. Two new tests in `TestSeedDemo`: both concepts carry exactly the labels seeded, and a
second `seed_demo` run does not duplicate them — inherent from the command's own delete-then-
reimport shape (`ConceptScheme.objects.all().delete()` before each load), not new production
logic.
RED observed first: with the two `.ttl` edits stashed, both new tests failed the right way —
`alt_labels("en")` and `hidden_labels("en")` both came back empty against the unmodified seed
files. Restored the `.ttl` changes and reran: green.
Verified: `poetry run pytest tests/test_demo/test_seed.py -q` — 6 passed. Then
`tests/test_demo/` as a whole (smoke, admin, demo, documented-commands): 23 passed.

## 2026-08-24 · Implementer US-3 · T017

Did: extended `demo/smoke.py`'s walk to follow the vocabulary list to a vocabulary's own page
and search inside it, keeping the existing separation between HTTP transport (`get()`) and
assertion (now four `check_*` functions plus one link-following helper, all importable and
directly testable). `extract_vocabulary_url(list_body, name)` reads the served list markup with
a small regex — no BeautifulSoup, since `demo/smoke.py` is stdlib-only by its own docstring and
`beautifulsoup4` is a `test`-extra dependency the smoke script cannot assume is installed.
`check_vocabulary_page` asserts the seeded concept `Dataset` is on the DCMI Type Vocabulary's own
page; `check_concept_search` searches `Datset` (T016's seeded hidden-label misspelling of
`Dataset`) and asserts the list narrows to it, excluding `Collection` — a search matching only a
hidden label, per FR-019 and User Story 3 scenario 3. `walk()` now chains all four checks in one
pass; the completion message names all three things it walked.
Fourteen new tests in `tests/test_demo/test_smoke.py`: `extract_vocabulary_url` against a hand-
built anchor and against a body naming nothing; `check_vocabulary_page` and `check_concept_search`
each against a real seeded, in-process response (pass, wrong-content fail, non-200 fail, wrong-
narrowing fail) — the same "exercised against a served page in-process" shape #140's own T017
established, so a broken assertion fails in the suite and not only in CI.
RED observed first: stashed the `demo/smoke.py` implementation, wrote the tests against the
unmodified module, ran them — collection failed with `ImportError: cannot import name
'HIDDEN_LABEL_SEARCH_TERM'`, the right reason (the names do not exist yet). Restored the
implementation and reran: 14 passed.
Verified beyond the test suite, per this task's own point (a template that renders in a test
client and not in a browser): migrated and seeded a real demo database, ran `manage.py runserver`
on a real socket, and ran `python demo/smoke.py http://127.0.0.1:8765` against it — `OK: walked
the demo vocabulary list, a vocabulary's page, and a search inside it, at
http://127.0.0.1:8765`, exit 0.
Verified: `poetry run pytest tests/test_demo/test_smoke.py -q` — 14 passed. Then
`tests/test_demo/` as a whole: 31 passed.
