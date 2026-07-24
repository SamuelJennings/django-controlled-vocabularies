# Implementation Plan: Multilingual names and descriptions for concepts

**Branch**: `002-multilingual-concepts` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-multilingual-concepts/spec.md`

## Summary

Grow a concept from #15's single default-language label into a full per-language lexical and
descriptive model, without disturbing the URI identity #15 established. Storage is relational: the
default-language preferred label stays a field on `Concept` (the identity anchor), while other
languages' preferred labels and all alternative/hidden labels live in a `ConceptLabel` child model,
and definitions plus the SKOS documentary notes live in a `ConceptNote` child model — each a row per
(concept, language, kind, value). One preferred label per language is a partial unique constraint; a
concept's slug derives from the default-language label unless explicitly pinned. `ConceptScheme`
gains an overridable `default_language`. No new runtime dependency; django-parler and the JSON
document/predicate-registry model are deliberately deferred to the import (R2) and editor (R5)
features that consume them (see `research.md` R1). Interaction is programmatic; tests cover per-
language storage, the one-preferred-per-language rule, identity stability under multilingual edits,
and the slug-override behaviour, with multilingual factories for later features.

## Technical Context

**Language/Version**: package runtime floor Python 3.11 (constitution Art. X); dev/test toolchain (`mvp-shared[test]`) needs 3.12+, so CI exercises 3.12/3.13 (unchanged from #15).

**Primary Dependencies**: Django 5.2 LTS + 6.0. **No new runtime dependency** — `django-parler`/`rdflib` remain undeclared (deptry fails an unused dep; this slice imports neither — `research.md` R1/R7).

**Storage**: host project's relational database via the Django ORM; two extended models + two new child models; one migration (squashed at convergence).

**Testing**: `pytest` + `pytest-django`; `factory_boy` factories, mirroring the source tree per the family testing standard (`tests/factories.py`, `tests/test_models.py`).

**Target Platform**: an installable Django app (also runnable standalone).

**Project Type**: single project — a reusable Django app package.

**Performance Goals**: none specific to this slice (large-vocabulary scale is roadmap R7). Label reads are FK-scoped and indexed.

**Constraints**: identity (`slug`/`uri`) must be provably stable under any non-default-language edit; one preferred label per language; slug derivation deterministic and Unicode-safe (inherited from #15).

**Scale/Scope**: two extended models, two new models, one migration, field-and-helper additions, factories, tests. No UI.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 design (unchanged).*

- **I Test-First** — tasks ordered tests-before-implementation per story; each failing test written before its code. Pass.
- **II Simplicity** — relational rows with ordinary Django constraints; no JSON document, no predicate registry, no parler. The one-preferred-per-language rule is a partial `UniqueConstraint`, not application logic. Pass. (The rejected heavier design is tracked in `research.md` R1, not `Complexity Tracking`, because the simpler design is the one chosen.)
- **III Anti-Abstraction** — one `ConceptNote` typed by `kind` rather than seven note models/fields; the identity anchor stays a plain field, not a translation framework. No base classes or wrappers. Pass.
- **IV Integration-First** — the ORM surface is the contract (`contracts/python-api.md`); acceptance tests exercise it exactly as a downstream developer would (create a concept, add labels/notes per language, read them back). Pass.
- **V Security & data-safety** — slugs via Django `slugify`; language values validated against `settings.LANGUAGES`; no secrets, no rendered output, no imported RDF this slice. Pass.
- **VI Documentation** — new public API (per-language labels/notes, overridable slug, scheme default language): README scope note + CHANGELOG entry + docstrings ship in this PR. Task included. Pass.
- **VII Dependency discipline** — no runtime dependency added (`research.md` R7); factories are test-only. Pass.
- **VIII Compatibility (dual contract)** — pre-1.0: the label/note storage shape and the relational→document deferral are recorded, not silent (`research.md` R1). The URI shape is unchanged from #15. No frozen contract broken. Pass.
- **IX URI identity & downstream-data safety** — honoured and strengthened: FR-004/SC-003 make identity stability under multilingual edits an explicit, tested invariant. Lifecycle/`PROTECT`/upsert remain deferred to #19/import (no references exist yet), as in #15. Pass.
- **X Stack & architecture** — Django 5.2+/Py 3.11 floor; models are the source of truth; SKOS-only; relational storage, no non-SKOS modelling. Pass.
- **XI RDF fidelity** — no import/export this slice; the label/note `kind` choices are named for their SKOS predicates so the later export map is a straight lookup. Deferred, recorded. N/A now.
- **XII Internationalization** — every new field carries translatable `verbose_name` + `help_text`; new validation messages (duplicate preferred label, missing default-language label) are `gettext_lazy` with named placeholders; asserted by the standards test (US-7). Pass.
- **XIII Data-model conventions** — indexing deliberate: `ConceptLabel(language, kind, text)` indexed for label search, FK auto-indexes, partial unique for one-preferred-per-language; `ConceptNote.value` unindexed by recorded decision (no lookup path this slice). Pass.

**No violations require Complexity Tracking.** The relational-vs-document choice is a deferral recorded in `research.md` R1 and surfaced at the Plan gate, not an unjustified shortcut.

## Project Structure

### Documentation (this feature)

```text
specs/002-multilingual-concepts/
├── spec.md              # approved at the Spec gate
├── plan.md              # this file
├── research.md          # Phase 0 — storage + design decisions
├── data-model.md        # Phase 1 — models, fields, rules
├── contracts/
│   └── python-api.md     # Phase 1 — the public ORM contract
├── quickstart.md        # Phase 1 — runnable validation scenarios
├── decisions.md         # self-resolved ambiguities + deferrals (from S1)
└── tasks.md             # Phase 2 (S3 tasks command) — the task graph
```

### Source Code (repository root)

```text
controlled_vocabularies/
├── models.py            # ConceptScheme (+default_language), Concept (+slug_is_manual, label
│                        #   clarified, read helpers), ConceptLabel (new), ConceptNote (new)
└── migrations/
    └── 000X_*.py         # generated; squashed to one at convergence

tests/
├── conftest.py          # fixtures (multi-language settings for the suite)
├── factories.py         # +ConceptLabelFactory, +ConceptNoteFactory, multilingual ConceptFactory traits
├── settings.py          # ensure LANGUAGES has >=2 entries + a LANGUAGE_CODE for deterministic tests
├── test_models.py       # per-language labels/notes, one-preferred rule, identity stability, slug override, scheme default language
├── test_factories.py    # multilingual factory output
└── test_standards.py    # metadata i18n + indexing over the new fields (US-7)
```

**Structure Decision**: single reusable-app layout, unchanged from #15. New models join the existing
`models.py` (four small models don't warrant a `models/` package — Anti-Abstraction). Tests mirror
the source tree per the family testing standard; `test_standards.py` is reinstated to walk the new
fields (it existed pre-align-tests and the metadata standard still applies).

## Complexity Tracking

No constitution violations to justify. The deliberate deferral (django-parler + JSON document +
predicate registry → the import/editor features that consume them) is recorded in `research.md` R1
and the Constitution Check above — a scope boundary, not a shortcut.
