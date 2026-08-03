# Progress — 006 Import a published SKOS vocabulary from a file

Append-only log of stage transitions and gate outcomes.

## 2026-08-03

- **S0 INTAKE** — issue #50 grilled. Four questions, all answered: escrow deferred to its own
  feature sequenced with export; the file is the authority for which vocabulary is imported; the
  import is authoritative for records the file contains and silent about those it does not; a run
  applies in full or not at all, with a small fatal set. Feature statement confirmed. Issue
  labelled `accepted`.
- **S1 SPECIFY** — branch `006-import-published-skos` created. `spec.md` written: 6 user stories
  (2×P1, 3×P2, 1×P3), FR-001..018, SC-001..018. Clarify scan run and self-answered — five
  ambiguities resolved into the spec, rationale in `decisions.md` (D1–D8). Spec lint green: no
  unresolved markers, every FR carried by a story scenario, goal ids cited (G4, G6, G8).
- **S2 SETUP** — spec committed and pushed as `forge-aeo[bot]`. Issue #50 promoted to the epic in
  place (intake paragraph preserved). Story sub-issues #61–#66 created and linked, no lifecycle
  labels, milestone `v0.1.0`. Draft PR #67 opened by the bot, title byte-identical to the epic,
  `Closes` block covering the epic and all six stories, milestone set. `check-issue-titles` green.
- **Spec gate — APPROVED** by Sam (SamuelJennings), 2026-08-03, in session. Scope as specified,
  including the four self-resolved decisions surfaced in the brief: escrow deferred, language
  filtering landing here rather than in #51, blank-node identity fatal, and the imported
  vocabulary's default language taken from the file. Proceeding to S3 PLAN.

## 2026-08-03T20:00:03Z · Implementer US0 · T002

**Did**: Scaffolded the `controlled_vocabularies/io/` package (docstring-only `__init__.py`, no
re-exports yet) and its mirroring `tests/test_io/` directory, with a failing-first test that the
package imports and carries a module docstring. Created `tests/fixtures/` (empty; populated by
T005). Dropped the redundant `mypy_path = "controlled_vocabularies/"` mypy config entry — it made
the new `io/` package collide with the stdlib `io` module ("Source file found twice"); removing it
changes nothing else (mini-ADR: `decisions.md` D10).

**Verified**: `poetry run pytest -q` — 287 passed (285 baseline + 2 new). `poetry run ruff check .`
— all checks passed. `poetry run ruff format --check .` — 15 files already formatted. `poetry run
mypy` — success, 5 source files (baseline 4 + `io/__init__.py`). `poetry run deptry .` — no issues,
11 files scanned. `poetry run pre-commit run --all-files` — all hooks passed.

**Next**: T003 — `report.py` (`ImportReport`, `SetAsideEntry`, the reason vocabulary).

**Watch**: the `mypy_path` removal is repo-wide config, not story-scoped — flag it in review since
it touches the shared toolchain config rather than only this feature's new files.
