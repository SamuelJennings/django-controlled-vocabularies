# Decisions — 015 Read a single record

Rationale too long to sit inline in `spec.md`, and the reasoning behind ambiguities resolved without
the maintainer. Every decision here is reflected in a requirement; this file explains why, and what
was rejected.

## D1 — A collection keeps its own address segment

**Decided:** the addresses served are exactly the ones the records already compose — a concept at the
vocabulary's address followed by its slug, a collection at the vocabulary's address followed by a
distinguishing segment and its slug.

The issue asked for one path serving every kind, on the reading that a published record's identifier
must equal the address it is read at so an external consumer's stored identifier leads back here.
That requirement is satisfied by either shape, and it is the requirement that matters.

The segment is not decoration. A concept's slug is unique among concepts and a collection's among
collections, so the same slug can legitimately exist as both inside one vocabulary. The segment is
what keeps the two address spaces disjoint. Flattening them would mean one slug space shared across
two tables, which no single database constraint can express, so uniqueness would become an
application-level check — the kind that loses a race or is bypassed by a bulk write. Minting two
records with one identity is the failure a linked-data system cannot recover from.

Three pieces of evidence were put to the maintainer and settled it:

- SKOS constrains nothing about URI shape. The Reference declines to require any particular
  dereferencing behaviour for concept, scheme or collection URIs and defers to the Cool URIs and
  Best Practice Recipes notes. The only hard rule is that one URI identifies one resource.
- AGROVOC distinguishes its concepts (`…/agrovoc/c_1234`) from its collections
  (`…/agrovoc/skosCollection_cb7b7c4a`) by a discriminator in the local name.
- GEMET distinguishes its concepts (`…/gemet/concept/95`) from its groups (`…/gemet/group/96`) by a
  path segment, which is the pattern the issue supposed nobody used.

**Rejected:** a shared slug namespace across concepts and collections. It is a change to what the
package stores and to how imports assign slugs, and it belongs with identity rather than with a
read-only browsing feature.

## D2 — A short form's prefix comes from the vocabulary's slug

**Decided:** the prefix of a record's CURIE is the slug of the vocabulary holding it.

Nothing records a short prefix for a vocabulary. A vocabulary has a name, a slug, a description, a
default language and an identifier. Slugs are unique across every vocabulary on the site, so a prefix
derived from one is never ambiguous, needs no new field, and needs no curator to maintain it.

**The cost, accepted by the maintainer:** a vocabulary published elsewhere usually has a prefix its
own community already writes, and this site will show its own instead. Nothing is misidentified — the
full canonical identifier is disclosed behind every short form and the link leads to the record — but
the short form is not the one that community recognises. Recording a real prefix per vocabulary
changes what the package stores and belongs with identity.

## D3 — Hidden labels stay hidden, against "everything"

**Decided:** every predicate except `skos:hiddenLabel`.

The maintainer asked for a raw view of everything recorded. Hidden labels exist in SKOS specifically
to be matched on and never displayed, which is the reading he took himself when specifying the
vocabulary page's search one feature ago. A hidden label is where a vocabulary keeps misspellings,
superseded wording, and terms deliberately retired — sometimes for being offensive. A complete raw
view would put every one of them in front of any reader who opens the page. Raised explicitly at
intake and confirmed.

## D4 — Collection membership sits outside the definition list

**Decided:** the collections gathering a concept appear below the term-and-value pairs, under a
plain-language heading, not as a row.

Every row in the list is a statement the record makes about itself and has a real SKOS property
behind it — including `skos:narrower`, which is the inverse of the broader links stored and is a
genuine SKOS property. Membership is a statement other records make about this one: SKOS has
`skos:member` pointing from a collection to its concepts and no inverse of it. Keying the row on an
invented CURIE would misrepresent the data, and keying it on `skos:member` would reverse its meaning.

**Rejected:** omitting membership entirely. The maintainer asked for where a record sits among the
records around it, and the collections gathering it are part of that.

## D5 — The term-and-value component is this package's own

**Decided:** build the reusable component here, and propose it upstream once its shape has proved
itself.

The user-interface package this project builds on ships a label-and-value component, but it renders a
heading and a paragraph rather than a definition list, so there is nothing upstream to consume. No
recorded rule forbids this package having components of its own, and the constitution already
reserves a test path for them.

**Rejected:** adding the component upstream first. It couples this feature to another package's
change and version bump for a component whose shape has not yet been proved in use. Promotion later
is cheap and better informed.

## D6 — One language, not every language a value was recorded in

**Decided:** the reading language, falling back to the vocabulary's default, exactly as the
vocabulary page already does.

The issue asked for a record in the languages its names and descriptions were recorded in, which
would have made a record page behave differently from every page leading to it. Put to the maintainer
with the alternative — a record's page being where the whole record is, so showing every language
there is defensible — and he chose consistency. A language switcher, or an "in other languages"
section, remains available later without contradicting anything specified here.

## D7 — A machine-readable representation is not served here

**Decided:** out of scope, and raised at the spec gate.

The address being served is the record's own identifier, and a published vocabulary is conventionally
expected to return RDF when that address is asked for it. That is a real gap and the obvious thing
R6 leaves behind, but it is a different feature: its own formats, its own round-trip fidelity rules
under the constitution's article on them, and its natural home is export rather than browsing.

## D8 — One step in each direction, and no path to the top

