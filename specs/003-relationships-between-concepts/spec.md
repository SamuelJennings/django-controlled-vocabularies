# Feature Specification: Relationships between concepts

**Feature Branch**: `003-relationships-between-concepts`

**Created**: 2026-07-25

**Status**: Draft

**Input**: Issue [#17](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/17) — "Concepts within a vocabulary need to link to one another: a broader/narrower hierarchy, and a looser 'related' association, so a vocabulary is a structured graph rather than a flat list, navigable in both directions."

**Serves**: G4 (faithful round-trip of managed vocabularies — the graph structure is part of what must survive export) · **Roadmap**: R1 · **Issue**: #17

> Scope note: this feature is one slice of roadmap item R1. It turns a vocabulary from a flat set of concepts (established in [#15](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/15), enriched with multilingual names in [#16](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/16)) into a structured graph: concepts link to one another through a broader/narrower hierarchy and a symmetric related association, navigable in both directions. Interaction is purely programmatic — through the ORM, no admin or editor UI (that is roadmap R5, matching the precedent set by #15 and #16). **Out of scope:** cross-vocabulary mappings (`exactMatch`, `closeMatch`, … — a different mechanism that lives in a concept's document, not the relation link), named collections ([#18](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/18)), the concept lifecycle and safe removal ([#19](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/19)), and RDF import/export (R2/R4). Cycle prevention in the hierarchy is deliberately not guaranteed this slice (see Assumptions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Broader/narrower hierarchy, navigable both ways (Priority: P1)

A curator building their own vocabulary arranges its concepts into a hierarchy: "Granite" is placed under "Igneous rock" by giving it a broader concept. Reading "Igneous rock" back, "Granite" appears among its narrower concepts without the curator ever having asserted the narrower direction separately — one assertion, both directions readable. A concept may be placed under more than one broader concept (polyhierarchy): "Granite" can be broader-linked to both "Igneous rock" and "Plutonic rock".

**Why this priority**: This is the core of the feature and the whole of what makes a vocabulary a graph rather than a list. The inverse-pair guarantee (assert `broader`, read `narrower` back) is the load-bearing behaviour every downstream navigation, publish, and export path depends on. Implemented alone, it is a viable, navigable concept hierarchy.

**Independent Test**: In a test, create a vocabulary with three concepts, give one two broader concepts, then read the narrower concepts back from each parent and assert the child appears in both, and that the child reports both parents — without any narrower assertion having been made.

**Acceptance Scenarios**:

1. **Given** a vocabulary with concepts "Igneous rock" and "Granite", **When** the curator gives "Granite" the broader concept "Igneous rock", **Then** "Granite" reports "Igneous rock" among its broader concepts, and "Igneous rock" reports "Granite" among its narrower concepts, with no separate narrower assertion made.
2. **Given** that hierarchy, **When** the curator also gives "Granite" the broader concept "Plutonic rock", **Then** "Granite" reports both "Igneous rock" and "Plutonic rock" as broader (polyhierarchy is allowed).
3. **Given** a broader link from "Granite" to "Igneous rock", **When** the link is removed, **Then** neither concept reports the other in either direction.
4. **Given** any concept, **When** the curator attempts to give it itself as a broader (or narrower) concept, **Then** the system refuses it — a concept cannot be its own broader or narrower.
5. **Given** "Granite" already broader-linked to "Igneous rock", **When** the same broader link is asserted again, **Then** the system refuses the duplicate — the pair is held once.

---

### User Story 2 - The related association, symmetric (Priority: P2)

A curator records a sideways association between two concepts where neither is above the other: "Granite" is related to "Quartz" — they belong together, but neither is a kind of the other. The association reads the same from either concept: asking "Granite" for its related concepts returns "Quartz", and asking "Quartz" returns "Granite", from the single assertion the curator made.

**Why this priority**: The related association is the second half of the graph the issue asks for and what captures the associations the strict hierarchy cannot. It reuses US-1's linking mechanism and is not needed for the hierarchy to be correct, so it follows it.

**Independent Test**: In a test, relate two concepts from one side, read the related concepts back from the other side and assert the first appears, assert the association is stored once (not mirrored into two rows), and assert relating a concept to itself is refused.

**Acceptance Scenarios**:

1. **Given** concepts "Granite" and "Quartz", **When** the curator relates "Granite" to "Quartz", **Then** "Granite" reports "Quartz" as related and "Quartz" reports "Granite" as related, from the one assertion.
2. **Given** "Granite" related to "Quartz", **When** the curator asserts the same association in the opposite order ("Quartz" related to "Granite"), **Then** the system treats it as the association that already exists — it is not stored a second time.
3. **Given** any concept, **When** the curator attempts to relate it to itself, **Then** the system refuses it.
4. **Given** "Granite" related to "Quartz", **When** the related link is removed, **Then** neither concept reports the other as related.

---

### User Story 3 - The graph stays coherent (Priority: P2)

A curator cannot, whether by mistake or otherwise, put the vocabulary into a state SKOS treats as contradictory: two concepts already joined in a broader/narrower line cannot also be marked related, because related is meant for associations *outside* the hierarchy. Attempting it is refused, with a message that says why. The one incoherence this slice does not police is a cycle in the hierarchy — that is left to a later feature and is called out so its absence is deliberate.

**Why this priority**: Disjointness is what keeps the exported SKOS valid and the graph meaningful, and it is the integrity guarantee the curator most needs protecting from. It spans both relation types, so it can only be expressed once US-1 and US-2 exist, which puts it at P2 behind them.

**Independent Test**: In a test, give two concepts a broader/narrower link, attempt to also relate them, and assert refusal; do the reverse (relate first, then attempt a broader link) and assert refusal; and assert that a broader link and a related link between two *different* pairs both succeed.

**Acceptance Scenarios**:

1. **Given** "Granite" broader-linked to "Igneous rock", **When** the curator attempts to relate "Granite" and "Igneous rock", **Then** the system refuses it — a directly hierarchical pair cannot also be related.
2. **Given** "Granite" related to "Quartz", **When** the curator attempts to give one the other as a broader concept, **Then** the system refuses it.
3. **Given** a vocabulary, **When** a broader link joins one pair and a related link joins a different pair, **Then** both succeed — disjointness constrains a pair, not the vocabulary.
4. **Given** a broader chain "Granite" → "Igneous rock" → "Rock", **When** the curator gives "Rock" the broader concept "Granite" (closing a loop), **Then** the system accepts it — cycle prevention is not guaranteed this slice (recorded deferral), and no traversal is performed.

---

### User Story 4 - Relation test scaffolding (Priority: P3)

A contributor building a later feature — publishing, export, the editor — constructs a small graph of related concepts in a few lines using the test factories, instead of wiring up broader and related links by hand in every test.

**Why this priority**: Every downstream feature that reads the graph (RDF export, the browsing UI, the consumption field's subtree-scoped autocomplete) needs graph-shaped test data. It is cheap to add alongside the models and paid back immediately, but nothing ships to a user because of it, so P3.

**Independent Test**: Write a test that asks the factory for a concept with broader and related links and asserts the graph is present and navigable in both directions.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** a test requests a small concept hierarchy from the factory, **Then** it receives saved concepts linked broader/narrower and navigable both ways.
2. **Given** the factories, **When** a test requests a related pair, **Then** it receives two concepts joined by a single related association.

---

### User Story 5 - Translatable field metadata and deliberate indexing (Priority: P3)

Every field this feature adds carries a human-readable, translatable label and help text, every user-facing validation message it introduces is translatable, and each new field's database indexing is a deliberate, recorded decision — because a consumer of a third-party package cannot add any of these themselves.

**Why this priority**: A family-wide standard for every Django package this maintainer publishes (non-negotiable at review, constitution Articles XII and XIII), already carried by #15 and #16. It adds no new capability but gates the merge, so it travels with the feature at P3.

**Independent Test**: The existing metadata test suite, which walks every concrete field on the models, automatically covers the new relation fields; extend it to the new through model. No UI needed.

**Acceptance Scenarios**:

1. **Given** any field the relation model adds, **When** its metadata is inspected, **Then** it declares a non-empty help text and a human-readable label, both lazily translatable.
2. **Given** a user-facing validation failure introduced here (a self-relation, a duplicate, a disjointness violation), **When** the error is raised, **Then** its message is translatable and uses named placeholders rather than baked-in values.
3. **Given** the database definition of the relation model, **When** its indexes are inspected, **Then** the columns used to look a concept's relations up are indexed, and any queryable-but-unindexed field is a recorded decision, not an omission.

### Edge Cases

- A concept given two broader concepts (polyhierarchy) reads both back; removing one leaves the other intact.
- Relating a pair that is *transitively* but not *directly* hierarchical (A broader B, B broader C; relate A and C) is **accepted** this slice — disjointness is checked against directly-asserted broader/narrower pairs only, because transitive checking needs the hierarchy traversal this slice deliberately omits (see Assumptions). Recorded so the boundary is explicit.
- A relation whose two concepts belong to *different* vocabularies is refused — broader/narrower/related are intra-vocabulary; a cross-vocabulary link is a mapping, which is out of scope.
- Reading a concept's broader, narrower, or related concepts when it has none returns an empty result, not an error.
- Removing a concept that participates in relations is governed by the lifecycle feature (#19); this slice adds relations to the existing concept model and does not change how a concept is removed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A concept MUST be able to be given one or more **broader** concepts within the same vocabulary; polyhierarchy (several broader concepts) MUST be supported.
- **FR-002**: The **narrower** direction MUST be derived from the broader assertion, never asserted separately: if A is broader than B, then B MUST report A as broader and A MUST report B as narrower, from the single assertion. Only one canonical direction is stored.
- **FR-003**: A concept MUST be able to be given **related** concepts within the same vocabulary; the related association MUST be symmetric — readable identically from either concept — from a single assertion, stored as one canonical row (an assertion in the mirror order MUST resolve to the same association, not a second one).
- **FR-004**: The programming interface MUST let a caller read a concept's broader concepts, its narrower concepts (derived), and its related concepts through the ORM, each returning an empty result when there are none.
- **FR-005**: A concept MUST be able to have a broader, narrower, or related link **removed**, after which neither concept reports the other in that direction.
- **FR-006**: A relation of any type between a concept and **itself** MUST be refused.
- **FR-007**: A **duplicate** relation MUST be refused: the same broader link asserted twice, or the same related association asserted in either order twice, is held once, not twice.
- **FR-008**: A pair of concepts joined by a **directly-asserted** broader/narrower link MUST NOT also be joinable by a related link, and vice versa (SKOS disjointness). The violation MUST be refused with a translatable message. Disjointness is evaluated against direct broader/narrower assertions only, not the transitive hierarchy.
- **FR-009**: Both endpoints of any relation MUST belong to the **same vocabulary** (`ConceptScheme`); a relation across vocabularies MUST be refused. (Cross-vocabulary links are mappings, out of scope.)
- **FR-010**: The system MUST NOT perform hierarchy traversal to prevent **cycles** in the broader relation this slice; a curator MAY create a cyclic broader chain, and this is a recorded, deliberate non-guarantee (a later feature may add cycle detection).
- **FR-011**: Every model field the relation model adds MUST declare a human-readable, lazily translatable label and non-empty help text; every user-facing validation message this feature introduces (self-relation, duplicate, disjointness, cross-vocabulary) MUST be translatable, with named placeholders so the translatable form is static. Developer-facing diagnostics are exempt.
- **FR-012**: Indexing of the relation model's fields MUST be deliberate: the columns used to look a concept's relations up (in either direction) MUST be indexed, the uniqueness that enforces FR-007 MUST be a database constraint, and any queryable-but-unindexed field MUST be a recorded decision.
- **FR-013**: The test suite MUST ship factories (or equivalent fixtures) able to produce concepts joined by broader/narrower and related links, navigable in both directions.

### Key Entities *(include if feature involves data)*

- **Concept relation**: a link between two concepts belonging to the same vocabulary, carrying its type. The hierarchy is stored in one canonical direction (broader), with narrower derived; the related association is symmetric and stored once. The relation is the new entity this feature introduces.
- **Concept (extended)**: unchanged in identity and labelling, now reachable as a node in a graph — it can report its broader concepts, its narrower concepts (derived), and its related concepts, all scoped to its own vocabulary.
- **Relationship type**: the kind of a stored relation — the hierarchical `broader` (its inverse `narrower` derived on read) and the symmetric `related`. Cross-vocabulary mapping types are explicitly not part of this entity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Through the ORM alone, a developer can give a concept several broader concepts and read the narrower concepts back from each parent, with no narrower assertion made — verified by test.
- **SC-002**: A related association set from one concept is readable, identically, from the other, and is stored exactly once regardless of the order it was asserted in — verified by test.
- **SC-003**: A self-relation of any type is refused — verified by test for broader and for related.
- **SC-004**: A duplicate relation is refused, including a related association re-asserted in mirror order — verified by test.
- **SC-005**: Two concepts in a directly-asserted broader/narrower line cannot also be related, in either order of attempt, while a broader link and a related link on two different pairs both succeed — verified by test.
- **SC-006**: A relation whose endpoints are in different vocabularies is refused — verified by test.
- **SC-007**: A cyclic broader chain can be created without error and without the system performing hierarchy traversal — verified by test, documenting the deliberate non-guarantee.
- **SC-008**: A test obtains a navigable concept graph (broader/narrower and a related pair) from the factories in a few lines.
- **SC-009**: Every field the relation model adds exposes translatable, non-empty metadata and a recorded indexing decision, and every validation message this feature introduces is translatable with named placeholders — verified by the standards test.
- **SC-010**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python/Django matrix.

## Assumptions

- **Programmatic only.** This slice has no user interface, including the Django admin. Relations are created, read, and removed through the ORM; the live curation experience for building a hierarchy lands with the management interface, roadmap R5 — matching the precedent set by #15 and #16.
- **Cycle prevention is deliberately deferred.** SKOS does not formally forbid a cycle in the broader relation, and detecting one requires walking the hierarchy on every write — the same traversal cost this slice avoids. Acyclicity is therefore not guaranteed here; a curator can create a loop. Recorded as a deliberate non-guarantee (FR-010, SC-007) for a later validation or editor feature to revisit.
- **Disjointness is checked at direct adjacency, not transitively.** SKOS's related/broaderTransitive disjointness is enforced only against directly-asserted broader/narrower pairs. Enforcing it across the transitive hierarchy needs the same traversal as cycle detection, so it is scoped to direct pairs this slice, consistent with the cycle deferral. Recorded so the boundary is explicit rather than an oversight.
- **Relations are intra-vocabulary.** Broader, narrower, and related join concepts within one vocabulary. A link to a concept in another vocabulary is a **mapping** (`exactMatch`, `closeMatch`, …), which SKOS and this package treat as a separate mechanism living in a concept's document — out of scope here and not modelled by the relation.
- **Storage shape is a planning decision.** How the relation is persisted (a self-referencing many-to-many with a through model carrying the type, the direction of the stored row, and how the derived and symmetric reads are exposed) is decided at planning (S3) and by the Implementers, guided by `docs/brainstorm.md`, not fixed by this specification.
- **Removal semantics come from #19.** How a concept that participates in relations is retired (deprecation, not deletion; `PROTECT`ed references) is the lifecycle feature's concern. This feature only adds the relations; it does not alter concept removal, and it does not depend on #19 landing first.
- **RDF projection is later.** How broader/narrower/related are emitted as `skos:broader` / `skos:narrower` / `skos:related` on export (and read on import) belongs to R2/R4. This slice makes the graph exist in the model so those features have something to project; it does not itself serialize RDF.
