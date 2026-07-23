# Feature Specification: Represent a vocabulary and its concepts

**Feature Branch**: `001-vocabulary-concepts`

**Created**: 2026-07-23

**Status**: Refined

**Refined**: 2026-07-23 — Added US-5 (translatable, self-documenting field metadata + deliberate indexing) after the maintainer set these as family-wide Django standards at the merge gate; FR-009–011 and SC-006 added.

**Input**: Issue [#15](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/15) — "A curator needs to define a controlled vocabulary and the concepts inside it, and to create and query both through Django's ORM and admin. Every concept must carry a stable, permanent identifier that stays fixed even as its wording or its database row changes."

**Serves**: G2, G3 (as an enabler: stable concept identity is what consumption and publishing depend on) · **Roadmap**: R1 · **Issue**: #15

> Scope note: this feature is one slice of roadmap item R1. It establishes the two base entities — the vocabulary and the concept — and the identity mechanism. Multilingual labels and notes (#16), concept relationships (#17), collections (#18), and lifecycle with safe removal (#19) are sibling slices built on top of this one. Publishing, which freezes identifiers, is a later feature; in this slice every vocabulary is self-managed and unpublished, so identifiers are computed and follow their source names.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a vocabulary (Priority: P1)

A curator creates a controlled vocabulary — for example "Geothermics" — with a name and an optional description, working in code. The vocabulary receives a URL-safe slug derived from its name. Renaming the vocabulary updates the slug to match.

**Why this priority**: Nothing else in the package can exist without a vocabulary to contain it. This is the ground floor of the ground floor.

**Independent Test**: Create, fetch, rename, and delete a vocabulary in a test; verify the slug tracks the name and no two vocabularies can share a slug.

**Acceptance Scenarios**:

1. **Given** an empty system, **When** a curator creates a vocabulary named "Geothermics", **Then** it can be retrieved and carries the slug `geothermics`.
2. **Given** the vocabulary "Geothermics", **When** it is renamed to "Geothermal Science", **Then** its slug becomes `geothermal-science`.
3. **Given** an existing vocabulary with slug `geothermics`, **When** a second vocabulary is created whose name would produce the same slug, **Then** the system refuses the ambiguity — no two vocabularies may share a slug.

---

### User Story 2 - Populate a vocabulary with concepts (Priority: P1)

A curator adds concepts to a vocabulary, each with a preferred label — "Heat flow", "Thermal conductivity" — and can list, retrieve, relabel, and remove them. A concept always belongs to exactly one vocabulary. Each concept receives a slug derived from its preferred label, unique within its vocabulary.

**Why this priority**: Concepts are the payload of the whole package; a vocabulary without concepts is an empty shell.

**Independent Test**: Add several concepts to a vocabulary in a test; list them, look one up by slug, relabel one, delete one — all through the package's programming interface.

**Acceptance Scenarios**:

1. **Given** the vocabulary "Geothermics", **When** a curator adds a concept labelled "Heat flow", **Then** the concept can be retrieved from that vocabulary under the slug `heat-flow`.
2. **Given** a concept "Heat flow" in "Geothermics", **When** its label changes to "Terrestrial heat flow", **Then** its slug becomes `terrestrial-heat-flow`.
3. **Given** a vocabulary containing concepts, **When** the concepts are listed, **Then** every concept added — and only those — is returned.
4. **Given** two concepts in the same vocabulary, **When** a curator tries to give them labels that would produce the same slug, **Then** the system refuses — a slug is unambiguous within its vocabulary.
5. **Given** a concept in a vocabulary, **When** the curator deletes it, **Then** it is gone from the vocabulary's concept list.

---

### User Story 3 - Every concept carries a stable identifier (Priority: P1)

Every concept exposes a full URI, composed from a configurable base address plus the vocabulary's slug plus the concept's slug — for example `https://example.org/vocabularies/geothermics/heat-flow`. The URI is the concept's identity: it can be looked up by it, and no two concepts can share one. While a vocabulary is unpublished (all vocabularies, in this slice), the URI follows label changes; freezing it is the future publishing feature's job.

**Why this priority**: The identifier is what issue #15 exists to establish. Everything downstream — attaching concepts to data, publishing, importing — hangs off this.

**Independent Test**: Create a vocabulary and concept in a test; verify the composed URI, look the concept up by it, rename things and verify the URI recomposes accordingly.

**Acceptance Scenarios**:

1. **Given** a base address of `https://example.org/vocabularies`, a vocabulary with slug `geothermics`, and a concept with slug `heat-flow`, **When** the concept's URI is read, **Then** it is `https://example.org/vocabularies/geothermics/heat-flow`.
2. **Given** a concept's URI, **When** it is used as a lookup key, **Then** exactly that concept is returned.
3. **Given** an unpublished vocabulary, **When** the vocabulary or a concept is renamed, **Then** the concept's URI reflects the new slugs.
4. **Given** any two concepts in the system, **When** their URIs are compared, **Then** they differ.

---

### User Story 4 - Ready-made test scaffolding (Priority: P2)

A contributor building a later feature can construct populated test vocabularies in a couple of lines, using factories (or fixtures) shipped with the test suite, instead of hand-assembling schemes and concepts in every test.

**Why this priority**: Four sibling features are queued behind this one; each will need test vocabularies on day one. Cheap now, paid back immediately.

**Independent Test**: Write a test that uses only the factories to produce a vocabulary with several concepts, and assert on it.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** a test requests a vocabulary from the factory, **Then** it receives a valid, saved vocabulary with sensible defaults.
2. **Given** the factories, **When** a test requests a concept without specifying a vocabulary, **Then** a containing vocabulary is created automatically and the concept is valid within it.

---

### User Story 5 - Translatable, self-documenting field metadata (Priority: P2)

A developer integrating the package — or a curator seeing its fields in a form — always gets a
human-readable label and help text for every field, in their own language once translations exist.
Nothing user-facing is hard-coded English-only, and the package's fields carry deliberate database
indexes, because a consumer of a third-party package cannot add either themselves.

**Why this priority**: a family-wide standard for every Django package this maintainer publishes
(non-negotiable at review); it gates the merge even though it adds no new capability.

**Independent Test**: a metadata test suite walks every field on both models and asserts the
standard holds — no UI needed.

**Acceptance Scenarios**:

1. **Given** any field on a vocabulary or concept, **When** its metadata is inspected, **Then** it
   declares a non-empty help text and a human-readable label, and both are lazily translatable.
2. **Given** a user-facing validation failure (empty name/label, slug collision), **When** the error
   is raised, **Then** its message is translatable and uses named placeholders rather than baked-in
   values.
3. **Given** the database table definitions, **When** their indexes are inspected, **Then** the
   vocabulary slug is uniquely indexed, the concept's vocabulary reference carries its index, and
   the vocabulary-plus-slug pair is enforced by the composite constraint — and any field left
   unindexed is a recorded decision, not an omission.

---

### Edge Cases

- A concept label or vocabulary name in a non-Latin script (for example "Wärmefluss" or Cyrillic text) must still produce a usable, URL-safe slug.
- An empty or whitespace-only name or label is rejected.
- Deleting a vocabulary that still contains concepts removes the vocabulary and its concepts — a concept cannot exist outside a vocabulary.
- Renaming a vocabulary changes the URI of every concept it contains. That is intended behaviour while unpublished, and tests document it as such.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A curator MUST be able to create a vocabulary with a required name and optional description, and to retrieve, rename, and delete it, through the package's programming interface.
- **FR-002**: Each vocabulary MUST carry a URL-safe slug derived automatically from its name, kept in sync when the name changes, and unique across all vocabularies.
- **FR-003**: A curator MUST be able to add a concept — with a required preferred label — to exactly one vocabulary, and to retrieve, relabel, and delete it. A concept MUST NOT exist outside a vocabulary.
- **FR-004**: Each concept MUST carry a URL-safe slug derived automatically from its preferred label, kept in sync when the label changes, and unique within its vocabulary.
- **FR-005**: Every concept MUST expose a full URI composed deterministically from a configurable base address, its vocabulary's slug, and its own slug. Every vocabulary MUST likewise expose its own URI (base address plus vocabulary slug).
- **FR-006**: A concept MUST be retrievable by its URI, by its vocabulary-plus-slug pair, and as part of a listing of its vocabulary's concepts.
- **FR-007**: Slug derivation MUST handle non-ASCII input, and slug collisions MUST be refused at the uniqueness scope of the entity (system-wide for vocabularies, per-vocabulary for concepts).
- **FR-008**: The test suite MUST ship factories (or equivalent fixtures) for vocabularies and concepts, usable by this and later features' tests.
- **FR-009**: Every model field MUST declare a human-readable label (`verbose_name`) and a non-empty `help_text`, both lazily translatable.
- **FR-010**: Every user-facing string — field labels, help text, model verbose names, and validation messages — MUST be translatable; validation messages use named placeholders so their translatable form is static. Developer-facing diagnostics are exempt.
- **FR-011**: Field indexing MUST be deliberate: fields with a lookup path are indexed at definition (unique, foreign-key, or composite constraint), and any queryable-but-unindexed field is a recorded decision.

### Key Entities

- **Vocabulary (concept scheme)**: the named container a curator manages — carries a name, an optional description, a slug, and a computed URI. Holds any number of concepts.
- **Concept**: a term within exactly one vocabulary — carries a preferred label, a slug, and a computed URI that embeds its vocabulary's slug.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can create a vocabulary, add concepts to it, and retrieve any concept by its identifier, in under ten lines of code.
- **SC-002**: Every concept in a system has exactly one URI and no two concepts share one, regardless of how many vocabularies exist.
- **SC-003**: Renaming a vocabulary or relabelling a concept is reflected in composed URIs immediately, with no manual step.
- **SC-004**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python/Django matrix.
- **SC-005**: A test for a later feature can obtain a populated vocabulary from the factories in three lines or fewer.
- **SC-006**: Every field on both models exposes translatable, non-empty metadata (label + help text), every user-facing message is translatable, and the indexing of every field is either present or recorded as a decision — all verified by automated tests.

## Assumptions

- A concept carries a single preferred label in this slice, treated as the default language's label. The full multilingual label model (per-language preferred/alternate labels, definitions, notes) is sibling feature #16, which will build on this label rather than replace the identity mechanism.
- All vocabularies here are self-managed and unpublished. Identifiers are computed and follow renames. The publishing feature (later) introduces freezing; nothing in this slice may assume a frozen identifier.
- The base address used to compose URIs is deployment-level configuration; its exact configuration mechanism is a planning decision, not part of this specification.
- Concept-to-concept relationships (#17), collections (#18), and lifecycle states with protected removal (#19) are sibling features and intentionally absent here.
- Notation codes (language-independent identifiers such as "HF") have no consumer in this slice and are deferred to the sibling that first needs them.
- No user interface of any kind — including the Django admin — is part of this slice; interaction is purely programmatic.
