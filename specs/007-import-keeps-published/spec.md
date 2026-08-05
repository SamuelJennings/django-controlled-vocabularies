# Feature Specification: Import keeps the languages the site supports and reports the rest

**Feature Branch**: `007-import-keeps-published`

**Created**: 2026-08-04

**Status**: Draft

**Input**: Issue [#51](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/51) — "External vocabularies are often published in far more languages than a given site cares about, and storing all of them fills the database with content nobody will read. A curator wants an import to keep the languages their site is configured for and to be told plainly what was left behind, rather than discovering later that content vanished silently. If they add a language to the site afterwards, re-running the import should fill in that language for the concepts already there, without disturbing anything else."

**Serves**: G8 (external vocabularies as read-only references — a published vocabulary the site stores nothing of is one it cannot reference) · G6 (multilingual concepts — this decides which of a publisher's languages become the site's) · G4 (faithful round-trip — a language kept is a language that can be given back) · **Roadmap**: R2 · **Issue**: #51

> Scope note: this is the third slice of roadmap item R2. [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50) built the import itself and, as a consequence of the models it writes through, already filters values to the languages the site is configured for and names what it set aside. This feature decides **which published language tags count as a configured language**, makes what was left behind usable to a curator rather than merely present in a list, and turns the additive re-import from a side effect into a guarantee. The entry point remains **programmatic**: rendering any of this at a terminal is [#52](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/52), which owns *where* a curator reads the account while this feature owns *what* they are told. **Out of scope:** any command-line or web-facing surface (#52 and R5), exporting or serving RDF (R4), the concept consumption field (R3), browsing (R6), translating content between languages, and storing content in languages the site is not configured for in any form.

## Clarifications

### Session 2026-08-04

The matching direction was settled with the maintainer at intake: language tags match by their base language, in both directions. Four consequences of that rule had no answer in the intake discussion and are resolved here against it, the constitution, and what [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50) already built. Longer rationale is in `decisions.md`.

- **Q: A file offers several variants of one configured language for the same value — which one is kept?** → A: An exact tag match always wins, and nothing can displace it. Where no variant matches exactly, the variant the vocabulary predominantly publishes in wins, with ties broken by language code so the same file always imports the same way. The alternative — taking whichever variant sorts first — is equally deterministic and simpler, but hands a curator on `en` the `en-au` spelling of a vocabulary published overwhelmingly in `en-gb`, for a reason nobody could explain from the file. Every value that loses is set aside and reported, exactly as a surplus preferred label already is. Integrated into FR-003 and FR-005.
- **Q: The site is configured for several languages sharing a base, and the file's tag matches none of them exactly — which one receives the value?** → A: The least specific configured language sharing that base, so a site configured for both `en` and `en-gb` stores an `en-us` value under `en`. The value is a variant of neither, and the broader audience is the defensible destination. Integrated into FR-002.
- **Q: Does base-language matching join variants that differ by script, such as `zh-Hant` filling a `zh-Hans` site's slot?** → A: Yes, under the agreed rule, and this is the rule's sharpest edge rather than an oversight. Simplified and Traditional Chinese share a base language and are not mutually readable, so a curator could receive content in a script they cannot use. It is not silent — every substitution is reported as one (FR-006) — and the alternative is a script-awareness rule the intake discussion never reached. Recorded here, in `decisions.md`, and raised at the Spec gate, because narrowing it is the maintainer's call and not this feature's. Integrated into FR-001.
- **Q: What is a curator actually told about content that could not be kept?** → A: How much of it there is, per language. A list naming several hundred set-aside values one by one answers "what happened" and not "what should I do", whereas a count per language tells a curator which single configuration change would recover the most content. The existing report already groups by reason, so the reason bucket is not the gap — the per-language breakdown inside it is. Integrated into FR-008.

### Session 2026-08-04 (coverage scan)

Four further ambiguities surfaced by the structured coverage scan over the drafted spec. The first is a defect in the draft rather than an omission in the intake discussion.

- **Q: Does the one-winner rule apply to every kind of value, or only where the models hold one per language?** → A: Only where they hold one. `ConceptLabel`'s uniqueness constraint is conditional on the preferred kind, and `ConceptNote` carries no uniqueness constraint at all, so alternative labels, hidden labels, and notes may hold as many values per language as the file offers. The draft's rule would have collapsed a `en-gb` and an `en-us` alternative label into one and set the other aside, discarding content the models can hold, in a feature whose purpose is keeping content. The contest exists only where the destination has one slot. Integrated into FR-003 and FR-004.
- **Q: What does the language account look like after a run that left nothing behind?** → A: Present and empty. An absent account and an account of zero are the same thing to a reader and different things to a caller, and #52 renders from it without knowing which kind of run produced it. Integrated into FR-008.
- **Q: Are base language, variant, and substitution established terms in this project?** → A: No, all three are new here, and the report will put two of them in front of a curator. The project keeps its glossary in `CONTEXT.md`, so they belong there rather than being defined only inside a spec that a reader of the report will never open. Integrated into FR-014.
- **Q: Does changing what an already-run import stores oblige a compatibility path?** → A: No. This feature makes a previously-refused value storable, so a site that re-imports after upgrading gains content it did not have. That would be a behaviour change owed a migration note if any release carried the old rule, and none does — the package is at `0.0.x` and its first publish is the v0.1.0 milestone this work sits inside. Recorded so the absence of a migration path is a decision rather than an oversight. Integrated into Assumptions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A vocabulary published in a variant of the site's language imports (Priority: P1)

A curator runs a site configured for British English and imports a published vocabulary whose labels and notes are tagged `en`. The content arrives instead of vanishing. The same holds in reverse: a site configured for plain `en` importing a vocabulary published only as `en-gb` gets its labels and notes, rather than an empty vocabulary and a report saying every value was in a language the site is not configured for.

**Why this priority**: This is the feature's reason to exist. Before it, a mismatch of region subtags between a publisher and a site meant a vocabulary imported as a shell of concepts with no readable content, and the report explained the loss without preventing it. Regional and script variants are ordinary in published vocabularies, so the mismatch is common rather than exotic.

**Independent Test**: Import a fixture tagged only `en` into a site configured only for `en-gb`, and a fixture tagged only `en-gb` into a site configured only for `en`. Both must produce concepts carrying their labels and notes.

**Acceptance Scenarios**:

1. **Given** a site configured for `en-gb` only, **When** a vocabulary whose labels are tagged `en` is imported, **Then** each concept carries its label stored under `en-gb`.
2. **Given** a site configured for `en` only, **When** a vocabulary whose labels are tagged `en-gb` is imported, **Then** each concept carries its label stored under `en`.
3. **Given** a site configured for `en` only, **When** a vocabulary whose labels are tagged `fr` is imported, **Then** those values are stored nowhere and are named in the report, because `fr` shares no base language with any configured language.
4. **Given** a site configured for `de` only, **When** a vocabulary declares itself in `de-at` and names its concepts in `de-at`, **Then** the vocabulary's default language resolves to `de` and every concept is named, rather than falling back to the site default with concepts left unnamed.

---

### User Story 2 - A curator can see what was left behind and what it would take to keep it (Priority: P1)

After an import, a curator wants to know the scale and shape of what could not be stored, without reading an entry for every value. They want to see that 312 values were left behind in French and 47 in German, so that adding one language to the site is a decision they can make from evidence rather than a guess.

**Why this priority**: The second half of the issue, and the half the dependency deliberately left open. [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50) already records every set-aside value with its reason and its language, and already groups those records by reason. What it does not do is answer the question a curator actually has, which is not "what happened" but "what should I change". A per-reason total of 359 unreadable values is a fact. A breakdown showing 312 of them are French is a decision.

**Independent Test**: Import a vocabulary carrying values in several unconfigured languages and read the per-language counts from the report, without parsing any rendered message.

**Acceptance Scenarios**:

1. **Given** a vocabulary carrying values in three languages the site is not configured for, **When** it is imported, **Then** the report exposes a count per language, as data.
2. **Given** the same import, **When** the counts are read, **Then** they cover every value that was not stored for a language reason and no value that was stored.
3. **Given** an import in which a value was stored under a configured language other than the tag it was published under, **When** the report is read, **Then** that substitution is named as one, distinctly from values that were not stored at all.

---

### User Story 3 - Competing variants resolve the same way every time (Priority: P2)

A published vocabulary carries a concept's preferred label in `en`, `en-gb`, and `en-us`, and the site is configured for one English. One value can be kept. The curator gets the same one on every run of the same file, and the report accounts for the others.

**Why this priority**: It is a correctness property rather than a capability, and it only bites files carrying several variants of one language. It travels below the two stories above because an import that keeps the wrong English is still an import that keeps English, whereas an import that keeps nothing is not. It cannot be deferred past this feature, though, because a non-deterministic choice makes a re-import rewrite content for no reason the file explains.

**Independent Test**: Import a fixture carrying three variants of one language for the same concept, twice, and compare. The stored value is identical across runs, and the two values not kept are named in the report.

**Acceptance Scenarios**:

1. **Given** a site configured for `en` and a file carrying a concept's preferred label in `en`, `en-gb`, and `en-us`, **When** it is imported, **Then** the `en` value is stored, because an exact match wins.
2. **Given** a site configured for `en` and a file carrying that label only in `en-gb` and `en-us`, where the vocabulary's other labels are predominantly `en-gb`, **When** it is imported, **Then** the `en-gb` value is stored.
3. **Given** the same file, **When** it is imported a second time, **Then** the stored value is unchanged.
4. **Given** any of the above, **When** the report is read, **Then** every variant value not stored is named with its language.
5. **Given** a site configured for `en` and a concept carrying alternative labels in `en-gb` and `en-us`, **When** it is imported, **Then** both are stored under `en`, because the models hold as many alternative labels per language as the file offers and no contest exists.

---

### User Story 4 - Adding a language and re-importing fills it in (Priority: P2)

A curator imports a vocabulary, later configures the site for an additional language the publisher provides, and runs the same import again. The concepts already there gain their values in the new language. Nothing else about them changes: not their identifiers, not their local addresses, not their content in the languages already stored.

**Why this priority**: The behaviour is already true as a consequence of the dependency's rule that a file is authoritative for the records it contains, which is why it sits below work that changes what the system does. True by accident is not the same as guaranteed, though, and this is the sentence in the issue a curator would rely on when deciding to adopt a vocabulary before the site is finished. A test is what turns it into a promise.

**Independent Test**: Import a multilingual fixture into a site configured for one language, reconfigure for two, re-import the same file, and compare every record before and after.

**Acceptance Scenarios**:

1. **Given** a vocabulary imported into a site configured only for `en`, **When** the site is configured for `en` and `fr` and the same file is imported again, **Then** the concepts already present carry their French labels and notes.
2. **Given** the same re-import, **When** the records are compared with their state before it, **Then** every identifier, local address, and database identity is unchanged.
3. **Given** the same re-import, **When** the English content is compared, **Then** it is unchanged except where the file itself changed it.
4. **Given** the same re-import, **When** the report is read, **Then** the values newly stored in French are no longer reported as left behind.

---

### User Story 5 - Translatable messages, deliberate indexing, and reusable test material (Priority: P3)

Every message this feature puts in front of a person is translatable, any field metadata it touches carries its own translations and help text, and the vocabularies it needs on disk are fixtures the features after it can use.

**Why this priority**: A family-wide standard carried by every slice of R1 and by both preceding slices of R2 (constitution Articles XII, XIII and XIV). It adds no capability but gates the merge, so it travels last. The fixtures are paid back immediately, because [#52](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/52) needs a vocabulary with variant language tags to demonstrate its summary against.

**Independent Test**: The standards test finds no untranslated message and no field lacking metadata, and the new fixtures load from the suite rather than being built inline.

**Acceptance Scenarios**:

1. **Given** any message this feature adds, **When** the standards test runs, **Then** it is translatable with named placeholders.
2. **Given** the test suite, **When** a test needs a vocabulary carrying variant language tags, **Then** it loads one from the fixtures rather than constructing it inline.

---

### Edge Cases

- A published tag differing from a configured language only in case, such as `EN-GB` against `en-gb`. Language tags are not case-sensitive, so this is an exact match and not a variant one.
- A published tag carrying more subtags than any configured language, such as `zh-Hans-CN` against a site configured for `zh-Hans`.
- A file carrying both an exact match and a variant for the same value, where the exact match is empty or unusable. The exact match wins the contest and then fails on its own merits, and the variant does not silently take its place.
- A concept whose preferred label in the vocabulary's default language arrives only by variant match. It names the concept and derives its slug exactly as an exact match would.
- A value carrying no language tag at all, which remains outside this feature's reach and continues to be set aside by the rule the dependency established.
- A vocabulary whose predominant variant is a language the site is not configured for at all, which decides nothing about which configured variant wins.
- Several variants of one language arriving for a kind the models hold many of, such as two alternative labels, where there is no contest to resolve and both are kept.
- A run in which nothing at all was left behind, whose account is present and empty rather than missing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A published language tag MUST match a configured language when the two share a base language, in both directions, so a file's `en` value MAY be stored under a configured `en-gb` and a file's `en-gb` value MAY be stored under a configured `en`. Matching MUST NOT be case-sensitive. A tag sharing no base language with any configured language MUST continue to be set aside and reported, unchanged from #50.
- **FR-002**: An exact tag match MUST always take precedence over a variant match, and MUST NOT be displaced by one. Where several configured languages share a base language with a published tag and none matches it exactly, the least specific of them MUST receive the value. *(Annotated 2026-08-05: an earlier refinement carved out the default-language slot from this rule. That carve-out is withdrawn — see FR-016 — and FR-002 stands exactly as the Spec gate approved it.)*
- **FR-003**: Where the models hold at most one value of a kind per language — the preferred label — and a file offers several published variants of one configured language with no exact match among them, the variant the vocabulary predominantly publishes in MUST be the one stored, with ties broken deterministically by language code. The same file MUST import to the same stored values on every run.
- **FR-004**: Where the models hold several values of a kind per language — alternative labels, hidden labels, and notes — every variant value MUST be stored under the configured language. Variant matching MUST NOT reduce them to one, and MUST NOT discard content the models are able to hold.
- **FR-005**: Every value not stored because FR-003 kept another in its place MUST be set aside and reported with its own published language, and MUST NOT fail the run.
- **FR-006**: A value stored under a configured language other than the tag it was published under MUST be reported as a substitution, never applied silently (Article XI), and MUST be distinguishable in the report from a value that was not stored at all.
- **FR-007**: The vocabulary's default language MUST be resolved by the same matching rule, so a vocabulary declaring itself in a variant of a configured language MUST resolve to that configured language rather than falling back to the site's default.
- **FR-008**: The report MUST expose, as data rather than prose, how many values were not stored for a language reason, broken down by the published language they carried. It MUST be sufficient for a caller to rank languages by what configuring them would recover, without parsing any rendered message. It MUST be present and empty after a run that left nothing behind, rather than absent.
- **FR-009**: Re-running an import after a language is added to the site's configuration MUST store that language's values for the records the file contains. It MUST NOT alter any record's identifier, local address, or database identity, and MUST NOT remove or alter stored values in any other language except where the file itself changed them.
- **FR-010**: This feature MUST NOT store content in any language the site is not configured for, in any form. It changes which published tags resolve to a configured language, never the set of languages the site holds.
- **FR-011**: This feature MUST NOT add a command-line, web-facing, or other curator-visible surface. What a curator is told is defined here as data on the report, and #52 owns rendering it.
- **FR-012**: Every message this feature puts in front of a person MUST be translatable with named placeholders. Developer-facing diagnostics are exempt (Article XII).
- **FR-013**: Any model field this feature adds MUST carry translatable metadata and non-empty help text, and its indexing MUST be a deliberate recorded decision (Articles XII and XIII).
- **FR-014**: The terms this feature introduces — base language, variant, and substitution — MUST be added to the project's glossary, so the vocabulary of the report matches the vocabulary of the documentation.
- **FR-015**: The test suite MUST ship a published vocabulary fixture carrying variant language tags for one base language, discoverable from the suite, so #52 does not rebuild it.
- ~~**FR-016**: The preferred label a concept is named by — the one in the vocabulary's default language, from which its local address is derived — MUST NOT change because the site's configured languages changed. The contest for that one slot MUST therefore be resolved over every published tag sharing the default language's base, whether or not some of those tags are themselves configured.~~ **Withdrawn 2026-08-05 before any code implemented it, superseded by FR-017 and FR-018** (`decisions.md` D35). It treated a symptom at the wrong layer: it held one label still so that an address derived from that label would stay still, when the address should never have been derived from a translated value at all.
- **FR-017**: An imported record's slug MUST be derived from the identifier its publisher assigned, and MUST NOT be derived from any translated value. It MUST NOT be recomputed on a later import for any reason — not a changed label, not a changed configured-language set, not a changed default language. The slug is the last segment of the published identifier: its fragment where it has one, otherwise the last segment of its path.
- **FR-018**: FR-017 governs the vocabulary's own slug on the same terms, so a local address is `/{vocabulary}/{record}` with **both** segments derived from published identifiers. A vocabulary whose name arrives in a different language on a later import MUST NOT move the address of a single record it holds.
- **FR-019**: A record authored on this site rather than imported has no publisher identifier to derive from, and MUST keep deriving its slug from its label as it does today. For those records this application composes the identifier *from* the slug, so the dependency runs the other way and nothing here changes it.
- **FR-020**: Where two records in one vocabulary would derive the same slug, the collision MUST be resolved deterministically **from their identifiers**, so that the same file produces the same slugs on every import and a record's slug does not depend on the order records were read.

### Key Entities *(include if feature involves data)*

- **Language match**: the resolution of one published language tag to one configured language, or to none. Either exact, or by shared base language, and in the second case a substitution the report names.
- **Language account**: the part of the report answering how much content was left behind and in which published languages, sufficient to rank what configuring a language would recover.
- **Import report**: the structured outcome of a run, established by #50. This feature adds to it rather than replacing it, and #52 consumes it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A vocabulary published only as `en` imports into a site configured only for `en-gb`, with every concept carrying its label and notes — verified by test.
- **SC-002**: A vocabulary published only as `en-gb` imports into a site configured only for `en`, with every concept carrying its label and notes — verified by test.
- **SC-003**: A vocabulary published in a language sharing no base language with any configured language stores nothing and is named in the report, exactly as before this feature — verified by test.
- **SC-004**: A published tag differing from a configured language only in case is treated as an exact match — verified by test.
- **SC-005**: Where a file offers an exact match and one or more variants for the same value, the exact match is the value stored — verified by test.
- **SC-006**: Where a file offers only variants, the vocabulary's predominant variant is the preferred label stored, and importing the same file twice stores the same value both times — verified by test.
- **SC-007**: Alternative labels, hidden labels, and notes published in several variants of one configured language are all stored, none of them set aside — verified by test.
- **SC-008**: Every variant value not stored is named in the report with its own language, and the run still succeeds — verified by test.
- **SC-009**: A value stored under a configured language other than its published tag is reported as a substitution and is distinguishable from a value that was not stored — verified by test.
- **SC-010**: A vocabulary declaring itself in a variant of a configured language resolves its default language to that configured language, and every concept is named — verified by test.
- **SC-011**: The report yields a count of values not stored for a language reason, broken down by published language, read as data — verified by test.
- **SC-012**: Those counts cover every value not stored for a language reason and no value that was stored — verified by test.
- **SC-013**: A run that left nothing behind yields an account that is present and empty rather than absent — verified by test.
- **SC-014**: Configuring an additional language and re-importing the same file stores that language's values for concepts already present — verified by test.
- **SC-015**: That re-import leaves every identifier, local address, and database identity unchanged, and every other language's stored content unchanged — verified by test.
- **SC-016**: After that re-import, the values newly stored are no longer counted as left behind — verified by test.
- **SC-017**: No content is stored in any language absent from the site's configuration, under any matching path — verified by test.
- **SC-018**: Every message this feature shows a person is translatable with named placeholders — verified by the standards test.
- **SC-019**: Base language, variant, and substitution are defined in the project glossary — verified by review of `CONTEXT.md`.
- **SC-020**: A published vocabulary fixture carrying variant language tags exists and is loaded by the tests from the suite rather than built inline — verified by test.
- **SC-021**: Every functional requirement above is exercised by at least one automated test, and the suite passes across the supported Python and Django matrix.
- **SC-022**: Adding a configured language that **shares a base** with one the site already holds, and re-importing the unchanged file, leaves every concept's ~~name,~~ slug, and local address exactly as they were — verified by test. The test MUST add a base-sharing language, because a test that only ever adds an unrelated one cannot fail (SC-015's did not). *(Annotated 2026-08-05, decisions.md D48: the `name` clause is struck. It was written for FR-016, which pinned a concept's displayed label so that an address derived from that label would stay still. FR-016 is withdrawn and the address no longer comes from the label at all (FR-017), so the clause now contradicts FR-002 as restored — configuring `en-gb` correctly moves an `en-us` value out of the `en` slot. The stability this criterion exists to guarantee is the address, and FR-017 guarantees it at the right layer.)*
- **SC-023**: A vocabulary whose effective default language is a code the site does not hold is refused or reported as that one problem, rather than silently importing nothing while reporting a missing preferred label per concept — verified by test under `LANGUAGE_CODE` set outside `LANGUAGES`.
- **SC-024**: A published value the models cannot store because of its own content — a label longer than the field allows — is set aside and reported, and ~~the rest of the file still imports~~ — verified by test. *(Annotated 2026-08-05, decisions.md D49: fix cycle 4 overturned the struck clause for one case the original wording did not anticipate — a vocabulary's own name, published only as an over-long value, on a vocabulary this run is creating. Without a resolved vocabulary the rest of the file has nowhere to import into, so that one case is fatal rather than set aside; see SC-031. Every other value this criterion covers — a matched vocabulary's name, and a concept's or a collection's own value, created or matched — still keeps the original guarantee, and is still set aside while the rest of the file imports around it.)*
- **SC-025**: A concept set aside for having no usable preferred label still contributes its published languages to the account, so the language whose configuration would recover it is visible — verified by test.
- **SC-026**: An imported record's slug equals the last segment of its published identifier, for an identifier carrying a fragment and for one carrying none — verified by test.
- **SC-027**: Re-importing a file whose publisher has renamed a record leaves that record's slug and local address unchanged — verified by test. This is the case the previous rule deliberately allowed to move, and it is now forbidden.
- **SC-028**: Re-importing a file whose vocabulary name arrives in a different language leaves the vocabulary's slug, and the local address of every record inside it, unchanged — verified by test.
- **SC-029**: Two records in one vocabulary whose identifiers end in the same segment both import, with distinct slugs, and both keep those slugs when the same file is imported again in any order — verified by test.
- **SC-030**: A record created on this site rather than imported still derives its slug from its label, and still follows a relabel — verified by test, so FR-019 is not quietly broken by the change FR-017 makes.
- **SC-031**: A vocabulary's own name, published only as a value longer than the field allows, refuses the whole run when this run is creating that vocabulary — nothing else in the file has a resolved vocabulary to import into — but leaves a matched vocabulary's existing name in place, set aside rather than fatal — verified by test (decisions.md D49).
- **SC-032**: A matched vocabulary whose own record fails to write — its stored slug is invalid, or a value the model refuses for any other reason — refuses the whole run rather than reporting a clean success while nothing was imported — verified by test (decisions.md D57).
- **SC-033**: A vocabulary or collection this run is creating that publishes no preferred label in any language is refused (a vocabulary) or dropped in full (a collection) rather than persisted with a blank name — verified by test (decisions.md D59).

## Assumptions

- The site's configured languages are whatever the project declares, and this feature reads that declaration rather than introducing a setting of its own. A project wanting different behaviour changes the languages it supports.
- A base language is the first subtag of a published language tag. Tags in published vocabularies follow the ordinary convention for language tags, and one that does not is a value the import cannot interpret rather than a case to accommodate.
- Script-differing variants of one base language are joined by this rule, as the Clarifications record. This is raised at the Spec gate rather than absorbed, because narrowing it is a maintainer decision.
- The models continue to refuse a language outside the site's configuration, and this feature writes through the same helpers #50 does rather than around them. Nothing here weakens that invariant.
- The report established by #50 is extended, not redesigned. #52 is being specified against its existing shape, and a redesign here would strand it.
- No published release carries the previous matching rule, so a site that re-imports after upgrading simply gains content it did not have, and no migration path or compatibility flag is owed. The package is at `0.0.x` and its first publish is the v0.1.0 milestone this work sits inside. Were that not so, the change would need one.
- Fixtures from #50 are reused where they serve, and the variant fixture is added alongside them rather than replacing any.
