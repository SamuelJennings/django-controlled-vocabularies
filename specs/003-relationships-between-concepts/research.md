# Research — 003-relationships-between-concepts

Phase 0 decisions. Each resolves a design question the plan depends on. The overarching design
(`docs/brainstorm.md` "Relations: a canonical-direction self-referencing link") is the starting
point; this file records the concrete choices made for this slice.

## R1 — Storage: one through model, canonical direction stored, inverse derived

**Decision.** A single `ConceptRelation` through model on `Concept`: `source` FK, `target` FK,
`kind` (a `TextChoices` of `BROADER` and `RELATED`). The hierarchy stores exactly one row per
edge — `source skos:broader target` (source is the narrower/child, target is the broader/parent) —
and the `narrower` direction is read back by querying rows whose `target` is the concept. `related`
stores one canonical row per unordered pair.

**Why.** `docs/brainstorm.md`: "persist `broader` and derive the inverse (read `narrower` back), so
the data can never assert one direction without the other." One stored direction makes the
inverse-pair guarantee (FR-002) a property of the schema rather than something application code has
to keep in sync. A through model (rather than a bare `ManyToManyField('self')`) is required because
the edge carries a `kind` and because the two kinds have different symmetry.

**Rejected.** (a) A `ManyToManyField('self', symmetrical=False)` per relation type — three fields
(`broader`, `related`) with no shared row shape, and `symmetrical=True` cannot be combined with a
custom `through` in a way that also stores `narrower` without duplication. (b) Storing both
directions of `broader` — doubles rows and reintroduces the drift the single-direction rule exists
to prevent. (c) A tree library (`django-mptt`/`treebeard`) — single-parent trees cannot represent
polyhierarchy (a concept with several broader concepts), which SKOS and FR-001 require.

## R2 — `related` symmetry: canonicalise the pair at write time

**Decision.** A `RELATED` row is stored with its endpoints ordered deterministically by primary key
(`source_id < target_id`). The write path (`Concept.add_related`) canonicalises before insert, so
asserting `a related b` and `b related a` resolve to the same row. Reads
(`Concept.related(...)`) return the *other* endpoint regardless of which column the concept sits in.

**Why.** SKOS `related` is symmetric; `docs/brainstorm.md` says "normalise the symmetric related to
one row." Ordering by PK gives a stable canonical form and lets the ordinary
`UniqueConstraint(source, target, kind)` (R3) catch a duplicate asserted in either order — no
separate unordered-pair machinery needed.

**Rejected.** Storing both `(a,b)` and `(b,a)` rows for one association (drift risk, and a duplicate
check that has to look both ways); a symmetric hash column (more storage and code than PK ordering
buys). PK ordering is safe here because both endpoints are persisted before a relation is created
(a relation between unsaved concepts is meaningless).

## R3 — Integrity: constraints where the DB can express them, `clean()`/`save()` where it can't

**Decision.**

- **No self-relation** (FR-006): a `CheckConstraint(~Q(source=target))` plus a `clean()` check for a
  friendly message.
- **No duplicate** (FR-007): `UniqueConstraint(source, target, kind)`. With R2's canonicalisation this
  also blocks a mirror-order `related` duplicate. A duplicate `broader` in the *opposite* direction
  (`a broader b` vs `b broader a`) is a different, permitted edge (a 2-cycle — allowed under the cycle
  deferral), so the ordered unique constraint is exactly right.
- **broader/related disjointness** (FR-008): checked in `clean()`/`save()`, because it spans an
  *unordered pair across two kinds* and cannot be a single-table DB constraint. When adding a relation
  between `a` and `b`, refuse it if a relation of the *other* kind already joins `{a, b}` in either
  direction. This is a single indexed lookup on the pair — no hierarchy traversal.
- **Intra-vocabulary** (FR-009): `source.scheme_id == target.scheme_id`, checked in `clean()`/`save()`
  (a cross-table equality no single-table constraint can express).

**Why the `save()` backstop.** `Model.clean()` runs only under `full_clean()`; `.objects.create()`,
`bulk_create`, and factories bypass it. #15/#16 established the repo pattern of re-checking
constraint-less invariants in `save()` so no bad row can be planted through any path (see
`ConceptLabel._reject_default_language_preferred`). The relation invariants that have no DB
constraint (disjointness, intra-vocabulary) follow that pattern. The write helpers
(`add_broader`/`add_related`) call `full_clean()` for the friendly-message path; `save()` is the
backstop.

**Cycle prevention (FR-010) is explicitly out.** Detecting a cycle needs a walk up the `broader`
chain on every insert — the traversal this slice avoids. Disjointness is therefore also scoped to
*direct* adjacency (not the transitive closure) for the same cost reason; both are recorded
deferrals (spec Assumptions, `decisions.md`). Recursive-CTE subtree queries land with the feature
that first needs them (subtree-scoped autocomplete, R3-consume), not here.

## R4 — Read API shape: explicit methods, not M2M descriptors

**Decision.** Expose `Concept.broader()`, `narrower()`, `related()` (returning `Concept` querysets)
and `add_broader`/`add_related`/`remove_broader`/`remove_related`, mirroring #16's explicit helper
style (`preferred_label`, `alt_labels`, `add_label`). No public `ManyToManyField` descriptor.

**Why.** The three reads have different shapes — `broader`/`narrower` are inverse directional reads
of one stored kind, `related` is a symmetric read spanning both columns — which a single Django M2M
accessor cannot express cleanly. Explicit methods keep the semantics obvious and match the
established model surface (Anti-Abstraction: no descriptor machinery that fights the data). The
methods return querysets so a caller can filter/order/`prefetch` further.

## R5 — No new runtime dependency

**Decision.** Nothing new is added. Relations are ordinary FKs and constraints on the existing
`django.db.models` surface.

**Why.** Constitution Art. VII / II. `rdflib` (RDF projection of `skos:broader`/`narrower`/`related`)
belongs to the export feature (R2/R4), not here; `deptry` would fail an unused declared dep.

## R6 — Indexing

**Decision.** `source` and `target` FKs are auto-indexed. The `UniqueConstraint(source, target, kind)`
gives a `source`-leading composite index (covers "a concept's outgoing relations of a kind"). Add one
explicit `Index(target, kind)` for the reverse reads — derived `narrower` (query by `target`,
`kind=BROADER`) and the incoming half of `related` — so both directions are indexed by deliberate
decision, not left to the bare `target` FK index. Recorded per Art. XIII.