**Decided:** a concept shows its broader concept, its narrower concepts, its related concepts, the
collections gathering it and the vocabulary holding it. No ancestor chain.

Walking up one step at a time reaches the top of any hierarchy, and computing an ancestor chain on
every page view is a cost that grows with depth — which is the subject of R7, not of the first
read-only page. The tree navigation the maintainer removed from the vocabulary page is not
reintroduced by showing one step in each direction.

## Gaps recorded, not solved

- **Cross-vocabulary mappings are not stored.** The import path reads a concept's exact, close,
  broad, narrow and related matches, reports them, and sets them aside, because the store they were
  meant to land in was deferred past the import feature. The page cannot show them however it is
  specified. Raised at the spec gate.
- **A concept has no status.** The draft, published and deprecated lifecycle is in the project's
  language but no field holds it, and it belongs to the publication and curation features.
- **A vocabulary has no short prefix.** See D2.

## D-015-01 — Two edge cases in the approved spec describe states the models refuse

**Decided (2026-08-24, design review):** the two cross-vocabulary edge cases in `spec.md` are struck
through and forward-tagged in place rather than deleted, and **no test is owed for either**.

`ConceptRelation._reject_cross_scheme` refuses a relation whose endpoints sit in different
vocabularies, enforced through `clean()` and re-applied in `save()`, and
`CollectionMember._reject_cross_scheme` does the same for membership — deliberately backstopped in
`save()` so a factory cannot bypass it. The fixtures the two edge cases need therefore cannot be
built. The spec's own Key Entities section already agrees: a relation links two concepts of one
vocabulary.

This is a fault in the approved specification rather than in the plan, which writes no task for
either. It changes nothing the feature delivers, so it is corrected in place rather than re-gated.
The short-form prefix still comes from the record's vocabulary, which is what those edge cases were
reaching for — it is simply always this record's own vocabulary.

## D-015-02 — The relation helpers are not prefetchable, so each read carries its own select_related

**Decided (2026-08-24, design review):** the plan's single `prefetch_related` covering the relation
paths is dropped. `broader()`, `narrower()`, `related()` and `collections()` build fresh querysets
rather than iterating a cached related set, so a prefetch of those paths is never read. Each
record-valued read chains `.select_related("scheme")` on the queryset the helper returns; the label
and note helpers keep the prefetch, because they do read `.all()`.

`collections()` and `Collection.members()` return lists. For those the prefix comes from the record's
own already-loaded scheme, which is sound precisely because D-015-01's constraints make every
relation and every membership intra-vocabulary.

## D-015-03 — The vocabulary row names the vocabulary, it does not abbreviate it

**Decided (2026-08-24, foundational phase):** the `skos:inScheme` row shows the vocabulary's
display name as its link text, with the vocabulary's own canonical identifier beside it and the
link leading to the vocabulary's page. It is not written as a short form.

FR-006 does not reach this row. A short form is a prefix naming the vocabulary that holds a record
and a local part naming the record within it, and a vocabulary is held by nothing and has no local
part of its own — the only short form available for it would be a bare prefix with an empty
reference, which is legal syntax and reads as a truncation. FR-011 requires the row and fixes its
property, not the form of its value, and FR-007's disclosure obligation is met either way: the
canonical identifier is on the page as text and the link leads somewhere a reader can read.

## D-015-04 — T019 supersedes a pre-existing "carries no link" assertion

**Decided (2026-08-24, US-4):** `test_a_concepts_row_carries_only_its_label` (test_views.py) was
written under 014-look-inside-a-vocabulary, when a concept had no page to lead to — its "no anchor
at all" assertion (`soup.find("a") is None`) was a correct claim about that state, not a claim this
feature happens to break. This feature's whole point, named by spec.md User Story 4 and plan.md §8
("The links the previous slices deferred"), is to make that assertion false: the row becomes the
link it was "always meant to be" once the concept's own page exists. `tasks.md` T019 lists
`tests/test_ui/test_views.py` among the files it touches, which is this feature naming the same file
as in-scope for the change.

The test was updated in place (renamed to
`test_a_concepts_row_carries_only_its_label_and_a_link_to_its_own_page`) rather than left red or
deleted: it keeps every other "carries only its label" assertion — no definition, no note, no
identifier, no relation-text, none of which US-4 touches — and its final assertion now checks the
row's one anchor resolves to the concept's own page. This mirrors the precedent already in this
codebase: `conceptscheme_list_item.html`'s own T004 superseded issue #140's "no entry may link to a
vocabulary" the same way, and `TestRowPartialLinksToTheVocabulary`'s docstring says so explicitly
rather than quietly deleting the old test.

**Rejected:** leaving the test in place and calling the task blocked. `craft-tdd`'s prohibition
against touching a test authored outside this story exists to protect a failing pre-existing test as
evidence about intent someone else asserted. Here the design documents this story was dispatched
from are that intent, dated after the test it supersedes, and explicit about superseding it by name
(User Story 4's own description: "The entries that have been plain text since the vocabulary page
shipped become the links they were always meant to be"). Blocking would report a story as unable to
proceed past the one requirement `tasks.md` names it should satisfy.

T020 supersedes a second such assertion, `test_nothing_links_to_a_collection`; that decision is
recorded separately at D-015-05 in T020's own commit, for the same reason and under the same
`tasks.md` file-scope naming.
