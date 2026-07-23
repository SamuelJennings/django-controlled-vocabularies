# Decision record — 001-vocabulary-concepts

Ambiguities resolved without escalation while specifying, with the reasoning that makes each
defensible. Gate-level decisions live on issue #15; this file carries the fine grain.

## Self-resolved at specify

1. **A concept carries one plain preferred label in this slice.**
   Ambiguous because full label modelling belongs to sibling #16, yet the identity design derives
   the concept slug from the preferred label, so this slice needs one. Resolved to a single
   default-language label that #16 later grows into the multilingual model. Grounded in the
   intake discussion: the concept slug is "based off of the preferred label of the concept".

2. **Notation codes are deferred.**
   Notation is identity-adjacent (a language-independent code), so it was a candidate for this
   slice. Excluded: identity here composes from slugs, and no requirement in this slice consumes
   a notation. First feature that needs it models it.

3. **The URI base address is deployment configuration; the mechanism is left to planning.**
   The spec fixes only the composition rule (base + vocabulary slug + concept slug) and its
   determinism. How the base is configured is not a user-visible property of this feature.

4. **Slug collisions are refused, not auto-disambiguated.**
   Two concepts in one vocabulary whose labels slug identically could be silently suffixed
   (`heat-flow-2`) or rejected. Rejected is the honest behaviour for curated vocabularies: a
   silent suffix mints an identifier the curator never chose, and identifiers are this
   feature's whole point. The curator resolves the wording.

5. **Deleting a vocabulary deletes its concepts.**
   A concept cannot exist outside a vocabulary, and lifecycle/protected-removal is sibling #19.
   Documented as an edge case with a test so the behaviour is explicit, not accidental.

## Deferred by design (recorded so later constitution checks read them as deliberate)

- **Constitution Article IX mechanisms** (lifecycle states, deprecation-not-deletion, PROTECT
  references, upsert-by-URI): deferred to siblings #19 (lifecycle) and the import feature
  (upsert). This slice contains no import and no external references, so the invariants have no
  surface here yet. The identity groundwork (URI as identity, never the database key) IS
  honoured here.
- **Identifier freezing at publish** (constitution Article VIII data contract): the publishing
  feature. All identifiers in this slice are computed and dynamic.
- **Architectural note to land as an ADR (agreed at intake):** the internal storage shape is not
  raw JSON-LD/RDF; RDF serializations are produced only at the import/export boundary. To be
  authored when the boundary features arrive, or earlier as a docs change.
