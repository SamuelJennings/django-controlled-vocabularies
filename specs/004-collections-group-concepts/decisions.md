# Decisions — FS-004 Collections that group concepts

Self-resolved ambiguities and the reasoning behind them. Grilling-level decisions are recorded
here; the gate-level trail lives on issue #18.

## D1 — No admin surface: align with the sibling slices (grilling)

**Ambiguous:** the intake framing and R1's roadmap text both name "the Django admin" as an R1
deliverable, and grilling initially carried "models + ORM + Django admin" into the statement-back.

**Chosen:** programmatic-only — models + ORM + tests, no Django admin or editor UI.

**Why:** all three landed R1 sibling slices (FS-001 #15, FS-002 #16, FS-003 #17) uniformly deferred
*every* admin/editor surface to roadmap R5 (the code-free management interface, G1); `admin.py` is
empty. Registering only Collection in admin would leave a half-built surface (schemes, concepts,
relations unregistered) and drag in Concept-admin work — searchable/autocomplete member pickers at
scale (G5) — that the siblings deferred. Flagged to Sam explicitly at grilling; he chose to align
with the siblings.

## D2 — No nested collections (grilling)

**Ambiguous:** SKOS permits a collection's members to be concepts *or* other collections (a shallow
tree of groupings).

**Chosen:** members are **concepts only**; no nesting this slice.

**Why:** nesting adds real model complexity (recursive membership, cycle concerns, ordered reads
over mixed member types) for a capability no one has asked for. Matches how CONTEXT.md phrases a
collection. Deferrable additively if a concrete need appears. Sam confirmed at grilling.

## D3 — Ordered-ness is a property of the collection (grilling)

**Ambiguous:** whether every collection always carries an (optional) order, or "ordered" is a
declared kind.

**Chosen:** a collection is either ordered (members carry a deliberate sequence) or unordered (a
plain set); ordered-ness is set on the collection. Confirmed by Sam.

**Why:** mirrors the SKOS `Collection` vs `OrderedCollection` distinction and keeps unordered
collections free of meaningless position bookkeeping.

## D4 — Collection carries a stable within-vocabulary identifier (self-resolved)

**Ambiguous:** the spec must round-trip (G4), but identity/URI mechanics for a collection were not
stated at intake.

**Chosen:** a collection gets a name plus a derived, URI-composable identifier, following the
existing `ConceptScheme` / `Concept` slug+`uri`-property precedent; two collections in one
vocabulary are distinguishable by it. The RDF *serialization* is deferred to R2/R4.

**Why:** Article IX makes identity-as-URI a day-one invariant for the domain; a collection that
managed vocabularies hold must be identifiable to survive export. Reuses the settled precedent
rather than inventing a new identity mechanism. Defensible from grilling context.

## D5 — Duplicate membership held once; intra-vocabulary confinement (self-resolved)

**Chosen:** a (collection, concept) membership is unique (a set, not a multiset), enforced by a DB
constraint; a member must belong to the collection's own vocabulary.

**Why:** consistent with the dedup and intra-vocabulary precedents FS-003 set for relations. Both
are the integrity guarantees a curator most needs. Defensible from grilling context.

## D6 — Removal semantics deferred to #19 (self-resolved)

**Chosen:** how a member concept is retired (deprecation not deletion; `PROTECT`) is #19's concern;
this slice only adds collections and membership referencing existing concepts.

**Why:** matches the FS-003 boundary; #19 (lifecycle) explicitly owns safe removal and depends on
this slice. Confirmed with Sam at grilling that lifecycle is a later spec.
