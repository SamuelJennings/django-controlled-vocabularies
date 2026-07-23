# Implementation Plan: Represent a vocabulary and its concepts

**Branch**: `001-vocabulary-concepts` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-vocabulary-concepts/spec.md`

## Summary

Two Django models — `ConceptScheme` (a vocabulary) and `Concept` (a term within one) — with a stable identity mechanism: each carries a slug derived from its name/label, and each concept exposes a URI composed from a configured base address, its scheme's slug, and its own slug. Identity is the URI, never the primary key; the URI is computed (not stored) because in this slice every vocabulary is unpublished and slugs track their source text. All interaction is programmatic (ORM); tests cover identity and uniqueness, and test factories are shipped for the sibling features that follow.

## Technical Context

**Language/Version**: Python 3.11+ (package floor); tested on 3.12 and 3.13
**Primary Dependencies**: Django 5.2 LTS + 6.0 (no new runtime dependency — `rdflib`/`django-parler` are not needed until import/multilingual features)
**Storage**: the host project's relational database via the Django ORM; migrations shipped with the app
**Testing**: `pytest` + `pytest-django` (from `mvp-shared[test]`); `factory_boy` for factories
**Target Platform**: an installable Django app (also runnable standalone)
**Project Type**: single project — a reusable Django app package
**Performance Goals**: none specific to this slice (large-vocabulary scale is roadmap R7)
**Constraints**: slug/URI composition must be deterministic and handle non-ASCII input; no user-facing rendering surface in this slice
**Scale/Scope**: two models, one migration, one settings hook, factories, tests

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 design (unchanged).*

- **I Test-First** — tasks are ordered tests-before-implementation per story; the Implementer writes each failing test before its code. Pass.
- **II Simplicity** — two models, a computed property, one settings read. No JSON document, no predicate registry, no `django-parler`, no `rdflib`. Pass.
- **III Anti-Abstraction** — concrete models, no base classes or wrapper layers; a shared slug helper only if two call sites genuinely need it. Pass.
- **IV Integration-First** — the ORM surface *is* the contract (`contracts/python-api.md`); acceptance tests exercise it exactly as a downstream developer would. Pass.
- **V Security & data-safety** — slug/URI built through Django's `slugify`, not hand-rolled string work; no secrets; no rendered output; no imported RDF in this slice. Pass.
- **VI Documentation** — new public API, so README (Scope note already present) + CHANGELOG entry + docstrings ship in this PR. Task included. Pass.
- **VII Dependency discipline** — no runtime dependency added (declaring `rdflib`/`parler` now would fail `deptry` as unused). `factory_boy` is test-only; confirm it is in `mvp-shared[test]`, else add it with the US-4 justification. Pass, pending that confirmation (Phase 0 research item).
- **VIII Compatibility (dual contract)** — pre-1.0: the URI shape (`base / scheme-slug / concept-slug`) is the data-contract seed but is not frozen until 1.0. Recorded, not silent. Pass.
- **IX URI identity & data-safety** — honoured now: identity is the URI, never the PK; lookups resolve by URI. **Deferred by design (Sam's grilling ruling, in `decisions.md`):** the lifecycle/deprecation/`PROTECT`/upsert-by-URI mechanisms — those belong to sibling #19 and the import feature, which are the first features with references to protect. No import and no external references exist in this slice, so the invariants have no surface here yet. Not an unjustified violation.
- **X Stack & architecture** — Django 5.2+/Py 3.11 floor, Poetry, ruff; models are the source of truth; SKOS-only, no non-SKOS modelling. Pass.
- **XI RDF fidelity** — no import/export in this slice; deferred to the boundary features. N/A.

No violations require Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-vocabulary-concepts/
├── spec.md              # approved at the Spec gate
├── plan.md              # this file
├── research.md          # Phase 0 — decisions + rationale
├── data-model.md        # Phase 1 — entities, fields, rules
├── contracts/
│   └── python-api.md     # Phase 1 — the public ORM contract
├── quickstart.md        # Phase 1 — runnable validation scenarios
├── decisions.md         # self-resolved ambiguities + deferred register (from S1)
└── tasks.md             # Phase 2 (S3 tasks command) — the task graph
```

### Source Code (repository root)

```text
controlled_vocabularies/
├── __init__.py
├── apps.py
├── models.py            # ConceptScheme, Concept (new)
├── conf.py              # base-URI settings read (new; thin, no framework)
└── migrations/
    └── 0001_initial.py  # generated

tests/
├── settings.py          # add controlled_vocabularies base-URI setting
├── conftest.py
├── factories.py         # SchemeFactory, ConceptFactory (new — US-4)
├── test_scheme.py       # US-1
├── test_concept.py      # US-2
└── test_identity.py     # US-3
```

**Structure Decision**: single reusable-app layout, matching the existing `controlled_vocabularies/` package and root `tests/`. Models live in one `models.py` (two small models don't warrant a `models/` package — Anti-Abstraction). A thin `conf.py` reads the base-URI setting with a default, so the composition rule has one home without a settings framework.

## Complexity Tracking

No constitution violations to justify. The one deliberate deferral (Article IX lifecycle mechanisms → #19) is recorded in `decisions.md` and the Constitution Check above, not because it is a shortcut but because the mechanisms protect references that do not exist until later features introduce them.
