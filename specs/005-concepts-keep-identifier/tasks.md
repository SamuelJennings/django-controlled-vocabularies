# Tasks: Concepts keep the identifier they were published under

**Feature**: `005-concepts-keep-identifier` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Test-first throughout (Constitution I): within each phase the failing test is written before the code
that satisfies it. `[USn]` marks the story a task serves; `[P]` marks tasks that may run in parallel with
others in the same phase.

Every model change lands in `controlled_vocabularies/models.py`, so phases touching it are sequential
by file even where they are independent by story.

## Phase 1: Foundational (sequential, before any story)

- [ ] T001 [Setup] Confirm `tests/settings.py` still carries a `CONTROLLED_VOCABULARIES_BASE_URI` that
      tests can override with `override_settings`, and that no new dependency is needed (`urllib.parse`
      is standard library). No code change expected — this is a check, not a task that edits files.
- [ ] T002 [Foundation] In `controlled_vocabularies/models.py` add `validate_static_uri(value)`:
      parse with `urllib.parse.urlsplit`, require a non-empty scheme and non-empty remainder, refuse
      `javascript`/`data`/`vbscript` case-insensitively, refuse over 500 characters. Every refusal is a
      `ValidationError` with a lazily translatable message using **named** placeholders.
- [ ] T003 [Foundation] Add the `static_uri` field to `ConceptScheme`, `Concept`, and `Collection`
      per `data-model.md`: `CharField(max_length=500, null=True, blank=True)`, translatable
      `verbose_name` and `help_text`, `validators=[validate_static_uri]`, and a
      `UniqueConstraint(fields=["static_uri"], condition=Q(static_uri__isnull=False))` in each
      model's `Meta`.
- [ ] T004 [Foundation] Generate the migration (`makemigrations`) — three `AddField` and three
      `AddConstraint`, no data migration. Assert by inspection that it contains no `RunPython`.

## Phase 2: User Story 1 — A record keeps the identifier it arrived with (P1) 🎯 MVP

- [ ] T005 [US1] Write failing tests in `tests/test_models.py` (class `TestStaticUri`):
      an identifier supplied at creation reads back verbatim from `uri`; it survives a rename; it
      survives `override_settings` changing the base address; a scheme and a collection keep their own,
      and a concept's is not derived from its scheme's; `has_static_uri` is `True`. Also the refusal
      cases: non-absolute, `javascript:`, over-length — each raising `ValidationError` — and `urn:`
      accepted.
- [ ] T006 [US1] Rework `uri` on all three models to return `self.static_uri or self.local_url`, and
      add `has_static_uri`. Keep the existing docstrings' intent: `uri` is still identity.
- [ ] T007 [US1] Call `validate_static_uri` from each model's `save()` when `static_uri` is set,
      so the import path is protected where `full_clean()` is not called. Add a test asserting a bare
      `Model.objects.create(...)` with a bad identifier raises rather than storing.
- [ ] T008 [US1] Add the cross-model duplicate check to `clean()` and `save()`: refuse a `static_uri`
      already held by a record of a different model, with a translatable named-placeholder message.
      Test a concept and a collection cannot share one.

## Phase 3: User Story 2 — Find a record by its identifier, wherever it points (P2)

- [ ] T009 [US2] Write failing tests in `tests/test_models.py` (class `TestGetByUri`): an external
      identifier resolves to its record; a local record still resolves by its own identifier; an
      unheld identifier raises `DoesNotExist` for both kinds; an imported and a local record do not
      answer to each other's identifier; `ConceptScheme` and `Collection` resolve too. Include the
      FR-014 compatibility assertion — `Concept.objects.get_by_uri` still exists under that name and
      still answers for locally authored concepts exactly as before.
- [ ] T010 [US2] Add `UriLookupMixin` with `get_by_uri(uri)`: exact match on `static_uri`
      first, then the model's base-relative parse, then `DoesNotExist` with R1's message. Move
      `ConceptManager.get_by_uri`'s existing parse into the model-specific hook the mixin calls; do not
      change its behaviour for local identifiers.
