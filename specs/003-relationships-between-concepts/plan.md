# Implementation Plan: Relationships between concepts

**Branch**: `003-relationships-between-concepts` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-relationships-between-concepts/spec.md`

## Summary

Turn a vocabulary from a flat set of concepts into a graph. One new through model,
`ConceptRelation(source, target, kind)`, stores each hierarchy edge in a single canonical direction
(`source skos:broader target`) and each `related` association as one PK-canonicalised row; the
`narrower` direction is derived by reading rows from the `target` side. `Concept` gains explicit
read/write helpers (`broader`/`narrower`/`related`, `add_broader`/`add_related`/`remove_*`) mirroring
#16's helper style. Integrity — no self-relation, no duplicate, broader/related disjointness on direct
pairs, intra-vocabulary only — is enforced by DB constraints where a single table can express them
(unique triple, self-check) and by `clean()` + a `save()` backstop where it spans rows (disjointness,
same-scheme), following the #15/#16 create/factory-safe pattern. Cycle prevention and transitive
disjointness are deliberately out (they need the hierarchy traversal this slice avoids). No new runtime
dependency; interaction is programmatic; one migration, squashed at convergence.

## Technical Context

**Language/Version**: package runtime floor Python 3.11 (Art. X); dev/test toolchain (`mvp-shared[test]`)
needs 3.12+, so CI exercises 3.12/3.13 (unchanged from #15/#16).

**Primary Dependencies**: Django 5.2 LTS + 6.0. **No new runtime dependency** — `rdflib` (RDF
projection of the relations) belongs to the export feature (R2/R4); `deptry` would fail an unused dep.

**Storage**: host project's relational database via the Django ORM; one new model
(`ConceptRelation`), one migration (squashed at convergence).

**Testing**: `pytest` + `pytest-django`; `factory_boy` factories mirroring the source tree per the
family testing standard (`tests/factories.py`, `tests/test_models.py`, `tests/test_standards.py`).

**Target Platform**: an installable Django app (also runnable standalone).

**Project Type**: single project — a reusable Django app package.

**Performance Goals**: none specific to this slice (large-vocabulary scale is roadmap G5/R-later).
Relation reads are FK-scoped and indexed (research R6); no traversal is performed.

**Constraints**: the inverse-pair guarantee must be a property of the schema (one stored direction);
integrity refusals must carry translatable messages and hold on the `create()`/factory path, not only
`full_clean()`; disjointness and cycle checks must not walk the hierarchy (direct-adjacency only).

**Scale/Scope**: one new model, read/write helpers on `Concept`, one migration, factories, tests. No UI.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 design (unchanged).*

- **I Test-First** — tasks order the failing test before its implementation per story. Pass.
- **II Simplicity** — one through model with ordinary FKs and constraints; integrity is DB constraints
  plus small `clean()`/`save()` checks, no traversal, no graph library. Pass.
- **III Anti-Abstraction** — a single relation model typed by `kind` rather than separate
  Broader/Related models; explicit `Concept` helpers rather than M2M-descriptor machinery that fights
  the asymmetric+symmetric split (research R4). No base classes/wrappers. Pass.
- **IV Integration-First** — the ORM surface is the contract (`contracts/python-api.md`); acceptance
  tests drive it exactly as a downstream developer would. Pass.
- **V Security & data-safety** — no rendered output, no secrets, no imported RDF this slice; validation
  messages use the framework's `ValidationError`/`gettext_lazy`, never hand-built interpolation. Pass.
- **VI Documentation** — new public API (relation helpers + `ConceptRelation`): README scope note +
  CHANGELOG entry + docstrings ship in this PR (T-Polish). Pass.
- **VII Dependency discipline** — no runtime dependency added (research R5); factories are test-only;
  `deptry` stays green. Pass.
- **VIII Compatibility (dual contract)** — pre-1.0; the Python API is additive (new methods, one new
  model), no existing surface changed. The RDF/URI data contract is untouched (relations are not
  serialized here). Pass.
- **IX URI identity & downstream-data safety** — honoured: adding/removing relations never touches a
  concept's `slug`/`uri` (FR-004/FR-005, tested). `ConceptRelation` FKs use `CASCADE` because an edge
  is not consumer data and is meaningless without both endpoints; Article IX's `PROTECT`/deprecation
  governs *consumer references* and concept *retirement* (#19), which this slice does not touch
  (data-model.md). Pass.
- **X Stack & architecture** — Django 5.2+/Py 3.11 floor; models are the source of truth; SKOS-only
  (`broader`/`narrower`/`related` are SKOS semantic relations); no triplestore, no traversal engine. Pass.
- **XI RDF fidelity** — no import/export this slice; `Kind` values are named for their SKOS predicates
  so the later export map is a straight lookup. Deferred, recorded. N/A now.
- **XII Internationalization** — every new field carries translatable `verbose_name` + `help_text`; the
  four new validation messages (self, duplicate, disjointness, cross-vocabulary) are `gettext_lazy` with
  named placeholders; asserted by the standards test (US-5). Pass.
- **XIII Data-model conventions** — indexing deliberate: unique `(source, target, kind)` gives the
  source-leading index, an explicit `(target, kind)` index covers the reverse reads, FKs auto-index; the
  self-check is a `CheckConstraint` (research R6/data-model). Migration squashed at convergence. Pass.

**No violations require Complexity Tracking.** The cycle-prevention and transitive-disjointness
omissions are scope deferrals (spec Assumptions, `decisions.md`), justified by the no-traversal
constraint, not unjustified shortcuts.

## Project Structure

### Documentation (this feature)

```text
specs/003-relationships-between-concepts/
├── spec.md              # approved at the Spec gate
├── plan.md              # this file
├── research.md          # Phase 0 — storage, symmetry, integrity, API-shape decisions
├── data-model.md        # Phase 1 — ConceptRelation, constraints, Concept helpers
├── contracts/
│   └── python-api.md     # Phase 1 — the public ORM contract
├── quickstart.md        # Phase 1 — runnable validation scenarios
├── decisions.md         # self-resolved ambiguities + deferrals (from S1)
└── tasks.md             # Phase 2 (S3 tasks command) — the task graph
```

### Source Code (repository root)

```text
controlled_vocabularies/
├── models.py            # +ConceptRelation model; +Concept.broader/narrower/related +add_/remove_ helpers
└── migrations/
    └── 000X_*.py         # generated; squashed to one at convergence

tests/
├── factories.py          # +ConceptRelationFactory (and a related-graph trait/helper)
├── test_models.py        # US-1..US-3: hierarchy, related, integrity (class-grouped)
├── test_factories.py     # US-4: relation factory output
└── test_standards.py     # US-5: metadata i18n + indexing over ConceptRelation
```

**Structure Decision**: single reusable-app layout, unchanged from #15/#16. The new model joins the
existing `models.py` (one small model does not warrant a `models/` package — Anti-Abstraction). Tests
mirror the source tree; the existing `test_standards.py` is extended to walk the new model's fields.

## Complexity Tracking

No constitution violations to justify. The deliberate omissions (cycle detection, transitive
disjointness, RDF projection, admin/editor UI) are scope boundaries recorded in the spec Assumptions
and `decisions.md`, each tied to a stated reason (no hierarchy traversal this slice; later feature owns
it) — not shortcuts.
