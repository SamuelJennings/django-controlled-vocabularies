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
