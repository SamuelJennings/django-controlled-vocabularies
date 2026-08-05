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

## 2026-08-05

- **S3 PLAN** — `plan.md`, `research.md` R1–R5, `tasks.md` T001–T020, ledger schema-valid, committed
  as `28f69e6`. One new `LanguageMatcher` class, four changed methods in `skos.py`, no model, no
  migration, no new dependency. Research R1 measured and rejected Django's own
  `get_supported_language_variant`: it refuses any language Django ships no translation catalog for,
  *including ones the project declares in `LANGUAGES`*, so a site configured for `sga` would store
  nothing.
- **S3R DESIGN REVIEW — first live run of the gate.** `check-skills --role design_reviewer` green
  before dispatch. Three reviewers in parallel, one lens each, against the plan with no diff in
  existence. `check-receipts` green on all three returned reports, all three schema-valid against
  `review-findings.schema.json`.
  - **Verdict `request_changes` on all three lenses.** 22 findings: 4 high (all `verified`), 8
    medium, 10 low. Every high was re-checked against the code before it was accepted, and all four
    held.
  - **SPEC-001** — the winner rule was assigned to one of the two places that compute a winner, so
    `Concept.label` and the surplus report could disagree and the report would contradict the
    database. Fixed by moving the rule onto `LanguageMatcher` (new T021) and having both call sites
    read it.
  - **SPEC-002** — reusing `SURPLUS_PREFERRED_LABEL` for contest losers loaded one reason with two
    populations FR-008 needs kept apart, and rendered a factually false sentence for the new one.
    Fixed by a dedicated set-aside reason (new T022) and an explicit fold membership in T004.
  - **ARCH-001** — the plan's "four call sites" missed a fifth raw-tag comparison at `skos.py:543`,
    which would have crashed the feature's own headline scenario with an uncaught `ValidationError`.
    Fixed in T008; one comparison changes operand.
  - **SEC-001** — `configured_language_codes()` returns a `set`, and Django's default `LANGUAGES`
    contains one ambiguous base (`zh-hans` / `zh-hant`), so a `zh`-tagged file would store under a
    script chosen by per-process hash order. Verified independently: five fresh processes returned
    both orders. Fixed by a stated lexicographic tie-break over an ordered sequence (T001, D15).
  - **Findings that removed work:** the `en`-published fixture in T005 was redundant against 51
    existing `@en` fixtures, and T002's second constructor was deleted in favour of one method on
    `SkosGraph`. No task was found without spec or constitution provenance.
  - Mediums and lows applied in the same pass: fixture paths corrected, the predominance denominator
    stated, the returned code's spelling pinned, FR-009's identity guarantee scoped, the FR-010
    invariant test extended to Django's default `LANGUAGES`, README obligation added, and one
    Complexity Tracking row added for the report bucket that now grows on the success path.
  - Three findings were spec-adjacent rather than plan faults and are recorded as D15, D16 and D17
    rather than resolved silently. None changes an approved behaviour, and all three are named in
    the plan notification for veto.
  - `design_review_cycles` 1 of 1 used.
