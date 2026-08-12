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
- **2026-08-12 — S3 PLAN.** `research.md` (R1–R7, all established empirically against the installed
  Django 5.2.16), `plan.md`, `tasks.md` (T001–T011 across eight stories), `decisions.md` extended
  with D7 (the two consumption fields do not share an implementation) and D8 (the required-set rule
  is installed onto `full_clean`). `stage-exit --stage S3` green.
- **2026-08-12 — S3R DESIGN_REVIEW.** One reviewer, three lenses, one round. Craft-skill receipts
  verified against the registry on all three findings files. Security: `approve`, no findings.
  Spec-compliance and architecture: `request_changes`, one verified `high` each, both accepted and
  applied as plan edits.
  - **SC-001** — D8's wrapper is installed once per consuming class, and nothing said it must
    resolve *every* required `ConceptsField` on that class rather than the one that triggered the
    install, so a second required field would go unenforced with nothing raising. Applied to
    `decisions.md` D8, `plan.md` Approach 5, `tasks.md` T009 (fourth constraint plus a three-part
    test case) and T001 (a two-required-field model to make the case declarable).
  - **ARC-001** — `tasks.md` T003 told the implementer to follow Django's own sequence,
    `super().contribute_to_class(...)` then generate. Read literally that double-registers the join
    model, because `ManyToManyField.contribute_to_class` generates and registers the CASCADE through
    model inside its own body. Confirmed against `django/db/models/fields/related.py:1957-2004` in
    the installed 5.2.16: there is no seam between attach and generate. `plan.md` Approach 3 and
    `tasks.md` T003 now specify the MRO skip, `super(ManyToManyField, self).contribute_to_class(...)`,
    require the hidden `related_name` branch that skip drops to be replicated (FR-011 accepts
    `related_name="+"`), and add a test asserting the registry warning is absent.
  No wording-drift notes returned. No finding fell on `spec.md`, so no delta brief and no re-gate.
- **2026-08-12 — SPEC AMENDMENT, re-gated and APPROVED by Sam.** Raised by the maintainer after the
  design review and before any code existed: requiring a non-empty `vocabulary` was too restrictive,
  because keywords drawn from several vocabularies — or from whatever a project has imported — are a
  standard shape in research metadata. The declaration now names one vocabulary, several, or none.
  Delta brief given in session and approved there. `spec.md` refined in place (FR-002, FR-004,
  FR-005, FR-006, FR-013, SC-002, User Story 2, new User Story 8, four new edge cases, one new
  assumption); `decisions.md` D9; propagated to `plan.md` (Summary, Approach 1, 4 and 7) and
  `tasks.md` (T001, T002, T005, T006, T010, T011, new T012). Story issue #110 created and linked,
  epic body and PR #109 `Closes` block re-synced, ledger carries US8/T012. Nothing was implemented
  against the superseded wording, so no code was reverted.
