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

## D2 — ~~The hierarchy is shown one level at a time, not as a whole tree~~ *(withdrawn)*

> **Withdrawn 2026-08-20, before the specification was signed off.** The maintainer read this back
> and removed hierarchy navigation from the feature entirely: the page holds one flat, searchable
> list of every concept, and how concepts relate is shown on a concept's own page, which is #142's.
> The reasoning is kept because it was acted on — the specification, the stories and the issue graph
> all carried it for a time — and because it is the argument to answer if a tree is ever proposed
> for this page again. Superseded by `spec.md` FR-006 and User Story 2.

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

## D3 — ~~Following a concept is not a link to a concept~~ *(withdrawn)*

> **Withdrawn 2026-08-20, with D2.** Nothing on the page is followable at all now, so the
> distinction this decision drew has nothing left to apply to. `spec.md` FR-011 states the plain
> rule that replaced it: nothing on the page links to an individual record.

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

## D5 — A row shows a label and nothing else

**Ambiguity**: how much of a concept a row in the list or in search results carries.

**Chosen**: the label. No definition, no notes, no identifier, and — since the hierarchy came out
with D2 — no indication of what a concept is broader or narrower than.

**Why defensible**: a definition per row turns a list a visitor scans into prose they must read, and
a definition is what #142's page is for — putting it here would build the part of #142 that is
cheapest to build and leave the part that matters. An earlier revision also showed whether a concept
had anything under it, which the one-level-at-a-time navigation needed; with a flat list it is a
claim about a relation the page otherwise says nothing about, and the maintainer's instruction is
that relations belong on a concept's own page.

---

## D6 — A search covers the whole vocabulary, never the page being viewed

**Ambiguity**: whether a search run from the second page of a long list is scoped to that page.

**Chosen**: the whole vocabulary, always.

**Why defensible**: a search confined to the page being viewed is silently wrong exactly when the
list is long enough to need one, and its failure is a well-formed empty result indistinguishable
from a term the vocabulary does not hold. #140 settled the identical question for the list of
vocabularies the same way.

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

**Chosen**: yes. FR-013 makes the list page's identifier a link, alongside the entry link this
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

## D9 — The demonstration gains collections and richer labels

**Ambiguity**: the demonstration project delivered by #140 seeds two vocabularies, neither of which
holds a single collection, and whose concepts carry only a preferred label each. Nothing said this
feature must change that.

**Chosen**: FR-018 and FR-019 require the demonstration to hold a vocabulary carrying both an
ordered and an unordered collection and concepts carrying alternative and hidden labels, and require
the unattended check to open a vocabulary page and search inside it.

**Why defensible**: #140's third user story exists because the maintainer pointed out that nothing
in the first two let him confirm the page renders, and that a test asserting markup and a person
looking at a page are different evidence. Two parts of this feature are invisible on the
demonstration as it stands — the collections section, and a search matching a name the reader is
never shown — so shipping it unchanged would reintroduce exactly the gap that story closed. The
hidden label is the sharper of the two: it is the one behaviour here that cannot be confirmed by
reading the page, only by searching for something that is not on it. The unattended check is
extended for the same reason it exists: a demonstration nobody walks rots without saying so.

---

## D10 — The list of concepts is paged

**Ambiguity**: #140 paginates the list of vocabularies. Nothing said whether the list of a
vocabulary's concepts is paged, or only its search results.

**Chosen**: the list is paged at a fixed size, search in force or not, with any search preserved
across pages (FR-016).

**Why defensible**: the unpaged case is the unbounded one. A vocabulary holds far more concepts than
a site holds vocabularies — the goal this package pursues names tens of thousands — so a page that
paginates only search results puts every concept in the vocabulary on the page a reader arrives at
first.

---

## D11 — The queryset's label annotation is named `resolved_label`

**Ambiguity**: the annotation carrying a concept's name in the reading language was called
`display_label` in the first draft of the plan.

**Chosen**: `resolved_label`.

**Why defensible**: `Concept.display_label()` is an existing public method on the same model, called
from the forms, the fields and the package's own concept-search endpoint. Django sets an annotation
as a plain instance attribute, so a concept fetched through this view's queryset would carry a
string where every other code path finds a bound method, and calling it would raise. The page
template would still render, so nothing here would fail — the next feature to hold one of these
instances is where it would surface.

---

## D12 — The new view's tests join `tests/test_ui/test_views.py`

**Ambiguity**: the first draft of the plan gave the new view its own test module.

**Chosen**: its tests are new classes inside the existing `tests/test_ui/test_views.py`.

**Why defensible**: both views live in one `controlled_vocabularies/ui/views.py`, and the recorded
standard puts one test module per source module, splitting per unit with classes rather than extra
files. A second module for the same source file is the case that standard names as non-conforming.

---

## D13 — `tests/test_checks.py`'s clean-check baseline is left red by T005's new check

**Ambiguity**: none at spec or plan level — this surfaced only when the full verify ran at the end
of the story, per the brief's own ritual, and no task names it.

**Found**: `tests.settings` imports `CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/
vocabularies"` from `tests.settings_core`, unchanged, while also installing
`controlled_vocabularies.ui` and mounting its routes at `/browse/` (`tests/urls.py`) — a
vocabulary/vocabulary mismatch of exactly the kind `controlled_vocabularies.ui.W001` (T005) exists
to report, on the project's own test settings. `tests/test_checks.py::TestCheckSurvivesUnmigratedDatabase::
test_check_reports_nothing_against_an_unmigrated_connection` asserts `manage.py check` is silent
under `tests.settings` and now sees this one warning.

**Not chosen**: overriding `CONTROLLED_VOCABULARIES_BASE_URI` in `tests/settings.py` to agree with
the `/browse/` mount — tried, reverted. Eleven pre-existing tests in `tests/test_models.py` and
`tests/test_factories.py` assert `.uri`/`.local_url` against the literal string
`https://example.org/vocabularies/...`, not through `conf.get_base_uri()`, and all eleven broke.
Moving the ui app's mount in `tests/urls.py` to `/vocabularies/` instead was also not chosen: it
collides with the core app's own mount at that prefix, and the file's own docstring records that
the two prefixes are deliberately different so a hard-coded path in either app would be caught.

**Chosen**: leave `tests/settings.py`, `tests/urls.py` and `tests/test_checks.py` untouched. This
story's own scope (`controlled_vocabularies/ui/`, `tests/test_ui/`, `tests/test_demo/`, `demo/`)
never touches any of the three, and the two production fixes available both ripple into tests this
story does not own. Reported in the completion report's `concerns` rather than silently patched.

**Revisit if**: a maintainer decides which of `tests/settings.py`'s base address or `tests/urls.py`'s
mount should move, and updates the eleven `test_models.py`/`test_factories.py` assertions (or
`SILENCED_SYSTEM_CHECKS`s the warning for the test settings specifically) in the same change.
