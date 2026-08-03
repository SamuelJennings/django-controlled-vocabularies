# Tasks: Concepts keep the identifier they were published under

**Feature**: `005-concepts-keep-identifier` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Test-first throughout (Constitution I): within each phase the failing test is written before the code
that satisfies it. `[USn]` marks the story a task serves; `[P]` marks tasks that may run in parallel with
others in the same phase.

Every model change lands in `controlled_vocabularies/models.py`, so phases touching it are sequential
by file even where they are independent by story.

## Phase 1: Foundational (sequential, before any story)

- [x] T001 [Setup] Confirm `tests/settings.py` still carries a `CONTROLLED_VOCABULARIES_BASE_URI` that
      tests can override with `override_settings`, and that no new dependency is needed (`urllib.parse`
      is standard library). No code change expected — this is a check, not a task that edits files.
- [x] T002 [Foundation] In `controlled_vocabularies/models.py` add `validate_permanent_uri(value)`:
      parse with `urllib.parse.urlsplit`, require a non-empty scheme and non-empty remainder, refuse
      `javascript`/`data`/`vbscript` case-insensitively, refuse over 500 characters. Every refusal is a
      `ValidationError` with a lazily translatable message using **named** placeholders.
- [x] T003 [Foundation] Add the `permanent_uri` field to `ConceptScheme`, `Concept`, and `Collection`
      per `data-model.md`: `CharField(max_length=500, null=True, blank=True)`, translatable
      `verbose_name` and `help_text`, `validators=[validate_permanent_uri]`, and a
      `UniqueConstraint(fields=["permanent_uri"], condition=Q(permanent_uri__isnull=False))` in each
      model's `Meta`.
- [x] T004 [Foundation] Generate the migration (`makemigrations`) — three `AddField` and three
      `AddConstraint`, no data migration. Assert by inspection that it contains no `RunPython`.

## Phase 2: User Story 1 — A record keeps the identifier it arrived with (P1) 🎯 MVP

- [x] T005 [US1] Write failing tests in `tests/test_models.py` (class `TestPermanentUri`):
      an identifier supplied at creation reads back verbatim from `uri`; it survives a rename; it
      survives `override_settings` changing the base address; a scheme and a collection keep their own,
      and a concept's is not derived from its scheme's; `has_permanent_uri` is `True`. Also the refusal
      cases: non-absolute, `javascript:`, over-length — each raising `ValidationError` — and `urn:`
      accepted.
- [x] T006 [US1] Rework `uri` on all three models to return `self.permanent_uri or self.local_url`, and
      add `has_permanent_uri`. Keep the existing docstrings' intent: `uri` is still identity.
- [x] T007 [US1] Call `validate_permanent_uri` from each model's `save()` when `permanent_uri` is set,
      so the import path is protected where `full_clean()` is not called. Add a test asserting a bare
      `Model.objects.create(...)` with a bad identifier raises rather than storing.
- [x] T008 [US1] Add the cross-model duplicate check to `clean()` and `save()`: refuse a `permanent_uri`
      already held by a record of a different model, with a translatable named-placeholder message.
      Test a concept and a collection cannot share one.

## Phase 2b: User Story 1 — a stored identifier cannot be rewritten or cleared (P1)

Added 2026-08-03 after reviewing the US-1 report. FR-002 ("never changed once stored") and FR-013
("fixedness moves in one direction only") had no implementing task, and a probe confirmed the gap:
after `ConceptScheme.objects.create(permanent_uri="http://vocab.example.org/ext")`, assigning a new
value and saving rewrites it, and assigning `None` and saving silently returns the record to a
provisional identity. This is a planning omission, not an implementer failure.

