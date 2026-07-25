# Decision record — 003-relationships-between-concepts

Self-resolved ambiguities from S0/S1. Each is defensible from grounding (issue #17,
CONTEXT.md, `docs/brainstorm.md`, the constitution) or from the integrity set Sam agreed in
grilling. Anything grilling could not defensibly settle was escalated to Sam, not recorded here.

## Grilled with Sam (S0)

- **Integrity set.** Enforce: reject self-relations; reject duplicates (same pair + type, incl.
  mirror-image `related`); enforce broader/related disjointness. **Do not** enforce acyclicity in
  the broader hierarchy — deliberate non-guarantee this slice. Confirmed by Sam.
- **ORM-only, admin deferred.** Corrected the intake framing: #15 and #16 both landed
  programmatic-only with all editing surfaces (incl. Django admin) deferred to R5. #17 follows that
  precedent — relations through the ORM only; admin/editor UI is R5. Confirmed by Sam.

## Self-resolved (S1)

- **Disjointness is checked at direct adjacency, not transitively.** SKOS's formal rule is
  related ⟂ broaderTransitive, but transitive enforcement needs the hierarchy traversal this slice
  deliberately omits (the cycle deferral). Scoping disjointness to directly-asserted broader/narrower
  pairs keeps it O(1)-ish and consistent with that deferral. Defensible: the two deferrals share one
  reason (no traversal this slice). Recorded in the spec (FR-008, Assumptions, Edge Cases).

- **Relations are intra-vocabulary; cross-scheme links are refused.** CONTEXT.md defines Relation as
  an "intra-vocabulary link" and Mapping as the cross-vocabulary mechanism that "lives in the JSON
  document, not the relation M2M." The issue says "concepts *within a vocabulary*." So both endpoints
  of a relation must share a `ConceptScheme`; a cross-scheme relation is refused (FR-009). Not a new
  decision — reading the grounding.

- **Stored relationship types = {broader, related}; narrower derived.** Per `docs/brainstorm.md`
  ("persist broader, read narrower back; normalise the symmetric related to one row"). The spec
  states the behaviour (FR-002, FR-003) and leaves the storage shape to planning.

- **Goal link G4 honoured as claimed.** The issue footer claims Serves: G4. The relation graph is
  part of what a managed vocabulary must export losslessly, so G4 (faithful round-trip) is a
  defensible anchor. Kept as the cited goal; not re-litigated.

## Self-resolved (S3 plan)

- **Storage: one `ConceptRelation` through model, canonical direction stored, inverse derived.** Per
  `docs/brainstorm.md`. One row per hierarchy edge (`source skos:broader target`); `narrower` is the
  read from the `target` side; `related` canonicalised to one PK-ordered row. Rejected: per-type M2M
  fields, both-direction storage, tree libraries (no polyhierarchy). Full reasoning in `research.md`
  R1–R2. **Revisit if:** the RDF exporter (R2/R4) needs a different persisted shape.

- **Integrity split: DB constraints where a single table expresses them, `clean()`+`save()` where it
  spans rows.** Unique `(source,target,kind)` (duplicate) and `CheckConstraint(~Q(source=target))`
  (self) are DB-level; disjointness (unordered pair, two kinds) and same-scheme (two tables) are
  `clean()` with a `save()` backstop, because `create()`/factories bypass `full_clean()` (the #15/#16
  pattern). `research.md` R3.

- **`ConceptRelation` FKs use `on_delete=CASCADE`.** An edge is not consumer data; it is meaningless
  without both endpoints. Article IX's `PROTECT`/deprecation governs *consumer references* to a
  concept and concept *retirement* (#19), not the relation edges themselves. `data-model.md`.
  **Revisit if:** #19 introduces a reason to retain dangling edges (it should not — deprecation keeps
  the concept row).

- **Read API is explicit methods, not a public M2M descriptor.** `broader`/`narrower`/`related` have
  three different read shapes (directional, inverse-directional, symmetric-spanning-both-columns) that
  one Django M2M accessor cannot express cleanly; explicit methods match #16's surface. `research.md` R4.

## Process (S4 implementation)

- **Phase-1 build is orchestrator-implemented, not per-story worktree Implementers.** The five stories
  share one `models.py` + one migration (no parallelism to isolate), so Forge implements the ordered
  task graph directly on the branch, test-first, with `verify.sh`/`tamper-check.sh` as the machine
  gates and an independent reviewer at S6. Recorded in `progress.md`. **Revisit if:** a future feature
  in this repo splits cleanly into parallel independent stories — then dispatch per-story worktrees.

## Convergence (S5)

- **Tamper-check flags triaged and cleared (additive-only).** `tamper-check.sh` flagged four modified
  test files (`tests/test_models.py`, `tests/test_factories.py`, `tests/test_standards.py`,
  `tests/factories.py`). Inspected: every change is an **addition** — new test classes
  (`TestBroaderNarrower`, `TestRelated`, `TestGraphIntegrity`), new factory/helper, new standards
  tests — plus two non-test edits (a widened import and the `ALL_MODELS` list gaining
  `ConceptRelation`). No pre-existing test function was modified, weakened, skipped, or deleted; no
  assertion was removed. Approved per D4 (coarse file-level flag, legitimate extension). The coverage
  extension is the intended shape for a story that adds a model to an existing suite.

- **Migration: single file, no squash needed.** The branch introduces exactly one migration
  (`0003_conceptrelation`). Migrate-from-zero reaches the final state and `makemigrations --check` is
  clean.

- **ADR graduation: none.** This repo records design in `docs/brainstorm.md` + the feature's
  `research.md`/`decisions.md`, not in a `docs/adr/` tree (none exists). Every decision here
  (canonical-direction storage, integrity placement, CASCADE-vs-Article-IX, explicit-method API) is
  already recorded in those docs, so none meets the "non-obvious AND not already recorded" ADR bar,
  and introducing the repo's first ADR mid-feature is unwarranted.

## Escalated to Sam

- None beyond the two grilled points above. The remaining scope was settled by grounding.
