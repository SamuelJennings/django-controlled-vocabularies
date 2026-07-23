# Tasks: Represent a vocabulary and its concepts

**Input**: design docs in `specs/001-vocabulary-concepts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md
**Tests**: requested — SC-004 requires every FR exercised by a test; test-first per Article I.

Format: `[ID] [P?] [Story] Description`. `[P]` = different files, no dependency. Paths are exact.

## Phase 1: Setup

- [ ] T001 Add `CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"` to `tests/settings.py`. (`factory_boy` is already provided by `mvp-shared[test]` — no dependency work needed.)

## Phase 2: Foundational (blocks all stories)

- [ ] T002 Add `controlled_vocabularies/conf.py` with `get_base_uri()` reading `settings.CONTROLLED_VOCABULARIES_BASE_URI` (documented default, trailing slash stripped).

**Checkpoint**: base-URI resolution available; stories can begin.

## Phase 3: User Story 1 — Define a vocabulary (P1) 🎯 MVP

**Goal**: create/rename/delete a vocabulary; slug derived from name, unique app-wide; scheme URI composes.
**Independent test**: `tests/test_scheme.py` green in isolation.

- [ ] T003 [P] [US1] Write failing `tests/test_scheme.py`: create → slug; rename → slug updates; empty/whitespace name → `ValidationError`; non-Latin name → non-empty slug; duplicate slug refused; `scheme.uri` composition.
- [ ] T004 [US1] Implement `ConceptScheme` in `controlled_vocabularies/models.py` (`name`, `description`, `slug` `allow_unicode=True` unique; `save()` derives + validates slug; `uri` property via `conf.get_base_uri()`; `__str__`).
- [ ] T005 [US1] `poetry run python -m django makemigrations controlled_vocabularies` → `0001_*`; tests pass.

**Checkpoint**: vocabularies fully functional.

## Phase 4: User Story 2 — Populate a vocabulary with concepts (P1)

**Goal**: add/list/relabel/delete concepts in a scheme; slug unique within scheme; scheme delete cascades.
**Independent test**: `tests/test_concept.py` green in isolation.
**Depends on**: US1 (`Concept.scheme` FK).

- [ ] T006 [P] [US2] Write failing `tests/test_concept.py`: add → slug; list; relabel → slug updates; delete; empty label → `ValidationError`; collision within scheme refused (not suffixed); same slug allowed across schemes; delete scheme cascades concepts; `concept.uri` composition.
- [ ] T007 [US2] Implement `Concept` in `controlled_vocabularies/models.py` (`scheme` FK `on_delete=CASCADE` `related_name="concepts"`; `label`; `slug` `allow_unicode=True`; `UniqueConstraint(scheme, slug)`; `save()` derives + validates slug; `uri` property; `__str__`).
- [ ] T008 [US2] `makemigrations` → `0002_*`; tests pass.

**Checkpoint**: vocabularies + concepts work independently.

## Phase 5: User Story 3 — Every concept carries a stable identifier (P1)

**Goal**: URI identity — composition, lookup by URI, global uniqueness, rename-flow.
**Independent test**: `tests/test_identity.py` green in isolation.
**Depends on**: US1, US2.

- [ ] T009 [P] [US3] Write failing `tests/test_identity.py`: full URI equals base + scheme-slug + concept-slug; `Concept.objects.get_by_uri(uri)` returns exactly that concept; no two concepts across schemes share a URI; non-Latin label → resolvable URI; rename scheme/label → URI recomposes.
- [ ] T010 [US3] Add `Concept.objects.get_by_uri(uri)` manager method (strip base, split `scheme-slug/concept-slug`, `get(scheme__slug=…, slug=…)`); ensure `uri` properties satisfy the identity tests.

**Checkpoint**: identity guarantees hold.

## Phase 6: User Story 4 — Ready-made test scaffolding (P2)

**Goal**: factories for downstream tests.
**Independent test**: `tests/test_factories.py` green.
**Depends on**: US1, US2.

- [ ] T011 [P] [US4] Add `tests/factories.py` (`ConceptSchemeFactory`; `ConceptFactory` with a `SubFactory` scheme) and `tests/test_factories.py` asserting both produce valid saved objects and `ConceptFactory()` auto-creates its scheme.

## Phase 8: User Story 5 — Translatable, self-documenting field metadata (P2)

**Propagated**: 2026-07-23 — Added from the spec refinement (US-5, FR-009–011, SC-006).

**Goal**: every field carries translatable `verbose_name` + non-empty `help_text`; all user-facing
strings wrapped in `gettext_lazy` with named placeholders; indexing deliberate and asserted.
**Independent test**: `tests/test_standards.py` green in isolation.
**Depends on**: US1, US2 (the fields must exist).

- [ ] T014 [P] [US5] Write failing `tests/test_standards.py`: walk every field on `ConceptScheme` and `Concept` asserting non-empty `help_text` and `verbose_name` that are lazy translation proxies; assert `Meta.verbose_name`/`verbose_name_plural` are lazy; assert the empty-name, empty-label, and both slug-collision `ValidationError` messages are translatable (lazy-backed, named placeholders); assert indexes — `ConceptScheme.slug` unique, `Concept.scheme` FK-indexed, `(scheme, slug)` composite constraint present.
- [ ] T015 [US5] Apply the metadata to `controlled_vocabularies/models.py`: `verbose_name` + `help_text` on all six fields, `Meta.verbose_name`(+plural) on both models, `gettext_lazy as _` wrapping for all user-facing strings, validation messages via named `%(slug)s` placeholders. Developer-facing `DoesNotExist` diagnostics stay unwrapped.
- [ ] T016 [US5] `makemigrations` → `0003_*` (metadata-only); full suite + all gates green.

---

## Phase 7: Polish & cross-cutting

- [ ] T012 [P] Docstrings on `ConceptScheme`, `Concept`, the manager, and `conf.get_base_uri`; add the `CONTROLLED_VOCABULARIES_BASE_URI` note to `README.md`; add a `CHANGELOG.md` entry (Article VI).
- [ ] T013 Run `specs/001-vocabulary-concepts/quickstart.md` scenarios and `kit/scripts/verify.sh` — lint, mypy, tests, build all green.

## Dependencies & order

- Setup (T001) → Foundational (T002) → US1 (T003-T005) → US2 (T006-T008) → US3 (T009-T010) and US4 (T011, parallelisable with US3) → US5 (T014-T016, added by refinement; depends on US1+US2) → Polish (T012-T013, re-run final verify after US5).
- Within each story: the test task precedes and must FAIL before its implementation task.
- US2 depends on US1 (FK); US3 and US4 depend on US1+US2. Stories are otherwise independently testable.

## Notes

- `[P]` = different file, no dependency. The three test files and `factories.py` are independent.
- Two migrations (`0001` scheme, `0002` concept) keep the stories independently committable.
- No runtime dependency is added; `deptry` must stay green (declaring `rdflib`/`parler` now would fail it).
