# Domain docs

This repository uses a single-context layout.

- **[`CONTEXT.md`](../../CONTEXT.md)** (repo root) — the ubiquitous language: every core domain
  term defined once, with synonyms-to-avoid. Read it before writing a spec or an issue so the work
  speaks the project's vocabulary.
- **[`docs/adr/`](../adr/)** — one record per architecturally significant decision, kept for the
  reasoning behind it: URI identity, canonical-direction relations, how a restriction is derived,
  what happens to an upstream defect, and the rest.
- **[`GOALS.md`](../../GOALS.md)** — what the project is for, who it serves, and what is out of
  scope.
- **[`docs/index.md`](../index.md)** — the adopter-facing manual: configuration, the model fields,
  choosing a concept, browsing, and importing.

The domain *is* SKOS; `CONTEXT.md` maps this project's terms onto the SKOS standard.
