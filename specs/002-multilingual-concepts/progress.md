# Progress log — 002-multilingual-concepts (FS-002, issue #16)

Chronological run log. The ledger (`feature-state.json`) is the machine source of truth; this is the
human narrative.

## 2026-07-24

- **S0 INTAKE** — grilled to shared understanding. Four decisions ruled by Sam: identity anchors to
  the default-language preferred label (supersedes #15's single-label decision); default language is
  app-wide with a per-vocabulary override; the concept slug is overridable; descriptions carry the
  full SKOS documentary note family. Label swapped `feature-request` → `feature`.
- **S1 SPECIFY** — authored `spec.md` (7 user stories, 15 FR, 8 SC) + `decisions.md`. Spec-lint
  green (no unresolved markers, G6 cited, every story has acceptance scenarios).
- **S2 SETUP** — promoted #16 to epic `FS-002`; created story sub-issues #28–#34; pushed the branch;
  opened draft PR #35 (bot-authored, `Closes` block for epic + all stories, milestone v0.1.0). Title
  lint green.
- **GATE_SPEC** — approved by Sam in-session. Sam added a standing convention: when a later feature
  supersedes an earlier landed spec's decision, annotate the old spec in place (strikethrough +
  forward "Superseded by" tag), landing in the superseding PR. Adopted; task T021 carries it.
- **S3 PLAN** — authored `plan.md`, `research.md`, `data-model.md`, `contracts/python-api.md`,
  `quickstart.md`, `tasks.md` (T001–T022). Key planning decision (research R1): relational child
  models `ConceptLabel`/`ConceptNote`, not django-parler + JSON document/registry — deferred to the
  import (R2) and editor (R5) features that consume them. Identity anchor stays a field on `Concept`
  (research R2). Constitution Check: all 13 articles pass, no Complexity Tracking needed. `analyze`:
  clean, no CRITICAL. Ledger created (schema-valid). Following #15's precedent, tasks live in the
  ledger + `tasks.md`, not as GitHub task sub-issues.
- **GATE_PLAN** — awaiting Sam.

## 2026-07-24 · Implementer US-1 · T002

- **Did**: Added the US-1 failing tests to `tests/test_models.py` — `TestConceptSchemeDefaultLanguage`
  (effective default = app `LANGUAGE_CODE`) and `TestConceptPreferredLabels` (en+de preferred labels
  read back by language; slug derived from the default-language label; second preferred in a language
  refused; missing default-language label refused; a PREFERRED row in the default language refused;
  slug+URI unchanged across a non-default label's add→edit→remove; absent language → `None`).
- **Verified**: `poetry run pytest tests/test_models.py -q` → collection ERROR
  (`ImportError: cannot import name 'ConceptLabel'`) — red for the right reason (API not yet built).
- **Next**: T003 — implement `ConceptLabel`, `effective_default_language`, `preferred_label`, `add_label`.
- **Watch**: none.

## 2026-07-24 · Implementer US-1 · T003

- **Did**: In `controlled_vocabularies/models.py` — added `ConceptScheme.effective_default_language`
  (returns `settings.LANGUAGE_CODE`; the per-scheme override is US-4, no field added here); clarified
  `Concept.label` help_text (identity anchor in the effective default language); added
  `Concept.preferred_label(language=None)` and `Concept.add_label(language, kind, text)`; added the
  new `ConceptLabel` model (FK `related_name="labels"`, `language`/`kind`/`text`, `Kind` TextChoices
  PREFERRED/ALTERNATIVE/HIDDEN, partial `UniqueConstraint` `one_preferred_label_per_language`, and a
  `clean()` rejecting a PREFERRED row in the effective default language). All new fields carry lazy
  `verbose_name` + non-empty `help_text`; validation messages use named placeholders.
- **Verified**: `poetry run pytest tests/test_models.py -q` → 52 passed (the 8 new US-1 tests green);
  `poetry run ruff check .` clean; `poetry run ruff format --check .` clean; `poetry run mypy` clean.
  (Table exists because the T004 migration was generated to run the DB tests.)
- **Next**: T004 — commit the migration and run the full verify suite.
- **Watch**: `add_label` validates via `full_clean()` — the duplicate-preferred refusal rides on
  `validate_constraints()` (partial UniqueConstraint), the default-language refusal on `clean()`.

## 2026-07-24 · Implementer US-1 · T004

- **Did**: Generated the migration
  `controlled_vocabularies/migrations/0002_alter_concept_label_conceptlabel.py`
  (`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  controlled_vocabularies`) — alters `Concept.label` help_text and creates `ConceptLabel`. Choices bake
  the deterministic test `LANGUAGES` (T001); the branch's migrations are squashed to one at convergence.
- **Verified**: `poetry run python -m django makemigrations --check --dry-run` → no changes;
  `poetry run pytest -q` → **61 passed**; `poetry run ruff check .` clean; `poetry run ruff format
  --check .` → 11 files already formatted; `poetry run mypy` → no issues; `poetry run deptry .` → no
  dependency issues.
- **Next**: US-1 complete; US-2 (alt/hidden labels) and US-3 (notes) build on `ConceptLabel`.
- **Watch**: none.
