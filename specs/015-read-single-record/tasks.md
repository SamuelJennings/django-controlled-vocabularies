# Tasks: Read a single record

**Feature**: `015-read-single-record` · **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Every task is test-first per Article I: the test is written and seen to fail before the production
change that makes it pass. Test scope per task is one class or one file; the full suite runs once per
story, at the story's report.

`[P]` marks tasks that could run in parallel with their siblings.

**Nothing in this feature changes a model, adds a migration, or touches
`controlled_vocabularies/ui/checks.py`.** A task that finds itself editing
`controlled_vocabularies/models.py` has gone wrong. The one core change is in `exchange/`, is a move
plus two derived constants, and is T001.

**A record's address is never built by hand.** In-site links use `{% url %}` against the
`controlled_vocabularies_ui` namespace. `local_url` is an identifier, not a route, and the existing
template test forbids it in a row partial.

---

## Foundational — no story is dispatched until every task here is green

### T001 — A stored kind knows the SKOS property it fills

**Files**: `controlled_vocabularies/exchange/mapping.py`, `controlled_vocabularies/exchange/skos.py`,
`tests/test_exchange/test_mapping.py` (new), `tests/test_exchange/test_skos.py`

Move `skos_curie` from `SkosGraph` in `skos.py` into `mapping.py` as a module-level function, and
update its two callers in `skos.py`. It depends only on the SKOS namespace, which lives in
`mapping.py` already, and `skos.py` imports `mapping.py`, so the dependency runs the right way.

Add `LABEL_CURIES` and `NOTE_CURIES`, each **derived by inverting the existing forward table and
applying `skos_curie`** — never hand-written. A predicate added to `LABEL_PREDICATES` or
`NOTE_PREDICATES` must therefore appear in the inverse with no second edit, and the test asserts
exactly that property rather than a fixed list of strings.

`tests/test_exchange/test_mapping.py` is new and mirrors a source module, so it needs no
conformance declaration.

**Proves**: FR-003 (the keying the rows depend on).
**Verify**: the exchange suite passes unchanged apart from the two updated call sites; inverting a
forward table and applying the function reproduces the constant.
**Depends on**: nothing.

### T002 — One component renders a term and its value

**Files**: `controlled_vocabularies/ui/templates/cotton/controlled_vocabularies/property_row.html`
(new), `tests/test_ui/test_templates.py`

A component taking a term, a value, and optionally a record's short form, canonical identifier and
in-site address. It renders a `<dt>`/`<dd>` pair; a caller wraps a run of them in a `<dl>`.

**Namespacing is load-bearing.** The path puts it at `<c-controlled_vocabularies.property_row />`.
A component at `cotton/data_field.html` in this package would silently shadow django-mvp's for every
project that installs both, because the two directories sit on one loader path.

**It composes django-mvp's own components and uses no class this package invents.** This package
ships no stylesheet and django-mvp's is prebuilt from django-mvp's own templates, so an invented
utility class is absent from the built CSS and does nothing at all, silently. Assert this: every
class the component names is present in the shipped stylesheet. Pick a control class the build has
no other reason to emit, so a passing assertion means something.

**Proves**: FR-016.
**Verify**: the component renders both shapes in isolation through `render_to_string`; the class
assertion passes; no `<dt>` or `<dd>` is written by hand anywhere else in this feature.
**Depends on**: nothing.

### T003 — The rows a record contributes, in a fixed order

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

The shared row-building both pages use: given a record and the reading language, return an ordered
list of rows, each carrying its term (a CURIE from T001), its value, and — where the value is a
record — that record's short form `{scheme.slug}:{record.slug}`, its `uri`, and its in-site address.

**The order is fixed here and not in a template**, so the page reads the same way every time: type,
preferred label, alternative labels, notes in the order `ConceptNote.Kind` declares them, relations,
then the vocabulary. A property with no value in the available languages **contributes no row**, so
no template ever needs emptiness logic.

Hidden labels are never a row (FR-004). Assert that with a concept that has one.

