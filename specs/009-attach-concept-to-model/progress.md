# Progress — 009 Attach a concept from a chosen vocabulary to a model

Append-only. One line per stage transition and per gate outcome, written at the moment it happens.

- **2026-08-11 — S0 INTAKE.** Issue #86 grilled. One question asked and answered: what happens when
  a field names a vocabulary that has not been imported yet. Feature statement confirmed by the
  maintainer. `accepted` label added.
- **2026-08-11 — S1 SPECIFY.** Branch `009-attach-concept-to-model` created,
  `specs/009-attach-concept-to-model/spec.md` written (6 user stories, 12 FRs, 6 SCs), clarify run
  in full (1 intake clarification + 4 from the coverage scan, all self-resolved), `decisions.md`
  written (D1–D6). Spec lint green: every FR maps to a story, every story carries acceptance
  scenarios, G2 cited, no unresolved markers.
- **2026-08-11 — S2 SETUP.** Branch pushed as `forge-aeo` (bot). Issue #86 promoted to epic in
  place. Story sub-issues #90–#95 created and linked. Draft PR #96 opened bot-authored, title
  byte-identical to the epic, `Closes` block seeded for the epic and all six stories, milestone
  `v0.1.0`. `check-issue-titles` green. `stage-exit --stage S2` green.
- **2026-08-11 — GATE_SPEC: APPROVED by Sam.** Approved in session against the epic, its six story
  sub-issues, and `spec.md` on the branch. Gate brief posted as a bot comment on #86
  (`issuecomment-5253525466`), carrying the five self-resolved ambiguities and the one open risk
  (Article IX still describing a per-concept lifecycle that #19's ruling superseded — R4's to
  reconcile). No conditions attached. Proceeding to S3 PLAN.
- **2026-08-11 — S3 PLAN.** `research.md` R1–R7 (every finding verified against Django's own source
  in the project virtualenv, not documentation), `plan.md` with the Constitution Check clean and no
  Complexity Tracking entries, `tasks.md` T001–T013 across a foundational phase and the six stories,
  `feature-state.json` generated. Cross-artifact analyze: all 12 FRs and all 6 SCs map to at least
  one task, every story maps to its issue, no unresolved markers. No spec amendment needed — the
  research confirmed the spec rather than contradicting it. Next: S3R design review.
