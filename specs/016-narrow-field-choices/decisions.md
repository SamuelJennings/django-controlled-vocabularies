# Decisions — FS-016 Narrow a field's choices to part of a vocabulary

Rationale too long to carry inline in `spec.md`, plus every ambiguity resolved without asking the
maintainer. The spec stands alone; this file explains why it reads the way it does.

## D1 — The three restrictions exclude one another rather than composing

**Ambiguous:** whether `collection`, `concepts` and `branch` may be combined, and what a
combination would mean.

**Chosen:** at most one. Two or more is refused when the declaration is read (FR-006).

**Why defensible:** a combination has two readings and no way to tell them apart from the source.
`collection="core", branch="thermal"` could mean *members of `core` that are also under `thermal`*
or *members of `core` plus everything under `thermal`*, and a reader of the declaration cannot know
which the writer meant. Article II settles it: the simplest design that satisfies the spec is one
restriction at a time, and no requirement asks for more. Nothing is foreclosed — if a real need for
an intersection appears, it can be added later with an explicit spelling, whereas a guessed default
shipped now would have to be broken to correct it.

## D2 — The failure lands at declaration time, not at validation time

**Ambiguous:** where an invalid declaration is caught.

**Chosen:** when the declaration is read — the same place the fields already refuse `on_delete`,
`through` and `limit_choices_to` (FR-005, FR-006).

**Why defensible:** the mistake is in code, so the report belongs to whoever imports that code, not
to whoever first submits a form built from it. It also matches the existing behaviour of these two
fields exactly, so a consumer learns one rule about when a bad declaration is reported rather than
two. The cost — that a declaration cannot be checked against data this way — is not a cost here,
because none of these rules is about data.

## D3 — Absent targets are reported by the existing check, not by a new mechanism

**Ambiguous:** how a mistyped or not-yet-imported target reaches a developer.

**Chosen:** extend the system check FS-009 established, as a warning with a stable identifier,
naming the specific absent target (FR-009).

**Why defensible:** FS-009's intake decision already settled the general shape of this question for
a missing vocabulary, with a reason that transfers unchanged — the targets arrive by import or
curation, which only a running project can perform, so an error that blocks `migrate` would make a
fresh install unbootstrappable. A second, differently-shaped reporting mechanism for the same class
of gap would be an inconsistency a consumer has to learn. Reporting the specific absent member of a
concept list rather than the list as a whole is the one addition: a list of ten with one typo is
otherwise a warning that says nothing useful.

## D4 — An empty concept list is refused

**Ambiguous:** whether `concepts=[]` means "no restriction" or is a mistake.

**Chosen:** refused (FR-003).

**Why defensible:** it is the same argument `_normalise_vocabulary` already makes about an empty
slug — a declaration that offers no choices at all while reading as restricted is the opposite of
what anyone writing it is reaching for. A consumer who wants no restriction omits the argument, and
that path already exists and is already tested.

## D5 — The branch read must terminate on a cyclic hierarchy

**Ambiguous:** whether the stored relation graph can contain a cycle, and what happens if it does.

**Chosen:** the traversal terminates and yields each concept once regardless (FR-004, SC-006).

**Why defensible:** `ConceptRelation` refuses a self-relation, a cross-vocabulary relation, and a
mirror-order duplicate of a *related* edge — the last through `_canonicalise`, which orders that
kind's endpoints by primary key. A reversed *broader* edge is a different, permitted edge, stated as
such at `models.py:1209-1211`, and nothing walks the graph. So the shortest storable cycle is two
edges, built with two ordinary `add_broader()` calls, which strengthens this decision rather than
weakening it: the state the traversal must survive is reachable through the public API and needs no
contrived construction. Whether that gap should be closed is a separate question
about the relation model, not about this field. What is not separable is that a restriction reading
that data must not hang or exhaust memory: the field cannot assume an invariant the database does
not enforce. Specifying termination costs nothing and removes a failure mode that would present as
a hung request with no error.

## D6 — Ordered-collection ordering is its own story, not folded into the collection restriction

**Ambiguous:** how to spec a behaviour the maintainer approved conditionally ("honour it if it's
not too complicated").

**Chosen:** User Story 6 at P2, separable from User Story 1.

**Why defensible:** a conditional approval has to be droppable without damage, and a scenario buried
inside a P1 story is not. As its own story it can be cut at planning if it turns out to require
reworking the selection control, and the three restrictions remain correct and complete without it.
If it is cheap — and the collection already resolves its members in order — it ships.

## D7 — Targets are named by slug, including for the explicit concept list

Settled with the maintainer at intake (`spec.md` §Clarifications), recorded here for the one
consequence the spec does not spell out: because a slug is unique only within its vocabulary, every
target resolves inside the single named vocabulary. That is what makes "exactly one vocabulary"
(FR-005) a precondition rather than a preference — with two vocabularies named, a collection slug
could resolve to two different collections, and there would be no way to say which was meant.

## D8 — The ordered sequence is applied at the endpoint, and only while the search box is empty

**Ambiguous:** the plan placed the ordering on the widget's own queryset, on the reading that this
is the list a person picks from. It is not. The selection control renders an empty `<select>` and
fetches every browsable option over this package's autocomplete URL; the widget queryset feeds
validation and the render of a value the record already holds. Ordering it would have shipped a
story whose tests pass and whose sequence no human ever sees.

**Chosen:** override `apply_ordering()` on `ConceptAutocompleteView` (FR-010, plan A5). It applies
the collection's member order when the restriction is an ordered collection *and* the request
carries no search term, and falls through to the inherited relevance order otherwise.

**Why defensible:** the maintainer's approval was conditional — honour the sequence if it is not too
complicated — so the cost is the whole question. The library exposes `apply_ordering()` as a single
method reading one attribute, and the declaration is already resolved on that request, so the change
is one override and one annotation. That is cheap enough to keep the story rather than drop it.

The empty-query condition settles a tension the first reading did not see. Browsing a small ordered
collection wants the curator's sequence; a typed query wants match quality. Conditioning on the
search term serves both rather than trading one for the other, which is what made the earlier
"leave the endpoint alone" argument look correct.

The position is read through a `Subquery` annotation keyed on the declaration's own collection, not
a membership join. A concept may belong to more than one collection, and this queryset reaches
`complex_filter()` without Django's `Exists()` wrapper, so a join would duplicate rows silently.

## D9 — A branch restriction's closure is recomputed per request, on an endpoint open to anyone

**Ambiguous:** nothing, in the sense that no requirement changes. Recorded because the plan stated
the branch cost as a per-declaration property — "one query per level of hierarchy depth" — which
reads as a one-off and is not.

**Chosen:** ship as specified, and record the cost accurately. The restriction resolves as a
callable, deliberately (FR-007), so it is re-resolved at every validation, every widget render and
every autocomplete request. The autocomplete endpoint allows anonymous access, so an unauthenticated
client re-runs the full downward closure — depth-many queries plus the materialised id set — on
every keystroke, before the 20-row page is cut.

**Why defensible:** the spec's Assumptions already defer branch-read performance to R7, and this
review is not reopening that. What R7 inherits is now stated in full: the single-query rewrite *and*
the repetition, which is the part that decides whether a cache or a bounded depth is the right
answer. The README says what a branch restriction costs, so a consumer choosing it for a public form
is choosing it knowingly.