**Proves**: FR-003, FR-004, FR-006, FR-018.
**Verify**: unit tests over the returned rows for a richly populated concept, a bare one, and one
carrying a hidden label.
**Depends on**: T001.

---

## Story US-1 — Open a concept and read what it holds (P1)

### T004 — A concept's address serves a read-only page

**Files**: `controlled_vocabularies/ui/views.py`, `controlled_vocabularies/ui/urls.py`,
`tests/test_ui/test_views.py`, `tests/test_ui/test_urls.py`

`ConceptDetailView`, routed as `path("<str:slug>/<str:concept_slug>/", …, name="concept-detail")`.
`<str:…>` and not `<slug:…>`, for the reason the vocabulary route already documents: the models
slugify with `allow_unicode=True` and Django's converter is ASCII-only. Assert it — a concept named
in a non-Latin script must serve.

404 for a concept slug naming nothing, **and equally for a vocabulary segment naming nothing**
(FR-001). A concept whose slug exists in a different vocabulary is not found here.

The page is read-only: `directory = []`, and **the test asserts on the rendered page that no editing
control appears**, rather than trusting the attribute name to be the only thing that produces one.

**Proves**: FR-001, FR-009 · SC-001 · US-1 scenario 5.
**Verify**: anonymous request to a real concept returns 200; both flavours of unknown address
return 404; no edit or delete affordance in the markup.
**Depends on**: T003.

### T005 — Everything recorded appears, keyed by its property

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_detail.html`
(new), `tests/test_ui/test_views.py`

The page renders the rows from T003 inside one `<dl>`, through the T002 component. A concept with a
preferred label, alternative labels, a definition and a scope note shows each on its own row under
the SKOS property it was recorded under. No hidden label appears anywhere in the markup.

**Proves**: FR-003, FR-004 · SC-001, SC-002 · US-1 scenarios 1, 2.
**Verify**: parse the page and assert term/value pairs by their CURIE; assert the hidden label's text
is absent from the whole response.
**Depends on**: T004.

### T006 — A value is shown in the language being read

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

The reading language, falling back to the vocabulary's own default — the rule
`Concept.display_label()` already implements, applied to notes and alternative labels as well as to
the preferred label. One language, never every language a value was recorded in.

**Proves**: FR-005 · US-1 scenario 3.
**Verify**: a concept with German and English values renders the German ones under a German reading
language, and a concept with no German value falls back to its vocabulary's default rather than
rendering nothing.
**Depends on**: T005.

### T007 — Type and identifier

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_detail.html`,
`tests/test_ui/test_views.py`

A row saying what kind of thing the record is, keyed by the RDF type property, and the record's own
identifier shown as a link — the treatment the vocabulary page already gives a vocabulary's.

**Proves**: FR-008, FR-012.
**Verify**: both rows present; the identifier is an anchor whose destination is the record's `uri`;
an imported concept shows its publisher's identifier.
**Depends on**: T005.

### T008 — An unfilled property produces no row [P]

**Files**: `tests/test_ui/test_views.py`

A concept carrying nothing beyond its label shows its label, its type, its identifier and its
vocabulary, and shows no row for any property it does not carry — not an empty one, not one reading
as absent.

**Proves**: FR-018 · US-1 scenario 4.
**Verify**: count the rows on a bare concept's page and name them.
**Depends on**: T005.

### T009 — The page's query count does not grow with what it shows [P]

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

`select_related("scheme")` and one `prefetch_related` covering labels, notes, both relation
directions and collection memberships — including the scheme of a related concept, whose slug
prefixes that concept's short form. The model helpers all iterate `.all()`, so the prefetch collapses
them.

**Proves**: SC-006.
**Verify**: establish the count with `CaptureQueriesContext`, then assert it with
`django_assert_num_queries` and show it unmoved when the concept gains labels, notes, relations and
memberships.
**Depends on**: T005.

### T010 — The README documents the concept page

**Files**: `README.md`

