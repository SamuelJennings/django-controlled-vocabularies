# Implementation Plan: Collections that group concepts

**Branch**: `004-collections-group-concepts` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-collections-group-concepts/spec.md`

## Summary

Add named collections that group a vocabulary's concepts. Two new models: `Collection` (`scheme` FK,
`name`, derived `slug` unique within the scheme, `ordered` boolean) and a `CollectionMember` through
model (`collection` FK, `concept` FK, `position`) joining a collection to its member concepts.
Membership is many-to-many, held once per `(collection, concept)` by a `UniqueConstraint`, and confined
to the collection's own scheme by a `clean()`/`save()` check (a cross-table equality no single-table
constraint can express) — following the #17 integrity pattern. Ordering is a **hand-rolled `position`
field**, not a library (research R5, Complexity Tracking): ordered collections read members
`ORDER BY position`; removing a member leaves survivors' relative order intact because gaps in an
ordered read are harmless. `Collection` gets a small helper API (`add`/`remove`/`members`/
`set_member_order`) mirroring #16/#17's helper style; `Concept` gains `collections()` (reverse read).
Membership is orthogonal to the relation graph (#17) by construction — separate tables, no shared
state. Interaction is programmatic; one migration, squashed at convergence; no admin/editor UI (R5).

## Technical Context

**Language/Version**: package runtime floor Python 3.11 (Art. X); dev/test toolchain (`mvp-shared[test]`)
needs 3.12+, so CI exercises 3.12/3.13 (unchanged from #15/#16/#17).

**Primary Dependencies**: Django 5.2 LTS + 6.0. **No new runtime dependency** — the ordering library Sam
flagged for consideration (`django-ordered-model`) is **rejected** (research R5): its last release is
March 2023 and its test matrix tops out at Django 5.1, with no 5.2/6.0 support, so it would fail this
repo's required 6.0 CI legs and adds an unmaintained dep to a core domain model. `rdflib` (RDF
projection of collections) belongs to export (R2/R4); `deptry` would fail an unused dep.

**Storage**: host project's relational database via the Django ORM; two new models (`Collection`,
`CollectionMember`), one migration (squashed at convergence).

**Testing**: `pytest` + `pytest-django`; `factory_boy` factories mirroring the source tree per the
family testing standard (`tests/factories.py`, `tests/test_models.py`, `tests/test_factories.py`,
`tests/test_standards.py`).

**Target Platform**: an installable Django app (also runnable standalone).

**Project Type**: single project — a reusable Django app package.

**Performance Goals**: none specific to this slice (large-vocabulary scale is roadmap G5/R-later).
Member reads are FK-scoped and index-backed (`(collection, position)`); no traversal.

**Constraints**: held-once membership must be a DB constraint; ordered reads and mid-list removal must
not leave a read-breaking gap (ordering by `position` makes gaps harmless — no compaction needed);
scheme-confinement and any refusal must carry translatable named-placeholder messages and hold on the
`add()`/factory path, not only `full_clean()`; membership must not touch a concept's `slug`/`uri` or its
relations.

**Scale/Scope**: two new models, a small `Collection` helper API, `Concept.collections()`, one
migration, factories, tests. No UI.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 design (unchanged).*

- **I Test-First** — tasks order the failing test before its implementation per story. Pass.
- **II Simplicity** — two ordinary models with FKs, one boolean, one integer `position`; integrity is a
  DB unique constraint plus a small `clean()`/`save()` scheme check; ordering is a plain integer field
  and an `ORDER BY`, no library, no graph machinery (research R5). Pass.
- **III Anti-Abstraction** — an explicit `CollectionMember` through model (it carries `position`) and
  explicit `Collection` helpers rather than a bare `ManyToManyField` whose descriptor cannot express
  ordered membership or the scheme check; no base classes/wrappers. Pass.
- **IV Integration-First** — the ORM surface is the contract (`contracts/python-api.md`); acceptance
  tests drive it exactly as a downstream developer would. Pass.
- **V Security & data-safety** — no rendered output, no secrets, no imported RDF this slice; validation
  uses the framework's `ValidationError`/`gettext_lazy`, never hand-built interpolation. Pass.
- **VI Documentation** — new public API (`Collection`, `CollectionMember`, the helpers): README scope
  note + CHANGELOG entry + docstrings ship in this PR (T-Polish). Pass.
- **VII Dependency discipline** — **no runtime dependency added**; the candidate ordering library is
  rejected on maintenance/compat grounds (research R5, Complexity Tracking); factories are test-only;
  `deptry` stays green. Pass.
- **VIII Compatibility (dual contract)** — pre-1.0; the Python API is additive (two new models, new
  helpers), no existing surface changed. The RDF/URI data contract is untouched (collections are not
  serialized here); the collection URI is composed under a `/collection/` segment so it can never
  collide with a concept URI when projection lands (research R4). Pass.
- **IX URI identity & downstream-data safety** — honoured: adding/removing membership never touches a
  concept's `slug`/`uri` (tested). `CollectionMember` FKs use `CASCADE` because a membership is not
  consumer data and is meaningless without both endpoints — identical to #17's edge reasoning; Article
  IX's `PROTECT`/deprecation governs *consumer references* and concept *retirement* (#19), which this
  slice does not touch (data-model.md). A collection carries a stable derived `slug`/`uri` like a scheme
  or concept. Pass.
- **X Stack & architecture** — Django 5.2+/Py 3.11 floor; models are the source of truth; SKOS-only
  (`Collection` is `skos:Collection`, ordered is `skos:OrderedCollection`); no triplestore. Pass.
- **XI RDF fidelity** — no import/export this slice; the model is shaped so the later export map is a
  straight lookup (`ordered` → `skos:OrderedCollection` + `skos:memberList`; unordered → `skos:member`).
  Deferred, recorded. N/A now.
- **XII Internationalization** — every new field carries translatable `verbose_name` + `help_text`; the
  new validation messages (cross-vocabulary member, and the not-ordered guard on `set_member_order`) are
  `gettext_lazy` with named placeholders; asserted by the standards test (US-5). Pass.
- **XIII Data-model conventions** — indexing deliberate: `UniqueConstraint(collection, concept)` gives
  the collection-leading membership index and enforces held-once (FR-004); `Index(collection, position)`
  backs ordered reads; the `concept` FK auto-index covers the reverse `Concept.collections()` read;
  `Collection` gets `UniqueConstraint(scheme, slug)` like `Concept`. Recorded in data-model. Migration
  squashed at convergence. Pass.

**One item requires Complexity Tracking** — the decision to hand-roll ordering rather than take the
suggested dependency (see below). It is a *rejection* of added complexity, recorded for the gate.

## Project Structure

### Documentation (this feature)

```text
specs/004-collections-group-concepts/
├── spec.md              # approved at the Spec gate
├── plan.md              # this file
├── research.md          # Phase 0 — models, ordering choice, integrity, URI namespacing, API shape
├── data-model.md        # Phase 1 — Collection, CollectionMember, constraints, helpers
├── contracts/
│   └── python-api.md     # Phase 1 — the public ORM contract
├── quickstart.md        # Phase 1 — runnable validation scenarios
├── decisions.md         # self-resolved ambiguities + deferrals (from S1, extended at S3)
└── tasks.md             # Phase 2 (S3 tasks command) — the task graph
```

### Source Code (repository root)

```text
controlled_vocabularies/
├── models.py            # +Collection, +CollectionMember; +Concept.collections()
└── migrations/
    └── 000X_*.py         # generated; squashed to one at convergence