- **S3R ROUND TWO** — the same three lenses re-run against the revised artefacts, `check-skills`
  green before dispatch and `check-receipts` green on all three returned reports, all schema-valid.
  **Verdict `approve` on all three lenses, risk `low`, zero critical and zero high.** The gate is
  green and the run proceeds to the plan notification.
  - Each lens confirmed its own round-one blocker was closed by the edit made rather than merely
    named, and checked the two added tasks (T021, T022) on its own terms. The architecture lens
    independently re-derived the `research.md` R4 overturn and agreed with it; the security lens
    re-measured the Django `zh-hans`/`zh-hant` reachability rather than trusting its own prior note.
  - Twelve non-blocking findings (8 medium, 4 low), applied in the same pass rather than carried as
    watch items, since each was a one-sentence edit. Three lenses converged independently on the same
    three: `SkosGraph.first_literal`'s `language=` filter is a sixth, seventh and eighth comparison
    that decides what the vocabulary and its collections are *named*; T002's predominance count fixed
    its predicate but not its node set, which would have silently changed #50's merged
    default-language rule; and T013's re-keying makes one candidate group hold both same-language
    duplicates and variant losers, with no stated discriminator between them.
  - Two findings caught factual errors introduced by the round-one fixes. The plan's "whole surface"
    claim was falsified for the second time, and the FR-010 test written to run "under Django's
    default `LANGUAGES`" would have run under `tests/settings.py`'s own three-language list and
    pinned nothing while reading as an obligation met. Both are recorded in D12.
  - One low finding became a decision rather than an edit: D18, that a concept's local URL follows the
    file rather than the concept, because predominance is file-wide and the slug is recomputed every
    run. Carried into #52's and R6's specification.
- **Plan notification (veto window, not a gate)** — sent to Sam carrying the panel's verdict.
  Silence is consent; the run proceeds to S4 IMPLEMENT.
- **S4 IMPLEMENT — US0 (foundational phase, T001/T002/T021/T003/T022/T004/T005), Implementer.**
  `craft-tdd` and `craft-increments` loaded by name, receipts verified against the brief before
  any task started. Baseline confirmed green (668 tests, HEAD `06a7760`) before touching anything.
  Seven commits, one per task, tree green and clean after each:
  - **T001** — `exchange/languages.py`: `LanguageResolution` and `LanguageMatcher.resolve`. Exact
    match wins; otherwise the least specific configured language sharing the base, computed over a
    deterministically ordered sequence (D15); case-insensitive; returns the code exactly as
    declared. `sga` regression pins the rejection of Django's own resolver (research.md R1).
  - **T002** — `SkosGraph.preferred_label_tag_counts` (concept nodes' `skos:prefLabel` only, per
    D4/D5); `SkosImporter.run` builds one matcher per run and passes it to `SchemeResolver` and
    `ConceptImporter` as a keyword-only constructor argument. Neither collaborator's body reads
    `self.matcher` yet — the five raw-tag comparisons are out of this phase's scope by the brief's
    own prohibition.
  - **T021** — `LanguageMatcher.resolve_winner`: one cascading sort key implements exact-match-first,
    then predominance, then a lexicographic tag tie-break, so `preferred_label_in` and
    `import_labels` will read the identical rule once their stories wire it in (S3R SPEC-001).
  - **T003** — `NormalizedReason.LANGUAGE_SUBSTITUTION`, in the normalised bucket (a substitution
    *was* stored).
  - **T022** — `SetAsideReason.VARIANT_NOT_KEPT`, a dedicated reason for a contest loser —
    `SURPLUS_PREFERRED_LABEL`'s message is false for this case (S3R SPEC-002, D14). Regression test
    pins `SURPLUS_PREFERRED_LABEL`'s own message unchanged.
  - **T004** — `ImportReport.language_account()`: a fold over `{UNCONFIGURED_LANGUAGE,
    VARIANT_NOT_KEPT}`, explicit membership rather than "carries a `language` param" (D14's own
    failure mode, guarded against directly).
  - **T005** — three fixtures (`variants.ttl`, `en-gb-only.ttl`, `declares-de-at.ttl`); no `en`-only
    fixture (51 already exist). Pass the existing predicate-coverage sweep unmodified — every
    variant tag is still `UNCONFIGURED_LANGUAGE` under this phase's untouched call sites.
  Full verify green throughout: `poetry run pytest -q` (724 passed), `ruff check .`, `ruff format
  --check .`, `mypy controlled_vocabularies`, `deptry .`, `pre-commit run --all-files`. Worktree
  clean. Three naming/shape choices not dictated by the brief are recorded as D19–D21. Next:
  US-1 (T006–T010) wires the matcher into the five call sites.
