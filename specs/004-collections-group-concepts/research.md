# Research — 004-collections-group-concepts

Phase 0 decisions. Each resolves a design question the plan depends on. The overarching design
(`docs/brainstorm.md` and CONTEXT.md's `Collection` entry — "a grouping of concepts within a scheme,
optionally ordered") is the starting point; this file records the concrete choices for this slice.

## R1 — Two models: `Collection` + a `CollectionMember` through model

**Decision.** A `Collection` model (`scheme` FK, `name`, derived `slug`, `ordered` boolean) and a
`CollectionMember` through model (`collection` FK, `concept` FK, `position`). Membership is
`ManyToManyField(Concept, through=CollectionMember)` on `Collection`.

**Why.** The membership edge carries `position` (for ordered collections) and must be validated for
scheme-confinement, so it needs an explicit through model — a bare `ManyToManyField` gives neither a
per-row column nor a validation hook. `Collection` is a first-class SKOS object (`skos:Collection`)
with its own identity, so it is a model, not a tag string. Mirrors #17's through-model precedent
(`ConceptRelation`).

**Rejected.** (a) A bare `ManyToManyField(Concept)` — no room for `position`, no scheme check. (b)
Reusing `ConceptRelation` with a new `kind` — a collection is a container with its own name/identity,
not an edge between two concepts; overloading the relation table would conflate two mechanisms the spec
keeps separate (FR-008). (c) A JSON list of concept ids on `Collection` — loses referential integrity
and the held-once constraint, and can't be queried from the concept side (`Concept.collections()`).

## R2 — Ordering: a hand-rolled `position` integer, ordered read is `ORDER BY position`

**Decision.** `CollectionMember.position` is a `PositiveIntegerField`. `Collection.add(concept)` appends
(position = current max in the collection + 1). `Collection.members()` returns concepts ordered by
`position` when the collection is `ordered`, and as a plain set otherwise. `Collection.set_member_order`
reassigns positions to a caller-supplied sequence and is only valid on an ordered collection.

**Why.** The two ordered guarantees the spec asks for (FR-006/FR-007) fall straight out of an integer
sort key: a deliberate sequence *is* the ascending `position` order, rearranging *is* reassigning
positions, and removing a member leaves the survivors' relative order intact because a gap between
integers does not affect `ORDER BY`. No gap-compaction, no rebalancing, no library.

**Rejected.** See R5 for the dependency evaluation. A float/fraction position (to insert without
touching neighbours) is unnecessary here — reorders are whole-list `set_member_order` operations, not
single-item drag-inserts, so integer reassignment is simplest.

## R3 — Integrity: DB constraint for held-once, `clean()`/`save()` for scheme-confinement

**Decision.**

- **Held once** (FR-004): `UniqueConstraint(collection, concept)` on `CollectionMember`. A second add of
  the same concept is refused at the database; `add()` is idempotent-safe via a friendly `clean()`
  check first.
- **Intra-vocabulary** (FR-005): `collection.scheme_id == concept.scheme_id`, checked in
  `clean()`/`save()` on `CollectionMember` — a cross-table equality no single-table constraint can
  express, with a translatable named-placeholder message. Enforced on the `add()`/factory path, not only
  `full_clean()`, matching #15/#16/#17.
- **No relation asserted** (FR-008): automatic — membership lives in `CollectionMember`, relations in
  `ConceptRelation`; they share no state. Tested by asserting `broader/narrower/related` are unchanged
  after shared membership, not enforced by code.

**Why.** Same split as #17: the DB expresses what a single table can (uniqueness), application code
expresses the cross-table rule (same scheme), and orthogonality is a property of the schema rather than
something to enforce.

## R4 — Collection URI namespaced under `/collection/`

**Decision.** `Collection.uri` is composed as `{scheme.uri}/collection/{slug}` (a property, like
`ConceptScheme.uri` and `Concept.uri`). The `slug` is derived from `name` and unique within the scheme
(`UniqueConstraint(scheme, slug)`).

**Why.** A concept's URI is `{scheme.uri}/{slug}`. Without a distinguishing segment, a collection and a
concept sharing a slug would mint the same URI. The `/collection/` segment keeps the two identity spaces
disjoint so RDF projection (R2/R4) can emit stable, non-colliding collection URIs later. Identity as URI
is an Article IX day-one concern, so the collection gets a stable identifier now even though the RDF
*serialization* is deferred.

**Rejected.** Sharing the concept namespace (collision risk); a UUID URI (opaque, not human-meaningful,
breaks the readable-slug precedent the scheme/concept set).

## R5 — Ordering dependency evaluated and rejected: `django-ordered-model`

**Decision.** Do **not** add `django-ordered-model` (or any ordering library). Hand-roll `position`
(R2).

**Why.** Sam flagged `django-ordered-model` for consideration during planning. Evaluated against this
repo's constraints:

- **Maintenance/compat, the decisive factor.** Its last PyPI release is **3.7.4, March 2023**. The
  upstream test matrix (even on `master`, last touched Nov 2024) reaches only **Django 5.1** — there is
  **no Django 5.2 LTS and no Django 6.0** anywhere in its tox envlist or open PRs. This repo's CI
  *requires* green on Django 5.2 and 6.0 (Article X; the seven required checks). The library would fail
  the 6.0 legs, or pass only incidentally on unmaintained code.
- **Longevity.** The package exists to replace bespoke vocabulary code with something that evolves for
  years (Article VIII). Anchoring a core domain model to a dependency with no release in two years and
  no support for the current Django is exactly the debt Article VII exists to prevent.
- **Cost of the alternative is trivial.** Ordering here is one integer field and an `ORDER BY` (R2); the
  library's headline feature (gap-free reordering) is unnecessary because gaps are harmless in an
  ordered read.

**Rejected library, chosen hand-roll.** Recorded in `plan.md` Complexity Tracking and `decisions.md`
(D7). If a *maintained* ordering need ever spans several models, revisit — but one through-model does
not justify the dependency.

## R6 — Helper API shape mirrors #16/#17

**Decision.** `Collection.add(concept)`, `Collection.remove(concept)`, `Collection.members()`,
`Collection.set_member_order(concepts)`, and `Concept.collections()`. `add`/`set_member_order` validate
via `full_clean()` on the membership before saving, so refusals fire on the ordinary write path.

**Why.** Consistent with the explicit read/write helpers #16 (`preferred_label`, `alt_labels`) and #17
(`broader`, `add_broader`) established, rather than exposing raw `CollectionMember` manipulation to
callers. Keeps the contract small and the validation centralised.
