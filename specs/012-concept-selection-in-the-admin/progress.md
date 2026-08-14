# Progress — 012 Concept selection inside the Django admin

Append-only. Each entry is written at the moment the event happens, not reconstructed afterwards.

| When (UTC) | Stage | Event |
|---|---|---|
| 2026-08-13 | S0 INTAKE | Issue #89 adopted. Grilled to one decision: the control is selection-only, no create or edit affordance on a consuming record's page. Statement confirmed by the maintainer. `accepted` label added. |
| 2026-08-13 | S1 SPECIFY | Branch `012-concept-selection-in-the-admin` created. `spec.md` written: 6 stories (2×P1, 3×P2, 1×P3), FR-001..FR-013, SC-001..SC-008. Coverage scan run: five ambiguities surfaced and self-resolved into `## Clarifications`; rationale in `decisions.md` D1–D8. Spec lint green. |
| 2026-08-13 | S2 SETUP | Branch pushed as forge-aeo. #89 promoted to epic `FS-012`, body grown with the original request preserved. Story sub-issues #125–#130 created and linked, no lifecycle labels. Draft PR #131 opened by the bot, milestone `v0.1.0`, `Closes` block covering the epic and all six stories. `stage-exit S2` green. |
| 2026-08-13 | Spec gate | **Approved** by SamuelJennings, in session, no changes requested. |
| 2026-08-13 | S3 PLAN | Research measured the admin path against Django 5.2.16 and django-tomselect 2026.6.2: the control already reaches admin pages intact, `RelatedFieldWidgetWrapper` is applied unconditionally at `options.py:193`, and the mechanism that declines it was prototyped before the plan was written. `plan.md`, `research.md`, `tasks.md` (18 tasks, 7 phases) and the ledger written. Decisions D9–D13 recorded. `stage-exit S3` green. |
| 2026-08-14 | S3R DESIGN_REVIEW | One reviewer, three lenses, no diff. Verdict `request_changes`: 7 findings (1 high, 3 medium, 3 low), all verified, all remedied in `spec.md`, `plan.md`, `research.md` and `tasks.md`; each remedy checked by the orchestrator against the finding's own evidence rather than a second review round. DR-001 amends FR-004 to the editable control (D14) and is raised with the maintainer in the plan notification. DR-002 dropped T016 (D15). One round, budget used. `stage-exit S3R` green. |

## 2026-08-14T06:01:02Z · Implementer US-1 · T002

Did: wrote `tests/test_admin.py` (new) — `TestConceptControlRendersOnAdminPages`, four
tests against the bare `ModelAdmin` registrations `tests/testapp/admin.py` already carries
(`Specimen.rock_type`, `Outcrop.minerals`). No production code — pins FR-001, FR-002, SC-001,
US-1 scenarios 1-3 and 6.

Verified: `poetry run pytest -q tests/test_admin.py::TestConceptControlRendersOnAdminPages` —
4 passed. All four passed on first run (expected: the context names this behaviour already
true by accident); sanity-checked the assertions are not vacuous by probing the rendered add
page directly outside pytest — the wrong field reference (`testapp.specimen.name`) is absent
while the right one (`testapp.specimen.rock_type`) is present, so the marker is genuinely
field-specific rather than always-on page furniture.

Next: T003 (vocabulary-size bound).

Watch: `tests/` is globally excluded from this repo's pre-commit hooks
(`.pre-commit-config.yaml` `exclude: "^docs/|/migrations/|^tests/"`), so `ruff check`/`ruff
format` on new test files must be run manually — pre-commit reported "no files to check" and
did not catch two lint findings (unused imports staged ahead of T004, one long test name) on
this task's first commit; fixed in two follow-up commits before moving on.

## 2026-08-14T06:01:44Z · Implementer US-1 · T003

Did: added `TestAdminPageRenderingIsBoundedByVocabularySize` to `tests/test_admin.py`,
mirroring `tests/test_forms.py::TestConceptFieldRenderingIsBoundedByVocabularySize` shape for
shape. No production code — pins FR-009, SC-006, US-1 scenario 4.

Verified: `poetry run pytest -q tests/test_admin.py::TestAdminPageRenderingIsBoundedByVocabularySize`
— 1 passed, on first run. `ruff check`/`ruff format --check` clean (run manually, per the T002
watch item).

Next: T004 (submission saves, foreign-vocabulary refusal, delete protection).

## 2026-08-14T06:04:28Z · Implementer US-1 · T004

Did: added `TestAdminSubmissionSavesAndFieldRulesStillBite` to `tests/test_admin.py`, six
tests, both field kinds. No production code — pins FR-010, US-1 scenario 5.

Verified: `poetry run pytest -q tests/test_admin.py::TestAdminSubmissionSavesAndFieldRulesStillBite`
— 6 passed; `poetry run pytest -q tests/test_admin.py` (whole file) — 11 passed. `ruff
check`/`ruff format --check` clean (manual, per the T002 watch item).

First draft of the two refusal tests asserted the model-level custom message
("is not a valid concept...") and failed against the real response — the actual text is
Django's generic ModelChoiceField message, because the widget's own queryset restriction
refuses the foreign pk before the model-level message is ever reached. Recorded as D19 and
fixed to assert on the errored field instead, matching the restraint `tests/test_forms.py`'s
own refusal tests already use.

Next: T005+ is US-2's scope, out of this story.

Watch: none beyond D19 and the T002 pre-commit-exclusion note above.

## 2026-08-14T08:20:00Z · Implementer US-2 · T005

Did: added `TestConceptFieldOffersNoRelatedObjectAffordance` to `tests/test_admin.py`
(five tests) plus two module-level fixtures (`concept_registered_admin_site`,
`bare_admin_site`) and a small `_URLConf` helper that mounts a dedicated
`AdminSite` instance (registering `Specimen`, `Outcrop` and, in the first
fixture, `Concept`) at `admin/`, alongside this package's own route at
`vocabularies/` so the widget's autocomplete reverse still resolves. No
production code — pins FR-004, US-2 scenarios 1-5, SC-002.

Verified: `poetry run pytest -q tests/test_admin.py::TestConceptFieldOffersNoRelatedObjectAffordance`
— 4 failed, 1 passed. The four failures are the correct RED: with `Concept`
registered and a superuser, both field kinds' add and change pages carry
`related-widget-wrapper-link` and (bar the multi-value field's forced-off
three) `add-related`/`change-related`/`delete-related`/`view-related` —
matching research.md R1's measured table exactly. The one pass
(`test_the_same_absence_holds_with_concept_not_registered`) is correctly
green already: `options.py`'s `wrapper_kwargs = {}` on `NotRegistered` leaves
every affordance boolean `False` regardless of the mechanism this story adds,
which is scenario 4's own point — sanity-checked by temporarily deleting one
`not in` assertion and confirming it fails, so the passing test is not
vacuous.

Two false starts before the fixture worked: `types.SimpleNamespace` as the
`ROOT_URLCONF` override is unhashable (`_get_cached_resolver` is
`functools.cache`d) — replaced with a plain `_URLConf` class; and the first
version of `_URLConf` mounted only the admin, so every render raised
`ImproperlyConfigured` from `forms.py`'s route-mixin before reaching an
affordance assertion — fixed by mounting `controlled_vocabularies.urls` too,
matching `tests/urls.py`.

Next: T006 — the form field declines the wrapper.

Watch: none beyond the T002 pre-commit-exclusion note (ruff run manually on
this file; `ruff check --fix` on first run removed the now-unused `types`
import after the `_URLConf` rewrite).
