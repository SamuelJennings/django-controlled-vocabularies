# Domain docs

This repository uses a single-context layout.

- **[`CONTEXT.md`](../../CONTEXT.md)** (repo root) — the ubiquitous language: every core domain
  term defined once, with synonyms-to-avoid. Read it before writing a spec or an issue so the work
  speaks the project's vocabulary.
- **[`docs/adr/`](../adr/)** — architectural decision records: the standing "why" behind the major
  design choices (models as source of truth, document-plus-projection storage, canonical-direction
  relations, URI identity, the shared/translated split, the predicate registry, the consumption
  field). One file per decision.
- **[`GOALS.md`](../../GOALS.md)** — what the project is for, who it serves, and what is out of
  scope; the maturity tiers that map to versions.

The domain *is* SKOS; `CONTEXT.md` maps this project's terms onto the SKOS standard.
