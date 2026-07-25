# Progress — 003-relationships-between-concepts

The run's human-readable narrative. The ledger (`feature-state.json`) is the machine source of truth;
this file is the story of what happened and why.

## 2026-07-24T22:29Z · S0–S3 · plan complete

- **Did:** Grilled to shared understanding (integrity set + ORM-only scope confirmed by Sam). Wrote
  `spec.md` (5 stories, 13 FR, 10 SC) and `decisions.md`. Promoted #17 to epic, created story issues
  #36–#40, opened draft PR #41 (bot) with the `Closes` block, milestone `v0.1.0`. Spec gate approved
  by Sam. Authored `research.md`, `data-model.md`, `contracts/python-api.md`, `quickstart.md`,
  `plan.md`, `tasks.md`. Analyze gate green (all prereq docs present; every FR maps to a task).
- **Verified:** spec-lint green (no unresolved markers, FR↔story coverage complete); issue-title lint
  green; `speckit check --require-tasks` lists all design docs.
- **Next:** S4 implement (test-first, T001→T015), then converge, review, PR finalize.
- **Watch:** the disjointness and same-scheme invariants have no single-table DB constraint — they
  must hold on the `create()`/factory path via the `save()` backstop, not only `full_clean()` (the
  #15/#16 pattern). Cycle prevention must stay absent (no hierarchy walk anywhere).

## Process note — Phase-1 implementation (recorded deviation)

The five stories all modify the single `controlled_vocabularies/models.py` and its one migration, so
they cannot run as parallel worktree Implementers — this is a sequential single-file build (the same
shape FS-002 took). Given that coupling and Sam's directive to run unattended to a review-ready PR,
Forge implements the ordered task graph directly on the feature branch, strictly test-first, with
`verify.sh` as the objective machine gate after each story and `tamper-check.sh` against the pre-work
base. Independence is preserved where it carries the weight: the S6 review runs as a separate
reviewer with the correctness+spec lens on the whole diff. Rationale: the substantive gates
(test-first, machine verify as evidence, tamper-check, independent review) are all kept; only the
per-story worktree isolation — which exists to de-conflict *parallel* stories — is dropped, because
there is no parallelism to isolate.

## 2026-07-24T22:48Z · S4–S7 · review-ready

- **Did:** Implemented US-1..US-5 test-first (ConceptRelation + Concept graph helpers, factories,
  standards). Converged (single migration, tamper flags triaged additive-only, no ADR graduation).
  Independent review returned approve (no critical/high); fixed two low findings, declined one with
  a recorded reason. Finalized the PR body and reconciled the Closes block (epic + 5 stories).
- **Verified:** `verify.sh` all green (lint/typecheck/test/build); 139 tests pass; migrate-from-zero
  clean; humanize scan of public markdown clean.
- **Next:** merge gate — Sam reviews and merges. Forge does not merge.
