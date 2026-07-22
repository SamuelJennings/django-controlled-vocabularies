# 1. SKOS-only scope

Date: 2026-07-22

## Status

Accepted

## Context

Controlled vocabularies in research infrastructure span SKOS, RDF, and OWL. Predecessor projects
(`django-research-vocabs`, then a general `rdflib`-builder) tried to stay format-general and became
diffuse — the API lost focus and the design never settled. In practice the vocabularies that need
managing are SKOS concept schemes.

## Decision

Target **SKOS only**. The models, editor, import, and export are shaped around SKOS concept
schemes, concepts, collections, labels, and semantic relations — not arbitrary RDF or OWL
ontologies, and with no reasoning/inference.

## Consequences

- The data model and UI can be shaped tightly around SKOS semantics rather than staying generic.
- Non-SKOS predicates encountered on import are preserved verbatim as escrow (see `0005`) but are
  not first-class modelled concepts — they round-trip, they are not "understood".
- OWL and general RDF needs remain rdflib's job; this package does not attempt them.
