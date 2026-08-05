# Progress — 007 Import keeps the languages the site supports and reports the rest

Append-only log of stage transitions and gate outcomes.

## 2026-08-04

- **S0 INTAKE** — issue #51 grilled. Grounding first: the issue, its dependency #50 (merged), the
  sibling #52, roadmap R2, `GOALS.md`, and the landed importer. That grounding showed two of the
  issue's three clauses already delivered by #50, and the feature was reported back to Sam as
  probable residue. What kept it alive is that language matching was exact string equality against
  `settings.LANGUAGES`, so a site on `en-gb` importing a vocabulary published as `en` stored
  nothing — the issue's own first sentence, unsatisfied. Three questions, all answered: match by
  base language, match in both directions, and this feature owns *what* a curator is told while #52
  owns *where* they read it. A fourth question drifted into rule design and was pulled back on
  Sam's correction. Feature statement confirmed. Issue labelled `accepted`.
- **S1 SPECIFY** — repo synced first at Sam's instruction: `main` was two commits behind
  (PR #68, constitution Articles XIV and XV), and Article XV constrains this feature's shape.
  Branch `007-import-keeps-published` created. `spec.md` written: 5 user stories (2×P1, 2×P2,
  1×P3), FR-001..015, SC-001..021. Clarify coverage scan run and self-answered — eight ambiguities
  resolved into the spec across two sessions, rationale in `decisions.md` (D1–D11). The scan caught
  a defect in the draft: FR-003 as first written collapsed competing variants to one winner
  everywhere, which is correct for a preferred label (whose uniqueness constraint is conditional on
  `kind="preferred"`) and wrong for alternative labels, hidden labels, and notes, which carry no
  such constraint. Spec lint green: no unresolved markers, every FR carried by a story scenario,
  goal ids cited (G8, G6, G4).
- **S2 SETUP** — spec committed and pushed as `forge-aeo[bot]`. Issue #51 promoted to the epic in
  place (intake paragraph preserved under `## Original request`). Story sub-issues #69–#73 created
  and linked, no lifecycle labels, milestone `v0.1.0`. Draft PR #74 opened by the bot, title
  byte-identical to the epic, `Closes` block covering the epic and all five stories, milestone set.
  `check-issue-titles` green, `stage-exit --stage S2` green (clarifications, issue-titles,
  pr-title).
- **Spec gate — APPROVED** by Sam (SamuelJennings), 2026-08-04, in session. Scope as specified,
  including all five self-resolved decisions surfaced in the brief: script-differing variants
  joined by base-language matching, the variant contest scoped to kinds the models hold one of per
  language, the predominant variant winning a contest, the vocabulary default language resolving by
  the same rule, and no compatibility path owed. Sam also flagged that the S3R design-review gate
  is newly added and this run is its first trigger, to be watched. Proceeding to S3 PLAN.