- [x] T024 [US1] Write failing tests in `tests/test_models.py` (class `TestPermanentUriIsFixed`), for
      each of the three models: a record loaded from the database refuses a save that changes its
      stored `permanent_uri`; it refuses a save that clears it to `None`; the refusal is a
      `ValidationError` on the `permanent_uri` key with a translatable named-placeholder message; and
      re-saving with the identifier unchanged succeeds. Also assert the two allowed transitions still
      work: a record created with an identifier keeps it, and a record created without one may still
      have one set once (this is the path R4's publish action will use).
- [x] T025 [US1] Enforce it: snapshot the loaded value in a `from_db` classmethod on each model
      (guarding against a deferred `permanent_uri` from `.only()`/`.defer()`, where no snapshot is
      available and the check must be skipped rather than fire on a phantom change), and refuse the
      change from `save()` and `clean()` via a module-level helper alongside
      `_reject_permanent_uri_held_by_another_model`. A record with no snapshot — one freshly
      constructed in memory — is unconstrained, so setting an identifier for the first time is
      allowed and only rewriting a stored one is refused.
- [x] T026 [US1] Close the two holes T025's snapshot left, found by probing the delivered code
      (decisions.md D12). A `.only()`/`.defer()` load carries no snapshot, so a rewrite *or* a clear
      through one was accepted silently — read the stored value back instead, but only once the
      deferred column has actually been assigned, so an untouched deferred save still never fetches
      it. And a record's own instance kept its `None` snapshot after the save that first stored an
      identifier, so it could be saved again under a second one — adopt the written value as the
      stored one at the end of each `save()`. Tests for both, per model, in `TestPermanentUriIsFixed`.

## Phase 3: User Story 2 — Find a record by its identifier, wherever it points (P2)

- [x] T009 [US2] Write failing tests in `tests/test_models.py` (class `TestGetByUri`): an external
      identifier resolves to its record; a local record still resolves by its own identifier; an
      unheld identifier raises `DoesNotExist` for both kinds; an imported and a local record do not
      answer to each other's identifier; `ConceptScheme` and `Collection` resolve too. Include the
      FR-014 compatibility assertion — `Concept.objects.get_by_uri` still exists under that name and
      still answers for locally authored concepts exactly as before.
- [x] T010 [US2] Add `PermanentUriLookupMixin` with `get_by_uri(uri)`: exact match on `permanent_uri`
      first, then the model's base-relative parse, then `DoesNotExist` with R1's message. Move
      `ConceptManager.get_by_uri`'s existing parse into the model-specific hook the mixin calls; do not
      change its behaviour for local identifiers.
- [x] T011 [US2] Put the mixin on the `ConceptScheme` and `Collection` managers, adding their parses
      (`{base}/{slug}` and `{base}/{scheme-slug}/collection/{slug}`).

## Phase 4: User Story 3 — A record authored here shows the identifier it will publish under (P2)

- [x] T012 [US3] Write failing tests (class `TestProvisionalUri`): a record with no `permanent_uri`
      reports the composed value; it follows a rename; it follows an `override_settings` base-address
      change; `permanent_uri` is `None` and `has_permanent_uri` is `False`.
- [x] T013 [US3] Write the upgrade test: build records the way a pre-005 database holds them (no
      `permanent_uri`) and assert each reports exactly the identifier R1's composition produced, and
      that existing references still resolve. This is the FR-009 / Article IX evidence.
- [x] T014 [US3] Write the uniqueness tests: two records of the same model holding one `permanent_uri`
      are refused **by the database constraint** (assert `IntegrityError`, not a `ValidationError`);
      many records holding none coexist freely.
- [x] T015 [US3] Make Phase 4's tests pass. Expected to be no production change beyond Phase 2 and 3 —
      if any is needed, it belongs here rather than being smuggled into an earlier phase.

## Phase 5: User Story 4 — Every record has a place on this site (P2)

- [x] T016 [US4] Write failing tests (class `TestLocalUrl`): a local unpublished record's `local_url`
      and `uri` are equal; an imported record's differ and its `local_url` is on this site; a
      collection's `local_url` can never equal a concept's; `local_url` follows a rename. **Include
      spec.md Edge Cases §4 explicitly** (raised in the US-1 report): a concept authored locally
      inside a vocabulary whose own identifier is externally fixed must compose its provisional
      identifier under *this site's* address, not the publisher's. Until T017 lands, `Concept.uri`
      still reads through `self.scheme.uri` and this case composes under the publisher's domain, so
      this test fails before the change and passes after — it is the evidence T017 closed it.
- [x] T017 [US4] Add `local_url` to all three models, composing from the parent's `local_url` — never
      from `uri`, which would put a concept of an imported vocabulary on the publisher's domain. Move
      R1's composition into it and leave `conf.get_base_uri()` as the single read site for the address.

## Phase 5b: User Story 1 — a blank identifier is absence, not an identifier (P1)

- [x] T027 [US1] Close the hole probing the delivered code found (decisions.md D13). `permanent_uri`
      is nullable so the partial `UniqueConstraint` exempts provisional records, but `""` is not
      null: it sits inside the constraint while `uri` and `has_permanent_uri` both read it as
      absent, so the second record assigned `""` fails at the database with an opaque
      `IntegrityError`. Normalise `""` to `None` in each `clean()` and in the shared save-path
      checks, after the deferred guard and before the rewrite guard so clearing a *stored*
      identifier with `""` is still refused. Tests in `TestBlankPermanentUriIsAbsent`.

## Phase 6: User Story 5 — Translatable metadata, indexing, factories (P3)

- [x] T018 [P] [US5] Extend `tests/test_standards.py` so the metadata walk covers the three new
      columns: non-empty lazily translatable `verbose_name` and `help_text`, and every refusal message
      this feature introduces translatable with named placeholders.
- [x] T019 [P] [US5] Add an `external` trait to `ConceptSchemeFactory`, `ConceptFactory`, and
      `CollectionFactory` in `tests/factories.py` producing a record with a plausible externally
      assigned identifier; cover it in `tests/test_factories.py`.
- [x] T020 [US5] Assert the indexing decision in `tests/test_standards.py`: `permanent_uri` is covered
      by its partial unique constraint, and record in `data-model.md` that nothing else gains an index
      (already written — verify it still matches the code).

## Phase 7: Polish and docs

- [x] T021 Update `CONTEXT.md`: the single **URI** glossary entry becomes **permanent URI**, and
      **local URL** joins it. Both defined in the vocabulary the code now uses (spec Assumptions, D9).
- [x] T022 Check `README.md` for any claim that a concept's identifier is always composed from the
      configured address, and correct it if present.
- [x] T023 Run `forge verify` (lint, typecheck, tests, build) and confirm green across the matrix.
      Confirm `makemigrations --check` is clean and a migrate-from-zero reaches the same state.

## Dependencies and parallelism

- Phase 1 is strictly first: every story needs the column to exist.
- Phases 2–5 all edit `models.py`, so they run **sequentially** despite being independent by story.
  Phase 1 (Phase 2 in the pipeline's numbering) parallelism is not available here for that reason.
- Phase 2b (T024–T026) closes FR-002/FR-013 and edits `models.py`, so it runs before Phase 3.
- Phase 6's T018 and T019 touch different test files and may run in parallel.
- Phase 7 is last; T021 and T022 are documentation and may run alongside each other.
- Migration squashing happens at convergence (S5), not here.
