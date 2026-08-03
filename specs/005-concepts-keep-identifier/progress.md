# Progress — 005-concepts-keep-identifier

Append-only narrative log. The ledger (`feature-state.json`) is the source of truth for state; this is
the human-readable trail.

## 2026-08-03 — S0→S2

- **S0 grill.** Grounded on issue #49, its three siblings (#50 import, #51 languages, #52 command
  line), `GOALS.md`, and the R1 code before asking anything. Three questions, each answered by Sam.
  The feature covers vocabularies, concepts, and collections, not concepts alone. A published record's
  identifier is stored and fixed, an unpublished local one is composed and provisional. The identity
  and the address a record is viewed at are two different things and both are needed, because an
  imported record's identifier points at its publisher's site while it still has to be viewable here.
  Sam named them: permanent URI and local URL. Issue #49 gained `accepted` alongside the permanent
  `feature-request` label.
- **S1 specify.** `spec.md` written (5 user stories, FR-001..014, SC-001..013). Clarify's taxonomy scan
  run in full: Functional Scope, Interaction, Integration, Constraints, and Completion Signals clear;
  Domain & Data Model, Non-Functional, and Terminology partial. Four questions raised and self-answered
  from grilling context, landed under `## Clarifications` and integrated into FR-002, FR-004, FR-013,
  FR-014. The scan caught a real defect drafting had missed — FR-002 carried an "other than an explicit
  re-import" escape hatch, which is wrong because upsert matches a record *by* its identifier and so
  never has occasion to rewrite it. Self-resolutions logged in `decisions.md` (D1–D9). Spec lint green:
  all 14 FRs map to a story, every story has acceptance scenarios and an independent test, both goal ids
  cited, no unresolved markers.
- **S2 setup.** Branch `005-concepts-keep-identifier` pushed as the bot (author and committer both
  `forge-aeo[bot]`, verified through the API — the repo's history carries three different numeric ids
  for that account and only one is real). #49 promoted to epic `FS-005` in place; story sub-issues
  #53–#57 created unlabelled and linked; draft PR #58 opened bot-authored, milestone v0.1.0, with a
  `Closes` line for the epic and each story; title lint green.
- **Spec gate: APPROVED by Sam, 2026-08-03.** Brief posted in-session and mirrored as a bot comment on
  #49. No changes requested.
