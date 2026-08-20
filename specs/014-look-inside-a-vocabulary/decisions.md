# Decisions — 014-look-inside-a-vocabulary

Decisions taken without asking the maintainer, and the rationale too long to sit inline in
`spec.md`. Each records what was ambiguous, what was chosen, and why the choice is defensible
against the intake decisions, the shipped models, `CONTEXT.md`, `GOALS.md` and the constitution.

The maintainer's own intake decisions are in `spec.md` under `## Clarifications`, not here.

---

## D1 — A notation cannot be searched, because nothing stores one

**Ambiguity**: the maintainer agreed at intake that the search should match "any label a term goes
by, including the ones kept hidden for the purpose, and on its notation".

**Chosen**: the search matches the three kinds of label and nothing else. The notation is recorded
in `spec.md` as a gap, in FR-010 and in Assumptions, and raised at the spec gate.

**Why defensible**: `CONTEXT.md` defines a notation as "a `skos:notation` — a typed, language-
*independent* code for a concept", but no field on `Concept` holds one, no `ConceptNote` kind covers
one, and no import path populates one. The search can only match what the data model records.
Adding a notation field is a change to what the package *stores* — a migration, an import mapping,
an export mapping, and a round-trip fidelity obligation under constitution Article XI — and none of
that belongs inside a feature about browsing. Silently dropping it from the agreed scope would have
been the alternative, and a gap the maintainer agreed to is exactly the kind that must be stated
rather than absorbed.

---

## D2 — The hierarchy is shown one level at a time, not as a whole tree

**Ambiguity**: "work down through it from the top" does not say whether the whole hierarchy is
rendered at once, expandable in place, or navigated one level at a time.

**Chosen**: one level at a time. The page opens at the concepts nothing is broader than; following
one shows the concepts directly narrower than it, with the path from the top on the page.

**Why defensible**: rendering the whole hierarchy puts every concept in the vocabulary on one page.
G5 names tens of thousands of concepts as the scale this package must stay responsive at, and the
demonstration's DCMI vocabulary is small only because it is a demonstration — the first real
vocabulary the package meets (R9, the heat-flow vocabularies) is not. A whole-tree render would have
to be undone by R7 rather than extended by it. It also loses the property that makes a position
linkable: a tree expanded in place has no address, so a colleague cannot be sent the place you
reached. The maintainer asked for this kept relatively simple; one level at a time is the simpler of
the two to specify, to test and to reason about, and it is the one that does not need replacing.

---

## D3 — Following a concept is not a link to a concept

**Ambiguity**: FR-014 forbids linking to an individual concept, and D2 requires following a concept
to see what is under it. These read as contradictory.

**Chosen**: what is followed is this same vocabulary page showing a different part of the same
vocabulary. A concept's own page — what the concept holds, its definition, its notes, its relations
— is #142's and does not exist.

**Why defensible**: the rule the maintainer set is that a link lands in the change that gives it
somewhere to lead, and #140 established it by shipping its entries unlinked. Following a concept
here leads somewhere that exists: this page, scoped. Nothing on the page leads to an address nothing
serves, which is the property the rule protects. The distinction is stated in `spec.md` FR-007 and
in the Edge Cases so that it cannot be read as an oversight.

---

## D4 — A concept is named in the reading language, falling back to the vocabulary's own

**Ambiguity**: a concept carries `Concept.label` — its preferred label in the vocabulary's effective
default language — plus a `ConceptLabel` row per other language. Nothing said which a visitor sees.

**Chosen**: the preferred label in the language the site is being read in, where the concept carries
one; otherwise the vocabulary's own default language, which is `Concept.label`.

**Why defensible**: constitution Article XII requires the interface to work in the reader's
language, and a vocabulary imported from a publisher carries whatever languages that publisher
wrote in, which need not include the reader's. Showing nothing rather than falling back would leave
unnamed rows on the page for exactly the imported vocabularies G8 exists to support. Falling back to
the vocabulary's default rather than to any available language keeps the fallback predictable: the
default language is the one the vocabulary's identity is anchored in, so it is the one a curator
guaranteed exists.

---

## D5 — A row shows a label and whether anything is under it, and nothing else

**Ambiguity**: how much of a concept a row in the hierarchy or in search results carries.

