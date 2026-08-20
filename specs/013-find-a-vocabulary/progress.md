# Progress — 013 Find a vocabulary

Append-only. Each entry: what happened, when, and the evidence for it.

## 2026-08-19 — Spec gate: APPROVED

Approved by Sam in session, on the epic (#140) plus story sub-issues #143 (US-1, P1) and #144
(US-2, P2), with `spec.md` and `decisions.md` on the branch. Gate brief posted as a comment on
#140 (comment 5345920852). Draft PR #145 open, bot-authored, milestone v1.0.0.

Two items raised and not folded into the feature: the goal G7 corner nobody fills (searching
concepts across vocabularies), and that "imported" is inferred from the identifier being fixed by
a publisher, which R4's publishing will complicate.

## 2026-08-19 — S3 PLAN

`research.md` read django-mvp v0.19.1 and django-literature's inner `ui` app against source.
`plan.md` and `tasks.md` authored: one new inner app behind a packaging extra, 14 tasks in three
phases (5 foundational, 5 for US-1, 4 for US-2). Ledger created and schema-valid.

Two findings from research that shape the plan: django-mvp's pagination preserves the query string
at 0.19.1 (so FR-010 needs a test, not a workaround), and its search action renders an input whose
form is defined by the *filter* action, so search alone cannot submit — worked around in our own
page template, to be filed upstream.

## 2026-08-19 — Design review: CHANGES REQUESTED, then applied

Three lenses over the design artefacts, no code. Six findings, all verified against django-mvp
v0.19.1 source before acting on them. All six applied to `plan.md` and `tasks.md`:

- **FR-009 was unreachable through the mechanism the plan chose** (high). django-mvp's empty-state
  component renders heading and message as autoescaped strings with no slot, so the required "back
  to the full list" link could not live in the message — and the shortest repair, `mark_safe` over
  a string that also echoes the search term, would have emitted an unescaped attacker-supplied
  term. The link now renders in the actions block T011 already owns; both empty-state methods
  return plain text, and T013 asserts on the escaped form.
- **`django_tables2` in the test settings** would have broken collection of the whole suite —
  it is not a django-mvp dependency, `--extras ui` does not install it, and `tests/settings.py` is
  the repo-wide settings module. Dropped, along with the inert `SITE_ID`.
- **The `[tool.forge.conformance] non-mirror-paths` declaration the plan promised** had no task
  creating it. T001 now writes it, naming the four files rather than the directory.
- **django-mvp's search submit button ships a hard-coded English label** its component exposes no
  variable for, which made SC-006 false. T011 renders our own translated button.
- **US-1 and US-2 are not independent** — same view module, same page template, same test module,
  and T011 rewrites the block T006 writes. They now run in sequence, and T011's dependency points
  at T009 rather than through a documentation task.
- **Ordering moved from `get_queryset()` to the `ordering` class attribute**, so it applies ahead
  of the search mixin's `.distinct()` rather than after it — the operand order upstream's own
  docstring says its mixin order exists to avoid, and one this SQLite-only suite could not catch.

Three editorial notes also applied: `paginate_by = 24` restated an inherited default and is gone;
search is multi-word OR, so a second word widens the list, which T014 now documents; and the
`tests/test_ui/conftest.py` in the plan's tree was unwanted, since the root conftest already
exposes the `scheme` fixture.

## 2026-08-19 21:11 UTC — forge-run-watcher: S3R exit, IMPLEMENT begun

`stage-exit --stage S3R` green (clarifications, ledger-schema, ledger-state, issue-titles,
pr-title). Transitioned `DESIGN_REVIEW` → `IMPLEMENT` (commit `06e318a`, pushed as the bot).
Recorded `gates.plan: notified` — the plan brief plus the S3R verdict (request_changes, 6
findings, all applied) carried as the veto-window notification per the inter-gate autonomy rule;
silence stands as consent.

Before dispatching the foundational phase, found `dcv-013-us1` (worktree, branch `013-us1`, based
on `b676c35`) already carrying live commits for T001–T005 plus a D8 decisions.md entry, the latest
timestamped under two minutes before this check. No task-brief or completion-report artifact for
this dispatch exists anywhere on disk or in reachable session logs, and `feature-state.json`'s
`stories[].worktree` is still null, so whatever dispatched it did not go through the ledger. Took
no action: did not dispatch a second Implementer into the same scope, did not touch the worktree,
did not edit any story or task status. This is live in-progress work, not a stalled one — left
alone for whoever holds that session to report back through the normal S4 acceptance path
(`check-receipts`, independent re-verify, `story-done`).
## 2026-08-19T00:00:00Z · Implementer US0 · T001

Did: declared `django-mvp` as an optional dependency (`>=0.19,<1.0`, `python = ">=3.12"` marker),
added `[tool.poetry.extras] ui = ["django-mvp"]`, `[tool.deptry.package_module_name_map]
django-mvp = "mvp"`, and `[tool.forge.conformance] non-mirror-paths` naming the four T001/T004
test files. Regenerated `poetry.lock`. Changed `.github/workflows/tests.yml`'s
`poetry-install-args` from `''` to `'--extras ui'`.

Verified: `poetry lock` (clean write), `poetry check` exit 0 (pre-existing legacy-format
deprecation warnings only, unrelated to this change), `poetry install --extras ui` (8 packages
installed: django-mvp + its own deps), `poetry run pytest -q` — 1355 passed. `poetry run deptry .`
reports `DEP002 'django-mvp' defined as a dependency but not used` — expected per decisions.md D7:
nothing imports `mvp` until T005's `ui/checks.py` does. The pyproject/lock/workflow changes stay
uncommitted until then (see D7's revision below, after the first commit attempt was rejected).

Next: T002 — the ui app and its registration test.
Watch: this repo's pre-commit hook runs `deptry` at commit time, not only at story end — the
`django-mvp` declaration cannot be committed on its own (see D7, revised after the first commit
attempt was rejected). T001's `pyproject.toml`/`poetry.lock`/workflow changes land in the same
commit as T005's, once `checks.py` gives `deptry` a real import to find.

## 2026-08-19T00:05:00Z · Implementer US0 · T002

Did: `controlled_vocabularies/ui/__init__.py` (docstring only), `controlled_vocabularies/ui/apps.py`
(`ControlledVocabulariesUIConfig`, `name="controlled_vocabularies.ui"`,
`label="controlled_vocabularies_ui"`, distinct from the core app's `controlled_vocabularies`
label). Test first: `tests/test_ui/test_apps.py`'s `TestUIAppConfig`, run and observed failing
(`LookupError: No installed app with label 'controlled_vocabularies_ui'` and
`FileNotFoundError` for `__init__.py`) before either file existed.

Verified: `poetry run pytest tests/test_ui/test_apps.py -q` — 2 passed. `poetry run ruff check
controlled_vocabularies/ui/ tests/test_ui/` — all checks passed.

Next: T003 — the widened test settings and the core-only settings module.

## 2026-08-19T00:10:00Z · Implementer US0 · T003

Did: `tests/settings_core.py` (new) — today's `tests/settings.py` contents verbatim, with
`ROOT_URLCONF` pointed at a new empty `tests/urls_core.py`. `tests/settings.py` now star-imports
`tests.settings_core` and appends the ui stack — `django_cotton`, `easy_icons`, `flex_menu`,
`mvp`, `crispy_forms`, `crispy_tailwind`, `controlled_vocabularies.ui` in `INSTALLED_APPS`
(django-literature's order, filtered per decisions.md: `django.contrib.sites`,
`django.contrib.staticfiles` and `django_tables2` dropped — the first two are already in the
core list or unneeded, and this page is a card grid, not a table), `mvp.context_processors.
mvp_config` appended to `TEMPLATES`, `CRISPY_TEMPLATE_PACK`, `CRISPY_ALLOWED_TEMPLATE_PACKS`,
`EASY_ICONS`, `FLEX_MENUS`, and `ROOT_URLCONF` reset to `tests.urls` (settings_core points it at
`tests.urls_core`).

**Deviation from tasks.md's literal text**: did not touch `tests/urls.py`. T003's own description
says it should mount `controlled_vocabularies.ui.urls` under a prefix, but that module is created
by T006 (Phase 2, `US-1`), which is out of this story's scope — my brief's prohibitions name "the
ui view, templates, urls" as US-1's work, and its T003 acceptance criterion for this task tests
only `INSTALLED_APPS` and `manage.py check`, not a urls.py mount. Mounting an `include()` of a
module that does not exist yet would also fail `manage.py check`'s own URL-resolution checks
immediately, contradicting the "clean under both settings modules" requirement. Left for T006.

Verified: `poetry run pytest -q` — 1357 passed (2 more than T001's baseline: T002's
`test_ui/test_apps.py`). `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin check` —
"System check identified no issues (0 silenced)". `DJANGO_SETTINGS_MODULE=tests.settings_core
poetry run django-admin check` — exit 0, one pre-existing warning (`controlled_vocabularies.W002`,
the core's own check reporting its route absent from the deliberately empty `urls_core.py` —
matches django-literature's own `tests/urls_core.py`, `urlpatterns = []`). `poetry run ruff check
tests/settings.py tests/settings_core.py tests/urls_core.py` — ruff's autofix removed two
now-redundant `# noqa: F403`/`F405` comments (F403/F405 are already in this repo's global
`ignore` list), all checks pass after.

Next: T004 — the three isolation proofs.

## 2026-08-19T00:15:00Z · Implementer US0 · T004

Did: `tests/test_ui/test_architecture.py` (AST-parses every `controlled_vocabularies/**/*.py`
outside `ui/`, asserts none imports `mvp`, `django_cotton`, `crispy_forms`, `easy_icons`,
`flex_menu` or `controlled_vocabularies.ui`), `tests/test_ui/test_boot.py` (fresh subprocess,
`DJANGO_SETTINGS_MODULE=tests.settings_core`, `django.setup()` + `call_command("check")` +
imports every core module, asserts `"controlled_vocabularies.ui" not in sys.modules`),
`tests/test_ui/test_packaging.py` (`tomllib`-parses `pyproject.toml`, asserts `django-mvp` is
`optional`, is exactly `[tool.poetry.extras] ui`, and is absent from every other extra and every
poetry dependency group).

All three passed immediately given T001–T003 (nothing to make green through new production code —
these are standing proofs, not TDD in the red/code/green sense). Proved each catches a real
violation before trusting it (craft-tdd's reproduce-first discipline, applied to the gate itself):
temporarily added `import mvp` to `controlled_vocabularies/apps.py` — `test_architecture.py`
failed naming `apps.py`; changed the import to `import controlled_vocabularies.ui` —
`test_boot.py` failed with `"controlled_vocabularies.ui was imported by the core boot"`; flipped
`django-mvp`'s `optional` to `false` in `pyproject.toml` — `test_packaging.py` failed. Reverted
all three mutations (`git diff` on `controlled_vocabularies/apps.py` empty after revert;
`pyproject.toml`'s `django-mvp` line unchanged).

Verified: `poetry run pytest tests/test_ui/test_architecture.py tests/test_ui/test_boot.py
tests/test_ui/test_packaging.py -q` — 35 passed. `poetry run ruff check
tests/test_ui/test_architecture.py tests/test_ui/test_boot.py tests/test_ui/test_packaging.py` —
all checks passed.

Next: T005 — the missing-extra system check, and the commit that lands T001 alongside it.

## 2026-08-19T00:20:00Z · Implementer US0 · T001 (commit) + T005

Did: `controlled_vocabularies/ui/checks.py` (`check_mvp_installed`, a real `try: import mvp`,
returns one `checks.Error` with a stable id `controlled_vocabularies.ui.E001` naming both the
`ui` extra and `controlled_vocabularies.ui` when the import fails) registered from
`ControlledVocabulariesUIConfig.ready()`. Test first: `tests/test_ui/test_checks.py`, run and
observed failing (`ModuleNotFoundError: No module named 'controlled_vocabularies.ui.checks'`)
before the module existed.

This is also the commit where T001's `pyproject.toml`/`poetry.lock`/`.github/workflows/tests.yml`
changes finally land (decisions.md D7): `checks.py`'s import is the first thing in this phase for
`deptry` to find, so `git commit` only succeeds once both are staged together.

Verified: `poetry run pytest tests/test_ui/test_checks.py -q` — 3 passed, using
`monkeypatch.setitem(sys.modules, "mvp", None)` to force the real `import mvp` statement to
raise, per the CPython import system's own `sys.modules[name] = None` convention (rather than
`importlib.util.find_spec`, which `deptry`'s static scan does not count as usage — decisions.md
D7). `poetry run ruff check controlled_vocabularies/ui/ tests/test_ui/test_checks.py` — all
checks passed. `poetry run deptry .` — "Success! No dependency issues found." (T001's own
acceptance, now satisfied). `poetry run pytest -q` — 1395 passed (full suite, T001 baseline
1355 + 40 across T002–T005's new test files).
`DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin check` — "System check identified
no issues (0 silenced)" (`mvp` genuinely importable, the new check reports nothing).
`DJANGO_SETTINGS_MODULE=tests.settings_core poetry run django-admin check` — exit 0, the same
single pre-existing `controlled_vocabularies.W002` warning as T003 (the ui app, and its check,
are not installed under `settings_core` at all).

Phase 1 (T001–T005) complete. Concern for the story report: `feature-state.json`'s `stories`
array has no `US0`/foundational entry at all — only `US1` (T006–T010) and `US2` (T011–T014) —
so there was nothing of my own to flip `status`/`attempts`/`evidence` on. Left the ledger
untouched rather than adding a structural entry outside my mandate.

## 2026-08-19T21:43:27Z · Implementer US1 · T006

Did: `controlled_vocabularies/ui/urls.py` (new — `app_name = "controlled_vocabularies_ui"`,
one route at the empty path named `vocabulary-list`), `controlled_vocabularies/ui/views.py`
(new — `VocabularyListView(MVPListView)` over `ConceptScheme`, `list_item_template` and
`template_name` set explicitly), `controlled_vocabularies/ui/templates/controlled_vocabularies/
ui/conceptscheme_list.html` (new — extends django-mvp's `list_view.html`, overrides
`page.actions` to render nothing) and `.../conceptscheme_list_item.html` (new — a Cotton
`c-card` rendering the vocabulary's name and description only; count and origin arrive in
T007). Added the `include("controlled_vocabularies.ui.urls")` line to `tests/urls.py` under
`browse/` (decisions.md D8 — this is the task D8 said would add it, now that
`controlled_vocabularies/ui/urls.py` exists to point at).

Test first: `tests/test_ui/test_urls.py::TestVocabularyListUrl` and
`tests/test_ui/test_views.py::TestVocabularyList` (3 cases: every vocabulary appears exactly
once, one added after the first request appears on the next, the page renders no `q`/`o`
search-or-sort control and no "Add new" create control). Run and observed failing —
`NoReverseMatch: 'controlled_vocabularies_ui' is not a registered namespace` — before the
namespace existed.

Verified: `poetry run pytest tests/test_ui/test_urls.py tests/test_ui/test_views.py -q` — 4
passed. `poetry run ruff check controlled_vocabularies/ui/urls.py
controlled_vocabularies/ui/views.py tests/test_ui/test_urls.py tests/test_ui/test_views.py
tests/urls.py` — all checks passed. Committed via `git commit` — the full local pre-commit
gate (trailing-whitespace, end-of-file-fixer, ruff lint, ruff format, mypy, deptry) passed
clean on the first attempt.

No create control needed suppressing explicitly: `CRUDDirectoryMixin.show_create_action`
defaults to `False`, so `MVPListViewMixin`'s own `directory = ["create"]` never resolves a
`create_url` and neither the actions bar (already emptied) nor the empty-state partial's
"Add new" button can appear — confirmed by reading `mvp/views/detail.py`'s `show_action()`
before writing the assertion, not by assuming it.

Next: T007 — `get_queryset()` annotates `concept_count`, the row partial adds count and
origin (imported vs. held here, publisher identifier as text never a link).

## 2026-08-19T21:46:32Z · Implementer US1 · T007

Did: `controlled_vocabularies/ui/views.py` — `get_queryset()` now annotates
`concept_count=Count("concepts")` (collections excluded — decisions.md D3). The row
partial (`conceptscheme_list_item.html`) adds a `badges` slot showing "Imported" when
`static_uri` is set and "Held here" when it is not (decisions.md D6), the identifier itself
as plain `<c-text>` (never a link — D6, and never `mark_safe`/`format_html` — D4's rule
applies here too even though D4 is about the empty states), and the concept count via
`{% blocktrans count %}`, always rendered including at zero.

Test first: `tests/test_ui/test_views.py::TestVocabularyListEntry` (6 cases). The count
annotation is proven through the full view (`client.get`, reading
`response.context["object_list"][...].concept_count`); the row's own rendering (identifier
text, imported/held-here wording, count wording, no stray element for a missing
description) is proven by calling `render_to_string()` on the row template directly with a
built (unsaved, for the pure-rendering cases) or saved (for the DB-backed annotation case)
`ConceptScheme` — the same template the page renders the row from, isolated from the
page's own `<c-text>`-based chrome (pagination summary, empty state) so an assertion about
one row's markup cannot be satisfied by unrelated markup elsewhere on the page. Run and
observed failing first — `AttributeError: 'ConceptScheme' object has no attribute
'concept_count'` and four content-assertion failures against the T006 row (no badge, no
identifier, no count) — before the annotation and the new partial markup existed.

Verified: `poetry run pytest tests/test_ui/test_views.py -k Entry -q` — 6 passed.
`poetry run pytest tests/test_ui -q` — 50 passed (full `test_ui` scope). `poetry run ruff
check controlled_vocabularies/ui/views.py tests/test_ui/test_views.py` — all checks passed.
Committed via `git commit` — the full local pre-commit gate passed clean on the first
attempt.

Next: T008 — `ordering = [Lower("name"), "pk"]` as a class attribute (not `.order_by()` in
`get_queryset()` — plan.md item 1's rationale, load-bearing).

## 2026-08-19T21:51:53Z · Implementer US1 · T008

Did: `controlled_vocabularies/ui/views.py` — `ordering = [Lower("name"), "pk"]` as a class
attribute (plan.md item 1, decisions.md D2 — never an `.order_by()` call inside
`get_queryset()`, which Django would apply after both django-mvp mixins rather than before).

Test first, and this task earned its RED the hard way: the first draft of
`test_names_differing_only_in_case_sort_as_a_reader_would_expect` and
`test_two_vocabularies_sharing_a_name_still_produce_a_deterministic_order` **passed before
`ordering` existed** — a false green (craft-tdd's "a test that passes on first run is
testing nothing you just wrote"). Diagnosed rather than accepted: T007's `Count()`
annotation forces a `GROUP BY` on every selected column, and this repo's SQLite test
database was satisfying that `GROUP BY` via the unique index on `slug` — which, for
ordinary slugified names, sorts the same way as case-insensitive name order, so the
original test data (`"banana"`/`"Apple"`/`"cherry"`, then `"Zebra"`/`"antelope"`) couldn't
tell a real ordering from that coincidence. Rewrote both cases so the vocabulary whose
*name* should sort last carries a `set_slug()`-assigned slug that would sort it *first* —
only a genuine `Lower("name")`/`pk` ordering can put it last regardless. Both then failed
for the right reason (`assert ['Zebra', 'antelope'] == ['antelope', 'Zebra']` and
`assert [2, 1] == [1, 2]`) before this commit's `ordering` attribute existed, and pass now
that it does. Recorded as a `decisions.md`-worthy note for whoever next writes an ordering
test against an annotated queryset in this repo — see `concerns` in the eventual completion
report.

Verified: `poetry run pytest tests/test_ui/test_views.py -k Ordering -q` — 4 passed.
`poetry run pytest tests/test_ui -q` — 54 passed (full `test_ui` scope). `poetry run ruff
check controlled_vocabularies/ui/views.py tests/test_ui/test_views.py` — all checks
passed. Committed via `git commit` — full local pre-commit gate passed clean on the first
attempt.

Next: T009 — empty-state overrides and the no-link proof (`test_templates.py`, new).

## 2026-08-19T21:55:43Z · Implementer US1 · T009

Did: `controlled_vocabularies/ui/views.py` — `get_empty_state_heading()` returns "This site
holds no vocabularies" (translatable); `get_empty_state_message()` returns `None` (nothing
to point at, no create action exists). Only the empty-site state exists in this story —
search (User Story 2) is what will later branch these on `?q=` for the second, distinct
wording D4 requires; not built here, per the brief's own prohibition on T011-T014.

Also refactored the row partial's origin badge (`conceptscheme_list_item.html`, T007): moved
"Imported"/"Held here" out of `<c-badge text="{% trans ... %}">`'s attribute value and into
slot content (`<c-badge>{% trans ... %}</c-badge>`) — both render identically, but a string
in a Cotton attribute value and a string in element content are indistinguishable from a
structural token (a slot name, a size key) by any regex-based scan that does not fully parse
HTML/Django-template syntax, so leaving it in the attribute would have made this task's own
"scan every shipped template for reader-visible text outside a translation tag" requirement
vacuous for this app's real content. `tests/test_ui/test_views.py::TestVocabularyListEntry`
(T007's tests, checking for the literal strings) needed no changes — same wording, same
`in html` assertions.

Test first: `tests/test_ui/test_views.py::TestVocabularyListEmptyState` (2 cases — the page
returns 200 with "no vocabularies" wording; `get_empty_state_heading()` itself says so, using
django-mvp's own default heading, "There's nothing here yet", as the pre-implementation RED).
New `tests/test_ui/test_templates.py` (T009's own file): `TestRowPartialNeverLinksToTheVocabulary`
(source contains no `{% url %}` tag, no `local_url` reference — both passed immediately, since
the row partial never had either; recorded as evidence rather than as a RED/GREEN pair),
`TestRenderedPageNeverLinksToAVocabulary` (no rendered anchor's `href` equals a scheme's
`local_url` — passed immediately, same reason), `TestEveryShippedTemplateWrapsReaderVisibleTextInATranslationTag`
(parametrized over every `.html` under `controlled_vocabularies/ui/templates/`; strips Django's
own comment/`blocktrans`/tag/variable syntax and asserts no reader-visible text-node fragment
survives — passed immediately against the already-correctly-wrapped templates, confirmed
meaningful by construction: the scanner is scoped to text nodes specifically because that is
where this app's strings now live, after the attribute-to-slot-content refactor above).

Verified: `poetry run pytest tests/test_ui/test_templates.py tests/test_ui/test_views.py -k
"EmptyState or Templates or Link" -q` — 7 passed. `poetry run pytest tests/test_ui -q` — 61
passed (full `test_ui` scope). `poetry run ruff check controlled_vocabularies/ui/views.py
controlled_vocabularies/ui/templates tests/test_ui/test_views.py tests/test_ui/test_templates.py`
— all checks passed. Committed via `git commit` — full local pre-commit gate passed clean on
the first attempt.

US-1 (T006-T009) implementation complete. Next: T010 — document the page in README.md and
CHANGELOG.md, then the story's own exit criteria (full `poetry run pytest -q`, full
`poetry run pre-commit run --all-files`, `makemigrations --check --dry-run`) before the
completion report.

## 2026-08-19T21:58:29Z · Implementer US1 · T010

Did: `README.md` — new "Finding a vocabulary" section (placed after "Choosing a concept in
the admin", before "Importing a published vocabulary"): what the page shows, the `pip
install django-controlled-vocabularies[ui]` install step, the full `INSTALLED_APPS` block
plus `CRISPY_TEMPLATE_PACK`/`CRISPY_ALLOWED_TEMPLATE_PACKS`/the `mvp_config` context
processor/`EASY_ICONS`/`FLEX_MENUS` settings — quoted verbatim from `tests/settings.py`,
mounting with `include("controlled_vocabularies.ui.urls")`, and reversing
`controlled_vocabularies_ui:vocabulary-list` by name. States plainly that an entry does not
yet link to its vocabulary, and why (`ConceptScheme.local_url` exists but nothing serves it
yet — #141 is what will). `CHANGELOG.md` — new `### Added` entry under `[Unreleased]`.

No new test file: this task's own acceptance is "the README's own instructions followed
against the test project produce the page," and the instructions are a byte-for-byte quote
of `tests/settings.py`'s ui-specific block — the same configuration
`tests/test_ui/test_views.py`, `test_templates.py` and `test_urls.py` already exercise the
real page against, 20 passing test cases across T006-T009. Confirmed this by first trying
to write a *slimmed-down* settings module for the README (omitting `EASY_ICONS` and
`FLEX_MENUS`, guessing they were test-suite-only concerns) and running it manually against
the view: it failed deep inside django-mvp's base chrome (`ImproperlyConfigured` from
`<c-icon>` with no `EASY_ICONS["default"]` renderer configured, cascading through a
production 500 page that itself needs the same chrome to render, since the scratch settings
module also left `DEBUG` at its `tests.settings_core` default of unset). That failed
experiment is why the README quotes the *whole* block rather than a hand-trimmed one — it is
evidence, not assumption, that every setting listed is load-bearing for this page. The
scratch settings module was not committed.

Verified: `poetry run ruff check` — no Python changed by this task. Committed via `git
commit` — full local pre-commit gate (including the two markdown-touching hooks,
trailing-whitespace and end-of-file-fixer) passed clean on the first attempt.

US-1 (T006-T010) implementation complete. Running the story's exit criteria next: full
`poetry run pytest -q`, full `poetry run pre-commit run --all-files`,
`makemigrations --check --dry-run`, then the completion report.

## 2026-08-20 — US-1 accepted, US-2 dispatched

US-1's branch fast-forwarded onto the feature branch and verified independently rather than on the
implementer's word: full suite 1414 passing, lint, type check, build and structure conformance
green. The documentation step was red — `VocabularyListView` is a new public name no page
documented — and is now green: the README's browsing section carries the class, where it lives and
how a project subclasses it. Tamper-check flagged the test project's settings and URL configuration;
both are additive and were the plan's own instruction, triaged in decisions.md D9. Completion
comment posted on #143, ledger flipped.

**The bot cannot push this branch while it carries a workflow-file change.** T001 edited
`.github/workflows/tests.yml` to install the ui extra, and a GitHub App without `workflows`
permission is refused — deliberately, since an app that can rewrite a workflow can disable the
checks gating its own release. This push therefore went under the maintainer's own credentials,
which makes him the last pusher and would block his own approval. US-2's push resets that; the
last-push actor must be confirmed to be the bot before the merge gate.

US-2 (T011–T014, search) dispatched into `/home/sam/projects/samueljennings/dcv-013-us2` on the
Sonnet tier.

## 2026-08-20T07:26:23Z · Implementer US2 · T011

Did: `controlled_vocabularies/ui/views.py` — `search_fields = ["name", "description"]` on
`VocabularyListView`. `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_list.html`
— replaced the empty `{% block page.actions %}` with a `GET` form of our own
(`id="filterForm"`) holding a `<c-form.field>` search input (same config django-mvp's own
search action uses: `name="q"`, value readback, aria-label, search-icon prelabel) and our
own `{% trans "Search" %}` submit button. Comment in the template names both upstream faults
(research R4: the shipped search action's `form="filterForm"` targets an id only the filter
action defines; its submit button's label is a hard-coded English literal with no variable
exposed) and why this block works around rather than patches them — decisions.md D10.

`tests/test_ui/test_views.py` — new `TestVocabularySearch` (9 tests): a word from the name
narrows; a word only in the description narrows; matching ignores case; `%`, `_` and `'`
are looked for literally (icontains escapes LIKE metacharacters) and match nothing; a
non-Latin term (`地質`) matches; the rendered page carries `name="q"` and no `name="o"`/no
`filterModal`; and — the assertion that actually proves the R4 defect is closed, since a
query-string-only test would pass even against the broken markup — a `BeautifulSoup` parse
confirms a real `<form id="filterForm" method="get">` nests both the `q` input and the
submit button.

Verified: `poetry run pytest tests/test_ui/test_views.py -k Search` — 9 passed (24
deselected). All 9 observed failing first, for the right reason (no `search_fields`, no
actions block) — confirmed by running the same command before the production edit.

Watch: running the same file *without* `-k Search` now shows 1 pre-existing failure —
`TestVocabularyList::test_page_renders_no_sort_filter_or_create_control`, authored in T006
(US-1), asserts `'name="q"' not in content`. That assertion predates this story's search box
and is now definitionally false; the other two assertions in the same test (no `o`, no "Add
new") are untouched and still pass. Per the brief's own prohibition on editing a test I did
not author, left as-is rather than fixed — decisions.md D11 has the full reasoning. This will
show as the one failure in the story-end full-suite run.

Next: T012 — prove search survives linking and paging (test-only).

## 2026-08-20T07:41:11Z · Implementer US2 · T012

Did: `tests/test_ui/test_views.py` — new `TestVocabularySearchAcrossRequestsAndPages` (2
tests), test-only per the task (no production change expected: django-mvp's pagination
links already build with Django's `{% querystring %}` tag on the installed 0.19.1, which
keeps every current parameter but `page`). One test requests the same `?q=` address twice
and asserts the same pks in the same order; the other seeds 30 matching vocabularies plus 5
non-matching, requests page one, reads the "page two" `href` straight out of the rendered
markup (`BeautifulSoup`, `"page=2" in href and "q=" in href` — never a hand-built
`?page=2`), follows it, and asserts the second page's pks are disjoint from the first
page's, a subset of the matching set, and together with page one account for exactly the
30 matches and nothing from the other 5.

Verified: `poetry run pytest tests/test_ui/test_views.py -k Search -q` — 11 passed, 15
deselected (9 from T011 plus these 2). Both new tests passed on first run, confirming
rather than fixing — matches the task's own framing.

Next: T013 — a search matching nothing says so, in its own words.

## 2026-08-20T07:52:03Z · Implementer US2 · T013

Did: `controlled_vocabularies/ui/views.py` — `get_empty_state_heading()` and
`get_empty_state_message()` both branch on `request.GET.get("q", "").strip()`. A search
term gives `_('Nothing matches "%(term)s"') % {"term": search_term}` and
`_("Try a different search term.")`; no term keeps T009's heading (`"This site holds no
vocabularies"`) and `None` message unchanged. Neither branch uses `mark_safe` or
`format_html` — both return plain (possibly `%`-interpolated) translatable text, escaped
by the template layer same as anything else in `{{ }}`.
`controlled_vocabularies/ui/templates/.../conceptscheme_list.html` — inside
`{% block page.actions %}`, `{% if search_query %}` renders a `{% trans %}`d link back to
the unsearched list (`{% url 'controlled_vocabularies_ui:vocabulary-list' %}`) beside the
search form — the way back FR-009 requires, kept out of the message per the task (a link
inside a heading/message the empty-state component renders autoescaped with no slot would
show as literal text, and marking either safe would emit the search term unescaped).

`tests/test_ui/test_views.py` — new `TestVocabularySearchEmptyState` (5 tests): a search
matching nothing returns 200, echoes the term, and does not show the exact site-empty
string; that state also carries a link back to the unsearched list (`list_url` present in
the page's `href`s); an empty site with no search keeps T009's wording and shows no such
link; the no-match and site-empty headings are different strings; and a term containing
`<script>alert(1)</script>` is escaped — asserted by parsing the empty-state `<h3>` with
`BeautifulSoup` and confirming it has no `<script>` *element* nested inside (an HTML
parser would produce one if the term had gone through `mark_safe`), only the term as
literal text.

Two real bugs caught before commit, both by observing RED for the right reason first:

1. My first cut of the "term is escaped" test asserted a blanket `"<script>" not in
   content` — false on *any* page here, since the base chrome's own theme-toggle script
   is a real `<script>` tag. Rewrote to scope the check to the empty-state heading
   specifically (`heading.find("script") is None`).
2. The actions-block link's own Django comment (`{# ... #}`) spanned two lines. Django's
   `{# #}` tag does not support multi-line content (confirmed with a two-line `Template()`
   probe outside the test suite) — unlike `{% comment %}`, it silently falls through as
   literal text instead of raising, so the comment itself leaked into the rendered page
   and broke an unrelated assertion. Switched to `{% comment %}...{% endcomment %}`,
   matching the block already at the top of this file from T011.
3. My first heading wording, "No vocabularies match "…"", shares the substring "no
   vocabularies" with T009's site-empty heading ("This site holds no vocabularies"), so a
   test asserting their absence by loose substring could not tell them apart. Changed the
   wording to "Nothing matches "…"" (no shared substring) and tightened the test to check
   for T009's *exact* heading string rather than a fragment of it.

Verified: `poetry run pytest tests/test_ui/test_views.py -k Search -q` — 16 passed, 15
deselected (9 T011 + 2 T012 + 5 T013). `poetry run pytest tests/test_ui/test_templates.py
-q` — 5 passed (the mechanical every-string-translated scan re-parametrizes over the
edited template automatically; no bare text introduced). `poetry run ruff check
controlled_vocabularies/ui/views.py tests/test_ui/test_views.py` — clean.

No decisions.md entry: the design (branch both hooks on the query, one comment naming
where the link lives) matches plan.md's already-written design closely enough that there
was no ambiguous call to record beyond the three bugs above, which are progress-note
material, not decisions.

Next: T014 — document search in README.md and CHANGELOG.md, then the story's exit
criteria (full `poetry run pytest -q`, the `forge verify` ritual) before the completion
report.

## 2026-08-20T07:56:12Z · Implementer US2 · T014

Did: `README.md` — new paragraph in "Finding a vocabulary", right after the page's own
intro paragraph and before the install step: what the search covers (name and
description, not concepts — "finding a concept without already knowing which vocabulary
holds it is not something this page does"), that the term travels in the address (`?q=`)
so a narrowed list can be linked to or bookmarked, that a second word **widens** rather
than narrows (OR across every word and both fields — flagged as the opposite of what a
reader assumes, per the task), that there is no other filter or sort, and that a search
matching nothing says so, repeats the term, and links back to the unsearched list.
`CHANGELOG.md` — a second `### Added` bullet under `[Unreleased]`, alongside T010's,
summarizing the same ground for a reader who does not open the README.

No new test file — this task's own acceptance is that the documented behaviour matches
the tests already proving it (T011-T013), same shape as T010.

Verified: read every sentence added against `controlled_vocabularies/ui/views.py` and
`tests/test_ui/test_views.py::TestVocabularySearch*` as they stand after T013 — each
claim (fields searched, `?q=` persistence, OR-widening, no-match wording and link) has a
passing test behind it. `poetry run ruff check` — no Python changed by this task.
Committed via `git commit` — pre-commit gate (trailing-whitespace, end-of-file-fixer)
passed clean on the first attempt.

US-2 (T011-T014) implementation complete. Running the story's exit criteria next: full
`poetry run pytest -q`, the `forge verify` ritual, then the completion report. Full-suite
run is expected to show exactly one failure —
`TestVocabularyList::test_page_renders_no_sort_filter_or_create_control` (T006, decisions.md
D11) — left untouched per the brief's prohibition on editing a test from another story.

## 2026-08-20 — US-2 accepted

Search landed (T011–T014) and was verified here rather than on the implementer's word: 1431 tests,
lint, type check, structure conformance, documentation and build all green; both craft-skill
receipts matched the registry; every commit on the branch is bot-authored.

One thing the implementer correctly refused to resolve. `TestVocabularyList::test_page_renders_no_sort_filter_or_create_control`,
authored in T006, asserted the page carried no `name="q"` — a true pin on the empty actions block
US-1 left behind, and false by design once T011 fills that block with the search form the spec
requires. The brief forbids an implementer editing another story's test, so it came back flagged
(decisions.md D11) rather than quietly fixed. Resolved here: the test was folded away, since the
US-2 test `test_the_rendered_page_carries_a_search_input_and_nothing_else` already covered sort and
filter absence, and its one unique claim — no create control — moved across. Deleting it outright
rather than editing the stale line avoids two near-duplicate tests of the same block drifting apart.

Tamper-check flags the same two files as US-1 — the test project's settings and URL configuration,
additive and the plan's own instruction, triaged in decisions.md D9. Nothing new.

Branch pushed as the bot (`0b9f20a..75d3cf5`); no workflow file is in this push, so the App's
missing `workflows` permission did not bite. Completion comment posted on #144, ledger flipped.

Next: the review panel over the whole feature branch.

## Review

Two lenses over the whole feature diff, one round each.

**Security — approve, risk low.** Nothing critical or high. Both real defects belong to django-mvp
rather than here, and both are now filed upstream: the search box's input and submit button target
a form id only the filter action defines (#280), and the search mixin builds one `Q` per word per
field straight from `?q=` with no cap, which on SQLite raises an unhandled `OperationalError` on a
long enough term (#281). Reproduced rather than taken on report: 499 words 500s the page, 300
returns 200. PostgreSQL has no equivalent ceiling. Applied here at convergence: the django-mvp pin
narrowed to `^0.19.1`, a word bound in our own view, and a README sentence saying the page enforces
no permission check.

**Correctness and spec — request_changes, risk medium.** Four findings, all reproduced here before
being acted on, all fixed.

- *Search was not case-insensitive for any letter outside ASCII* (high). On SQLite, `Ökologie` is
  found by `ÖKOLOGIE` and not by `ökologie`, and the reader gets the no-match empty state, which
  looks exactly like a correct answer. The existing non-Latin test could not catch it, because
  Japanese has no case. There is no repair above the database, so the limit is now stated in the
  README and in FR-006, pinned by a test in both directions, and recorded as ADR 0014 because every
  later search surface inherits it (decisions.md D15).
- *No test asserted an entry shows its vocabulary's name or description* (medium). The factory
  leaves the description blank, so that branch of the row partial was never rendered under test and
  both could have been deleted with the suite green. One test now covers both, and it fails when
  either is removed.
- *A description running to several paragraphs rendered in full* (medium), against the spec's own
  edge case. Shortened in the template rather than clamped in CSS: this package ships no stylesheet,
  and a utility class django-mvp's prebuilt one does not already contain is absent from the file, so
  a clamp would render and silently do nothing (decisions.md D14).
- *A whitespace-only `?q=` read as a search* (low) — the full list, but with the box prefilled and
  the way-back link offered. The page now branches on the same stripped term the queryset was
  filtered on (decisions.md D13).

Each of the three new gates was proved against the defect it exists to catch: the fix reverted, the
test seen to fail, the fix restored.

Full verify after the fixes: 1438 tests pass, lint, types, dependency check, migration check and
build all green.

The three remediations named in the security summary were outstanding when the correctness review
came back, and are applied in the same commit: the django-mvp pin narrowed to `^0.19.1` (the
browsing page's template works around two faults in 0.19's search action, so an upstream fix is as
breaking here as an upstream change, and a 0.x minor is free to make either), a README paragraph
saying the page carries no permission rule of its own, and a 100-word bound on the search term
(decisions.md D16). The bound is proved both ways: a 600-word term 500s without it and returns 200
with it, and the truncation it costs is pinned by its own test rather than left implicit.

## 2026-08-20 — Amendment: US-3, a runnable demonstration

The maintainer raised that nothing on this branch lets him confirm the page renders — a test
asserting markup and a person looking at the page are different evidence. Agreed, and taken into
this feature rather than a later one: a merge gate whose deliverable is only checkable after a
*later* pull request lands inverts the point of the gate, and #141 and #142 inherit the demo the
moment it exists.

Spec amended with User Story 3, FR-014 through FR-018 and SC-007; `tasks.md` gains Phase 4
(T015–T018); `plan.md` records the amendment, one complexity entry and two new risks. Story issue
#146 created and linked under the epic, epic body and the pull request's `Closes` block re-synced,
ledger amended and schema-valid. Re-gated in session — the maintainer approved the amended scope
and, separately and explicitly, the demo's CI workflow file.

The workflow file remains unpushable by the bot. That constraint is now written into T017 as
something to report rather than route around.

## 2026-08-20T00:00Z · Implementer US-3 · T015

Did: added `manage.py`, `demo/__init__.py`, `demo/settings.py` and `demo/urls.py` — the demo
project boots against the exact `INSTALLED_APPS`/settings README.md's "Finding a vocabulary"
section documents, plus the Django/django-mvp boilerplate a runnable project needs beyond it. A
root route named `home` redirects to the vocabulary list, satisfying django-mvp's footer menu
reversal and FR-015. Test-first: `tests/test_demo/test_demo.py` (`TestDemoProject`) boots the
demo settings module in a subprocess, runs `manage.py check`, and asserts `DEBUG`/local-database
and the root's URL resolution — declared a non-mirror path in `pyproject.toml` (its subject is
the whole project, not one module).

Verified: `poetry run pytest tests/test_demo/ -q` — 1 passed. `ruff check manage.py demo/
tests/test_demo/ pyproject.toml` — clean.

Next: T016 — seeding.

Watch: `manage.py check` reports non-fatal warnings (`controlled_vocabularies.W002-W004`) for
`django_tomselect` and the core app's own URL mount, because the demo's `INSTALLED_APPS`
deliberately matches only the README's "Finding a vocabulary" section, which does not include
them — that feature (typed concept search) is not part of this page. Not a blocker; noted in
`concerns` for the completion report.

## 2026-08-20T00:20Z · Implementer US-3 · T016

Did: added `demo/seed/dcmi_types.ttl` (the real DCMI Type Vocabulary, five concepts, declaring
its own `skos:ConceptScheme` at `http://purl.org/dc/dcmitype/` — lands as imported) and
`demo/seed/research_methods.ttl` (four concepts, no `skos:ConceptScheme` declared — loaded
against a vocabulary `seed_demo` creates directly, lands as authored here), and
`demo/management/commands/seed_demo.py`, which deletes every vocabulary and reloads both
through `controlled_vocabularies.exchange.import_skos`. Test-first:
`tests/test_demo/test_seed.py` (`TestSeedDemo`), four tests covering both vocabularies existing
with concepts after one run, identical counts after a second run, a hand-added vocabulary gone
after a rerun, and one vocabulary reading as imported and the other as authored here.

Verified: `poetry run pytest tests/test_demo/test_seed.py -q` — 4 passed. `poetry run pytest
tests/test_demo/ -q` — 5 passed. `ruff check demo/ tests/test_demo/` — clean.

Next: T017 — the unattended walk.

Watch: none new.

## 2026-08-20T00:45Z · Implementer US-3 · T017

Did: added `demo/smoke.py` (assertion logic in `check_list`/`check_search`, kept separate from
the HTTP transport in `get`/`walk` so the assertions are exercised in-process by pytest, per the
task brief) and `.github/workflows/demo.yml`, modelled on
`/home/sam/projects/fairdm/django-literature`'s `demo.yml` (checkout, Poetry env with `--extras
ui`, migrate + seed, start `runserver --noreload`, poll `/browse/` until ready, run
`demo/smoke.py`, stop the server). No paths filter on `pull_request`, matching this repo's other
required checks. Test-first: `tests/test_demo/test_smoke.py` (`TestCheckList`,
`TestCheckSearch`), six tests — the passing case and three failure modes for the list, the
passing case and the not-narrowed failure for search — all against a page Django's test client
actually rendered from a real `seed_demo` run, never a hand-built body.

While running the three documented commands by hand for this task's own "Verify" line
(`python -m demo.smoke` end to end), `seed_demo` failed under `demo/settings.py` even though
the identical import passes in every automated test — `DEFAULT_LANGUAGE_UNCONFIGURED`, because
Django's default `LANGUAGE_CODE` is not a member of Django's own default `LANGUAGES` list.
`tests.settings` sets `LANGUAGE_CODE` explicitly and never hits this. Fixed in this commit by
setting `LANGUAGE_CODE = "en"` in `demo/settings.py` (decisions.md D19) — one line of ordinary
project boilerplate, no package behaviour touched.

Verified by hand, in order, against a throwaway `DEMO_DB_PATH`: `python manage.py migrate`,
`python manage.py seed_demo` (loaded 2 vocabularies), `python manage.py runserver`. Confirmed
by curl against the running server: `/` redirects (302) to `/browse/`; the list page's body
contains both `DCMI Type Vocabulary` and `Data Collection Methods`, both concept counts (`5
concepts`, `4 concepts`), and both badges (`Imported`, `Held here`); `/browse/?q=DCMI` narrows
to `DCMI Type Vocabulary` only. `python -m demo.smoke http://127.0.0.1:8000` printed `OK: walked
the demo vocabulary list and a search, at http://127.0.0.1:8000`. Browser control was not
reachable from this sandbox (`Unable to connect`), so the visual look was curl against the live
response body, not a rendered screenshot — noted in concerns.

Verified (automated): `poetry run pytest tests/test_demo/ -q` — 11 passed. `ruff check demo/
tests/test_demo/` — clean.

Next: T018 — document the demo.

Watch: `.github/workflows/demo.yml` cannot be pushed by the bot (no `workflows` permission) —
flagged in the completion report per the task brief; the maintainer pushes this branch.

## 2026-08-20T01:00Z · Implementer US-3 · T018

Did: added a "Try it: the demo project" subsection to README.md, nested under "Finding a
vocabulary" right after the page's own documentation (matching django-literature's placement
under its own browsing section) — the three commands in order, the address they lead to
(`http://127.0.0.1:8000/`, redirecting to `/browse/`), what the seeded content holds (the DCMI
Type Vocabulary, imported, and Data Collection Methods, authored here), that seeding is
destructive and idempotent, and that the demo is not a production configuration. Added a
CHANGELOG.md entry under `[Unreleased] > Added` naming the demo, its three commands and the
unattended check.

Verified: followed the section from the throwaway state used for T017's by-hand walk (already
run this session — see the T017 entry for the exact output) rather than re-running it, since
nothing about the commands or the address changed, only their documentation. `poetry run pytest
tests/test_demo/ -q` — 11 passed (unaffected, as expected — docs only).

Next: full verify, then the completion report.

Watch: none new.

## 2026-08-20T01:30Z · Implementer US-3 · full verify and by-hand walk

Did: ran the three documented commands by hand end to end against a fresh throwaway
`DEMO_DB_PATH`, on a clean server: `migrate`, `seed_demo` ("seed_demo loaded 2 vocabularies"),
`runserver`. Confirmed by curl against the live server: `/` redirects (302) to `/browse/`; the
list page's body carries both vocabulary names, both descriptions, both concept counts (`5
concepts`, `4 concepts`), and both badges (`Imported`, `Held here`); `/browse/?q=DCMI` narrows
to `DCMI Type Vocabulary` only. `python -m demo.smoke http://127.0.0.1:8001` printed `OK: walked
the demo vocabulary list and a search`. Server stopped and throwaway files removed.

Ran the story's full verify command once:
`/home/sam/.openclaw/workspaces/forge/engineering-org/kit/forge verify --repo . --base
013-find-a-vocabulary`. First run failed conformance: `tests/test_demo/test_demo.py` and
`tests/test_demo/test_seed.py` reported as mirroring no source module, despite T015's
`"tests/test_demo/"` directory-prefix declaration in `pyproject.toml`. Root cause: the tool's
non-mirror-paths parser is regex-based and an apostrophe in my own in-array comment corrupted
its parsing of every following entry (decisions.md D20). Fixed by listing the three files
explicitly and moving the comment above the array, matching the file's own existing convention;
confirmed by calling `forgekit.conformance.declared_non_mirror_paths` directly before and after.

Verified: `forge verify` — conformance passed, docs passed, `poetry:lint` passed, `poetry:
typecheck` passed, `poetry:test` passed (all 1451 tests — the suite this story added 15 to),
`poetry:build` passed.
