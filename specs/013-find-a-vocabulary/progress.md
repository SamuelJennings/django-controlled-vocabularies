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