**Chosen**: the label, and whether the concept has concepts narrower than it. No definition, no
notes, no identifier.

**Why defensible**: a definition per row turns a list a visitor scans into prose they must read, and
a definition is what #142's page is for — putting it here would build the part of #142 that is
cheapest to build and leave the part that matters. Whether anything is under a concept is not
decoration: without it a visitor cannot tell a leaf from a branch they have not opened, and D2's
one-level-at-a-time navigation depends on that distinction being visible.

---

## D6 — A search covers the whole vocabulary, never the current position

**Ambiguity**: whether a search run from a position below the top is scoped to that subtree.

**Chosen**: the whole vocabulary, always.

**Why defensible**: a visitor searches because stepping down did not find the term. A search scoped
to where they had already looked would fail in exactly that case, and would fail silently — the
result is a well-formed empty list, indistinguishable from a term the vocabulary does not hold. The
same reasoning settled the list page's equivalent question in #140 (a search applies to every
vocabulary, not to the page being viewed).

---

## D7 — Three empty states, not one

**Ambiguity**: what is shown when a vocabulary holds no concepts, when a search matches nothing, and
when a vocabulary holds no collections.

**Chosen**: a vocabulary with no concepts says so; a search matching nothing says so, repeats the
term and offers the way back; a vocabulary with no collections shows no collections section at all.

**Why defensible**: #140 established that collapsing an empty database into an empty search result
tells someone whose search missed that the site is empty. The same fault applies one level down.
Collections differ from both because their absence is unremarkable — most vocabularies have none —
and an empty section headed "Collections" is noise on every page rather than information on one.

---

## D8 — The list page's identifier becomes a link in this change

**Ambiguity**: the maintainer's instruction that a linked-data record should render its link was
given about a vocabulary's own page. Whether it also revises the list page's plain-text identifier —
a decision taken deliberately one feature ago (#140 D6, "the identifier is never a link — it is not
always a resolvable address") — was asked twice and answered about the published/unpublished axis
instead.

**Chosen**: yes. FR-016 makes the list page's identifier a link, alongside the entry link this
feature was always going to add there.

**Why defensible**: leaving the two pages disagreeing about whether an identifier is a link would
ship an inconsistency the next reader has to discover and explain. The maintainer's stated reason —
"it doesn't make much sense to me to present a vocabulary or a record without rendering the link" —
is about what a record is, not about which page it appears on, and it is stated broadly enough
("a vocabulary or a record") to cover both. The decision is provisional on both pages by the
maintainer's own framing ("make it a link and we will see how it goes"), so revisiting it later
revisits it in one place rather than two. What is *not* changed is which vocabularies show an
identifier at all on the list page: that stays as #140 settled it, the publisher's identifier for an
imported vocabulary and none for one held here.

---

## D9 — The demonstration gains a hierarchy and collections

**Ambiguity**: the demonstration project delivered by #140 seeds two vocabularies, neither of which
has a single broader/narrower relation or a single collection. Nothing said this feature must change
that.

**Chosen**: FR-019 and FR-020 require the demonstration to hold a vocabulary with a hierarchy at
least two levels deep and both an ordered and an unordered collection, and require the unattended
check to open a vocabulary page, step down and search inside it.

**Why defensible**: #140's third user story exists because the maintainer pointed out that nothing
in the first two let him confirm the page renders, and that a test asserting markup and a person
looking at a page are different evidence. Every part of this feature — the hierarchy, the path back
to the top, the leaf-versus-branch distinction, the collections section — is invisible on the
demonstration as it stands, so shipping it unchanged would reintroduce exactly the gap that story
closed. The unattended check is extended for the same reason it exists: a demonstration nobody walks
rots without saying so.

---

## D10 — Paging applies to the hierarchy as well as to search results

**Ambiguity**: #140 paginates the vocabulary list. Nothing said whether a level of the hierarchy is
paginated.

**Chosen**: both are, at a fixed size, preserving the current position or search across pages
(FR-017).

**Why defensible**: a single level can be large — a vocabulary with a flat structure has *every*
concept at the top, which FR-006 and User Story 2 scenario 6 both admit as a normal case. Paginating
search results but not the level they were reached from would put the unbounded case on the page
that is hardest to leave.