- [ ] T011 [US2] Put the mixin on the `ConceptScheme` and `Collection` managers, adding their parses
      (`{base}/{slug}` and `{base}/{scheme-slug}/collection/{slug}`).

## Phase 4: User Story 3 — A record authored here shows the identifier it will publish under (P2)

- [ ] T012 [US3] Write failing tests (class `TestProvisionalUri`): a record with no `static_uri`
      reports the composed value; it follows a rename; it follows an `override_settings` base-address
      change; `static_uri` is `None` and `has_static_uri` is `False` — the permanent URI exists
      throughout and is simply still dynamic.
- [ ] T013 [US3] Write the upgrade test: build records the way a pre-005 database holds them (no
      `static_uri`) and assert each reports exactly the identifier R1's composition produced, and
      that existing references still resolve. This is the FR-009 / Article IX evidence.
- [ ] T014 [US3] Write the uniqueness tests: two records of the same model holding one `static_uri`
      are refused **by the database constraint** (assert `IntegrityError`, not a `ValidationError`);
      many records holding none coexist freely.
- [ ] T015 [US3] Make Phase 4's tests pass. Expected to be no production change beyond Phase 2 and 3 —
      if any is needed, it belongs here rather than being smuggled into an earlier phase.

## Phase 5: User Story 4 — Every record has a place on this site (P2)

- [ ] T016 [US4] Write failing tests (class `TestLocalUrl`): a local unpublished record's `local_url`
      and `uri` are equal; an imported record's differ and its `local_url` is on this site; a
      collection's `local_url` can never equal a concept's; `local_url` follows a rename.
- [ ] T017 [US4] Add `local_url` to all three models, composing from the parent's `local_url` — never
      from `uri`, which would put a concept of an imported vocabulary on the publisher's domain. Move
      R1's composition into it and leave `conf.get_base_uri()` as the single read site for the address.

## Phase 6: User Story 5 — Translatable metadata, indexing, factories (P3)

- [ ] T018 [P] [US5] Extend `tests/test_standards.py` so the metadata walk covers the three new
      columns: non-empty lazily translatable `verbose_name` and `help_text`, and every refusal message
      this feature introduces translatable with named placeholders.
- [ ] T019 [P] [US5] Add an `external` trait to `ConceptSchemeFactory`, `ConceptFactory`, and
      `CollectionFactory` in `tests/factories.py` producing a record with a plausible externally
      assigned identifier; cover it in `tests/test_factories.py`.
- [ ] T020 [US5] Assert the indexing decision in `tests/test_standards.py`: `static_uri` is covered
      by its partial unique constraint, and record in `data-model.md` that nothing else gains an index
      (already written — verify it still matches the code).

## Phase 7: Polish and docs

- [ ] T021 Update `CONTEXT.md`: the single **URI** glossary entry becomes **permanent URI**, and
      **local URL** joins it. Both defined in the vocabulary the code now uses (spec Assumptions, D9).
- [ ] T022 Check `README.md` for any claim that a concept's identifier is always composed from the
      configured address, and correct it if present.
- [ ] T023 Run `forge verify` (lint, typecheck, tests, build) and confirm green across the matrix.
      Confirm `makemigrations --check` is clean and a migrate-from-zero reaches the same state.

## Dependencies and parallelism

- Phase 1 is strictly first: every story needs the column to exist.
- Phases 2–5 all edit `models.py`, so they run **sequentially** despite being independent by story.
  Phase 1 (Phase 2 in the pipeline's numbering) parallelism is not available here for that reason.
- Phase 6's T018 and T019 touch different test files and may run in parallel.
- Phase 7 is last; T021 and T022 are documentation and may run alongside each other.
- Migration squashing happens at convergence (S5), not here.
