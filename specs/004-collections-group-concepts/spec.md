# Feature Specification: Collections that group concepts

**Feature Branch**: `004-collections-group-concepts`

**Created**: 2026-07-25

**Status**: Draft

**Input**: Issue [#18](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/18) — "A curator should be able to gather concepts within a vocabulary into named collections, optionally in a deliberate order, to capture groupings that aren't part of the broader/narrower hierarchy."

**Serves**: G4 (faithful round-trip of managed vocabularies — a collection is part of what a managed vocabulary holds and must survive export) · **Roadmap**: R1 · **Issue**: #18

> Scope note: this feature is one slice of roadmap item R1. It adds the last structural piece the foundation lacks: a **Collection** — a named grouping of concepts *within a single vocabulary* (established in [#15](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/15), enriched with multilingual names in [#16](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/16) and a relation graph in [#17](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/17)). A collection may be unordered or carry a deliberate member order, and its membership is orthogonal to the broader/narrower hierarchy — it captures how a curator wants a vocabulary organised and displayed, not a semantic relation. Interaction is purely programmatic — through the ORM, no admin or editor UI (that is roadmap R5, matching the precedent set by #15, #16, and #17). **Out of scope:** nested collections (a collection's members are concepts only, never other collections — see Assumptions), the broader/narrower hierarchy and the related association (#17, already delivered), cross-vocabulary membership, the concept lifecycle and safe removal ([#19](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/19)), and RDF import/export of collections (R2/R4).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gather concepts into a named collection (Priority: P1)

A curator building their own vocabulary gathers a handful of its concepts into a named collection — "Common igneous rocks" — to capture a grouping that the broader/narrower hierarchy does not express. They add concepts to the collection and read its members back; the same concept can also sit in another collection ("Rocks pictured in the field guide") without either grouping disturbing the other.

**Why this priority**: This is the core of the feature and the whole of what the issue asks for at its simplest — a named, curator-defined grouping of concepts that is not the hierarchy. Implemented alone it is a viable, useful capability: a vocabulary can be organised into overlapping named sets. Everything else refines it.

**Independent Test**: In a test, create a vocabulary with several concepts, create a collection, add three of them, read the members back and assert exactly those three appear; add one of them to a second collection and assert both collections report it and neither is disturbed by the other.

**Acceptance Scenarios**:

1. **Given** a vocabulary with concepts "Granite", "Basalt", and "Quartz", **When** the curator creates a collection "Common igneous rocks" and adds "Granite" and "Basalt", **Then** the collection reports exactly "Granite" and "Basalt" as members and not "Quartz".
2. **Given** that collection, **When** the curator also adds "Granite" to a second collection "Field-guide rocks", **Then** both collections report "Granite", and removing "Granite" from one leaves it in the other.
3. **Given** a collection with members, **When** the curator removes a member, **Then** the collection no longer reports it and the remaining members are unaffected.
4. **Given** a newly created collection with no members, **When** its members are read, **Then** the result is empty — not an error.
5. **Given** a concept already in a collection, **When** the curator adds the same concept again, **Then** the membership is held once, not duplicated.

---

### User Story 2 - A collection with a deliberate order (Priority: P2)

A curator marks a collection as **ordered** and arranges its members into a deliberate sequence — the order the concepts should be presented in, which is neither alphabetical nor the hierarchy. Reading the ordered collection back returns its members in exactly that sequence; rearranging them changes what subsequent reads return. A collection left unordered asserts no sequence over its members.

**Why this priority**: "Optionally in a deliberate order" is the second thing the issue explicitly asks for, and ordered presentation is what distinguishes a curated display list from a plain set. It builds directly on US-1's grouping and is not needed for an unordered grouping to be correct, so it follows at P2.

**Independent Test**: In a test, create an ordered collection, add members in one sequence, read them back and assert the sequence is preserved, rearrange two of them and assert the new sequence reads back; separately assert an unordered collection makes no order guarantee.

**Acceptance Scenarios**:

1. **Given** an ordered collection, **When** the curator adds "Basalt", then "Granite", then "Gabbro" in a chosen sequence, **Then** reading the collection's members returns them in that same sequence.
2. **Given** that ordered collection, **When** the curator rearranges the members so "Gabbro" comes first, **Then** subsequent reads return the new sequence.
3. **Given** an ordered collection of three members, **When** the middle member is removed, **Then** the two remaining members read back in their original relative order, with no gap that breaks the read.
4. **Given** a collection that is **not** marked ordered, **When** its members are read, **Then** no particular sequence is promised — the collection is a set, and ordering carries no meaning for it.

---

### User Story 3 - Membership stays inside the vocabulary and clear of the hierarchy (Priority: P2)

A curator cannot, by mistake or otherwise, pull a concept from a *different* vocabulary into a collection — a collection groups the concepts of its own vocabulary and nothing else — and putting a concept into a collection never asserts that it is broader than, narrower than, or related to any other member. The grouping is an organisational overlay, sealed off from the semantic graph.

**Why this priority**: Scheme confinement is the integrity guarantee the curator most needs protecting from, and the independence-from-hierarchy promise is what keeps a collection from being mistaken for a relation (and keeps the exported SKOS meaningful). Both span the whole membership mechanism, so they are expressed once US-1 exists, at P2 alongside ordering.

**Independent Test**: In a test, attempt to add a concept belonging to another vocabulary to a collection and assert refusal; add two concepts to a collection and assert that neither gains a broader, narrower, or related link to the other as a result.

**Acceptance Scenarios**:

1. **Given** a collection in vocabulary A and a concept in vocabulary B, **When** the curator attempts to add the vocabulary-B concept to the collection, **Then** the system refuses it with a translatable message — a collection groups only its own vocabulary's concepts.
2. **Given** two concepts with no relation between them, **When** the curator adds both to a collection, **Then** neither reports the other as broader, narrower, or related — collection membership asserts no semantic relation.
3. **Given** two concepts already joined by a broader/narrower or related link, **When** both are added to a collection, **Then** the collection holds them and their existing relation is unchanged — the two mechanisms are independent.

---

### User Story 4 - Collection test scaffolding (Priority: P3)

A contributor building a later feature — publishing, export, the browsing UI — constructs a collection of concepts, ordered or not, in a few lines using the test factories, instead of wiring up a collection and its memberships by hand in every test.

**Why this priority**: Every downstream feature that reads a vocabulary's structure (RDF export of `skos:Collection` / `skos:OrderedCollection`, the browsing UI, the management interface) needs collection-shaped test data. It is cheap to add alongside the models and paid back immediately, but nothing ships to a user because of it, so P3.

**Independent Test**: Write a test that asks the factory for a collection with members and asserts they are present, and for an ordered collection with a known sequence and asserts the sequence reads back.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** a test requests a collection with members from the factory, **Then** it receives a saved collection whose members are the requested concepts, all in the collection's own vocabulary.
2. **Given** the factories, **When** a test requests an ordered collection with a given member sequence, **Then** it receives a saved ordered collection that reads its members back in that sequence.

---

### User Story 5 - Translatable field metadata and deliberate indexing (Priority: P3)

Every field this feature adds carries a human-readable, translatable label and help text, every user-facing validation message it introduces is translatable, and each new field's database indexing is a deliberate, recorded decision — because a consumer of a third-party package cannot add any of these themselves.

**Why this priority**: A family-wide standard for every Django package this maintainer publishes (non-negotiable at review, constitution Articles XII and XIII), already carried by #15, #16, and #17. It adds no new capability but gates the merge, so it travels with the feature at P3.

**Independent Test**: The existing metadata test suite, which walks every concrete field on the models, automatically covers the new collection and membership fields; extend it to the new models. No UI needed.

**Acceptance Scenarios**:

1. **Given** any field the collection or membership model adds, **When** its metadata is inspected, **Then** it declares a non-empty help text and a human-readable label, both lazily translatable.
2. **Given** a user-facing validation failure introduced here (a cross-vocabulary member, a duplicate membership), **When** the error is raised, **Then** its message is translatable and uses named placeholders rather than baked-in values.
3. **Given** the database definition of the collection and membership models, **When** their indexes are inspected, **Then** the columns used to look up a collection's members and a concept's collections are indexed, the uniqueness that holds a membership once is a database constraint, and any queryable-but-unindexed field is a recorded decision, not an omission.

### Edge Cases

- A collection with no members reads back as empty, not an error; a collection whose members are the whole vocabulary is allowed.
- The same concept in two collections is held independently by each; removing it from one leaves the other intact.
- A concept added to the same collection twice is held once (membership is a set, not a multiset).
- Adding a concept whose vocabulary differs from the collection's is refused — a collection is intra-vocabulary, mirroring the intra-vocabulary rule relations follow (#17).
- In an ordered collection, removing a member leaves the survivors in their original relative order with no read-breaking gap; adding a member places it into the sequence deliberately, not at an arbitrary position.
- Whether an existing collection can be switched between ordered and unordered after it has members is a planning decision (see Assumptions); the feature's guarantees are stated for a collection whose ordered-ness is set.
- Removing a concept that is a member of collections is governed by the lifecycle feature (#19); this slice adds membership referencing existing concepts and does not change how a concept is removed.
- Two collections in the same vocabulary are distinguishable — a collection carries a stable identifier within its vocabulary (see FR-009).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A curator MUST be able to create a named **Collection** that belongs to exactly one vocabulary (`ConceptScheme`), and to rename and delete it.
- **FR-002**: A curator MUST be able to add concepts to a collection as **members** and remove them; reading a collection's members MUST return exactly its current members, and an empty result when it has none.
- **FR-003**: Collection membership MUST be many-to-many: a concept MAY belong to several collections at once, and a collection MAY hold many concepts. Memberships are independent — removing a concept from one collection MUST NOT affect its membership in another.
- **FR-004**: A concept added to the same collection more than once MUST be held **once** (membership is a set, not a multiset); the uniqueness MUST be a database constraint.
- **FR-005**: Every member of a collection MUST belong to the collection's **own vocabulary**; adding a concept from another vocabulary MUST be refused with a translatable message.
- **FR-006**: A collection MUST be markable as **ordered**. When ordered, its members carry a deliberate, persistent sequence, and reading its members MUST return them in that sequence. An unordered collection asserts no order over its members and is read as a set.
- **FR-007**: A curator MUST be able to arrange and rearrange the members of an ordered collection through the ORM; the new sequence MUST persist and MUST be what subsequent reads return. Removing a member from an ordered collection MUST leave the remaining members' relative order intact.
- **FR-008**: Adding concepts to a collection MUST assert **no semantic relation** between them: a collection's members gain no broader, narrower, or related link by virtue of shared membership, and any relation that already exists between two members is left unchanged. Collections and relations (#17) are independent mechanisms.
- **FR-009**: A collection MUST carry a **stable identifier within its vocabulary** — a human-readable name and a derived, URI-composable identifier, consistent with the scheme/concept identity precedent (Article IX) — so the collection can be round-tripped when RDF projection lands. Two collections in one vocabulary MUST be distinguishable by that identifier. (The URI *serialization* itself is R2/R4, out of scope here.)
- **FR-010**: Every model field the collection and membership models add MUST declare a human-readable, lazily translatable label and non-empty `help_text`; every user-facing validation message this feature introduces (cross-vocabulary member, duplicate membership) MUST be translatable, with named placeholders so the msgid stays static. Developer-facing diagnostics are exempt.
- **FR-011**: Indexing of the collection and membership models MUST be deliberate: the columns used to look up a collection's members and a concept's collections MUST be indexed, the uniqueness enforcing FR-004 MUST be a database constraint, the ordering position (FR-006/FR-007) MUST be indexed if it backs ordered reads, and any queryable-but-unindexed field MUST be a recorded decision.
- **FR-012**: The test suite MUST ship factories (or equivalent fixtures) able to produce a collection with members and an ordered collection with a known member sequence, all members in the collection's own vocabulary.

### Key Entities *(include if feature involves data)*

- **Collection**: a named grouping of concepts within one vocabulary — a `skos:Collection`. It belongs to exactly one `ConceptScheme`, may be ordered or unordered, and carries a stable identifier within its vocabulary. The new entity this feature introduces. Distinct from a scheme (the vocabulary itself) and from the hierarchy (a semantic relation).
- **Collection membership**: the link joining a collection to a member concept, both in the same vocabulary, carrying the member's position when the collection is ordered. Held once per (collection, concept). The second new entity; whether it is a distinct through-model is a planning decision (see Assumptions).
- **Concept (extended)**: unchanged in identity, labelling, and relations; now additionally able to report the collections it belongs to. It gains no new relation and no new identity behaviour from this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Through the ORM alone, a curator can create a collection in a vocabulary, add and remove concept members, and read exactly the current members back (empty when there are none) — verified by test.
- **SC-002**: A concept can belong to several collections at once, and removing it from one leaves its membership in the others intact — verified by test.
- **SC-003**: Adding the same concept to a collection twice holds it once — verified by test asserting the membership is not duplicated.
- **SC-004**: Adding a concept from a different vocabulary to a collection is refused with a translatable message — verified by test.
- **SC-005**: An ordered collection reads its members back in the deliberate sequence they were arranged in, a rearrangement changes that sequence, and removing a member preserves the survivors' relative order — verified by test.
- **SC-006**: An unordered collection makes no order promise and behaves as a set — verified by test.
- **SC-007**: Adding two concepts to a collection creates no broader/narrower/related link between them, and leaves any pre-existing relation between two members unchanged — verified by test.
- **SC-008**: A collection carries a stable, distinguishing identifier within its vocabulary (name plus derived identifier) — verified by test, following the scheme/concept precedent.
- **SC-009**: Every field the collection and membership models add exposes translatable, non-empty metadata and a recorded indexing decision, and every validation message this feature introduces is translatable with named placeholders — verified by the standards test.
- **SC-010**: A test obtains a populated collection and an ordered collection with a known sequence from the factories in a few lines.
- **SC-011**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python/Django matrix.

## Assumptions

- **Programmatic only.** This slice has no user interface, including the Django admin. Collections are created, populated, ordered, and read through the ORM; the live curation experience for building and arranging collections lands with the management interface, roadmap R5 — matching the precedent set by #15, #16, and #17. (This corrects the intake framing that named the Django admin: R1's slices have uniformly deferred every admin/editor surface to R5, and Collections aligns with them — recorded in `decisions.md`.)
- **No nested collections.** A collection's members are **concepts only**, never other collections. SKOS permits a collection to contain other collections; that nesting is deliberately deferred until a concrete need appears, because it adds model complexity for a capability no one has asked for (Sam, grilling — recorded in `decisions.md`).
- **Ordered is a property of the collection**, set on the collection, not a per-member opt-in: a collection is either ordered (its members carry a deliberate sequence) or not (a plain set). Confirmed at grilling.
- **Storage shape is a planning decision.** How membership is persisted (a many-to-many, with or without an explicit through-model; how the ordered sequence is stored — an integer position, a list, or Django ordering — and how ordered vs unordered reads are exposed) is decided at planning (S3) and by the Implementers, guided by `docs/brainstorm.md` and the existing `ConceptRelation` through-model precedent, not fixed by this specification.
- **Switching a collection's ordered-ness after it has members** is not a guaranteed operation this slice; the feature's ordering guarantees are stated for a collection whose ordered-ness is set. Whether a toggle is supported is left to planning. Recorded so the boundary is explicit.
- **Identity follows the scheme/concept precedent.** A collection gets a stable within-vocabulary identifier (a name and a derived, URI-composable slug, as `ConceptScheme` and `Concept` already do) so it can round-trip later. The RDF *serialization* of a collection — emitting `skos:Collection` / `skos:OrderedCollection`, `skos:member` / `skos:memberList` — belongs to R2/R4 and is out of scope here.
- **Removal semantics come from #19.** How a concept that is a member of collections is retired (deprecation, not deletion; `PROTECT`ed references) is the lifecycle feature's concern. This feature only adds collections and membership; it does not alter concept removal, and it does not depend on #19 landing first.
- **Membership is intra-vocabulary, like relations.** A collection groups concepts of one vocabulary. This mirrors the intra-vocabulary rule broader/narrower/related follow (#17); a grouping that spanned vocabularies would be a different mechanism and is not modelled here.
