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
- **Spec gate** — briefed, awaiting sign-off.