A section covering what the page shows, how it is reached, and the view that serves it, in the shape
the vocabulary sections already use. Every public name the story introduces is quoted.

**Proves**: Article VI.
**Verify**: the documented reverse names and view names exist; the documented behaviour matches the
tests.
**Depends on**: T009.

---

## Story US-2 — Open a collection and see what it holds (P2)

### T011 — A collection's address serves a page

**Files**: `controlled_vocabularies/ui/views.py`, `controlled_vocabularies/ui/urls.py`,
`tests/test_ui/test_views.py`, `tests/test_ui/test_urls.py`

`CollectionDetailView`, routed as
`path("<str:slug>/collection/<str:collection_slug>/", …, name="collection-detail")`, declared before
the concept route. Same read-only treatment and the same two flavours of 404 as T004.

Assert that a concept and a collection sharing one slug inside one vocabulary are both reachable —
the disjointness the address segment exists for.

**Proves**: FR-002, FR-009 · Edge case 2.
**Verify**: 200 on a real collection; 404 on both flavours of unknown; the shared-slug pair both
serve, at different addresses.
**Depends on**: T003.

### T012 — Name, type and members

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/collection_detail.html`
(new), `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

The same definition list: the collection's name, its identifier as a link, a type row distinguishing
an ordered collection from an unordered one, and its members under the membership property matching
its kind. An ordered collection's members appear in the sequence their positions record.

**Proves**: FR-008, FR-012, FR-013 · SC-005 · US-2 scenarios 1, 2.
**Verify**: an unordered collection and an ordered one render different type rows and different
membership properties; the ordered one's members are in position order, asserted against a
deliberately non-alphabetical sequence so the assertion cannot pass by accident.
**Depends on**: T011.

### T013 — A collection holding nothing says so [P]

**Files**: `tests/test_ui/test_views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/collection_detail.html`

Distinct wording, and no empty membership row.

**Proves**: FR-017 · US-2 scenario 3.
**Verify**: the page renders, says the collection holds nothing, and carries no membership row.
**Depends on**: T012.

### T014 — The collection page's query count is flat [P]

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

As T009, for members and their schemes.

**Proves**: SC-006.
**Verify**: the count does not move as members are added.
**Depends on**: T012.

### T015 — The README documents the collection page

**Files**: `README.md`

**Depends on**: T014.

---

## Story US-3 — Follow a record to the records around it (P2)

### T016 — A record-valued row carries a short form, an identifier and a link

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/cotton/controlled_vocabularies/property_row.html`,
`tests/test_ui/test_views.py`

The short form is `{scheme.slug}:{record.slug}`. The link goes to that record's page **on this
site**, reversed through the app's namespace. The canonical identifier is the record's `uri`, which
for an imported record is its publisher's.

**The identifier must be reachable without a pointer** (FR-007). A `title` attribute alone does not
satisfy that — it is invisible to a keyboard user and unreliable for a screen reader. Carry it in
the markup as text associated with the link. The test asserts the reader-facing outcome: the
identifier is present in the response and associated with its link, without relying on hover.

**Proves**: FR-006, FR-007 · SC-003 · US-3 scenarios 3, 4.
**Verify**: a concept in an imported vocabulary shows the publisher's identifier while its link
resolves to this site's page for it; the identifier is in the markup, not only in an attribute a
pointer reveals.
**Depends on**: T005, T012.

### T017 — Broader, narrower and related

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

Each as its own row keyed by the SKOS property naming the relation. **Narrower is derived** — only
the broader direction is stored — so assert it from a concept that is the broader of two others.

**Proves**: FR-010 · SC-003 · US-3 scenarios 1, 2.
**Verify**: use the existing relation graph builder; follow a broader link and arrive at that
concept's page.
**Depends on**: T016.

### T018 — The vocabulary a record belongs to, and no further step [P]

**Files**: `controlled_vocabularies/ui/views.py`, `tests/test_ui/test_views.py`

A row for the vocabulary, keyed by its SKOS property and linking to its page. **No ancestor chain**:
a concept three levels down shows its immediate broader concept and nothing above it.

**Proves**: FR-011.
**Verify**: build a three-level chain and assert the middle concept's page names only its immediate
neighbours.
**Depends on**: T017.

---

## Story US-4 — Reach a record from the vocabulary that holds it (P2)

### T019 — A vocabulary's concepts link to their pages

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_list_item.html`,
`tests/test_ui/test_views.py`, `tests/test_ui/test_templates.py`