tests/
├── factories.py          # +CollectionFactory, +CollectionMemberFactory (+ ordered trait/helper)
├── test_models.py        # US-1..US-3: grouping, ordering, integrity (class-grouped)
├── test_factories.py     # US-4: collection factory output
└── test_standards.py     # US-5: metadata i18n + indexing over the new models
```

**Structure Decision**: single reusable-app layout, unchanged from #15/#16/#17. The two new models join
the existing `models.py` (small models do not warrant a `models/` package — Anti-Abstraction). Tests
mirror the source tree; the existing `test_standards.py` field-walk automatically reaches the new
models.

## Complexity Tracking

| Decision | Why it is the simpler choice | Alternative rejected, and why |
|---|---|---|
| **Hand-rolled `position` integer for ordering** (no `django-ordered-model` or other ordering lib) | The ordered read is `ORDER BY position`; removing a member leaves survivors' relative order intact with no compaction, because gaps in an ordered read are harmless. The whole ordering surface is one `PositiveIntegerField`, an `add` that appends, and a `set_member_order` that reassigns positions — a fraction of the integrity logic #17 already hand-rolls. Owning ~30 lines keeps the dependency tree clean and the package's longevity in our hands. | **`django-ordered-model`** (Sam's suggested candidate): last release March 2023, test matrix tops out at Django 5.1 — no 5.2 LTS or 6.0 support, which this repo's CI *requires* (Article X, the seven checks). Taking an unmaintained dep for a core domain model contradicts Article VII and the package's evolve-for-years mandate (Article VIII). Evaluated and rejected (research R5); the small hand-rolled field carries no such risk. |

No other constitution violations. The deliberate omissions (nested collections, RDF projection,
admin/editor UI, lifecycle-driven removal) are scope boundaries recorded in the spec Assumptions and
`decisions.md`, each tied to a stated reason — not shortcuts.
