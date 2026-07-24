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

## 2026-07-24 · Implementer US-2 · T005

- **Did**: Added the US-2 failing tests to `tests/test_models.py` — `TestConceptAlternativeAndHiddenLabels`
  (two `en` + one `de` alternative → `alt_labels("en")` returns the two English texts only; hidden
  labels stored/read per language and held separately from alternatives, neither reader bleeding into
  the other; an absent language reads an empty list; slug+URI unchanged across an alt/hidden label's
  add→edit→remove in both the default and a non-default language).
- **Verified**: `poetry run pytest tests/test_models.py::TestConceptAlternativeAndHiddenLabels -q` →
  4 failed with `AttributeError: 'Concept' object has no attribute 'alt_labels'/'hidden_labels'` — red
  for the right reason (readers not yet built). `poetry run ruff check tests/test_models.py` +
  `format --check` clean.
- **Next**: T006 — add `alt_labels`/`hidden_labels`; confirm `add_label` spans alt/hidden kinds.
- **Watch**: none.

## 2026-07-24 · Implementer US-2 · T006

- **Did**: In `controlled_vocabularies/models.py` — added `Concept.alt_labels(language)` and
  `Concept.hidden_labels(language)` (each returns the matching `ConceptLabel` texts, ordered as the
  model orders labels, empty list when none); clarified `add_label`'s docstring — it already routes
  every `Kind` through `full_clean()`, and alt/hidden simply carry no uniqueness to trip, so no code
  change was needed there. Corrected a wrong expected sort order in the T005 hidden-labels test
  (`"heatflow"` sorts before `"heet flow"`) — see decisions.md §15.
- **Verified**: `poetry run pytest -q` → **65 passed**; `poetry run ruff check .` clean;
  `poetry run ruff format --check .` → 11 files already formatted; `poetry run mypy` → no issues;
  `poetry run deptry .` → no dependency issues.
- **Next**: T007 — confirm no migration drift; US-2 green.
- **Watch**: `alt_labels`/`hidden_labels` return `list[str]` (texts), not row objects, mirroring the
  read-by-language contract; callers wanting rows use `concept.labels.filter(...)`.

## 2026-07-24 · Implementer US-2 · T007

- **Did**: No migration generated — `Kind` already baked PREFERRED/ALTERNATIVE/HIDDEN in US-1's
  `0002` migration (decisions.md §14), and US-2 added no fields, so there is no schema drift. Verified
  rather than authored, per the task's "only add a migration if Django reports drift".
