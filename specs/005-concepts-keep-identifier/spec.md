# Feature Specification: Concepts keep the identifier they were published under

**Feature Branch**: `005-concepts-keep-identifier`

**Created**: 2026-08-03

**Status**: Draft

**Input**: Issue [#49](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/49) — "An imported vocabulary arrives with identifiers already assigned by whoever published it, and those identifiers are how the rest of the world refers to its concepts. Right now a concept's identifier is worked out from where it sits in this app, which is right for vocabularies created here but leaves nowhere to put the identifier an external concept came with."

**Serves**: G8 (external vocabularies as read-only references — an imported vocabulary cannot reference anything if its identifiers are discarded) · G4 (faithful round-trip — a record that cannot hold its source identifier cannot be exported as itself) · **Roadmap**: R2 · **Issue**: #49

> Scope note: this feature is the first slice of roadmap item R2 and the prerequisite for the rest of it. Today a vocabulary, concept, or collection has exactly one identifier, composed on read from the site's configured base address and the record's slugs, and lookup by identifier refuses anything outside that base. That is correct for vocabularies authored here and leaves nowhere to put the identifier an external vocabulary arrives with. This feature separates the two ideas that one string is currently carrying: a **static URI**, which is the record's identity and belongs to whoever published it, and a **local URL**, which is where the record is viewed on this site and always belongs to this site. Reading vocabulary files is [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50), language normalisation is [#51](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/51), and running an import from the command line is [#52](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/52), all of which build on the identity this feature establishes. **Out of scope:** parsing or importing any file, publishing a vocabulary and freezing its identifiers (roadmap R4, which owns the publication moment), attaching views or routes to the local URL (R4 serving and R6 browsing), the editing interface (R5), and any curator-facing way to type an identifier in by hand.

## Clarifications

### Session 2026-08-03

Four ambiguities surfaced by the coverage scan, resolved from the intake discussion, the constitution, and the precedent set by R1. Longer rationale is in `decisions.md`.

- **Q: Which identifiers may an external publisher assign — any absolute URI, or a restricted set?** → A: Any absolute URI with a scheme, except schemes that can carry executable content (`javascript:`, `data:`, `vbscript:`), which are refused. A stored identifier is rendered as a link by the browsing interface later, so a hostile value accepted here becomes a hazard there. An allowlist of `http` and `https` was rejected because real vocabularies legitimately use `urn:` identifiers, and refusing them would discard valid content to solve a problem a short refusal list already closes. Escaping at render time remains R6's responsibility as well. Integrated into FR-004.
- **Q: How long may an identifier be?** → A: 500 characters. That is far beyond any identifier real SKOS vocabularies use, and it stays inside the unique-index limit of every mainstream database, including MySQL's 3072-byte cap on `utf8mb4`. A larger bound would make the uniqueness of FR-006 unenforceable as an index on some deployments. Integrated into FR-004.
- **Q: Can an identifier move between fixed and provisional after the record exists?** → A: Only in one direction, and only twice in the system's whole design. A record becomes fixed when it is created from external content (this feature) or when its vocabulary is published (R4). Nothing turns a fixed identifier back into a provisional one, and no ordinary edit changes fixedness. A re-import matches an existing record *by* its identifier and therefore never rewrites it, which tightened FR-002. Integrated into FR-013.
- **Q: Does the existing identifier attribute keep its name and meaning?** → A: Yes. `uri` has always meant the record's identity (Article IX, `CONTEXT.md`), which is exactly the static URI, so it keeps its name and gains external values. Lookup by identifier keeps its name too and gains external resolution. The local URL is the new name on the surface, not a rename of anything. This is stated as a requirement so the change cannot arrive as a rename of a published package's API. Integrated into FR-014.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A record keeps the identifier it arrived with (Priority: P1)

A curator brings in a vocabulary published elsewhere. Its concepts, the vocabulary itself, and any collections in it already have identifiers assigned by their publisher — addresses on the publisher's own site, which is how the rest of the world refers to them. Those identifiers are held exactly as given. The app never rewrites one to look like an address of its own, and never recomputes one because a name or slug changed here. Moving this site to a different address, or reconfiguring the address it composes its own identifiers from, leaves every one of them untouched.

**Why this priority**: This is the whole of what the issue asks for and the blocker sitting in front of the rest of R2. Without somewhere for an external identifier to live, an imported concept cannot be matched back to its source, and the "import upserts by URI" invariant (Article IX) cannot be satisfied for external content at all. Implemented alone it is already useful: a vocabulary's true identifiers survive in the system.

**Independent Test**: In a test, create a vocabulary, a concept, and a collection each carrying an identifier from an unrelated domain, read the identifiers back and assert they are returned verbatim; rename each record and assert the identifiers are unchanged; change the site's configured base address and assert they are still unchanged.

**Acceptance Scenarios**:

1. **Given** a concept recorded with the identifier `http://vocabs.example.org/rock/granite`, **When** its static URI is read, **Then** exactly that string is returned, not a value composed from this site's base address.
2. **Given** that concept, **When** its name and slug are changed, **Then** its static URI is unchanged.
3. **Given** that concept, **When** the site's configured base address is changed, **Then** its static URI is unchanged.
4. **Given** a vocabulary and a collection each recorded with an identifier from an external publisher, **When** their static URIs are read, **Then** each returns the identifier it was given, and a concept's identifier is not derived from its vocabulary's.
5. **Given** an externally assigned identifier, **When** anything writes to the record, including a re-import that matched the record by that very identifier, **Then** the identifier is not rewritten, normalised, or re-cased, and the record does not revert to a provisional identifier.
6. **Given** a value that is not an absolute identifier, one carrying a script-bearing scheme such as `javascript:`, and one longer than the permitted bound, **When** each is offered as an externally assigned identifier, **Then** each is refused with a translatable message and nothing is stored.
7. **Given** a `urn:` identifier from a publisher that uses them, **When** it is offered as an externally assigned identifier, **Then** it is accepted and held verbatim.

---

### User Story 2 - Find a record by its identifier, wherever that identifier points (Priority: P2)

Something holding an identifier — an import matching a concept it has seen before, code resolving a reference — asks the system for the record it names. It gets an answer whether the identifier is one of this site's own or belongs to an external publisher. Today only the first kind can be found, because lookup refuses any identifier outside the configured base address before it reaches the database at all.

**Why this priority**: Upsert by identifier is the mechanism [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50) is built on and the Article IX invariant that keeps a re-import from destroying data. Storing an identifier that cannot then be looked up would leave the feature useless to the thing that needs it. It is second only because storage has to exist before anything can be found by it.

**Independent Test**: In a test, record a concept with an external identifier, look it up by that exact identifier and assert the right concept comes back; look up a local record by its own identifier and assert it still resolves; look up an identifier no record holds and assert the established not-found behaviour.

**Acceptance Scenarios**:

1. **Given** a concept whose static URI is `http://vocabs.example.org/rock/granite`, **When** it is looked up by that identifier, **Then** that concept is returned.
2. **Given** a vocabulary authored on this site, **When** one of its concepts is looked up by its own static URI, **Then** that concept is returned, preserving the behaviour established in R1.
3. **Given** an identifier no record holds, **When** it is looked up, **Then** the established not-found error is raised, with the same behaviour for an external identifier as for a local one.
4. **Given** two vocabularies, one imported and one authored here, **When** a concept from each is looked up by identifier, **Then** each returns its own record and neither is found by the other's identifier.
5. **Given** code written against the package as it stands today, **When** it reads a record's identifier and looks a record up by it, **Then** both still exist under the names they have now and answer as they did — this feature widens what they accept and never renames them.

---

### User Story 3 - A record authored here shows the identifier it will publish under (Priority: P2)

A curator building a vocabulary in the app, which has not been published, can still see the identifier each record will carry once it is. That value is composed from the site's configured address and the record's slugs, so it follows a rename while the vocabulary is still being worked on. The identifier is dynamic at this stage, and becomes static once the vocabulary is published. Every record already in the system when this feature lands shows the same identifier it did before, so nothing that already points at one breaks.

**Why this priority**: It keeps a single rule for the whole system — every record has a static URI, and only its fixedness differs — instead of a missing identity that half the app has to special-case. It also preserves R1's behaviour exactly, which is what stops this feature from being a breaking change. It is not P1 because an imported record can be stored and matched without it.

**Independent Test**: In a test, create a vocabulary and concept with no externally assigned identifier, assert each reports the identifier composed from the configured address and its slugs; rename one and assert the reported identifier follows the new slug; apply the upgrade to records created before this feature and assert each reports the identifier R1's composition gave it.

**Acceptance Scenarios**:

1. **Given** a concept created here with no externally assigned identifier, **When** its static URI is read, **Then** it is the value composed from the site's configured address, its vocabulary's slug, and its own slug.
2. **Given** that concept, **When** it is renamed and its slug changes, **Then** its static URI follows the new slug, because the value is provisional until publication.
3. **Given** records created before this feature landed, **When** the upgrade is applied and their static URIs are read, **Then** each is the identifier the previous composition produced for it, and every existing reference to a record still resolves.
4. **Given** a record with no externally assigned identifier, **When** the site's configured base address changes, **Then** its static URI reflects the new address, because it is this site's record and not yet published.
5. **Given** any two records in the system, **When** their static URIs are compared, **Then** no two records share one, and the uniqueness is enforced by the database.

---

### User Story 4 - Every record has a place on this site, whoever owns its identifier (Priority: P2)

An imported concept has to be viewable here even though its identifier points at somebody else's site. Every vocabulary, concept, and collection therefore has a local URL of its own — this site's address, its vocabulary's slug, and its own slug — separate from the identifier it publishes under. For a record authored here and not yet published the two read the same, which is why they look like one thing today. For an imported record they differ, and both are needed.

**Why this priority**: It stops the app having to choose between showing an imported concept and telling the truth about who published it, and it is the address the browsing interface (R6) and the serving layer (R4) will route on. It is specified now, alongside the identity split it belongs to, rather than being reverse-engineered later against records whose identifiers point elsewhere.

**Independent Test**: In a test, assert a locally authored concept's local URL and static URI are the same string; assert an imported concept's local URL is on this site and composed from its slugs while its static URI is the external one; assert a collection's local URL stays distinguishable from a concept's.

**Acceptance Scenarios**:

1. **Given** a concept authored here with no externally assigned identifier, **When** its local URL and static URI are read, **Then** both return the same value.
2. **Given** an imported concept whose static URI is on an external site, **When** its local URL is read, **Then** it is composed from this site's configured address, the concept's vocabulary slug, and the concept's slug, naming a place on this site.
3. **Given** an imported vocabulary and a collection inside it, **When** their local URLes are read, **Then** each names a place on this site, and a collection's address remains distinguishable from a concept's so the two can never name the same place.
4. **Given** any record, **When** it is renamed, **Then** its local URL follows the new slug, because a local URL is where the record currently sits rather than a promise.

---

### User Story 5 - Translatable field metadata and deliberate indexing (Priority: P3)

Every field this feature adds carries a human-readable, translatable label and help text, every user-facing validation message it introduces is translatable, and each new field's database indexing is a deliberate, recorded decision, because a consumer of a third-party package cannot add any of these themselves. The test factories can also produce a record carrying an externally assigned identifier in a line, so the import work that follows is not blocked on hand-building one.

**Why this priority**: A family-wide standard for every Django package this maintainer publishes (constitution Articles XII and XIII), carried by every slice of R1 before this one. It adds no new capability but gates the merge, so it travels with the feature at P3. The factory addition is small and is paid back immediately by [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50).

**Independent Test**: The existing metadata test suite walks every concrete field on the models and will cover the new ones; extend it. Separately, ask the factories for a record with an external identifier and assert it is saved and reports that identifier.

**Acceptance Scenarios**:

1. **Given** any field this feature adds, **When** its metadata is inspected, **Then** it declares a non-empty help text and a human-readable label, both lazily translatable.
2. **Given** a user-facing validation failure this feature introduces, **When** the error is raised, **Then** its message is translatable and uses named placeholders rather than baked-in values.
3. **Given** the database definition of the changed models, **When** their indexes are inspected, **Then** the identifier used for lookup is indexed, its uniqueness is a database constraint, and any queryable-but-unindexed field this feature adds is a recorded decision rather than an omission.
4. **Given** the test suite, **When** a test requests a vocabulary, concept, or collection carrying an externally assigned identifier from the factories, **Then** it receives a saved record reporting that identifier.

### Edge Cases

- An externally assigned identifier that happens to sit under this site's own configured address is still externally assigned and is never recomputed. Fixedness is a recorded property of the record, never inferred by comparing strings.
- Changing the site's configured base address moves every provisional identifier and no fixed one. A deployment that changes address after publishing is the concern of R4, which owns the freeze.
- Two records may not hold the same static URI. What an import should *do* when it meets one already held is matching behaviour and belongs to [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50). This feature only guarantees the collision cannot be stored.
- An imported vocabulary and a vocabulary authored here can sit side by side, and a record's fixedness is its own: a vocabulary whose identifier is external does not make a concept added to it afterwards external, and the reverse holds too.
- A record's local URL and static URI being equal is the ordinary case for local unpublished work, not a sign the two have been conflated. The equality must not be relied on anywhere as an invariant.
- An externally assigned identifier is stored as the publisher wrote it, within the bounds FR-004 sets: absolute, no script-bearing scheme, no longer than the permitted length. What an importer does when its source carries a value that fails those bounds — skip the record, abort the run, or report it — is [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50)'s concern, not this feature's.
- Refusing script-bearing schemes on the way in does not relieve the browsing interface (R6) of escaping what it renders. The refusal keeps a hostile value out of the database; escaping keeps a merely awkward one out of the page.
- Fixedness never reverses. There is no operation in this feature, or planned for any later one, that turns an imported record back into a locally provisional one — an identifier wrongly recorded as fixed is corrected by removing the record, not by demoting it.
- Existing deployments upgrade without any record changing the identifier it reported before (Article IX: migrations preserve concept URIs and existing references).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A vocabulary (`ConceptScheme`), a concept, and a collection MUST each carry a **static URI** — the record's identity, a single value that is either externally assigned or provisional, readable on every record without exception.
- **FR-002**: An externally assigned static URI MUST be held verbatim: never composed, never recomputed from the site's configured address or the record's slugs, never normalised or re-cased, and never changed once stored. A re-import matches an existing record *by* its identifier and therefore has no occasion to rewrite it.
- **FR-003**: A record MUST record **explicitly** whether its static URI is externally assigned (fixed) or provisional. This MUST NOT be inferred by testing the identifier against the site's configured base address, because that address can change and an external publisher's address may legitimately resemble it.
- **FR-004**: An externally assigned static URI MUST be a well-formed absolute identifier carrying a scheme, MUST NOT use a scheme that can carry executable content (`javascript:`, `data:`, `vbscript:`), and MUST NOT exceed 500 characters. A value failing any of these MUST be refused with a translatable message rather than stored. A value that could never be resolved would corrupt the identity guarantee this feature exists to provide, a script-bearing value becomes a hazard the moment the browsing interface renders it as a link, and a value beyond the length bound cannot be covered by the unique index FR-006 requires on every supported database.
- **FR-005**: A record whose static URI is **provisional** MUST report the value composed from the site's configured base address, its vocabulary's slug, and its own slug — the composition R1 established — and that value MUST follow a rename and a change to the configured address.
- **FR-006**: No two records MAY hold the same static URI. The uniqueness MUST be enforced by a database constraint, not by application code alone.
- **FR-007**: Looking a record up by static URI MUST resolve records whose identifier lies **outside** the site's configured base address as readily as those within it, and MUST raise the established not-found error, unchanged, when no record holds the identifier given.
- **FR-008**: A vocabulary, a concept, and a collection MUST each expose a **local URL** — this site's configured address, the vocabulary's slug, and the record's own slug — which names a place on this site regardless of who assigned the record's static URI, and which follows a rename. A collection's local URL MUST stay distinguishable from a concept's, preserving the separation R1 established.
- **FR-009**: Upgrading an existing deployment MUST leave every record reporting the same identifier it reported before, and MUST preserve every existing reference to a record (Article IX).
- **FR-010**: Every model field this feature adds MUST declare a human-readable, lazily translatable label and non-empty help text, and every user-facing validation message it introduces MUST be translatable with named placeholders so the message identifier stays static. Developer-facing diagnostics are exempt.
- **FR-011**: Indexing MUST be deliberate: the static URI is the column identity lookups run against and MUST be indexed, its uniqueness (FR-006) MUST be a database constraint, and any queryable-but-unindexed field this feature adds MUST be a recorded decision.
- **FR-012**: The test suite MUST ship factories able to produce a vocabulary, a concept, and a collection carrying an externally assigned static URI.
- **FR-013**: Fixedness MUST move in one direction only. A record's static URI becomes fixed when the record is created from external content, and no ordinary edit, rename, or re-import MAY turn a fixed identifier back into a provisional one. (The second and only other way a record becomes fixed is publication, which R4 owns.)
- **FR-014**: The existing identifier attribute and the existing lookup-by-identifier MUST keep their current names and meanings — the identity they have always denoted is the static URI — and MUST gain external values and external resolution rather than being renamed. The local URL is an addition to the package's surface, not a rename of anything already published.

### Key Entities *(include if feature involves data)*

- **Static URI**: the globally stable identity of a vocabulary, concept, or collection. Externally assigned when the record came from a vocabulary published elsewhere, in which case it is that publisher's address and is fixed. Provisional when the record was authored here and has not been published, in which case it is composed from this site's address and the record's slugs and follows a rename. Identity has always lived here rather than in the database key (Article IX); what changes is that it can now belong to somebody else.
- **Local URL**: where a record is viewed on this site — this site's configured address, the vocabulary's slug, and the record's own slug. Always this site's own, for every record, whoever assigned its static URI. Equal to the static URI for local unpublished work and different for anything imported. The value R4 and R6 will attach routes to.
- **ConceptScheme, Concept, Collection (extended)**: unchanged in naming, structure, relations, and membership. Each gains a static URI it may hold as given, an explicit record of whether that identifier is fixed, and a local URL separate from it. No new relationship between the three models is introduced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A vocabulary, concept, or collection recorded with an identifier from an external publisher reports that exact identifier, unchanged, after a rename and after the site's configured base address is changed — verified by test.
- **SC-002**: A record recorded with an external identifier is found by looking that identifier up, and a locally authored record is still found by its own — verified by test, with the established not-found behaviour preserved for an identifier no record holds.
- **SC-003**: A record authored here with no external identifier reports the identifier composed from the configured address and its slugs, and that value follows a rename — verified by test.
- **SC-004**: Whether a record's identifier is fixed is answerable from the record itself, and a fixed identifier that happens to resemble this site's own address is still not recomputed when the configured address changes — verified by test.
- **SC-005**: Two records cannot be stored holding the same static URI, and the refusal comes from the database constraint — verified by test.
- **SC-006**: An identifier that is not a well-formed absolute identifier, one carrying a script-bearing scheme, and one beyond the length bound are each refused with a translatable message rather than stored, while a `urn:` identifier is accepted — verified by test.
- **SC-007**: Every record reports a local URL on this site composed from its slugs, an imported record's local URL and static URI differ while a local unpublished record's are equal, and a collection's local URL can never collide with a concept's — verified by test.
- **SC-008**: Upgrading a deployment created before this feature leaves every record reporting the identifier it reported previously, with every existing reference intact — verified by test against pre-existing records.
- **SC-009**: Every field this feature adds exposes translatable, non-empty metadata and a recorded indexing decision, and every validation message it introduces is translatable with named placeholders — verified by the standards test.
- **SC-010**: A test obtains a vocabulary, concept, or collection carrying an externally assigned identifier from the factories in a line.
- **SC-011**: A record whose identifier is fixed cannot be returned to provisional by a rename, an edit, or a re-import — verified by test.
- **SC-012**: The identifier attribute and the lookup-by-identifier this package already publishes still exist under their current names and still answer for locally authored records exactly as they did — verified by test.
- **SC-013**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python and Django matrix.

## Assumptions

- **The publication moment belongs to R4.** This feature builds the mechanism — an identifier that is fixed when externally assigned and provisional otherwise — but nothing here publishes a locally authored vocabulary or freezes its identifiers. R4 owns that moment explicitly ("publishing a vocabulary and freezing its concept URIs are the same moment"), and it will fix a local record's provisional identifier using the mechanism this feature provides. Confirmed at grilling.
- **Every record has a permanent URI; what changes is whether it is dynamic or static.** While a record is authored here and unpublished its permanent URI is dynamic: composed from the site's configured address and the record's slugs, and free to move when those move. It becomes static when the record arrives from an external publisher, or when its vocabulary is published (R4), and from that moment it never changes again. There is no state in which a record lacks a permanent URI. Confirmed at grilling.
- **The local URL has no routes yet.** The package has no URL configuration, no views, and no `get_absolute_url`, so a route defined here would point at nothing. This feature defines the composition rule and exposes the value. Whether it is later resolved through Django's URL machinery rather than composed directly is R4's and R6's decision, when the views those items add give it something to resolve against. Recorded in `decisions.md`.
- **Storage shape is a planning decision.** Whether the static URI is a stored column kept in step on save or a stored column with a computed fallback, how fixedness is represented, and how a provisional value is kept current as slugs and the configured address change, are decided at planning (S3), guided by `docs/brainstorm.md` and the R1 precedent. The specification fixes the observable guarantees, not the mechanism.
- **The glossary splits in two.** `CONTEXT.md` currently carries one **URI** entry, defined as "the globally stable identifier of a scheme or concept". That entry becomes **static URI**, and **local URL** joins it as a distinct term. Both are updated as part of this feature so the shared vocabulary matches the code that follows it.
- **No hand-entered identifiers.** Nothing here gives a curator a way to type an identifier in or override one. An externally assigned identifier arrives with imported content. The editing interface is R5.
- **Matching is not identity.** This feature guarantees an identifier can be stored, is unique, and can be looked up. Deciding which existing record an incoming one *is*, and what to do when an identifier is already held, is import behaviour and belongs to [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50).
- **The configured base address is this site's own address.** It composes local URLes for every record and provisional identifiers for unpublished local ones. It has no bearing on an externally assigned identifier, which is the change this feature makes to its meaning.
