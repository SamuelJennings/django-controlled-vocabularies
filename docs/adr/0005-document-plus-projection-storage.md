# 5. Document-plus-projection storage

Date: 2026-07-22

## Status

Accepted

## Context

The SKOS schema defines many predicates, but published vocabularies populate only a small core
(prefLabel, definition, hierarchy) and leave the long tail empty. Declaring thirty sparse nullable
columns buys migration weight and little else, and hand-mixed schemas in the wild (e.g.
`dcterms:description` where `skos:definition` was meant) don't fit fixed columns cleanly.

## Decision

A concept's editable state is a **JSON document of predicate→object pairs — the sole source of
truth** for its literal-valued and unknown predicates. A small set of hot predicates (`uri`,
`pref_label`, `definition`) are **projected into concrete, read-only, indexed columns**, synced
from the document in `save()`. The document holds everything; the columns are a **materialised
index derived from it**, never separately editable — so there is exactly one editable
representation and the columns can never drift from it.

Boundaries:

- **Relations never go in the document** — they are FK/M2M (`0003`). The document is for
  literal-valued and unknown predicates, plus cross-vocabulary mappings.
- **Import normalises via a configurable predicate-alias map** (`dcterms:description` → the
  `definition` predicate), surfaced to the user because it changes the data on re-export. Unmapped
  predicates fall through to the document untouched — lossless escrow.
- The document carries a `_schema` version key from day one.

## Consequences

- One editable representation → no drift between "the document" and "the columns".
- The document doubles as the round-trip escrow (`0001`) for **managed** vocabularies: unknown
  predicates are preserved verbatim. Imported external vocabularies are instead normalised to what
  the app supports (see `0006`), so external imports are deliberately lossy, not escrowed.
- **Writes must go through the sync path.** Bulk operations (`QuerySet.update`, `bulk_create`,
  `bulk_update`) bypass `save()`; all write paths — including the importer — must call an explicit
  `sync_from_json()`, and a `CheckConstraint` (non-empty `pref_label`) is the database backstop.
- Searching document-only predicates uses a JSONB GIN index; the 95% case (URI, prefLabel,
  definition) hits indexed columns. Individual hot JSON keys can be indexed later if needed.
