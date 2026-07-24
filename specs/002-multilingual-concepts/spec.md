# Feature Specification: Multilingual names and descriptions for concepts

**Feature Branch**: `002-multilingual-concepts`

**Created**: 2026-07-24

**Status**: Draft

**Input**: Issue [#16](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/16) — "Each concept should carry its names and descriptions in several languages: one preferred name per language, plus any number of alternative and hidden names, and definitions and notes that also vary by language, all editable one language at a time."

**Serves**: G6 (multilingual concepts — labels and definitions carry per-language values, editable one language at a time) · **Roadmap**: R1 · **Issue**: #16

> Scope note: this feature is one slice of roadmap item R1. It grows a concept from the single default-language label established in [#15](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/15) into a full per-language lexical and descriptive model, and settles how a concept's identity behaves once labels exist in many languages. It **supersedes** #15's decision that a concept carries one plain label (recorded there as a deliberate deferral to this feature). Interaction is purely programmatic — no admin or editor UI (that is roadmap R5). RDF import/export (R2/R4), notation codes, concept relationships (#17), collections (#18), and lifecycle with safe removal (#19) are sibling or later features and intentionally absent here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preferred labels in several languages, identity preserved (Priority: P1)

A curator building their own vocabulary gives a concept a preferred label in each language they work in — "Heat flow" (en), "Wärmefluss" (de) — with exactly one preferred label per language, and reads any language's preferred label back. The concept's stable identity (its slug and URI) is anchored to the preferred label in the vocabulary's **default language**, which is required; adding, changing, or removing a preferred label in any other language never disturbs that identity.

**Why this priority**: This is the core promise of the feature and the whole of goal G6's minimum. It also settles the load-bearing question the multilingual model forces — which label anchors identity — without which none of the richer label or note stories are safe to build. Implemented alone, it is a viable multilingual concept.

**Independent Test**: In a test, create a vocabulary and a concept, set preferred labels in two languages, read each back by language, then add and edit a non-default-language label and assert the concept's URI is unchanged; assert a second preferred label in an already-used language is refused.

**Acceptance Scenarios**:

1. **Given** a vocabulary whose default language is English, **When** a curator adds a concept with the English preferred label "Heat flow" and a German preferred label "Wärmefluss", **Then** each language's preferred label can be read back, and the concept's slug is `heat-flow` (derived from the default-language label).
2. **Given** that concept, **When** the German preferred label is changed to "Terrestrischer Wärmefluss" or removed entirely, **Then** the concept's slug and URI are unchanged.
3. **Given** that concept, **When** the English (default-language) preferred label is changed to "Terrestrial heat flow", **Then** the slug becomes `terrestrial-heat-flow` and the URI recomposes (unpublished behaviour inherited from #15).
4. **Given** a concept that already has an English preferred label, **When** a second English preferred label is added, **Then** the system refuses it — at most one preferred label per language.
5. **Given** a new concept, **When** it is saved without a preferred label in the vocabulary's default language, **Then** the system refuses it — the default-language preferred label is required as the identity anchor.

---

### User Story 2 - Alternative and hidden labels per language (Priority: P2)

A curator records, for a concept, any number of alternative names and any number of hidden names in each language — synonyms a person might search by ("terrestrial heat flow", "geothermal heat flow") and misspellings or deprecated forms to catch but not display — each tagged to its language and independent of the preferred label.

**Why this priority**: Alternative and hidden labels are what make a vocabulary findable and forgiving of how people actually type. They build directly on US-1's per-language label mechanism but are not needed for the identity model to be correct, so they follow it.

**Independent Test**: In a test, add several alternative and hidden labels in two languages to a concept, read them back filtered by language, and assert the counts and language tags are preserved and that they are distinct from the preferred label.

**Acceptance Scenarios**:

1. **Given** a concept with an English preferred label, **When** a curator adds two English alternative labels and one German alternative label, **Then** reading the concept's alternative labels for English returns both English values and none of the German ones.
2. **Given** a concept, **When** a curator adds hidden labels in a language, **Then** they are stored and readable per language and are held separately from alternative labels.
3. **Given** a concept, **When** its alternative or hidden labels are added, changed, or removed, **Then** its slug and URI are unaffected.

---

### User Story 3 - Definitions and documentary notes per language (Priority: P2)

A curator writes a concept's meaning and editorial context in each language: a definition, and any of the SKOS documentary notes — scope note, example, editorial note, history note, change note, and a general note — each language-tagged, so a reader in any supported language gets the concept explained in theirs.

**Why this priority**: Descriptions are half of what issue #16 asks for and are what a published vocabulary needs to be usable rather than a bare list of names. They reuse US-1's per-language mechanism and matter for the later faithful round-trip (G4), but the vocabulary is navigable without them, so they sit at P2 alongside the other label enrichments.

**Independent Test**: In a test, attach a definition and each kind of documentary note in two languages to a concept, read them back filtered by language, and assert each note type is held and returned distinctly and tagged to its language.

**Acceptance Scenarios**:

1. **Given** a concept, **When** a curator sets an English and a German definition, **Then** each is readable by its language.
2. **Given** a concept, **When** a curator adds a scope note, an example, an editorial note, a history note, a change note, and a general note in a language, **Then** each is stored under its own note type and readable per language.
3. **Given** a concept, **When** definitions or notes are added, changed, or removed in any language, **Then** the concept's slug and URI are unaffected.

---

### User Story 4 - Per-vocabulary default language (Priority: P2)

A curator running one instance that hosts several vocabularies in different working languages sets a default language on each vocabulary. A German-authored vocabulary anchors its concepts' identity in German; an English one in English. Where a vocabulary sets no default of its own, it falls back to the application's configured default language.

**Why this priority**: The package is explicitly meant to host several independently-authored vocabularies at once, and they will not all share one primary language. Without a per-vocabulary default, a German vocabulary in an English-default instance would anchor its identifiers in English. It refines US-1's identity model rather than standing alone, so it follows it.

**Independent Test**: In a test, create two vocabularies — one defaulting to the app language, one overridden to another — add a concept to each with preferred labels in both languages, and assert each concept's slug is derived from its own vocabulary's default-language label.

**Acceptance Scenarios**:

1. **Given** an application whose default language is English and a vocabulary with no explicit default language, **When** a concept is added, **Then** its default-language (identity) label is the English one.
2. **Given** a vocabulary whose default language is overridden to German, **When** a concept with English and German preferred labels is added, **Then** its slug derives from the German preferred label.
3. **Given** a vocabulary, **When** its default language is read, **Then** it reports either its explicit override or the application default.

---

### User Story 5 - Overridable concept slug (Priority: P2)

A curator who does not want an identifier auto-derived from a label — because the label's language is awkward as a URL, or they want a specific stable path — sets a concept's slug explicitly. Once set explicitly, the slug is theirs: later changes to the preferred label do not move it.

**Why this priority**: It removes the sharp edge of anchoring identity to a label (a curator is never forced into an identifier they did not choose) and, with the same mechanism, leaves room for later import to carry an external vocabulary's own slugs unchanged. It is a refinement of the identity model, so P2.

**Independent Test**: In a test, create a concept with an explicit slug, assert the slug is exactly what was set (not derived), then change the preferred label and assert the slug does not change; create a second concept without an explicit slug and assert it still derives from the label.

**Acceptance Scenarios**:

1. **Given** a new concept, **When** the curator provides an explicit slug, **Then** the concept's slug is exactly that value and is not derived from the preferred label.
2. **Given** a concept with an explicitly set slug, **When** its default-language preferred label changes, **Then** the slug is unchanged.
3. **Given** a concept created without an explicit slug, **When** it is saved, **Then** the slug is derived from the default-language preferred label, exactly as in #15.
4. **Given** an explicit slug that collides with another concept's slug in the same vocabulary, **When** the concept is saved, **Then** it is refused, per the uniqueness rule inherited from #15.

---

### User Story 6 - Multilingual test scaffolding (Priority: P3)

A contributor building a later feature constructs a concept already populated with labels and notes across several languages in a couple of lines, using the test factories, instead of assembling multilingual state by hand in every test.

**Why this priority**: Every sibling feature and the import/publish work will need multilingual test data. It is cheap to add here and paid back immediately, but nothing ships to a user because of it, so P3.

**Independent Test**: Write a test that asks the factory for a multilingual concept and asserts it has preferred labels and at least one note in more than one language.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** a test requests a multilingual concept from the factory, **Then** it receives a valid, saved concept with preferred labels in more than one language.
2. **Given** the factories, **When** a test requests labels or notes in specific languages, **Then** the produced concept carries exactly those.

---

### User Story 7 - Translatable field metadata and deliberate indexing (Priority: P3)

Every field this feature adds carries a human-readable, translatable label and help text, all user-facing strings and validation messages are translatable, and each new field's database indexing is a deliberate, recorded decision — because a consumer of a third-party package cannot add any of these themselves.

**Why this priority**: A family-wide standard for every Django package this maintainer publishes (non-negotiable at review), already established for #15's fields by its US-5. It adds no new capability but gates the merge, so it travels with the feature at P3.

**Independent Test**: The existing metadata test suite, which walks every concrete field on the models, automatically covers the new fields; extend it only where new models are introduced. No UI needed.

**Acceptance Scenarios**:

1. **Given** any field added by this feature, **When** its metadata is inspected, **Then** it declares a non-empty help text and a human-readable label, both lazily translatable.
2. **Given** a user-facing validation failure introduced here (a duplicate preferred label in a language, a missing default-language label), **When** the error is raised, **Then** its message is translatable and uses named placeholders rather than baked-in values.
3. **Given** the database definitions of the new fields, **When** their indexes are inspected, **Then** the value used for preferred-label lookup is indexed, and any queryable-but-unindexed field is a recorded decision, not an omission.

### Edge Cases

- A preferred label in a non-Latin script (Cyrillic, CJK) in the default language must still produce a usable, URL-safe slug (inherited from #15's slug handling).
- A concept with preferred labels only in non-default languages is rejected: the default-language preferred label is the required identity anchor.
- Changing a vocabulary's default language after concepts exist: the change does not retroactively re-slug existing concepts whose slugs were already derived or set (slugs move only when their own source label changes and no explicit slug is set) — the behaviour is documented and tested so it is explicit, not accidental.
- Requesting labels or notes for a language the concept has none in returns an empty result, not an error.
- An empty or whitespace-only preferred label in the default language is rejected (inherited from #15).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A concept MUST carry, per application-configured language, at most one preferred label; a second preferred label in a language that already has one MUST be refused.
- **FR-002**: A preferred label in the vocabulary's default language MUST be required — a concept without one MUST be refused — and it is the anchor from which the concept's slug is derived.
- **FR-003**: A concept's slug MUST, when not explicitly set, derive from its default-language preferred label, and its URI MUST compose exactly as established in #15 (base + vocabulary slug + concept slug); this feature MUST preserve that identity mechanism.
- **FR-004**: Adding, changing, or removing any label or note in a language **other than** the vocabulary's default language MUST NOT change the concept's slug or URI.
- **FR-005**: A concept MUST support any number of alternative labels and any number of hidden labels per language, each held distinctly from the other and from the preferred label.
- **FR-006**: A concept MUST support, per language, a definition and each of the SKOS documentary notes — scope note, example, editorial note, history note, change note, and a general note — each holdable independently and, where its value type permits, more than once per language.
- **FR-007**: The programming interface MUST let a caller read a concept's preferred label, alternative labels, hidden labels, definition, and each note type filtered to a specified language, returning an empty result for a language with no such value.
- **FR-008**: A curator MUST be able to author one language's labels and notes without supplying or altering any other language's values — languages are edited independently.
- **FR-009**: Each vocabulary MUST have a default language that defaults to the application's configured default language and MAY be overridden per vocabulary; the effective default language determines which preferred label anchors that vocabulary's concepts' slugs.
- **FR-010**: A curator MUST be able to set a concept's slug explicitly; an explicitly set slug MUST NOT be re-derived when the preferred label later changes, while a concept with no explicit slug MUST continue to track its default-language preferred label.
- **FR-011**: The set of languages a concept may carry values in MUST be the application's configured languages; the effective default language MUST be the application's configured default language unless a vocabulary overrides it.
- **FR-012**: Slug uniqueness within a vocabulary (from #15) MUST continue to hold for both derived and explicitly set slugs, and collisions MUST be refused, never auto-suffixed.
- **FR-013**: The test suite MUST ship factories (or equivalent fixtures) able to produce a concept populated with preferred labels, and at least alternative labels and notes, across more than one language.
- **FR-014**: Every model field this feature adds MUST declare a human-readable, lazily translatable label and non-empty help text; every user-facing string and validation message MUST be translatable, with validation messages using named placeholders so their translatable form is static. Developer-facing diagnostics are exempt.
- **FR-015**: Indexing of the fields this feature adds MUST be deliberate: the value used for preferred-label lookup/search MUST be indexed, and any queryable-but-unindexed field MUST be a recorded decision.

### Key Entities *(include if feature involves data)*

- **Concept (extended)**: still a term within exactly one vocabulary, now carrying — per language — one preferred label, any number of alternative labels, any number of hidden labels, a definition, and the documentary notes (scope note, example, editorial note, history note, change note, general note). Its identity (slug, URI) is anchored to the default-language preferred label unless a slug is explicitly set.
- **Vocabulary / ConceptScheme (extended)**: gains an effective default language (application default, overridable per vocabulary) that decides which preferred label anchors its concepts' identity.
- **Label**: a language-tagged name for a concept — preferred (one per language), alternative (many per language), or hidden (many per language).
- **Note**: a language-tagged descriptive value on a concept — a definition or one of the SKOS documentary note types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Through the ORM alone, a developer can give a concept preferred, alternative, and hidden labels plus a definition and documentary notes in each configured language and read every one of them back filtered by language.
- **SC-002**: A concept has at most one preferred label per language, and an attempt to add a second in the same language is refused — verified by test.
- **SC-003**: A concept's URI is provably unchanged by any addition, change, or removal of content in a non-default language — verified by a test that mutates non-default-language state and asserts URI stability.
- **SC-004**: A concept with no explicit slug re-slugs when its default-language preferred label changes, and a concept with an explicit slug does not — both verified by test.
- **SC-005**: Two vocabularies with different default languages each anchor their concepts' slugs in their own default language — verified by a test using an app default and a per-vocabulary override.
- **SC-006**: A test obtains a fully multilingual concept (preferred labels and notes in more than one language) from the factories in three lines or fewer.
- **SC-007**: Every field this feature adds exposes translatable, non-empty metadata and a recorded indexing decision, and every validation message it introduces is translatable with named placeholders — all verified by the standards test.
- **SC-008**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python/Django matrix.

## Assumptions

- **Programmatic only.** This slice has no user interface, including the Django admin. "Editable one language at a time" is a guarantee of the data model and programming interface here; the live editing experience (type a label, watch the slug fill in, override it) lands with the management interface, roadmap R5.
- **Supersedes #15's single-label decision.** The concept's single default-language label from #15 becomes the default-language preferred label within this multilingual model. Nothing is released (the repo is at 0.0.x, models are branch-local and on no shared database), so there is no production data to migrate and the identity mechanism is preserved rather than rebuilt.
- **Language configuration is the application's.** Available languages are the app's configured languages; the application default language is its configured default, which a vocabulary may override. Exactly how a language set and default are configured is standard Django and not re-specified here.
- **Imported external vocabularies keep their own slugs.** For a pre-published vocabulary brought in later (roadmap R2), the concept slugs are its source URI paths and are never re-derived or edited. This feature's explicit-slug mechanism (FR-010) is what will later carry those slugs unchanged; the import behaviour itself is out of scope here.
- **Notation codes remain deferred.** A notation is a language-independent code with no consumer in this slice; the first feature that needs it models it (unchanged from #15).
- **SKOS pairwise label disjointness is not enforced this slice.** The SKOS integrity condition that a concept's preferred, alternative, and hidden labels in one language be pairwise distinct is deferred to a later validation or editor feature; recorded here so the omission is deliberate.
- **Storage shape is a planning decision.** How per-language, multi-valued labels and notes are persisted (and which values are projected into indexed columns) is decided at planning (S3) and by the Implementers, not fixed by this specification.
- **Sibling and later scope is untouched.** Concept relationships (#17), collections (#18), lifecycle and protected removal (#19), publishing with frozen URIs, and RDF import/export (R2/R4) are out of scope.
