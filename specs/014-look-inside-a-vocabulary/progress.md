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
