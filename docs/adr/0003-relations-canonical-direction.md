# 3. Concept relations: a canonical-direction self-referencing M2M

Date: 2026-07-22

## Status

Accepted

## Context

SKOS concepts form a graph: `broader`/`narrower` (an inverse pair), `related` (symmetric), plus
cross-vocabulary mappings (`exactMatch`, `broadMatch`, …). SKOS explicitly permits **polyhierarchy**
— a concept may have several broader concepts — which single-parent tree libraries (MPTT,
treebeard, as used by comparable editors) structurally cannot represent.

## Decision

Model intra-vocabulary relations as a **self-referencing `ManyToMany` on `Concept` with a
`through` model carrying a `relationship_type`** field. Rules:

- **Store one canonical direction; derive the inverse.** Persist `broader` rows only; `narrower`
  is the reverse accessor. The UI may display both directions, but only one is stored, so the data
  can never assert one direction without the other.
- **Normalise the symmetric relation.** `related` is stored once (e.g. lower-URI-first) — one fact,
  one row.
- **Mappings are not relations.** Cross-vocabulary mappings usually point at URIs with no local
  row, so they cannot be a local FK/M2M. They live in the JSON document (see `0005`), or a
  dedicated mapping model later if they need to be queryable.

## Consequences

- Polyhierarchy is represented natively; export is unambiguous.
- Subtree queries ("all descendants of X") require recursive CTEs rather than a tree-library
  one-liner — provided via a manager method (e.g. `django-tree-queries` or a raw CTE). This is a
  day-one need for subtree-scoped autocomplete.
- The M2M holds only intra-database relations; mapping fidelity is the escrow's job.
