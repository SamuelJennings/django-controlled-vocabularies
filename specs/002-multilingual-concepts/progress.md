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
