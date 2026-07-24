# Tasks: Multilingual names and descriptions for concepts

**Input**: design docs in `specs/002-multilingual-concepts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md
**Tests**: requested — SC-008 requires every FR exercised by a test; test-first per Article I.

Format: `[ID] [P?] [Story] Description`. `[P]` = different files, no dependency. Paths are exact.
Model tests land in `tests/test_models.py` (class-grouped, mirroring the single `models.py`), so
same-file tasks are **not** `[P]`. Stories are implemented sequentially in dependency order
(Phase 1 pipeline), which also avoids migration-merge friction on the shared `models.py`.

## Phase 1: Setup

- [ ] T001 [Setup] In `tests/settings.py` ensure `LANGUAGE_CODE = "en"` and `LANGUAGES` contains at least `("en", …), ("de", …), ("fr", …)` so per-language behaviour is deterministic; add any needed `tests/conftest.py` fixture. (`factory_boy` already ships in `mvp-shared[test]`.)

## Phase 2: User Story 1 — Preferred labels per language, identity preserved (P1) 🎯 MVP

**Goal**: one preferred label per language; the default-language one is the required anchor; other languages never move identity. Serves the whole of G6's minimum.
**Independent test**: the US-1 classes in `tests/test_models.py` green in isolation.
**Depends on**: #15 (`Concept`, `ConceptScheme`).

- [ ] T002 [US1] Write failing tests in `tests/test_models.py`: en+de preferred labels readable via `preferred_label(lang)`; slug derived from the default-language `label`; a second preferred label in a language already having one raises `ValidationError`; saving a concept with no default-language `label` raises `ValidationError`; a `ConceptLabel` PREFERRED row in the scheme's effective default language raises `ValidationError`; `concept.uri`/`concept.slug` unchanged when a non-default preferred label is added, edited, or removed; `effective_default_language == settings.LANGUAGE_CODE` when no override.
- [ ] T003 [US1] In `controlled_vocabularies/models.py`: clarify `Concept.label` (verbose_name/help_text) as the preferred label in the scheme's effective default language; add `ConceptScheme.effective_default_language` property returning `settings.LANGUAGE_CODE` (override added in US-4); add `ConceptLabel` model (`concept` FK `related_name="labels"`, `language` `choices=settings.LANGUAGES`, `kind` choices with `PREFERRED`, `text`) with `UniqueConstraint(concept, language) WHERE kind=PREFERRED` and a `clean()` rejecting a PREFERRED row in the effective default language; add `Concept.preferred_label(language=None)` and `add_label(language, kind, text)` (preferred path) plus the missing-default-label validation.
- [ ] T004 [US1] `poetry run python -m django makemigrations controlled_vocabularies`; US-1 tests green in isolation.

**Checkpoint**: multilingual preferred labels work; identity provably stable under non-default edits.

## Phase 3: User Story 2 — Alternative and hidden labels per language (P2)

**Goal**: any number of alt/hidden labels per language, held separately, never moving identity.
**Independent test**: the US-2 classes in `tests/test_models.py` green.
**Depends on**: US-1 (`ConceptLabel`).

- [ ] T005 [US2] Write failing tests in `tests/test_models.py`: two `en` + one `de` alternative → `alt_labels("en")` returns both English only; hidden labels stored/read per language and separate from alternatives; adding/changing/removing alt or hidden labels leaves `uri`/`slug` unchanged.
- [ ] T006 [US2] Extend `ConceptLabel.kind` with `ALTERNATIVE` and `HIDDEN`; add `Concept.alt_labels(language)` / `hidden_labels(language)`; extend `add_label` for those kinds (no uniqueness).
- [ ] T007 [US2] `makemigrations` (choices change); US-2 tests green.

**Checkpoint**: full lexical model (pref/alt/hidden) per language.

## Phase 4: User Story 3 — Definitions and documentary notes per language (P2)

**Goal**: a definition plus the six SKOS documentary notes, per language, repeatable.
**Independent test**: the US-3 classes in `tests/test_models.py` green.
**Depends on**: US-1 (`Concept`).

- [ ] T008 [US3] Write failing tests in `tests/test_models.py`: en+de definitions readable by language; each documentary note kind (scope/example/editorial/history/change/note) stored under its kind and read per language; repeated notes of a kind allowed; adding/changing/removing notes leaves `uri`/`slug` unchanged.
- [ ] T009 [US3] Add `ConceptNote` model (`concept` FK `related_name="concept_notes"`, `language` `choices=settings.LANGUAGES`, `kind` choices `DEFINITION/SCOPE/EXAMPLE/EDITORIAL/HISTORY/CHANGE/NOTE` with their SKOS CURIEs, `value` `TextField`, no uniqueness, `value` unindexed by decision); add `Concept.definition(language)`, `notes(language, kind=None)`, `add_note(language, kind, value)`.
- [ ] T010 [US3] `makemigrations`; US-3 tests green.

**Checkpoint**: descriptions complete; RDF export map is a straight kind→predicate lookup later.

## Phase 5: User Story 4 — Per-vocabulary default language (P2)

**Goal**: a vocabulary's default language, overridable, decides its concepts' identity anchor.
**Independent test**: the US-4 classes in `tests/test_models.py` green.
**Depends on**: US-1 (`effective_default_language`).

- [ ] T011 [US4] Write failing tests in `tests/test_models.py`: a scheme with no override anchors identity in the app default; a scheme overridden to `de` derives its concepts' slugs from the `de` `label`; reading `effective_default_language` returns the override or the app default.
- [ ] T012 [US4] Add `ConceptScheme.default_language` (`CharField(blank=True, choices=settings.LANGUAGES)`); extend `effective_default_language` to `self.default_language or settings.LANGUAGE_CODE`.
- [ ] T013 [US4] `makemigrations`; US-4 tests green.

**Checkpoint**: independently-authored vocabularies anchor identity in their own language.

## Phase 6: User Story 5 — Overridable concept slug (P2)

**Goal**: an explicit slug is pinned; an auto slug tracks the default-language label.
**Independent test**: the US-5 classes in `tests/test_models.py` green.
**Depends on**: US-1 (label/slug anchor).

- [ ] T014 [US5] Write failing tests in `tests/test_models.py`: an explicit slug is exactly the value set (not derived); changing the default-language `label` leaves an explicit slug unchanged; a concept with no explicit slug derives it from the label (as #15); an explicit slug colliding within the scheme is refused.
- [ ] T015 [US5] Add `Concept.slug_is_manual` (`BooleanField(default=False)`); `save()` re-derives `slug` from `label` only when not manual; add the explicit-slug entry point (a `set_slug`/manager path that sets the flag); keep the uniqueness validation for both auto and manual slugs.
- [ ] T016 [US5] `makemigrations`; US-5 tests green.

**Checkpoint**: curators control identity formation; imported slugs later fit the same mechanism.

## Phase 7: User Story 6 — Multilingual test scaffolding (P3)

**Goal**: factories produce a multilingual concept in a couple of lines.
**Independent test**: `tests/test_factories.py` green.
**Depends on**: US-1, US-2, US-3.

- [ ] T017 [P] [US6] In `tests/factories.py` add `ConceptLabelFactory`, `ConceptNoteFactory`, and a `multilingual` trait on `ConceptFactory` that populates en+de preferred labels and at least one note; in `tests/test_factories.py` assert the trait yields preferred labels and notes in more than one language.

## Phase 8: User Story 7 — Translatable field metadata and deliberate indexing (P3)

**Goal**: the family metadata + indexing standard over every new field.
**Independent test**: `tests/test_standards.py` green.
**Depends on**: US-1..US-5 (all new fields/models exist).

- [ ] T018 [US7] Reinstate `tests/test_standards.py`: walk every concrete, editable field on all four models asserting lazily-translatable non-empty `verbose_name` + `help_text`; assert the new validation messages (duplicate preferred label, missing default-language label) are lazy `Promise`s with named placeholders; assert `ConceptLabel(language, kind, text)` is indexed and the one-preferred partial unique exists; assert `ConceptNote.value` is unindexed (recorded decision).
- [ ] T019 [US7] Make the new fields/messages satisfy T018 (add any missing `verbose_name`/`help_text`; ensure validation messages use `ValidationError(msgid, params=…)` lazy form with named placeholders — the pattern from #15's `decisions.md` §9).

## Phase 9: Polish, docs, and supersession

- [ ] T020 [P] [Polish] README scope note + CHANGELOG entry: concepts now carry per-language preferred/alternative/hidden labels and the SKOS documentary notes, an overridable slug, and a per-vocabulary default language. Run the humanizer over the changed public markdown before it lands.
- [ ] T021 [Polish] Supersession annotation (cross-spec convention): in `specs/001-vocabulary-concepts/` strike-through + tag **Superseded by FS-002 (#16)** on the single-label assumption in `spec.md` (Assumptions + the "one plain label" note), the `Concept.label` "one label" line in `data-model.md`, and `decisions.md` §1; add a dated supersession line to #15's `decisions.md`. Do **not** strike the `label` field itself (it survives, meaning clarified).
- [ ] T022 [Polish] Full suite green across the matrix; `makemigrations --check` clean. (Migration squash to one file is the pipeline's S5 convergence step, not a code task.)

## Dependencies & parallelism

- **Order**: Setup → US-1 → {US-2, US-3, US-4, US-5} → US-6 → US-7 → Polish. US-2/3/4/5 each depend only on US-1 and are mutually independent, but Phase-1 pipeline runs them **sequentially** on one worktree (shared `models.py`/migrations), which sidesteps convergence friction.
- **Test-first**: within each story the failing test task precedes its implementation task (Article I).
- **Migrations**: each story runs `makemigrations`; the branch's migrations are squashed to one at convergence (S5), regenerated from zero, verified green — safe because nothing is released.
- `[P]` is marked only where files genuinely differ (T017 factories, T020 docs); model-test tasks share `tests/test_models.py` and are not parallel.