- **Verified**: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  --check --dry-run` → "No changes detected"; `poetry run pytest -q` → **65 passed**;
  `poetry run ruff check .` clean; `poetry run ruff format --check .` → 11 files already formatted;
  `poetry run mypy` → no issues; `poetry run deptry .` → no dependency issues.
- **Next**: US-2 complete; US-3 (notes) builds on `Concept`.
- **Watch**: none.

## 2026-07-24 · Implementer US-3 · T008

- **Did**: Added the US-3 failing tests to `tests/test_models.py` — `TestConceptDefinitionsAndNotes`
  (en+de definitions read back by language; each documentary note kind scope/example/editorial/
  history/change/note stored under its own kind and read per language and kind; `notes(language)`
  with no kind returns every value for that language; repeated notes of a kind allowed; slug+URI
  unchanged across a note's add→edit→remove, exercised in the default language to prove even a
  default-language note leaves identity alone). Kinds passed as plain choice values (`"definition"`,
  `"scope"`, …) so the module stays importable while `ConceptNote` is unbuilt.
- **Verified**: `poetry run pytest tests/test_models.py::TestConceptDefinitionsAndNotes -q` →
  6 failed with `AttributeError: 'Concept' object has no attribute 'add_note'` / `definition` — red
  for the right reason (the US-3 API is not yet built), and the 65 prior tests stay green because the
  module still imports. `poetry run ruff check` + `format --check` on the test file clean.
- **Next**: T009 — add `ConceptNote`, `Concept.definition`/`notes`/`add_note`.
- **Watch**: kinds are passed as choice-value strings, not a `ConceptNote.Kind` enum, deliberately
  (decisions.md §18) — the enum import would fail collection and blank the red signal.

## 2026-07-24 · Implementer US-3 · T009

- **Did**: In `controlled_vocabularies/models.py` — added the `ConceptNote` model (FK
  `related_name="concept_notes"`, `language` `choices=settings.LANGUAGES`, `kind` `TextChoices`
  DEFINITION/SCOPE/EXAMPLE/EDITORIAL/HISTORY/CHANGE/NOTE with logical-name values, `value` `TextField`,
  no uniqueness, `Meta.ordering=("language","kind")`); a module-level `SKOS_CURIE` map from each kind to
  its SKOS predicate CURIE (decisions.md §19); and `Concept.definition(language)` (first definition
  value or `None`), `Concept.notes(language, kind=None)` (all values, optionally one kind), and
  `Concept.add_note(language, kind, value)` (validates via `full_clean`, decisions.md §21). All new
  fields carry lazy `verbose_name` + non-empty `help_text`; `value` is left deliberately unindexed
  (decisions.md §20).
- **Verified**: `poetry run pytest tests/test_models.py::TestConceptDefinitionsAndNotes -q` →
  **6 passed** (was 6 failed at T008); `poetry run ruff check controlled_vocabularies/models.py` +
  `format` clean. (Migration `0003_conceptnote.py` was generated so the DB tests run; it is committed
  in T010.)
- **Next**: T010 — commit the migration, confirm no drift, run the full verify gate.
- **Watch**: `notes(language)` with `kind=None` spans every kind (definition included); `definition`
  is just the DEFINITION-kind reader narrowed to the first row.

## 2026-07-24 · Implementer US-3 · T010

- **Did**: Committed the US-3 migration `controlled_vocabularies/migrations/0003_conceptnote.py`
  (`makemigrations controlled_vocabularies` — creates `ConceptNote`; `value` a plain `TextField` with
  no `db_index`, FK auto-indexed, no uniqueness). A new migration is expected here (unlike US-2) because
  US-3 adds a whole model. Choices bake the deterministic test `LANGUAGES` (T001); the branch's
  migrations are squashed to one at convergence (S5).
- **Verified** (full gate, in the worktree via poetry):
  1. `poetry run pytest -q` → **71 passed** (65 prior + 6 US-3).
  2. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check
     --dry-run` → **No changes detected**.
  3. `poetry run ruff check .` → **All checks passed!**
  4. `poetry run ruff format --check .` → **11 files already formatted**.
  5. `poetry run mypy` → **Success: no issues found in 4 source files**.
  6. `poetry run deptry .` → **Success! No dependency issues found**.
- **Next**: US-3 complete. US-4 (per-vocabulary default language) and US-5 (overridable slug) build on
  `Concept`; US-6 factories build on `ConceptNote`.
- **Watch**: none.

## 2026-07-24 · Implementer US-4 · T011

- **Did**: Added the US-4 failing tests to `tests/test_models.py` —
  `TestConceptSchemePerVocabularyDefaultLanguage` (a scheme with no override carries an empty
  `default_language` and anchors identity in the app default — slug from the English `label`; a scheme
  overridden to `de` makes `Concept.label` the German preferred label so the slug derives from it,
  while the English preferred label is an additive `ConceptLabel` row; `effective_default_language`
  returns the override when set, else `settings.LANGUAGE_CODE`).
- **Verified**: `poetry run pytest tests/test_models.py::TestConceptSchemePerVocabularyDefaultLanguage
  -q` → **3 failed** — `AttributeError` reading `scheme.default_language` and `TypeError` passing
  `default_language=` to `create()`; red for the right reason (the override field is unbuilt). The
  module still imports, so the prior **71 tests stay green** (`3 failed, 71 passed`). See decisions.md §24.
- **Next**: T012 — add `ConceptScheme.default_language`; extend `effective_default_language`.
- **Watch**: none.

## 2026-07-24 · Implementer US-4 · T012

