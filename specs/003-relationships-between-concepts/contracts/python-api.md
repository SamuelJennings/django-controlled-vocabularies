# Public API contract — 003-relationships-between-concepts

The ORM surface a downstream developer touches. This is the tested contract (Article IV). All reads
return querysets of `Concept`; all writes validate and raise `django.core.exceptions.ValidationError`
on an invalid edge.

## `Concept` methods

```python
# --- reads (empty queryset when none) ---
concept.broader()   -> QuerySet[Concept]   # concepts one step broader than `concept`
concept.narrower()  -> QuerySet[Concept]   # concepts one step narrower (derived from broader)
concept.related()   -> QuerySet[Concept]   # concepts related to `concept` (symmetric, both directions)

# --- writes ---
concept.add_broader(other)    -> ConceptRelation   # `concept` skos:broader `other`  (concept is narrower)
concept.add_related(other)    -> ConceptRelation   # symmetric; order-independent
concept.remove_broader(other) -> None              # no-op if the edge is absent
concept.remove_related(other) -> None              # no-op if the edge is absent
```

### Guarantees

- **Inverse pair.** After `a.add_broader(b)`: `b in a.broader()` and `a in b.narrower()`, from the one
  call. No `narrower` is ever asserted directly. (FR-001, FR-002 · SC-001)
- **Polyhierarchy.** `a.add_broader(b); a.add_broader(c)` → `a.broader()` contains both. (FR-001)
- **Symmetric related.** After `a.add_related(b)`: `b in a.related()` and `a in b.related()`. `b.add_related(a)`
  afterwards raises (duplicate) rather than storing a second row. (FR-003 · SC-002)
- **Removal.** `remove_broader`/`remove_related` clear both directions of the edge; calling with an
  absent edge does nothing. (FR-005)

### Refusals (raise `ValidationError`)

| Attempt | Rule |
|---|---|
| `a.add_broader(a)` / `a.add_related(a)` | no self-relation (FR-006 · SC-003) |
| the same `broader` edge twice, or `related` re-asserted in either order | no duplicate (FR-007 · SC-004) |
| `add_related(b)` when `a`/`b` are already in a direct broader/narrower line (or the reverse) | broader/related disjointness, direct pairs (FR-008 · SC-005) |
| a relation whose two concepts are in different `ConceptScheme`s | intra-vocabulary only (FR-009 · SC-006) |

### Explicitly permitted

- A cyclic `broader` chain (`a→b→c→a`) is accepted without error; no traversal is performed. Cycle
  prevention is a recorded non-guarantee this slice. (FR-010 · SC-007)
- A `related` link between concepts that are only *transitively* (not directly) hierarchical is
  accepted — disjointness is checked at direct adjacency only.

## `ConceptRelation` model

A public model (importable), but the `Concept` helpers are the intended surface. Fields: `source`,
`target`, `kind` (`ConceptRelation.Kind.BROADER` / `.RELATED`). Direct construction is validated the
same as the helper path (`save()` backstops `clean()`), so a raw `ConceptRelation.objects.create(...)`
with an invalid edge also raises.

## Stability

Pre-1.0 (Article VIII): this Python API may still change to correct mistakes, recorded in the
CHANGELOG. Nothing here is a frozen data contract — the RDF projection of these relations
(`skos:broader`/`skos:narrower`/`skos:related`) is a later feature (R2/R4) and is where the data
contract will attach.
