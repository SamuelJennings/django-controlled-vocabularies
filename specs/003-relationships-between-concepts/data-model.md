# Data model — 003-relationships-between-concepts

One new model, `ConceptRelation`, and read/write helpers on the existing `Concept`. No change to
`Concept`'s own fields or to `ConceptScheme`. Terminology follows `CONTEXT.md` (**Relation**,
**Concept**, **ConceptScheme**).

## New model: `ConceptRelation`

A directed row linking two concepts in the same vocabulary, carrying the relation `kind`. One row per
hierarchy edge (canonical direction stored); one row per `related` pair (canonicalised by PK order).

| Field | Type | Rules |
|---|---|---|
| `source` | FK → `Concept`, `on_delete=CASCADE`, `related_name="relations_as_source"` | the narrower/child for `BROADER`; the lower-PK endpoint for `RELATED` |
| `target` | FK → `Concept`, `on_delete=CASCADE`, `related_name="relations_as_target"` | the broader/parent for `BROADER`; the higher-PK endpoint for `RELATED` |
| `kind` | `CharField(max_length=16, choices=Kind.choices)` | `BROADER = "broader"` or `RELATED = "related"` |

`Kind` is a `models.TextChoices`: `BROADER = "broader"`, `RELATED = "related"`. `narrower` is **not**
a stored kind — it is the inverse read of `BROADER`.

**`on_delete=CASCADE` is correct here and does not contradict Article IX.** Article IX's `PROTECT`
governs *references from consumer data* to a concept (the consumption field, R3) and *deprecation vs
deletion* of a referenced concept (the lifecycle, #19). A `ConceptRelation` is not consumer data — it
is the edge itself; if a concept is removed, its own edges go with it. How a concept that
participates in relations is *retired* is #19's concern (deprecation, not deletion), unchanged by this
slice.

### Meta

- `verbose_name = _("concept relation")`, `verbose_name_plural = _("concept relations")`.
- `ordering = ("source", "kind", "target")`.
- **Constraints:**
  - `UniqueConstraint(fields=["source", "target", "kind"], name="unique_concept_relation")` — blocks a
    duplicate edge (FR-007); with PK-ordered `RELATED` (research R2) it also blocks a mirror duplicate.
  - `CheckConstraint(condition=~Q(source=F("target")), name="concept_relation_not_self")` — blocks a
    self-relation at the DB (FR-006).
- **Indexes:**
  - `Index(fields=["target", "kind"], name="cv_relation_target_kind_idx")` — the reverse reads
    (derived `narrower`, incoming `related`) (FR-012, research R6). `source`-leading is covered by the
    unique constraint; both FKs are auto-indexed.

### Validation (`clean()` + `save()` backstop)

`clean()` raises `ValidationError` with translatable, named-placeholder messages; `save()` re-checks
the constraint-less invariants so no bad row is planted via `create()`/factories (the #15/#16
pattern). Invariants:

1. **Not self** (FR-006) — `source_id == target_id` refused. (DB `CheckConstraint` backstop.)
2. **Same vocabulary** (FR-009) — `source.scheme_id != target.scheme_id` refused. Message names the
   two vocabularies via placeholders.
3. **Disjointness** (FR-008) — refuse if a relation of the *other* `kind` already joins the unordered
   pair `{source, target}` in either stored direction. Evaluated against directly-asserted rows only
   (no traversal). Message names the conflicting kind.
4. **Duplicate** (FR-007) — the unique constraint is the backstop; `clean()` surfaces a friendly
   message when the ordered triple already exists (including a `RELATED` re-asserted mirror-order,
   which canonicalises to the same triple).

Cross-`kind` disjointness and the same-vocabulary rule have **no** single-table DB constraint (they
span two rows / two tables), so `save()` is their only hard backstop — hence the re-check there.

## `Concept` — new helpers (no field changes)

Read (return `Concept` querysets, empty when none — FR-004/FR-007):

- `broader()` — targets of `BROADER` rows where `self` is `source`.
- `narrower()` — sources of `BROADER` rows where `self` is `target` (the derived inverse).
- `related()` — the other endpoint of every `RELATED` row touching `self` (either column).

Write (validate then persist; never touch `self.slug`/`uri` — FR-004/FR-005):

- `add_broader(other) -> ConceptRelation` — creates `BROADER` `self → other` (self narrower).
- `add_related(other) -> ConceptRelation` — creates a PK-canonicalised `RELATED` row; a mirror
  re-assert resolves to the existing row (FR-003/FR-007).
- `remove_broader(other) -> None`, `remove_related(other) -> None` — delete the matching edge if
  present; a no-op when absent (FR-005).

All write helpers call `full_clean()` before save so the friendly validation messages fire on the
`add_*` path; the model `save()` backstops the create/factory path.

## Fields touched elsewhere

None. `Concept` and `ConceptScheme` field sets are unchanged; only methods are added to `Concept`.

## Migration

One migration adds `ConceptRelation` (table, unique constraint, check constraint, index). No data
migration. Squashed to a single file at convergence (Article XIII), regenerated from zero and verified.