- **Did**: In `controlled_vocabularies/models.py` — added `ConceptScheme.default_language`
  (`CharField(max_length=16, blank=True, choices=settings.LANGUAGES)` with lazy `verbose_name`
  "default language" + non-empty `help_text`); extended `effective_default_language` to
  `self.default_language or settings.LANGUAGE_CODE` (decisions.md §22).
- **Verified**: `poetry run pytest tests/test_models.py::TestConceptSchemePerVocabularyDefaultLanguage
  -q` → **3 passed** (was 3 failed at T011); `poetry run ruff check controlled_vocabularies/models.py`
  + `format --check` clean; `poetry run mypy` → no issues. (Migration `0004` was generated so the DB
  tests run; it is committed in T013.)
- **Next**: T013 — commit the migration, confirm no drift, run the full verify gate.
- **Watch**: the US-1 `TestConceptSchemeDefaultLanguage` (unsaved `ConceptScheme()`, no override) still
  passes because the field default is `""` (falsy → falls back to the app default).

## 2026-07-24 · Implementer US-4 · T013

- **Did**: Committed the US-4 migration
  `controlled_vocabularies/migrations/0004_conceptscheme_default_language.py`
  (`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  controlled_vocabularies` — adds `default_language` to `ConceptScheme`). A new migration is expected
  here (a genuine field-add, unlike US-2's no-migration — decisions.md §23); choices bake the
  deterministic test `LANGUAGES` (T001); the branch's migrations are squashed to one at convergence (S5).
- **Verified** (full gate, in the worktree via poetry):
  1. `poetry run pytest -q` → **74 passed** (71 prior + 3 US-4).
  2. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check
     --dry-run` → **No changes detected**.
  3. `poetry run ruff check .` → **All checks passed!**
  4. `poetry run ruff format --check .` → **11 files already formatted**.
  5. `poetry run mypy` → **Success: no issues found in 4 source files**.
  6. `poetry run deptry .` → **Success! No dependency issues found**.
- **Next**: US-4 complete. US-5 (overridable slug) builds on `Concept`; US-6 factories build on the
  full label/note model.
- **Watch**: none.

## 2026-07-24 · Implementer US-5 · T014–T016

- **Did**: Overridable concept slug (model layer). T014 (RED): added
  `TestConceptOverridableSlug` (4 tests) to `tests/test_models.py` covering FR-010/FR-012 —
  explicit slug exactly the value set, explicit slug survives a default-language relabel, no-override
  slug still derives from the label (as #15), explicit slug colliding within scheme refused; they
  failed on the missing `set_slug`/`slug_is_manual` (`AttributeError`), module still imports, prior 74
  green (decisions.md §28). T015 (GREEN): added `Concept.slug_is_manual`
  (`BooleanField(default=False)`, lazy `verbose_name` "slug set manually" + non-empty `help_text`);
  `save()` re-derives `slug` from `label` only when not manual; `set_slug(value)` sets the value
  verbatim + flags manual + saves; within-scheme uniqueness enforced for both derived and explicit
  slugs; empty-slug guard splits by provenance — `label` for auto, `slug` for manual
  (decisions.md §25–§27). T016: committed migration `0005_concept_slug_is_manual` (genuine field-add,
  default `False` → existing concepts stay auto-derived; branch migrations squash at S5).
- **Verified** (full gate, in the worktree via poetry):
  1. `poetry run pytest -q` → **78 passed** (74 prior + 4 US-5).
  2. `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin makemigrations --check --dry-run`
     → **No changes detected**.
  3. `poetry run ruff check .` → **All checks passed!**
  4. `poetry run ruff format --check .` → **11 files already formatted**.
  5. `poetry run mypy` → **Success: no issues found in 4 source files**.
  6. `poetry run deptry .` → **Success! No dependency issues found**.
- **Next**: US-5 complete. US-6 (factories) and US-7 build on the full label/note/slug model.
- **Watch**: `set_slug` stores the value verbatim (no `slugify`) so R2 import can later carry source
  slugs unchanged — the caller owns URL-safety; the model only guarantees non-empty + unique.
