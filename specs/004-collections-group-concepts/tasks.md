# Tasks: Collections that group concepts

**Input**: design docs in `specs/004-collections-group-concepts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md
**Tests**: requested — SC-011 requires every FR exercised by a test; test-first per Article I.

Format: `[ID] [P?] [Story] Description`. `[P]` = different files, no dependency. Paths are exact.
Model tests land in `tests/test_models.py` (class-grouped, mirroring the single `models.py`), so
same-file tasks are **not** `[P]`. Stories run sequentially in dependency order (Phase-1 pipeline) on
one worktree — they share `models.py` and the migration, so sequencing avoids migration-merge friction.

## Phase 1: Setup

- [ ] T001 [Setup] Confirm `tests/settings.py` (`LANGUAGE_CODE` + multi-entry `LANGUAGES`) and the
  `ConceptSchemeFactory`/`ConceptFactory` in `tests/factories.py` are usable (all present from
  #15/#16/#17); no new setup expected. If a fixture is missing for the cross-scheme test, add it.
  (`factory_boy` ships in `mvp-shared[test]`.)

## Phase 2: User Story 1 — Gather concepts into a named collection (P1) 🎯 MVP

**Goal**: a named `Collection` in a vocabulary; add/remove concept members; read exactly the members
back (empty when none); a concept in several collections; a member held once. The grouping MVP.
**Independent test**: the US-1 classes in `tests/test_models.py` green in isolation.
**Depends on**: #15 (`Concept`, `ConceptScheme`).

- [ ] T002 [US1] Write failing tests in `tests/test_models.py` (class `TestCollectionMembership`):
  create a collection, `add` two of three concepts → `members()` is exactly those two; a newly created
  collection's `members()` is empty (not an error); `add` the same concept twice → held once (one
  membership row, no raise); add a concept to a second collection → both report it, and `remove` from
  one leaves it in the other; `remove` a member → gone, others unaffected; two collections in one scheme
  whose names slugify equally → the second raises (slug collision); `add`/`remove` leave the concept's
  `uri`/`slug` unchanged.
- [ ] T003 [US1] In `controlled_vocabularies/models.py` add `Collection` (`scheme` FK
  `related_name="collections"`, `name`, `slug`, `ordered`; `members` M2M through `CollectionMember`;
  `UniqueConstraint(scheme, slug)`; `uri` property under `/collection/`; `save()` deriving/validating
  the slug per the `Concept.save` pattern; translatable metadata) and `CollectionMember` (`collection`
  FK `related_name="memberships"`, `concept` FK `related_name="collection_memberships"`, `position`;
  `UniqueConstraint(collection, concept)`; `Index(collection, position)`; translatable metadata). Add
  `Collection.add(concept)` (append; held-once no-op), `remove(concept)`, `members()` (set for now),
  and `Concept.collections()`, per `contracts/python-api.md`. `add` calls `full_clean()` on the
  membership before save.
- [ ] T004 [US1] `poetry run python -m django makemigrations controlled_vocabularies`; US-1 tests green
  in isolation.

**Checkpoint**: named collections hold members, overlap across collections, held once, identity stable.

## Phase 3: User Story 2 — A collection with a deliberate order (P2)

**Goal**: `ordered` collections read members by `position`; `add` appends; `set_member_order`
rearranges; removal keeps relative order; unordered collections make no order promise and refuse
`set_member_order`.
**Independent test**: the US-2 classes in `tests/test_models.py` green.
**Depends on**: US-1 (`Collection`, `CollectionMember`).

- [ ] T005 [US2] Write failing tests in `tests/test_models.py` (class `TestOrderedCollection`): on an
  `ordered=True` collection, `add` in a sequence → `members()` returns that sequence; `set_member_order`
  to a new sequence → `members()` reflects it; removing a middle member → survivors keep relative order;
  `set_member_order` on an unordered collection raises `ValidationError`; `set_member_order` whose set
  differs from the current members raises; an unordered collection's `members()` returns the correct set
  regardless of order.
- [ ] T006 [US2] Implement ordering in `controlled_vocabularies/models.py`: `Collection.members()`
  returns `position`-ordered concepts when `self.ordered` (else the set); `add` sets `position` = current
  max + 1; add `Collection.set_member_order(concepts)` — ordered-only (translatable not-ordered
  message), requires the given set to equal the current members, reassigns positions. No new field or
  migration expected (`position` exists from T003); confirm with `makemigrations --check`.
- [ ] T007 [US2] `poetry run python -m django makemigrations --check` clean (no schema change); US-2
  tests green.

**Checkpoint**: ordered collections carry and rearrange a deliberate sequence; unordered stay a set.

## Phase 4: User Story 3 — Membership stays inside the vocabulary and clear of the hierarchy (P2)

**Goal**: a member must be in the collection's own scheme (cross-vocabulary refused); membership asserts
no `broader`/`narrower`/`related` link and leaves an existing relation unchanged.
**Independent test**: the US-3 classes in `tests/test_models.py` green.
**Depends on**: US-1 (membership); #17 (`ConceptRelation`, for the orthogonality assertions).

- [ ] T008 [US3] Write failing tests in `tests/test_models.py` (class `TestMembershipIntegrity`): adding
  a concept from another scheme raises `ValidationError`; adding two concepts to a collection leaves each
  with empty `broader()`/`narrower()`/`related()`; two concepts already joined by a broader (and by a
  related) link keep that relation unchanged after both join a collection.
- [ ] T009 [US3] Add the scheme-confinement check to `CollectionMember.clean()`+`save()` backstop: refuse
  a membership whose `concept.scheme_id != collection.scheme_id` (FR-005) with a translatable
  named-placeholder message, holding on the `add()`/factory path. (Orthogonality, FR-008, needs no code
  — it is a property of separate tables; T008 asserts it.)
- [ ] T010 [US3] `makemigrations --check` clean (no schema change); US-3 tests green.

**Checkpoint**: membership is intra-vocabulary and provably independent of the relation graph.

## Phase 5: User Story 4 — Collection test scaffolding (P3)

**Goal**: factories build a populated collection and an ordered collection in a few lines.
**Independent test**: `tests/test_factories.py` green.
**Depends on**: US-1, US-2.

- [ ] T011 [P] [US4] In `tests/factories.py` add `CollectionFactory` and `CollectionMemberFactory` (and
  a small helper/trait building a populated collection and an ordered collection with a known sequence,
  going through `add`/`set_member_order` so validation and positions are honoured, members in the
  collection's own scheme); in `tests/test_factories.py` assert the populated collection reports its
  members and the ordered one reads its sequence back.

## Phase 6: User Story 5 — Translatable field metadata and deliberate indexing (P3)

**Goal**: the family metadata + indexing standard over the two new models.
**Independent test**: `tests/test_standards.py` green.
**Depends on**: US-1..US-3 (models and messages exist).

- [ ] T012 [US5] Extend `tests/test_standards.py`: the field walk already covers all concrete models —
  assert `Collection` and `CollectionMember` fields carry lazily-translatable non-empty `verbose_name` +
  `help_text`; assert the new validation messages (cross-vocabulary member, not-ordered guard) are lazy
  `Promise`s with named placeholders; assert `UniqueConstraint(collection, concept)`,
  `UniqueConstraint(scheme, slug)`, and `Index(collection, position)` exist (indexing decision recorded).
- [ ] T013 [US5] Make the models satisfy T012 — add any missing `verbose_name`/`help_text`; ensure every
  validation message uses `ValidationError(msgid, params=…)` lazy form with named placeholders (the
  #15/#16/#17 pattern).

## Phase 7: Polish, docs

- [ ] T014 [P] [Polish] README scope note + CHANGELOG entry: a vocabulary's concepts can now be grouped
  into named collections, optionally ordered, through the ORM, with the held-once and intra-vocabulary
  guarantees and the recorded no-nesting / no-admin boundaries. Run the humanizer over the changed public
  markdown before it lands.
- [ ] T015 [Polish] Full suite green across the matrix; `makemigrations --check` clean. (Migration squash
  to one file is the pipeline's S5 convergence step, not a code task.) This feature is additive; no
  supersession of #15/#16/#17 is expected — if any earlier decision record is affected, annotate in place
  per the cross-spec convention (do not delete).

## Dependencies & parallelism

- **Order**: Setup → US-1 → US-2 → US-3 → {US-4, US-5} → Polish. US-2/US-3 build on US-1's models; US-4
  and US-5 depend on the finished models. Phase-1 pipeline runs them sequentially on one worktree
  (shared `models.py`/migration).
- **Test-first**: within each story the failing-test task precedes its implementation task (Article I).
- **Migrations**: only US-1 adds schema (the two tables); US-2/US-3 add behaviour and one cross-table
  check, not columns — `makemigrations --check` must stay clean after them. The single migration is
  regenerated from zero at convergence (S5) and verified green.
- `[P]` marked only where files genuinely differ (T011 factories, T014 docs); model-test tasks share
  `tests/test_models.py` and are not parallel.
