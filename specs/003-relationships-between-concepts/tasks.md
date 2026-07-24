# Tasks: Relationships between concepts

**Input**: design docs in `specs/003-relationships-between-concepts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md
**Tests**: requested — SC-010 requires every FR exercised by a test; test-first per Article I.

Format: `[ID] [P?] [Story] Description`. `[P]` = different files, no dependency. Paths are exact.
Model tests land in `tests/test_models.py` (class-grouped, mirroring the single `models.py`), so
same-file tasks are **not** `[P]`. Stories are implemented sequentially in dependency order (Phase-1
pipeline) on one worktree — they share `models.py` and the migration, so sequencing avoids
migration-merge friction.

## Phase 1: Setup

- [ ] T001 [Setup] Confirm `tests/settings.py` has `LANGUAGE_CODE` + a multi-entry `LANGUAGES` and a
  usable `ConceptSchemeFactory`/`ConceptFactory` in `tests/factories.py` (all present from #15/#16);
  no new setup expected. If a fixture is missing for cross-scheme tests, add it. (`factory_boy` ships
  in `mvp-shared[test]`.)

## Phase 2: User Story 1 — Broader/narrower hierarchy, navigable both ways (P1) 🎯 MVP

**Goal**: assert `broader`, read `narrower` back derived; polyhierarchy; remove; no self; no duplicate;
intra-vocabulary. The whole graph MVP.
**Independent test**: the US-1 classes in `tests/test_models.py` green in isolation.
**Depends on**: #15 (`Concept`, `ConceptScheme`).

- [ ] T002 [US1] Write failing tests in `tests/test_models.py` (class `TestBroaderNarrower`):
  `a.add_broader(b)` → `b in a.broader()` and `a in b.narrower()` with no narrower assertion; a concept
  may have two broader concepts (both in `broader()`); `remove_broader` clears both directions;
  `a.add_broader(a)` raises `ValidationError`; the same broader edge twice raises; a broader edge whose
  endpoints are in different schemes raises; adding/removing a broader edge leaves `a.uri`/`a.slug`
  unchanged.
- [ ] T003 [US1] In `controlled_vocabularies/models.py` add `ConceptRelation` (`source`/`target` FKs
  `related_name="relations_as_source"`/`"relations_as_target"`, `Kind` TextChoices `BROADER`/`RELATED`,
  `kind`), with `UniqueConstraint(source, target, kind)`, `CheckConstraint(~Q(source=F("target")))`,
  `Index(target, kind)`, translatable field metadata, and `clean()`+`save()` enforcing not-self and
  same-scheme (FR-006/FR-009) with named-placeholder messages. Add `Concept.broader()`, `narrower()`,
  `add_broader(other)`, `remove_broader(other)` per `contracts/python-api.md`. `add_broader` calls
  `full_clean()` before save.
- [ ] T004 [US1] `poetry run python -m django makemigrations controlled_vocabularies`; US-1 tests green
  in isolation.

**Checkpoint**: hierarchy works, navigable both ways, identity provably stable, self/duplicate/cross-scheme refused.

## Phase 3: User Story 2 — The related association, symmetric (P2)

**Goal**: symmetric `related`, stored once (PK-canonicalised), read from either side, removable; no
self; no mirror duplicate.
**Independent test**: the US-2 classes in `tests/test_models.py` green.
**Depends on**: US-1 (`ConceptRelation`).

- [ ] T005 [US2] Write failing tests in `tests/test_models.py` (class `TestRelated`): `a.add_related(b)`
  → `b in a.related()` and `a in b.related()`; re-asserting `b.add_related(a)` raises (one row, either
  order); `a.add_related(a)` raises; `remove_related` clears both sides; a related edge across schemes
  raises; adding/removing a related edge leaves `uri`/`slug` unchanged.
- [ ] T006 [US2] Add `Concept.add_related(other)` (canonicalise endpoints by PK per research R2),
  `related()` (span both columns), `remove_related(other)`; `add_related` validates via `full_clean()`.
  No new field or migration expected (RELATED already in `Kind`); if `makemigrations` reports drift,
  none should exist — confirm with `--check`.
- [ ] T007 [US2] `poetry run python -m django makemigrations --check` clean (no schema change); US-2
  tests green.

**Checkpoint**: full graph — hierarchy plus symmetric associations.

## Phase 4: User Story 3 — The graph stays coherent (P2)

**Goal**: broader/related disjointness on direct pairs; cycles accepted (no traversal); the
cross-vocabulary and self rules already hold from US-1/US-2 — assert them at the coherence level too.
**Independent test**: the US-3 classes in `tests/test_models.py` green.
**Depends on**: US-1, US-2 (both kinds must exist to express disjointness).

- [ ] T008 [US3] Write failing tests in `tests/test_models.py` (class `TestGraphIntegrity`): a directly
  hierarchical pair cannot also be related (both attempt orders raise); a related pair cannot be given a
  broader link (both orders raise); a broader link and a related link on two *different* pairs both
  succeed; a `related` link between only-transitively-hierarchical concepts (`a→b→c`, relate `a`,`c`) is
  accepted; a cyclic broader chain (`a→b→c→a`) is accepted without error.
- [ ] T009 [US3] Add the disjointness check to `ConceptRelation.clean()`+`save()` backstop: refuse a new
  relation if a row of the *other* kind already joins the unordered pair in either direction (single
  indexed lookup, no traversal), with a translatable named-placeholder message. Confirm cycles are
  untouched (no hierarchy walk anywhere).
- [ ] T010 [US3] `makemigrations --check` clean (no schema change); US-3 tests green.

**Checkpoint**: the graph cannot enter a SKOS-contradictory state; the deferred non-guarantees are pinned by tests.

## Phase 5: User Story 4 — Relation test scaffolding (P3)

**Goal**: factories build a graph in a few lines.
**Independent test**: `tests/test_factories.py` green.
**Depends on**: US-1, US-2.

- [ ] T011 [P] [US4] In `tests/factories.py` add `ConceptRelationFactory` and a small helper/trait that
  builds a broader/narrower pair and a related pair (respecting the validation path, i.e. going through
  `add_broader`/`add_related` or a valid direct create); in `tests/test_factories.py` assert the factory
  yields a saved, both-ways-navigable hierarchy and a single related association.

## Phase 6: User Story 5 — Translatable field metadata and deliberate indexing (P3)

**Goal**: the family metadata + indexing standard over the new model.
**Independent test**: `tests/test_standards.py` green.
**Depends on**: US-1..US-3 (the model and its messages exist).

- [ ] T012 [US5] Extend `tests/test_standards.py`: the field walk already covers all concrete models —
  assert `ConceptRelation`'s fields carry lazily-translatable non-empty `verbose_name` + `help_text`;
  assert the four new validation messages (self, duplicate, disjointness, cross-vocabulary) are lazy
  `Promise`s with named placeholders; assert `UniqueConstraint(source, target, kind)`, the self
  `CheckConstraint`, and `Index(target, kind)` exist (indexing decision recorded).
- [ ] T013 [US5] Make the model satisfy T012 — add any missing `verbose_name`/`help_text`; ensure every
  validation message uses `ValidationError(msgid, params=…)` lazy form with named placeholders (the
  #15/#16 pattern).

## Phase 7: Polish, docs, supersession

- [ ] T014 [P] [Polish] README scope note + CHANGELOG entry: concepts can now be linked by a
  broader/narrower hierarchy and a symmetric related association through the ORM, with the integrity
  guarantees and the recorded cycle deferral. Run the humanizer over the changed public markdown before
  it lands.
- [ ] T015 [Polish] Full suite green across the matrix; `makemigrations --check` clean. (Migration
  squash to one file is the pipeline's S5 convergence step, not a code task.) No supersession of #15/#16
  is expected — this feature is additive; if any earlier decision record is affected, annotate in place
  per the cross-spec convention (do not delete).

## Dependencies & parallelism

- **Order**: Setup → US-1 → US-2 → US-3 → {US-4, US-5} → Polish. US-2/US-3 build on US-1's model; US-4
  and US-5 depend on the finished model. Phase-1 pipeline runs them sequentially on one worktree
  (shared `models.py`/migration).
- **Test-first**: within each story the failing-test task precedes its implementation task (Article I).
- **Migrations**: only US-1 adds schema (the `ConceptRelation` table); US-2/US-3 add behaviour, not
  columns — `makemigrations --check` must stay clean after them. The single migration is regenerated
  from zero at convergence (S5) and verified green.
- `[P]` marked only where files genuinely differ (T011 factories, T014 docs); model-test tasks share
  `tests/test_models.py` and are not parallel.