The row partial becomes a link, and the comment naming this issue as the owner of the address comes
out. A narrowed list links its results the same way.

**Proves**: FR-015 · SC-004 · US-4 scenarios 1, 3.
**Verify**: follow an entry from the vocabulary page and from a search result, and arrive at the
right concept.
**Depends on**: T004.

### T020 — A vocabulary's collections link to their pages

**Files**: `controlled_vocabularies/ui/templates/controlled_vocabularies/ui/conceptscheme_detail.html`,
`tests/test_ui/test_views.py`

Same, for the collections section, and its comment comes out too.

**Proves**: FR-015 · SC-004 · US-4 scenario 2.
**Verify**: follow a collection entry and arrive at the right collection.
**Depends on**: T011.

---

## Story US-5 — See which collections a concept belongs to (P3)

### T021 — The membership section

**Files**: `controlled_vocabularies/ui/views.py`,
`controlled_vocabularies/ui/templates/controlled_vocabularies/ui/concept_detail.html`,
`tests/test_ui/test_views.py`

Below the definition list and outside it, under a heading in plain language rather than a CURIE,
because SKOS has a property pointing from a collection to its concepts and no inverse of it. Each
collection links to its page.

**Proves**: FR-014 · US-5 scenario 1.
**Verify**: a concept gathered by two collections names both, outside the `<dl>`, each linking
correctly.
**Depends on**: T012, T016.

### T022 — No section when no collection gathers it [P]

**Files**: `tests/test_ui/test_views.py`

Absent, not empty.

**Proves**: FR-014 · US-5 scenario 2.
**Verify**: the heading does not appear at all.
**Depends on**: T021.

---

## Cross-cutting — the guarantees no single story owns

### T024 — Translation, escaping, and the links that cannot exist

**Files**: `tests/test_ui/test_views.py`, `tests/test_ui/test_templates.py`

Three requirements that hold across both pages and belong to no one story, asserted once here rather
than assumed everywhere.

- **Every user-visible string these pages show is translatable** (FR-019). A CURIE is not a
  user-visible string — it is a SKOS identifier and stays untranslated. Assert that the strings the
  pages introduce carry no hard-coded English, in the way the existing template tests do.
- **Values reach the reader escaped** (FR-021). A concept whose label, note or publisher-supplied
  identifier contains markup renders it as text. Nothing is marked safe, and a publisher-supplied
  identifier reaches an attribute only as a link's destination.
- **No cross-vocabulary link appears** (FR-020). Nothing stores a concept's exact or close matches,
  so no row can carry one. Assert it against a concept imported from a file that offered them, so
  the assertion is about the shipped behaviour rather than about an empty database.

**Proves**: FR-019, FR-020, FR-021 · SC-007.
**Verify**: the three assertions above pass; the escaping test fails if `|safe` is introduced
anywhere in either template.
**Depends on**: T012, T017.

---

## Closing

### T023 — The demo reaches the new pages, and the changelog records them

**Files**: `README.md`, `CHANGELOG.md`, `demo/` as needed

The demo walkthrough already seeds two vocabularies, one of each kind of collection, and concepts
with relations. Extend the documented walk so it ends on a concept's page and a collection's page,
and confirm the seeded data actually exercises what the pages show — a relation, a collection
membership, and a note in more than one language. Changelog entry per the quality bar.

**Proves**: Article VI, SC-008.
**Verify**: run the documented commands from a clean database and walk the documented path.
**Depends on**: T022.
