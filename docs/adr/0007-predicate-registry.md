# 7. A predicate registry drives the editor

Date: 2026-07-22

## Status

Accepted

## Context

The editor is a key→value document editor: rows of predicate → object, added as needed, with the
predicate chosen from a dropdown. A flat string→string widget cannot express what vocabulary data
needs: values have RDF types (a `definition` is a language-tagged literal; an `exactMatch` is a
URI; a `notation` is a typed literal; an `altLabel` is a *list*), and predicates have cardinality
(one prefLabel per language; many altLabels). Guessing a value's type from its string (e.g. "starts
with http") produces malformed RDF.

## Decision

Maintain a **predicate registry**: a curated map of CURIE →
`{value_type: literal|uri|typed, cardinality: one|many, translatable: bool}`. Five things read
from it:

1. the editor's predicate dropdown contents,
2. the per-row widget (text vs URI vs list editor),
3. form/serializer validation (cardinality, value type),
4. the shared-vs-translated routing (`0006`),
5. the import predicate-alias normalisation (`0005`).

Unregistered predicates remain fully supported — free-text key, string value, escrow semantics —
so arbitrary vocabularies still import losslessly. The registry makes the *known* predicates safe
and pleasant; it never gates the *unknown* ones.

## Consequences

- Export emits correct `URIRef` vs `Literal` vs typed literals because the type is declared, not
  guessed.
- One data structure keeps the editor, validation, storage routing, and import normalisation
  consistent — change a predicate's rules in one place.
- The SKOS core registry ships with the package; deployments can extend it for their own predicates.
