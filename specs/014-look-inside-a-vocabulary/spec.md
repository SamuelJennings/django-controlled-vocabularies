# Feature Specification: Look inside a vocabulary

**Feature Branch**: `014-look-inside-a-vocabulary`

**Created**: 2026-08-20

**Status**: Draft

**Input**: Issue [#141](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/141) — "Once a visitor has picked a vocabulary they need a way into its terms, which for a vocabulary of any size means both a way to search it and a way to work down through it from the top. This is the page a vocabulary's own address leads to. It describes the vocabulary and who publishes it, and presents the concepts and collections inside so a person can find one without already knowing its name."

**Serves**: G7 (vocabulary browsing) · **Roadmap**: R6 · **Issue**: #141

> Scope note: this is the second of three slices of roadmap item R6, and it depends on
> [#140](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/140), which
> delivered the list of vocabularies and deliberately left its entries unlinked because nothing
> served a vocabulary's address yet. This feature owns **one page: the page a vocabulary's own
> address leads to**, everything it tells a reader about that vocabulary, the two ways it offers
> into the vocabulary's terms, and the link from the list page that finally leads here.
> **Out of scope:** a page for an individual concept, collection or ordered collection, which is
> [#142](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/142); searching for
> a term without knowing which vocabulary holds it, which no roadmap item currently covers; editing
> anything shown here; any access rule of the package's own; keeping the page fast at a scale the
> project has not yet met, which is R7; and publication, deprecation and the curator interface,
> which are R4 and R5.

## Clarifications

### Session 2026-08-20 (intake)

Five decisions were taken with the maintainer at intake, because each decides what the feature is
rather than how it is built.

- **Q: The issue says the page shows "who publishes it". Nothing in the data model records a publisher — does this feature start recording one?** → A: No. Provenance only: whether the vocabulary is held on this site or was published elsewhere, exactly as the list page already expresses it. The maintainer named a named publisher as a genuine future need, to be derived from an existing record or required on the data model when it comes, and deferred it out of this feature. Integrated into FR-003 and Assumptions.
- **Q: Do the concepts and collections shown here link to their own pages?** → A: No, and for the same reason the list page's entries did not link to a vocabulary: the addresses of individual records are served by #142, and a link to a page that does not exist is a broken one. The link lands in the change that gives it somewhere to lead. Integrated into FR-014 and Edge Cases.
- **Q: The vocabulary's identifier — plain text, as it is on the list page, or a link?** → A: A link, for every vocabulary. The point of SKOS is that a vocabulary is a linked thing, and presenting a record without rendering its link makes little sense. A vocabulary published elsewhere links to its publisher; a vocabulary held here links to this page, its identifier being computed from this site's address until publication fixes it. This reverses the decision taken one feature ago that an identifier is never a link, and the maintainer expects to revisit it once he has seen it working. Integrated into FR-004, and applied to the list page in FR-016.
- **Q: What are the two ways into the terms, and how do they relate?** → A: The page opens at the concepts nothing else in the vocabulary is broader than, and a visitor steps down from there into narrower ones. A search over the vocabulary's concepts replaces that view with a flat list of matches, the same way a search replaces the full list on the list page. Collections sit apart from the hierarchy, listed as their own thing, because a collection is a curator's grouping rather than a step in the broader/narrower tree. The maintainer asked for it kept relatively simple, to be expanded once it can be seen. Integrated into User Stories 2, 3 and 4.
- **Q: What does searching a vocabulary's concepts match on?** → A: Every name a term goes by — its preferred label, its alternative labels, and its hidden labels, the last of which exist in SKOS precisely to be matched on without ever being shown. Definitions are not matched: prose matching returns results whose connection to the search a visitor cannot see. Integrated into FR-009 and FR-010.

### Session 2026-08-20 (coverage scan)

Seven further ambiguities surfaced by the structured coverage scan over the drafted specification,
resolved here against the intake decisions, the shipped models, `CONTEXT.md` and the constitution.

- **Q: A concept's notation was agreed as a search target at intake. Can it be matched?** → A: No, because nothing stores it. `CONTEXT.md` defines a notation as a language-independent code for a concept, but no field on the concept holds one and no import path populates one — the search can only match what the data model records, which is the three kinds of label. Adding a notation to the data model is a change to what the package stores, not to how it is browsed, and belongs nowhere near a browsing feature. Recorded as a gap and raised at the spec gate. Integrated into FR-010 and Assumptions.
- **Q: How does a visitor step down through the hierarchy — is the whole tree on the page, or one level at a time?** → A: One level at a time. The page shows the concepts nothing is broader than; following one shows the concepts directly narrower than it, with the path back to the top shown so a visitor can step up again. Rendering the whole hierarchy at once would put every concept in a vocabulary on one page, which the goal this package pursues — tens of thousands of concepts staying responsive — makes untenable on the first real vocabulary, and R7 is where that is confronted rather than worked around here. Integrated into FR-006, FR-007 and FR-008.
- **Q: Following a concept to see what is under it — is that not a link to a concept, which this feature excludes?** → A: It is not. What is followed is this same vocabulary page, showing a different part of the same vocabulary; a concept's own page, showing what that concept holds, is #142's and does not exist. The distinction is what lets a visitor work down through the vocabulary without any link leading to a missing page. Integrated into FR-007 and Edge Cases.
- **Q: A concept has labels in several languages. Which one does a visitor see?** → A: The one in the language they are reading the site in, where the concept has one, falling back to the vocabulary's own default language, which is the language its concepts' identity is anchored in. Falling back rather than showing nothing matters because a vocabulary imported from a publisher carries whatever languages that publisher wrote in, which need not include the visitor's. Integrated into FR-011.
- **Q: What does an entry in the hierarchy or in a search result tell a reader?** → A: The concept's label, and whether anything sits under it. Nothing else — a definition per row turns a scannable list into prose, and a definition is what #142's page is for. Integrated into FR-012.
- **Q: Does a search look at the whole vocabulary or only the part being looked under?** → A: The whole vocabulary. A search confined to the current position in the hierarchy would silently miss exactly the term a visitor could not find by stepping down, which is why they searched. Integrated into FR-009.
- **Q: What does a reader see when a vocabulary holds nothing, or a search matches nothing?** → A: Three distinct messages, never one. A vocabulary holding no concepts says so. A search matching nothing says so, repeats what was searched for, and offers the way back. A vocabulary holding no collections simply shows no collections section rather than an empty one. Integrated into FR-013 and FR-015.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a vocabulary and know what it is (Priority: P1)

A person who has found a vocabulary on the list — or who was handed its address by a colleague, or
followed its identifier from somewhere else entirely — opens it and gets a page about that
vocabulary: what it is called, what it covers, whether it is held on this site or was published
elsewhere, and its identifier, rendered as the link a linked-data identifier is meant to be. From
the list page, the vocabulary's name now leads here, which is the link #140 could not yet make.

**Why this priority**: This is the feature. A vocabulary's address has led nowhere since the day
records got addresses, and both of the ways into its terms are parts of this page.

**Independent Test**: Open a vocabulary's address directly on a site holding both a locally authored
vocabulary and an imported one, and confirm each serves a page naming and describing that
vocabulary, showing where it came from, and offering its identifier as a link. Then confirm the list
page's entries lead to those same pages.

**Acceptance Scenarios**:

1. **Given** a vocabulary held on this site, **When** its address is requested, **Then** a page is
   served showing its name and its description.
2. **Given** a vocabulary imported from a publisher, **When** its page is read, **Then** it is shown
   as published elsewhere, and the identifier its publisher assigned it is shown.
3. **Given** a vocabulary authored on this site, **When** its page is read, **Then** it is shown as
   held here.
4. **Given** any vocabulary, **When** its page is read, **Then** its identifier is a link, and
   following it leads to the publisher's address for a vocabulary published elsewhere and back to
   this page for one held here.
5. **Given** a vocabulary with no description, **When** its page is read, **Then** the rest of the
   page is shown without a stray heading or empty space where the description would be.
6. **Given** the list of vocabularies, **When** an entry is followed, **Then** it leads to that
   vocabulary's page.
7. **Given** an address that names no vocabulary the site holds, **When** it is requested, **Then**
   the response says the page was not found rather than failing.
8. **Given** the page, **When** it is requested by someone not signed in, **Then** it is served.

---

### User Story 2 - Work down through the terms from the top (Priority: P1)

A person who does not know what is in a vocabulary starts where it starts: the terms nothing else in
it is broader than. Following one of them shows the terms directly under it, and the path they took
to get there is on the page, so they can step back up at any point. They can send a colleague a link
to the exact place they reached.

**Why this priority**: P1 alongside the page itself. Working down from the top is one of the two
ways into a vocabulary the issue asks for, and it is the one that serves a person who cannot yet
name what they are looking for.

**Independent Test**: On a vocabulary with a hierarchy several levels deep, confirm the page opens
at the terms with nothing above them, that following one shows exactly the terms directly under it
and no others, that the path from the top is shown, and that the address of a position reached this
way returns to the same position when opened fresh.

**Acceptance Scenarios**:

1. **Given** a vocabulary whose concepts form a hierarchy, **When** its page is opened, **Then** the
   concepts nothing is broader than are shown, and concepts below them are not.
2. **Given** a concept with narrower concepts under it, **When** it is followed, **Then** the
   concepts directly narrower than it are shown, and concepts further down are not.
3. **Given** a position below the top, **When** the page is read, **Then** the path from the top to
   that position is shown, and each step of it leads back to that step.
4. **Given** a position below the top, **When** its address is opened in a new session, **Then** the
   same position is shown.
5. **Given** a concept with nothing narrower than it, **When** it is shown in a list, **Then** it is
   distinguishable from one that has concepts under it, and offers nothing to follow.
6. **Given** a vocabulary whose concepts have no hierarchy at all, **When** its page is opened,
   **Then** every concept is shown, because nothing is broader than any of them.
7. **Given** a vocabulary holding no concepts, **When** its page is opened, **Then** it says so, and
   the rest of the page is still shown.
8. **Given** an address naming a concept that is not in this vocabulary, **When** it is requested,
   **Then** the response says the page was not found rather than showing another vocabulary's
   concepts.

---

### User Story 3 - Find a term inside the vocabulary (Priority: P2)

A person who knows roughly what the term is called, but not where it sits, types it and gets a flat
list of the terms in this vocabulary matching it — including terms found under a name they are not
shown, which is what a vocabulary's hidden labels are for. They can send the narrowed list as a
link, and get back to the top of the vocabulary from there.

**Why this priority**: The hierarchy alone is a complete way in for a small vocabulary, which is
every vocabulary in the demonstration today. Search is what makes a vocabulary of any real size
usable, and it is the way in for someone who knows the word but not the structure.

**Independent Test**: On a vocabulary holding terms with alternative and hidden labels, search for a
word appearing only in a preferred label, then only in an alternative one, then only in a hidden
one, and confirm the term is found each time and that the hidden label itself is never displayed.
Confirm the resulting address, opened fresh, returns the same matches.

**Acceptance Scenarios**:

1. **Given** a vocabulary's page, **When** a word from a concept's preferred label is searched for,
   **Then** that concept is among the results and non-matching concepts are not.
2. **Given** a concept carrying an alternative label, **When** a word appearing only in that label
   is searched for, **Then** the concept is found.
3. **Given** a concept carrying a hidden label, **When** a word appearing only in that label is
   searched for, **Then** the concept is found, and the hidden label is not shown anywhere on the
   page.
4. **Given** a concept whose definition contains the searched word and whose labels do not, **When**
   that word is searched for, **Then** the concept is not among the results.
5. **Given** a search in one letter case, **When** the matching text is in another, **Then** it
   still matches.
6. **Given** a search run from a position below the top of the hierarchy, **When** the results are
   shown, **Then** they cover the whole vocabulary and not only that position.
7. **Given** a search matching nothing, **When** the results are shown, **Then** the page says
   nothing matched, repeats what was searched for, and offers the way back to the top of the
   vocabulary.
8. **Given** a narrowed list, **When** its address is opened in a new session, **Then** the same
   search is applied and the same concepts are shown.
9. **Given** a search matching a concept in another vocabulary, **When** the results are shown,
   **Then** that concept is not among them.

---

### User Story 4 - See the groupings a curator made (Priority: P3)

A person reading a vocabulary sees the collections it holds — the groupings its curator made that
the broader/narrower hierarchy does not express — named alongside it, so they know the vocabulary is
organised in a way the tree does not show, and which of those groupings carry a deliberate order.

**Why this priority**: Lowest of the four. A collection cannot be opened until #142 serves its
address, so this slice tells a reader that groupings exist and what they are called, which is worth
having but is worth less than either way into the terms themselves.

**Independent Test**: On a vocabulary holding both an ordered and an unordered collection, confirm
both are named on the page, that the ordered one is identifiable as ordered, and that a vocabulary
holding no collections shows no collections section at all.

**Acceptance Scenarios**:

1. **Given** a vocabulary holding collections, **When** its page is read, **Then** each collection
   is named.
2. **Given** a collection whose members carry a deliberate order, **When** it is shown, **Then** it
   is distinguishable from one that does not.
3. **Given** a vocabulary holding no collections, **When** its page is read, **Then** no empty
   collections section is shown.
4. **Given** the collections shown, **When** the page is read, **Then** they are separate from the
   concept hierarchy rather than mixed into it.

---

### Edge Cases

- A vocabulary with no description, no concepts and no collections — the page is still served and
  still identifies the vocabulary.
- A description running to several paragraphs — the page stays readable rather than burying
  everything below it.
- A concept whose label is long enough to break the layout.
- A hierarchy deep enough that the path from the top is longer than the page is wide.
- A concept that is broader than one concept and narrower than another, reached by two different
  routes — each route shows the same concepts under it.
- A search string containing characters with a meaning in a query — `%`, `_`, a quote — is treated
  as text to look for, not as an instruction.
- A search string in a non-Latin script, and a search that differs from the text only by letter case
  in such a script — the same database-dependent behaviour the list page already discloses (ADR
  0014) applies here and is disclosed the same way.
- A concept carrying no label in the language the site is being read in — the vocabulary's own
  default language is used rather than showing an unnamed row.
- Nothing on the page links to an individual concept or collection — until #142 serves those
  addresses, such a link would lead to a missing page.
- A vocabulary published elsewhere whose identifier is not a resolvable address — it is still shown
  as a link, and following it fails in the browser rather than on this page.
- The page is requested by someone not signed in, on a site where nothing else is public.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST serve a page at the address of every vocabulary the site holds, and
  MUST respond that the page was not found for an address naming no vocabulary.
- **FR-002**: The page MUST show the vocabulary's name and its description, omitting the description
  cleanly when there is none.
- **FR-003**: The page MUST show whether the vocabulary is held on this site or was published
  elsewhere, and MUST show the publisher's own identifier where it was published elsewhere. It MUST
  NOT claim to name who the publisher is, which nothing in the data model records.
- **FR-004**: The vocabulary's identifier MUST be shown as a link, for every vocabulary — the
  publisher's address for one published elsewhere, and this site's own computed address for one held
  here.
- **FR-005**: The page MUST carry no access rule of its own: whatever the site holds is shown to
  whoever requests the page, leaving any restriction to the project mounting the package's routes.
- **FR-006**: The page MUST open showing the concepts in the vocabulary that no other concept in it
  is broader than.
- **FR-007**: A concept shown in the hierarchy that has concepts narrower than it MUST be followable
  to a view of this same page showing exactly the concepts directly narrower than it, and no others.
  It MUST NOT link to a page for the concept itself.
- **FR-008**: A view below the top MUST show the path from the top to the current position, each
  step of which returns to that step, and the position MUST be carried in the page's own address so
  that it can be linked to, bookmarked and returned to.
- **FR-009**: A visitor MUST be able to search the concepts of this vocabulary, the search covering
  every concept in it regardless of the position the search was run from, and covering no concept in
  any other vocabulary. The search MUST be carried in the page's own address.
- **FR-010**: The search MUST match a concept's preferred label in any language, its alternative
  labels and its hidden labels, matching regardless of letter case and treating the search string as
  text rather than as query syntax. It MUST NOT match a concept's definition or any other
  documentary note. A hidden label MUST never be displayed, matched or not.
- **FR-011**: A concept MUST be named in the language the site is being read in where it carries a
  preferred label in that language, and otherwise in the vocabulary's own default language.
- **FR-012**: A concept shown in the hierarchy or in search results MUST show its label and whether
  anything is narrower than it, and MUST NOT show its definition.
- **FR-013**: A vocabulary holding no concepts MUST say so, in wording distinct from a search that
  matched nothing; a search matching nothing MUST say so, repeat what was searched for, and offer
  the way back to the top of the vocabulary.
- **FR-014**: Nothing on the page may link to an individual concept, collection or ordered
  collection, because nothing serves those addresses yet.
- **FR-015**: The page MUST name every collection the vocabulary holds, distinguishing one whose
  members carry a deliberate order, presenting them separately from the concept hierarchy, and
  showing nothing at all where the vocabulary holds no collections.
- **FR-016**: The list of vocabularies MUST link each entry to that vocabulary's page, and MUST show
  the identifier it already displays as a link, replacing the plain text it displays today.
- **FR-017**: Both the hierarchy and the search results MUST be divided into pages of a fixed size
  where they are longer than one, navigable from one page to the next with the current position or
  search preserved.
- **FR-018**: The page MUST be reachable by a name the package owns rather than a fixed path, so a
  project chooses the address it is mounted at.
- **FR-019**: The demonstration project MUST hold a vocabulary whose concepts form a hierarchy at
  least two levels deep and which holds both an ordered and an unordered collection, so that every
  part of this page can be looked at rather than described.
- **FR-020**: The unattended check that already installs, seeds and serves the demonstration MUST
  additionally open a vocabulary's page, step down into the hierarchy, and run a search inside it,
  failing if any of those does not work.

### Requirement → story

| Story | Requirements |
|---|---|
| US-1 — Open a vocabulary and know what it is | FR-001, FR-002, FR-003, FR-004, FR-005, FR-016, FR-018 |
| US-2 — Work down through the terms from the top | FR-006, FR-007, FR-008, FR-011, FR-012, FR-013, FR-014, FR-017, FR-019 |
| US-3 — Find a term inside the vocabulary | FR-009, FR-010, FR-011, FR-012, FR-013, FR-017, FR-020 |
| US-4 — See the groupings a curator made | FR-014, FR-015, FR-019 |

FR-019 lands across the two stories whose subject it makes visible — a hierarchy for US-2, an
ordered and an unordered collection for US-4. FR-020 lands with US-3, the last of the three
browsing stories, so that one extension of the unattended walk covers all of them at once.

### Key Entities

- **ConceptScheme (vocabulary)**: the record the page is about. Contributes its name, its
  description, its identifier, and whether that identifier was fixed by a publisher elsewhere.
- **Concept**: what the page presents. Reached through the hierarchy or through search; named by its
  labels; never linked to a page of its own in this feature.
- **ConceptRelation**: the broader/narrower links that give the vocabulary its top and its levels.
  Only the broader direction is stored; the narrower direction is read back from it.
- **ConceptLabel**: the alternative and hidden labels a search matches on, and the per-language
  preferred labels that decide what a visitor sees a concept called.
- **Collection**: named on the page, marked as ordered or not, and not opened.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person handed only a vocabulary's identifier can open it and say what the vocabulary
  covers and whether this site authored it.
- **SC-002**: A person who cannot name the term they want can reach any concept in a vocabulary by
  stepping down from the top, one level at a time, without ever leaving the vocabulary's page.
- **SC-003**: A person who knows a term by a name that is not its preferred one finds it in a single
  search of the vocabulary.
- **SC-004**: The address of any position in the hierarchy, and of any search, opened fresh,
  produces the same concepts.
- **SC-005**: The number of database queries the page runs does not grow with the number of concepts
  it shows, nor with the depth of the position being shown.
- **SC-006**: Every string the page shows a reader can be translated, and none is fixed in one
  language.
- **SC-007**: A person with a fresh clone can look at a populated vocabulary page, step down through
  a real hierarchy and search inside it, within the same documented commands that already serve the
  list, and the same walk runs unattended on every proposed change.

## Assumptions

- A vocabulary holds hundreds of concepts rather than tens of thousands. Keeping the page fast at a
  scale beyond that is R7, not this feature — which is why the hierarchy is shown one level at a
  time rather than whole.
- A named publisher is a genuine future need and not a gap this feature leaves by accident. It will
  be derived from a record or required on the data model when the maintainer decides which; until
  then provenance is the only claim the page makes about where a vocabulary came from.
- A concept's notation cannot be searched because nothing stores one. The ubiquitous language
  defines it, no field holds it, and adding one is a change to what the package records rather than
  to how it is browsed.
- Whether a vocabulary was published elsewhere is read from its identifier having been fixed by a
  publisher, which is the only signal the data carries. A vocabulary published from this site (R4)
  will also carry a fixed identifier, and distinguishing those two cases is R4's to settle.
- Rendering a vocabulary's identifier as a link is provisional, adopted because a linked-data record
  presented without its link makes little sense, and expected to be revisited once it has been seen
  working.
- A visitor's browser may not run JavaScript. Nothing on this page depends on it, which is why the
  position in the hierarchy is carried in the address rather than expanded in place.
- Access control across the browsing interface remains a later decision, and this feature does not
  prejudge it.
