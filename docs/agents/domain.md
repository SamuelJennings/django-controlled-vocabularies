# Domain docs

This repository uses a single-context layout.

- **[`CONTEXT.md`](../../CONTEXT.md)** (repo root) holds the ubiquitous language: every core domain
  term defined once, with synonyms to avoid. Read it before writing a spec or an issue so the work
  speaks the project's vocabulary.
- **[`docs/brainstorm.md`](../brainstorm.md)** holds the early design notes: the reasoning behind
  the major design leanings (models as source of truth, document-plus-projection storage,
  canonical-direction relations, URI identity, the shared/translated split, the predicate registry,
  the consumption field).
- **[`GOALS.md`](../../GOALS.md)** covers what the project is for, who it serves, and what is out of
  scope.

The domain *is* SKOS; `CONTEXT.md` maps this project's terms onto the SKOS standard.
