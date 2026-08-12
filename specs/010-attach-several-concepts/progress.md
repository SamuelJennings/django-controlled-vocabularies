# Progress — 010 Attach several concepts from a chosen vocabulary to a model

Append-only. One line per stage transition and per gate outcome, written at the moment it happens.

- **2026-08-12 — S0 INTAKE.** Issue #87 grilled. One question asked and answered: whether the set
  of attached concepts carries an order the consuming project can rely on. Answer: no, unordered,
  and ordered tagging becomes its own feature if it is ever wanted. Feature statement confirmed by
  the maintainer. `accepted` label added. Dependency #86 verified closed and merged before starting.
- **2026-08-12 — S1 SPECIFY.** Branch `010-attach-several-concepts` created,
  `specs/010-attach-several-concepts/spec.md` written (7 user stories, 13 FRs, 7 SCs), clarify run
  in full (1 intake clarification + 4 from the coverage scan, all self-resolved), `decisions.md`
  written (D1–D6). Spec lint green: every FR maps to a story, every story carries acceptance
  scenarios, G2 cited, no unresolved markers.
- **2026-08-12 — S2 SETUP.** Branch pushed as `forge-aeo` (bot). Issue #87 promoted to epic in
  place. Story sub-issues #102–#108 created and linked. Draft PR #109 opened bot-authored, title
  byte-identical to the epic, `Closes` block seeded for the epic and all seven stories, milestone
  `v0.1.0`. `check-issue-titles` green.
- **2026-08-12 — GATE_SPEC: APPROVED by Sam.** Approved in session against the epic, its seven
  story sub-issues, and `spec.md` on the branch. Gate brief posted as a bot comment on #87
  (`issuecomment-5264353690`), carrying the four self-resolved decisions and the two open risks
  (whether the two consumption fields share an implementation, left to the plan; and the delete
  guard having to be built rather than inherited, since Django drops a membership silently).
