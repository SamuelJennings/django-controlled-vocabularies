2026-08-24T15:47:04Z SPEC_GATE sent — epic #142, stories #157-#161, draft PR #162, branch 015-read-single-record
2026-08-24T15:58:26Z SPEC_GATE approved by Sam (in session, webchat) — proceeding to plan
2026-08-24T16:15:59Z PLAN complete — plan.md, tasks.md (24 tasks / 5 stories + foundational), ledger generated and schema-valid
2026-08-24T16:34:50Z DESIGN_REVIEW complete — request_changes, 10 findings (3 high, 3 medium, 4 low), all verified against the code
2026-08-24T16:34:50Z PLAN corrected — record resolution specified, prefetch claim replaced with per-read select_related, routes+resolution moved to new T000, closing phase split out (T023 cross-cutting then T024 demo), CURIE terms for relations/scheme/membership/type added, skos_curie namespace guard, T001 assertion de-tautologised, two unreachable spec edge cases struck through; 25 tasks / 5 stories + foundational + closing; trace and stage-exit green

## 2026-08-24T16:46:28Z · Implementer US0 · T000

Did: added `collection-detail` and `concept-detail` routes to `controlled_vocabularies/ui/urls.py`
exactly as plan.md §2 gives them (collection first, `<str:…>` converters, mounted before the
single-segment `vocabulary-detail`). Added `ConceptDetailView` and `CollectionDetailView` to
`controlled_vocabularies/ui/views.py`, both `MVPDetailView` subclasses whose `setup()` resolves
the vocabulary from the address's first segment (raising `Http404` when it names nothing, the
shape `VocabularyDetailView.setup()` already uses), retargets `slug_url_kwarg` to
`concept_slug`/`collection_slug`, and scopes `get_queryset()` to the resolved vocabulary. No
template, context or row-building added — that stays with T003/T004/T011.

Verified: wrote 10 new tests in `tests/test_ui/test_urls.py` first and watched all 10 fail with
`NoReverseMatch` before the routes existed. After implementation: `poetry run pytest
tests/test_ui/test_urls.py -q` — 10 passed. `poetry run ruff check` and `poetry run ruff format
--check` on the three changed files — clean. `poetry run mypy controlled_vocabularies/ui/views.py
controlled_vocabularies/ui/urls.py` — no issues. `poetry run python manage.py makemigrations
--check --dry-run` — no changes detected.

Next: T001 (the CURIE tables in `exchange/mapping.py`).
Watch: nothing outstanding.

## 2026-08-24T16:51:04Z · Implementer US0 · T001

Did: moved `skos_curie` from `SkosGraph` in `exchange/skos.py` to a module-level function
in `exchange/mapping.py`, and updated its two callers in `skos.py` (both `self.skos_graph.
skos_curie(predicate)` sites, in `import_labels` and `import_notes`) to call it directly.
Gave it a namespace guard: it now raises `ValueError` for a predicate outside the SKOS
namespace instead of returning a mangled string. Added `LABEL_CURIES` and `NOTE_CURIES` to
`mapping.py`, each derived by inverting `LABEL_PREDICATES`/`NOTE_PREDICATES` and applying
`skos_curie` — never hand-written. Added the terms no forward table holds as written-out
module constants: `BROADER_CURIE`, `NARROWER_CURIE`, `RELATED_CURIE`, `IN_SCHEME_CURIE`,
`MEMBER_CURIE`, `MEMBER_LIST_CURIE`, `TYPE_CURIE`, `CONCEPT_TYPE_CURIE`,
`COLLECTION_TYPE_CURIE`, `ORDERED_COLLECTION_TYPE_CURIE`.

Verified: wrote `tests/test_exchange/test_mapping.py` (new) first. Confirmed RED by
`git stash`-ing the production changes and re-running the file — it failed with
`ImportError: cannot import name 'LABEL_CURIES'`, the right reason, before restoring the
stash. After implementation: `poetry run pytest tests/test_exchange/test_mapping.py -q` —
6 passed. Two assertions per derived table, neither borrowing the implementation: one
compares `LABEL_CURIES`/`NOTE_CURIES` against a hand-written expectation restating
decisions.md D48's own predicate/CURIE pairs (not recomputed via `skos_curie`), the other
compares `set(LABEL_PREDICATES.values())`/`set(NOTE_PREDICATES.values())` against the
derived table's keys — the no-second-edit property. `poetry run pytest
tests/test_exchange/ -q` — 628 passed, confirming the exchange suite is unchanged apart
from the two updated call sites. `poetry run ruff check`, `poetry run ruff format --check`
and `poetry run mypy` on the three changed/added files — clean. `poetry run python
manage.py makemigrations --check --dry-run` — no changes detected.

Next: T002 (the `property_row` cotton component).
Watch: nothing outstanding.

## 2026-08-24T16:57:04Z · Implementer US0 · T002

Did: added the `property_row` cotton component at `controlled_vocabularies/ui/templates/
cotton/controlled_vocabularies/property_row.html`. Renders a `<dt>`/`<dd>` pair; a plain
`value` renders in `<dd>` as-is, and a record-valued row (`short_form`/`uri`/`href` given)
renders the short form as `<c-link>`'s own text (never `local_url`), with the canonical
identifier (`uri`) as ordinary reader-reachable text beside it via `<c-text muted>` —
never a `title` attribute (FR-007). The `<dt>`/`<dd>` wrapper carries the only two literal
classes the component names, copied verbatim from django-mvp's own `data_field.html`;
everything else composes `<c-link>`/`<c-text>` directly, so nothing this package invents
can go silently unstyled.

Verified: extended `tests/test_ui/test_templates.py` first (4 new tests plus a CSS-class
test pair) and watched them fail — `TemplateDoesNotExist`/`FileNotFoundError` — before the
component existed. After implementation: `poetry run pytest tests/test_ui/test_templates.py
-q` — 12 passed (11 before this task's tests, +1 from the new template joining the
existing repo-wide no-bare-text parametrize sweep). The CSS-class test reads django-mvp's
actual shipped stylesheet (`mvp.__path__[0]/static/css/django-mvp.css` — `mvp` is a
namespace package, so `mvp.__file__` is `None`) and asserts every class the component
names by hand is present, escaping the colon and slash the compiled selector carries
(`.text-base-content\/60{`) the way the build actually spells them; a negative-control
assertion proves the check discriminates a real class from an absent one rather than
passing regardless of what it is given. `poetry run ruff check`, `poetry run ruff format
--check` and `poetry run mypy` on the two changed/added files — clean. `poetry run python
manage.py makemigrations --check --dry-run` — no changes detected.

Next: T003 (the row-building the two pages share).
Watch: nothing outstanding.

## 2026-08-24T17:03:59Z · Implementer US0 · T003

Did: added `concept_property_rows(concept, language)` to `controlled_vocabularies/ui/
views.py` — the shared row-building both T004 and T011 will render from. Returns rows in
the fixed order: type (`rdf:type` → `skos:Concept`), preferred label, alternative labels,
notes in `ConceptNote.Kind`'s own declared order, relations (broader, then narrower, then
related), then the vocabulary. No collections row — decisions.md D4 places collection
membership outside this list entirely, as a statement other records make about this
concept rather than one it makes about itself. Hidden labels are never read (FR-004). A
property absent in the given `language` contributes no row, with no fallback logic inside
this function — decisions.md D6 leaves that to the caller. Each relation read chains
`.select_related("scheme")` per decisions.md D-015-02 (none of the three is prefetchable).
The vocabulary row has no genuine "short form" of its own (decisions.md D2 — nothing
records a vocabulary's own prefix), so it is named by its plain `.name` instead; every
record-valued row's link is reversed through `controlled_vocabularies_ui`, never built
from `local_url`.

Verified: extended `tests/test_ui/test_views.py` first (6 new test classes, 12 tests) and
watched them fail with `ImportError: cannot import name 'concept_property_rows'` before
the function existed. After implementation: `poetry run pytest tests/test_ui/test_views.py
-q -k ConceptPropertyRows` — 8 passed (later expanded to the 12 total across the added
classes, all green). `poetry run pytest tests/test_ui/test_views.py -q` — 113 passed, 1
skipped (the pre-existing #147/django-mvp#291 skip, untouched) — no regressions. `poetry
run ruff check`, `poetry run ruff format --check` and `poetry run mypy` on both changed
files — clean. `poetry run python manage.py makemigrations --check --dry-run` — no
changes detected.

Next: none — T000-T003 (US0, the foundational phase) are all committed.
Watch: the vocabulary row's `short_form` (its plain `.name`, not a `{prefix}:{slug}` form)
and its D-015-02-driven per-relation `.select_related("scheme")` are judgment calls made
under decisions.md D2/D-015-02 respectively rather than settled by an explicit T003
acceptance criterion — worth a second look at T004/T005 gate time if the rendered
vocabulary row reads oddly next to a concept's own short form.

## 2026-08-24T19:15:00Z · Implementer US1 · T004

Did: gave `ConceptDetailView` its own template candidate
(`controlled_vocabularies/ui/concept_detail.html`, falling back to django-mvp's
`detail_view.html` — empty body — until T005 adds the file) and a
`get_context_data()` that wires T003's `concept_property_rows(self.object,
get_language())` into the page as `context["rows"]`. T000's `setup()`/`get_queryset()`
already served 200 for a real concept and 404 for both flavours of unknown address, and
already resolved a slug shared by two vocabularies to the right one, so this task adds
no new resolution behaviour — only the row wiring and the read-only assertion.

Verified: extended `tests/test_ui/test_views.py` first (`TestConceptDetail`, 6 tests)
and watched them fail — 5 already passed against T000's resolution alone (right reason:
nothing new to prove there), the 6th (`context["rows"]`) failed with `KeyError: 'rows'`
before `get_context_data()` existed. After implementation: `poetry run pytest
tests/test_ui/test_views.py -q -k TestConceptDetail` — 6 passed. The read-only test
asserts both `response.context["directory"] == {}` (a context-level check, catching the
upstream `show_<action>_action` defaults) and, on the rendered markup, no `re.compile("Edit")`
/`re.compile("Delete")` text node — plan.md's stated risk mitigation for a default
flipping in a 0.x dependency. `poetry run pytest tests/test_ui/test_views.py -q` — 119
passed, 1 skipped (the pre-existing django-mvp#291 skip, untouched) — no regressions.
`poetry run ruff check`, `poetry run ruff format --check` and `poetry run mypy` on both
changed files — clean. `poetry run python manage.py makemigrations --check --dry-run` —
no changes detected.

Next: T005 (the `concept_detail.html` template renders `rows` inside one `<dl>`).
Watch: nothing outstanding.

## 2026-08-24T17:22:56Z · Implementer US1 · T005

Did: added `concept_detail.html`, extending `detail_view.html` and rendering T003's
`rows` inside one `<dl>` through the T002 `property_row` component. Two branches per
row rather than one call passing every key unconditionally: a Python `None` substituted
into `{{ }}` renders as the literal text `"None"`, which would make
`property_row.html`'s `{% if short_form %}` true for every plain-value row too, so only
the keys a row actually carries are passed.

Verified: this task's test-writing had already started before an infrastructure fault
interrupted the prior run — inherited `TestConceptDetailShowsWhatIsRecorded` (2 tests)
in `tests/test_ui/test_views.py` and the template itself, both uncommitted. Read both
against tasks.md's T005 requirements before trusting them: the two tests cover a
preferred label, a definition and a scope note each on their own row (test 1) and
alternative labels appearing while a hidden label appears nowhere in the response
(test 2) — matching FR-003/FR-004/SC-001/SC-002/US-1 scenarios 1-2 exactly, asserted by
parsing `<dt>`/`<dd>` pairs by CURIE via BeautifulSoup, the shape T004's tests already
use. Confirmed RED by moving the template aside and re-running: both tests failed with
`AssertionError: assert (...) in []` — the right reason, an empty `<dl>` — before
restoring it. `poetry run pytest tests/test_ui/test_views.py -q -k TestConceptDetail` —
8 passed (the inherited 2 plus T004's existing 6). `poetry run ruff check`, `poetry run
ruff format --check` and `poetry run mypy` on `tests/test_ui/test_views.py` — clean (the
template is not a Python file). `poetry run python manage.py makemigrations --check
--dry-run` — no changes detected.

Next: T006 (the reading-language rule, applied to notes and alternative labels).
Watch: nothing outstanding.

## 2026-08-24T17:28:04Z · Implementer US1 · T006

Did: gave `concept_property_rows()` an opt-in `default_language: str | None = None`
parameter. Two local helpers, `localized_text`/`localized_list`, retry a property's
getter in `default_language` when `language` produced nothing and a `default_language`
was actually given — mirroring `Concept.display_label()`'s own
`preferred_label(active) or label` pattern, extended here to alternative labels and
every note kind, per-property rather than as one whole-concept decision (FR-005: "each
value appears in that language, and where the concept has no value in it, in the
vocabulary's own default language"). `default_language=None` (the default) keeps the
prior no-fallback contract exactly, which is why `TestConceptPropertyRowsLanguageScoping`
(T003, calling the function with only two positional args) needed no change and stayed
green throughout — decisions.md D6's "the caller's decision, not this function's" is now
literally which optional argument the caller passes. `ConceptDetailView.get_context_data`
opts in by passing `self.object.scheme.effective_default_language`.

Verified: extended `tests/test_ui/test_views.py` first
(`TestConceptDetailValuesInTheReadingLanguage`, 2 tests) and watched them fail before the
fallback existed. The first test (values present in both languages) passed immediately
on first run — a concept carrying full German content needs no fallback to prove
anything, so it is not a reproduction of the missing behaviour but a real coverage case
for "each value appears in that language" across three property types at once, kept for
that reason. The second (a concept holding only default-language content, read in
German) failed for the right reason — `AssertionError: assert 'Granite' in [...]`, the
expected fallback value simply absent from the rendered `<dl>` — before the fallback
existed. `poetry run pytest tests/test_ui/test_views.py -q -k "TestConceptDetail or
TestConceptPropertyRows"` — 18 passed, confirming the T003 language-scoping test and
every T004/T005 test stayed green unmodified. `poetry run pytest
tests/test_ui/test_views.py -q` — 123 passed, 1 skipped (the pre-existing
django-mvp#291 skip, untouched) — no regressions. `poetry run ruff check`, `poetry run
ruff format --check` and `poetry run mypy` on both changed files — clean. `poetry run
python manage.py makemigrations --check --dry-run` — no changes detected.

Next: T007 (the type row's literal key, and the identifier link).
Watch: nothing outstanding.

## 2026-08-24T17:30:08Z · Implementer US1 · T007

Did: added the record's own identifier to `concept_detail.html` as an outbound anchor —
`<a href="{{ object.uri }}" rel="noopener">{{ object.uri }}</a>` inside `<c-text size="xs"
muted>` — the same markup pattern `conceptscheme_detail.html` already uses for a
vocabulary's identifier (FR-008). Deliberately not a `<dl>` row: plan.md Key design
decision #4 fixes the row order as type, preferred label, alternative labels, notes,
relations, vocabulary, with no identifier row in it, so it sits after the closing
`</dl>` rather than going through `concept_property_rows()`/`property_row`. The type
row itself (FR-012) needed no new code — T003 already built it, keyed by the literal
`TYPE_CURIE = "rdf:type"` module constant (`exchange/mapping.py`), written out rather
than derived through `skos_curie()` because `rdf:type` sits outside the SKOS namespace
that function's guard refuses (T001). `Concept.uri` already prefers `static_uri` over
`local_url` (`models.py:315-323`), so an imported concept's publisher identifier needed
no view change either — only the test proving it.

Verified: extended `tests/test_ui/test_views.py` first
(`TestConceptDetailTypeAndIdentifier`, 3 tests) and watched them run: the type-row test
passed immediately (T003's existing row, right reason — nothing new to prove there,
matching T004's own precedent for a test that asserts prior work); the identifier-anchor
test and the imported-concept test both failed with `assert None is not None` — no
anchor at either `concept.uri` or `concept.static_uri` — before the template addition.
`poetry run pytest tests/test_ui/test_views.py -q -k TestConceptDetailTypeAndIdentifier`
— 3 passed after implementation. `poetry run pytest tests/test_ui/test_views.py -q` —
126 passed, 1 skipped (the pre-existing django-mvp#291 skip, untouched) — no
regressions. `poetry run ruff check`, `poetry run ruff format --check` and `poetry run
mypy` on both changed files — clean. `poetry run python manage.py makemigrations
--check --dry-run` — no changes detected.

Next: T008 (an unfilled property produces no row) and T009 (flat query count) — both [P],
either order.
Watch: nothing outstanding.

## 2026-08-24T17:31:26Z · Implementer US1 · T008

Did: no production change — this task is test-only per tasks.md's own file list. Added
`TestConceptDetailUnfilledPropertiesProduceNoRow` to `tests/test_ui/test_views.py`,
proving FR-018 through the rendered page rather than through `concept_property_rows()`
directly (T003's `TestConceptPropertyRowsForABareConcept` already covers the function in
isolation): a bare concept's `<dl>` carries exactly three `<dt>`s, in order — `rdf:type`,
`skos:prefLabel`, `skos:inScheme` — and its identifier anchor (T007) is present, with no
row for any property it does not carry.

Verified: the test passed on first run, since T003 and T007 already built the behaviour
it asserts — per craft-tdd, a claim of pre-existing coverage must be probed rather than
just read. Probed by temporarily inserting a spurious extra row
(`row("skos:definition", value="")`) at the front of `concept_property_rows()`'s return
list and re-running: the test failed on the term-list mismatch, the right reason, before
the probe was reverted (`git checkout -- controlled_vocabularies/ui/views.py`, confirmed
clean via `git status`). `poetry run pytest tests/test_ui/test_views.py -q -k
TestConceptDetailUnfilledPropertiesProduceNoRow` — 1 passed, both before and after the
probe/revert cycle. `poetry run pytest tests/test_ui/test_views.py -q` — 127 passed, 1
skipped (the pre-existing django-mvp#291 skip, untouched) — no regressions. `poetry run
ruff check`, `poetry run ruff format --check` and `poetry run mypy` on the changed file
— clean. `poetry run python manage.py makemigrations --check --dry-run` — no changes
detected.

Next: T009 (the page's query count does not grow with what it shows).
Watch: nothing outstanding.

## 2026-08-24T17:36:15Z · Implementer US1 · T009

Did: gave `ConceptDetailView.get_queryset()` `.select_related("scheme")` and
`.prefetch_related("labels", "concept_notes")` (plan.md Key design decision #7) — the
two helpers (`alt_labels()`, `notes()` per `ConceptNote.Kind`) that read a cached related
set via `.all()`, plus the vocabulary row's `concept.scheme` lookup, which
`select_related` folds into the same query as the object fetch instead of a separate
round trip. `broader()`/`narrower()`/`related()` build fresh querysets each call
(decisions.md D-015-02) and stay untouched — a prefetch of those paths would never be
read, and each already carries its own `.select_related("scheme")` from T003.

Verified: first measured the *actual* per-property-growth invariant with an unmodified
tree (a probe script under `tests/test_ui/`, discarded after) and found it already held
— every relation/label/note helper here executes one query per *distinct call site*
regardless of row count, so a growth-comparison test alone (add labels/notes/relations,
assert the query count is unchanged) would pass identically with or without the
optimisation and prove nothing about it. Added a second assertion carrying the actual
weight: `assert baseline <= 8`, a real ceiling reflecting the optimised shape (vocabulary
lookup + joined object fetch + two prefetches + three relation queries), which a
`git checkout`-free run confirmed RED at 14 before the `get_queryset()` change (`assert
14 <= 8`, the unoptimised baseline: one query for the vocabulary-row scheme lookup, one
for `alt_labels`, seven for the note-kind loop, three for the relation querysets, plus
the two initial lookups). Extended `tests/test_ui/test_views.py`
(`TestConceptDetailQueryCount`, 1 test carrying both the ceiling and the growth
invariant). After implementation: baseline fell to 7, both assertions pass. `poetry run
pytest tests/test_ui/test_views.py -q -k TestConceptDetailQueryCount` — 1 passed.
`poetry run pytest tests/test_ui/test_views.py -q` — 128 passed, 1 skipped (the
pre-existing django-mvp#291 skip, untouched) — no regressions. `poetry run ruff check`,
`poetry run ruff format --check` (both files needed `ruff format` to apply the
multi-line queryset chain and the new test's own layout — reapplied and reverified
clean) and `poetry run mypy` on both changed files — clean. `poetry run python manage.py
makemigrations --check --dry-run` — no changes detected.

Next: T010 (the README documents the concept page) — the last task of Story US-1.
Watch: nothing outstanding.

## 2026-08-24T17:38:20Z · Implementer US1 · T010

Did: added a `### A concept's own page` section to `README.md`, between `### A
vocabulary's own page` and `### Try it: the demo project`, in the same shape those
sections already use: what the page shows (the definition list keyed by SKOS property,
hidden labels never appearing, a property with no value contributing no row), the
language rule (reading language, falling back to the vocabulary's own default), the
identifier treatment (a link, publisher's for an imported concept), the read-only and
no-permission-rule guarantees, the two indistinguishable 404 cases and the shared-slug
resolution, a `reverse()` example passing both `slug` and `concept_slug`, and the
serving view's name. Scoped strictly to what T005-T009 actually deliver: no mention of
the collection membership section (T021, not yet built) or of the vocabulary list
page linking to a concept entry (T019, not yet built) — those belong to their own
stories. No test file: T010, like T015 for the collection page, documents only.

Verified: reversed the documented name directly — `poetry run python manage.py shell
-c "from django.urls import reverse; print(reverse('controlled_vocabularies_ui:
concept-detail', kwargs={'slug': 'demo-vocab', 'concept_slug': 'demo-concept'}))"` —
`/browse/demo-vocab/demo-concept/`, confirming the route name and both kwargs exist
exactly as documented. `poetry run pytest tests/test_ui/test_views.py -q -k
"TestConceptDetail or TestConceptPropertyRows"` — 23 passed, confirming the documented
behaviour matches every US-1 test written across T003-T009. `poetry run python
manage.py makemigrations --check --dry-run` — no changes detected. `ruff`/`mypy` do not
apply to a markdown-only change.

Story US-1 (T004-T010) is complete. All tasks committed individually; the tree is clean.

## 2026-08-24T19:52:00Z · Implementer US2 · T011

Did: gave `CollectionDetailView` its page: `template_name` (falling back to django-mvp's
`detail_view.html` — empty body — until T012 adds the file) and a `get_context_data()`
wiring a new `collection_property_rows(collection)` into the page as `context["rows"]`.
Added `collection_property_rows` to `controlled_vocabularies/ui/views.py`, mirroring
`concept_property_rows`'s shape (type, name, members, vocabulary) rather than reusing it
directly — a collection's `name` is a plain `CharField` with no per-language variants, so
there is no reading-language argument, and its type/membership CURIEs depend on
`Collection.ordered` rather than being fixed. Its member rows reuse the collection's own
already-loaded `scheme` for the short-form prefix and identifier composition rather than
each member's own (D-015-02), assigning it onto the FK cache directly (`member.scheme =
collection.scheme`) so no query is spent per member — `Collection.members()` itself is
out of this feature's scope (models.py) and only `select_related`s `"concept"`. T000's
`setup()`/`get_queryset()` already served 200 for a real collection and 404 for both
flavours of unknown address, so this task adds no new resolution behaviour.

Verified: extended `tests/test_ui/test_views.py` first (`TestCollectionDetail`, 6 tests)
and watched them fail — `ImportError: cannot import name 'collection_property_rows'`, the
right reason, before the function existed. After implementation: `poetry run pytest
tests/test_ui/test_views.py -q -k TestCollectionDetail` — 6 passed, including the
shared-slug assertion (FR-002, Edge case 2: a concept and a collection in one vocabulary
carrying the same slug, both reachable at their own addresses) and the read-only
assertion (`directory == {}`, no "Edit"/"Delete" text — the same default-flipping
mitigation T004 uses). `poetry run pytest tests/test_ui/test_views.py -q` — 134 passed, 1
skipped (the pre-existing django-mvp#291 skip, untouched) — no regressions. `poetry run
ruff check`, `poetry run ruff format --check` and `poetry run mypy` on both changed files
— clean. `poetry run python manage.py makemigrations --check --dry-run` — no changes
detected.

Next: T012 (the `collection_detail.html` template — name, type and members).
Watch: nothing outstanding.

## 2026-08-24T20:05:00Z · Implementer US2 · T012

Did: added `collection_detail.html`, extending `detail_view.html` and rendering
`collection_property_rows()`'s rows inside one `<dl>` through the T002 `property_row`
component — byte-identical two-branch shape to `concept_detail.html`'s own, plus the
same outside-the-`<dl>` identifier anchor T007 gave the concept page. No further
`views.py` change: T011 already built `collection_property_rows()` with the type row
keyed by `Collection.ordered` (`skos:Collection` vs `skos:OrderedCollection`) and the
member rows keyed the same way (`skos:member` vs `skos:memberList`), an ordered
collection's rows following `Collection.members()`'s own position order.

Verified: extended `tests/test_ui/test_views.py` first
(`TestCollectionDetailNameTypeAndMembers`, 3 tests) and watched them fail — the
identifier test with `assert None is not None` (no anchor against the empty
`detail_view.html` fallback body) and the two `<dl>`-content tests against an empty
`pairs` list — the right reason, before the template existed. An unordered collection's
members are asserted by counting `skos:member` rows (three, none `skos:memberList`); an
ordered one's by extracting each `skos:memberList` row's short-form anchor text (not the
whole `<dd>`'s, which also carries the canonical identifier as a second text node) and
comparing it against `collection_with_members`'s own insertion order — built from a
deliberately non-alphabetical label sequence (`Granite, Basalt, Gabbro`) so the
assertion cannot pass by coincidental sort order. `poetry run pytest
tests/test_ui/test_views.py -q -k TestCollectionDetail` — 9 passed (T011's existing 6
plus this task's 3). `poetry run pytest tests/test_ui/test_views.py
tests/test_ui/test_templates.py -q` — 151 passed, 1 skipped (the pre-existing
django-mvp#291 skip, untouched) — the repo-wide no-bare-text template sweep in
`test_templates.py` already parametrizes over every file under the templates root, so
the new template joined it with no test change of its own. `poetry run ruff check`,
`poetry run ruff format --check` and `poetry run mypy` on the changed Python file —
clean (the template is not a Python file). `poetry run python manage.py makemigrations
--check --dry-run` — no changes detected.

Next: T013 (a collection holding nothing says so).
Watch: nothing outstanding.

## 2026-08-24T20:12:00Z · Implementer US2 · T013

Did: `CollectionDetailView.get_context_data()` gains `context["collection_has_members"]`,
computed from the already-built `rows` (a membership-CURIE row present, `skos:member` or
`skos:memberList`) rather than a second `.members()` call. `collection_detail.html`
renders a translated `"This collection holds no members."` message when that flag is
false, placed after the `<dl>` and before the identifier anchor. No change to
`collection_property_rows()` itself: a collection with no members already contributed no
membership row (its `.extend(member_row(...) for member in collection.members())` simply
has nothing to iterate), so FR-017's "no empty membership row" half was already true —
this task only adds the "says so" half.

Verified: extended `tests/test_ui/test_views.py` first
(`TestCollectionDetailEmptyState`, 3 tests: an empty unordered collection, an empty
ordered one, and a populated one showing no such message) and watched the first two fail
— `assert None is not None`, the message absent from the rendered page — before the
template addition; the third passed immediately (right reason: nothing to prove there,
matching T004's own precedent for asserting the absence of something never built). After
implementation: `poetry run pytest tests/test_ui/test_views.py -q -k
TestCollectionDetailEmptyState` — 3 passed. `poetry run pytest
tests/test_ui/test_views.py -q -k TestCollectionDetail` — 12 passed (T011's 6, T012's 3,
this task's 3), confirming the `context["rows"]` equality test from T011 stayed green
unmodified despite the new context key. `poetry run pytest tests/test_ui/test_views.py
tests/test_ui/test_templates.py -q` — 154 passed, 1 skipped (the pre-existing
django-mvp#291 skip, untouched) — no regressions. `poetry run ruff check`, `poetry run
ruff format --check` and `poetry run mypy` on the changed Python file — clean. `poetry
run python manage.py makemigrations --check --dry-run` — no changes detected.

Next: T014 (the collection page's query count does not grow with what it shows).
Watch: nothing outstanding.

## 2026-08-24T20:20:00Z · Implementer US2 · T014

Did: added `.select_related("scheme")` to `CollectionDetailView.get_queryset()`, joining
the vocabulary row's own scheme lookup into the object fetch — the same `collection.scheme`
`collection_property_rows()` already reads once for the `skos:inScheme` row and, since T011,
reuses (via `member.scheme = collection.scheme`) for every member row's short-form prefix
instead of querying each member's own (D-015-02). `Collection.members()` itself
(`models.py`, out of this feature's scope) still only `select_related`s `"concept"`, not
`"concept__scheme"` — the member-row reuse from T011 is what makes that not cost a query
per member, and this task's own addition removes the one remaining per-request query (the
collection's own scheme, previously fetched lazily on first access).

Verified: extended `tests/test_ui/test_views.py` first
(`TestCollectionDetailQueryCount`, 1 test) and it **passed on first run** — T011 had
already built the member-row reuse this task's own docstring describes, so nothing new
needed proving there; per craft-tdd, a claim of pre-existing coverage must be probed
rather than just read. Probed by temporarily disabling the `member.scheme = collection.scheme`
line (`sed`-style edit, reverted via `git checkout` immediately after) and re-running a
one-off script hitting the view directly with `CaptureQueriesContext`: baseline query
count rose from 3 to 6 for a 2-member collection — two extra queries, one per member's
own `scheme` lookup — confirming the reuse is load-bearing and the test would catch its
removal. `poetry run pytest tests/test_ui/test_views.py -q -k
TestCollectionDetailQueryCount` — 1 passed, before and after the probe/revert cycle
(confirmed clean via `git status` after the revert). The `assert baseline <= 3` ceiling
was set from the same probe script's measured count after `select_related("scheme")`
was added (vocabulary lookup + joined object fetch + one memberships query — a real
ceiling a caller can regress past, not only a bound flat by construction). `poetry run
pytest tests/test_ui/ -q` — 209 passed, 1 skipped (the pre-existing django-mvp#291 skip,
untouched) — no regressions. `poetry run ruff check`, `poetry run ruff format --check`
and `poetry run mypy` on both changed files — clean. `poetry run python manage.py
makemigrations --check --dry-run` — no changes detected.

Next: T015 (the README documents the collection page) — the last task of Story US-2.
Watch: nothing outstanding.

## 2026-08-24T20:26:00Z · Implementer US2 · T015

Did: added a `### A collection's own page` section to `README.md`, between `### A
concept's own page` and `### Try it: the demo project`, in the same shape those sections
already use: what the page shows (name, type, members, keyed by their SKOS/membership
properties, the empty-collection wording), the shared-slug disjointness with a concept's
address, the identifier and read-only treatment, the two indistinguishable 404 cases, a
`reverse()` example passing both `slug` and `collection_slug`, and the serving view's
name. Scoped strictly to what T011-T014 actually deliver — no mention of US-3's
broader/narrower/related rows or US-4's vocabulary-page links, which are not yet built.
No test file: like T010, this documents only.

Verified: reversed the documented name directly — `poetry run python manage.py shell -c
"from django.urls import reverse; print(reverse('controlled_vocabularies_ui:
collection-detail', kwargs={'slug': 'demo-vocab', 'collection_slug':
'demo-collection'}))"` — `/browse/demo-vocab/collection/demo-collection/`, confirming
the route name and both kwargs exist exactly as documented. `poetry run pytest
tests/test_ui/test_views.py -q -k "TestCollectionDetail or TestCollectionPropertyRows"`
— 13 passed, confirming the documented behaviour matches every US-2 test written across
T011-T014. `poetry run python manage.py makemigrations --check --dry-run` — no changes
detected. `ruff`/`mypy` do not apply to a markdown-only change.

Story US-2 (T011-T015) is complete. All tasks committed individually; the tree is clean.

### Full suite and pre-commit, run once at the story's end

`poetry run pytest -q` — 1604 passed, 1 skipped (the pre-existing django-mvp#291 skip,
untouched) — no regressions across the whole tree, not only `tests/test_ui/`.

`poetry run pre-commit run --all-files` — all hooks passed (trim trailing whitespace,
fix end of files, check yaml, poetry-check, ruff lint, ruff format, mypy, deptry).

Next: none — Story US-2 (T011-T015) is complete. US-3 (T016-T018) is next in plan.md's
story sequence, dispatched separately.
Watch: nothing outstanding.

## 2026-08-24T20:06:00Z · Implementer US3 · T016

Did: no production change. T003's `concept_property_rows()`/`member_row()` already
carry a record-valued row's canonical identifier via `record.uri` (which already
prefers `static_uri` — an imported record's publisher-assigned identifier — over
`local_url`, `models.py:315-323`), and T002's `property_row.html` already renders it
as ordinary reader-reachable text (`<c-text size="xs" muted tight>{{ uri }}</c-text>`)
beside the in-site link, never a `title` attribute — both built before this task was
dispatched. What was genuinely absent was a test proving it at the rendered page for a
*related* record's row (T007's existing imported-concept test only covers a concept's
own identifier on its own page, not a related concept shown on someone else's).

Added `TestConceptDetailRelatedRecordIdentifiers` to `tests/test_ui/test_views.py` (2
tests): a broader row's identifier is present as text within the `<dd>` and the
anchor carries no `title` attribute; an imported broader concept's row shows its
`static_uri` (asserted to start with `http://publisher.example.org/`, the `external`
factory trait's fixed prefix) while the link still reverses to this site's page for
it, and following that link returns 200 with `response.context["object"]` equal to
the imported concept.

Verified: both tests passed on first run — per craft-tdd, a claim of pre-existing
coverage must be probed rather than just read. Probed by temporarily replacing
`property_row.html`'s `<c-link>`/`<c-text>` pair with a single `<a href="{{ href }}"
title="{{ uri }}">{{ short_form }}</a>` (identifier moved into a `title` attribute,
the exact anti-pattern FR-007 forbids) and re-running: both tests failed for the
right reason (`assert link.get("title") is None` found the URI where it should have
found nothing; `assert parent.static_uri in broader_dd.get_text()` found the short
form alone, the identifier no longer in the text) — before reverting via `git diff`
inspection and restoring the original two-tag markup, confirmed clean with `git
status`. `poetry run pytest tests/test_ui/test_views.py -q -k
TestConceptDetailRelatedRecordIdentifiers` — 2 passed. `poetry run pytest
tests/test_ui/test_views.py -q` — 143 passed, 1 skipped (the pre-existing
django-mvp#291 skip, untouched) — no regressions. `poetry run ruff check`, `poetry
run ruff format --check` on the changed file, and `poetry run mypy
controlled_vocabularies/ui/views.py` — all clean (no production file changed).
`poetry run python manage.py makemigrations --check --dry-run` — no changes
detected.

Next: T017 (broader, narrower and related as their own rows; following one opens
that concept's page).
Watch: nothing outstanding.

## 2026-08-24T20:12:00Z · Implementer US3 · T017

Did: no production change. T003's `concept_property_rows()` already builds a row
for each of `concept.broader()`, `.narrower()` and `.related()` in that fixed
order, and `.narrower()` (models.py:863-872) is already read back from the target
side of the stored `BROADER` relation rather than asserted directly — only the
narrower->broader direction is ever written (research R1). Nothing here needed
building; what was absent was proof at the rendered page that each relation's row
carries the right related concept and that its link actually opens that concept's
own page.

Added `TestConceptDetailBroaderNarrowerAndRelated` to
`tests/test_ui/test_views.py` (3 tests): a broader concept's row and its followed
link; a concept that is the broader of two others shows both as narrower rows
(`child_one`/`child_two` each call `.add_broader(parent)` — only the stored
direction — and `parent`'s page is asserted to carry both derived narrower rows),
following one of the two narrower links to confirm it opens one of the two
children's own page; a related concept's row and its followed link.

Verified: all three passed on first run — per craft-tdd, probed rather than
trusted. Probed by deleting the three `rows.extend(...)` lines building the
broader/narrower/related rows from `concept_property_rows()` and re-running: all
three tests failed for the right reason (`ValueError: not enough values to
unpack (expected 1, got 0)` for the single-relation broader/related tests, an
empty-set mismatch for the two-narrower test) — before restoring the three lines
verbatim, confirmed clean via `git diff controlled_vocabularies/ui/views.py`
(no output). `poetry run pytest tests/test_ui/test_views.py -q -k
TestConceptDetailBroaderNarrowerAndRelated` — 3 passed. `poetry run pytest
tests/test_ui/test_views.py -q` — 146 passed, 1 skipped (the pre-existing
django-mvp#291 skip, untouched) — no regressions. `poetry run ruff check` on
both files — clean. `poetry run ruff format --check` first flagged the new test
file (one long line); `poetry run ruff format` reapplied and reverified clean.
`poetry run mypy controlled_vocabularies/ui/views.py` — no issues (no production
file changed). `poetry run python manage.py makemigrations --check --dry-run` —
no changes detected.

Next: T018 (the vocabulary row, and the three-level chain proving no ancestor
step beyond the immediate neighbour).
Watch: nothing outstanding.

## 2026-08-24T20:18:00Z · Implementer US3 · T018

Did: no production change. T003's `concept_property_rows()` already appends
exactly one `IN_SCHEME_CURIE` row per call, and `Concept.broader()`/`.narrower()`
(models.py:852-872, out of this feature's scope) are each a single flat
`Concept.objects.filter(...)` — no recursion anywhere in the codebase walks
beyond the one hop FR-010/FR-011 ask for. Nothing needed building.

Added `TestConceptDetailVocabularyRowAndNoAncestorChain` to
`tests/test_ui/test_views.py` (2 tests): the vocabulary row appears keyed by
`IN_SCHEME_CURIE`, is linked by the vocabulary's display name (decisions.md
D-015-03 — not a short form), and following it opens the vocabulary's own page
(`response.context["vocabulary"]`); a three-level chain
(grandparent -> parent -> child, built with two `add_broader()` calls) shows the
middle concept's page naming exactly its immediate broader (grandparent) and
narrower (child) neighbours, asserted as an exact ordered list rather than a
membership check, so any extra or missing relation row fails it.

Verified: both passed on first run — probed per craft-tdd rather than trusted.
Two separate probes, one per test: (1) temporarily removed the `IN_SCHEME_CURIE`
`rows.append(...)` block from `concept_property_rows()` — the vocabulary-row
test failed with `StopIteration` (no such `<dt>` on the page), the right reason;
(2) temporarily duplicated the `BROADER_CURIE` `rows.extend(...)` line so the
grandparent's row appeared twice — the three-level-chain test's exact-list
assertion failed on the extra entry (`Left contains one more item:
('skos:narrower', ...)`, a list-length mismatch caused by the duplicate broader
row shifting the narrower row's index), confirming the assertion is exact
rather than a loose membership check and would catch surplus relation content
regardless of its source. Both reverted individually and confirmed clean via
`git diff controlled_vocabularies/ui/views.py` (no output) before the next
probe. `poetry run pytest tests/test_ui/test_views.py -q -k
TestConceptDetailVocabularyRowAndNoAncestorChain` — 2 passed. `poetry run
pytest tests/test_ui/test_views.py -q` — 148 passed, 1 skipped (the
pre-existing django-mvp#291 skip, untouched) — no regressions. `poetry run
ruff check` and `poetry run ruff format --check` on both files — clean.
`poetry run mypy controlled_vocabularies/ui/views.py` — no issues (no
production file changed). `poetry run python manage.py makemigrations --check
--dry-run` — no changes detected.

Story US-3 (T016-T018) is complete. All tasks committed individually; the tree
is clean. No production code changed across the story — every behaviour US-3
proves was already built by the foundational phase (T003) and Stories US-1/US-2;
this story's own work was entirely the tests that pin it, each probed by
temporarily breaking the mechanism it claims to cover.

### Full suite and pre-commit, run once at the story's end

`poetry run pytest -q` — 1611 passed, 1 skipped (the pre-existing django-mvp#291
skip, untouched) — no regressions across the whole tree.

`poetry run pre-commit run --all-files` — all hooks passed (trim trailing
whitespace, fix end of files, check yaml, poetry-check, ruff lint, ruff format,
mypy, deptry).

Next: none — Story US-3 (T016-T018) is complete. US-4 (T019-T020) is next in
plan.md's story sequence, dispatched separately.
Watch: nothing outstanding.

### Amendment to T018, after review

The three-level chain the task text asked for cannot fail its own assertion. The
concept under test sits in the middle, so its broader concept is the chain's top
and its narrower concept is the chain's bottom: a page that walked two steps in
either direction would find nothing further to show and the exact-list assertion
would hold anyway. The fixture is now five levels, which gives the second hop a
real concept to surface in each direction.

Probed by making the view emit each broader concept's own broader concept as a
further row: `poetry run pytest tests/test_ui/test_views.py -q -k
test_a_five_level_chain` — 1 failed, for the right reason (the surplus row).
`controlled_vocabularies/ui/views.py` restored from a pre-edit copy and confirmed
clean via `git diff --stat` (test file only). `poetry run pytest -q` — 1611
passed, 1 skipped. `poetry run pre-commit run --all-files` — all hooks passed.

## 2026-08-24T20:33:00Z · Implementer US4 · T019

Did: `concept_list_item.html`'s row is now an anchor to the concept's own page
(`{% url 'controlled_vocabularies_ui:concept-detail' object.scheme.slug
object.slug %}`, inside a `title` slot rather than `<c-card>`'s `title` attribute,
which auto-escapes and so cannot carry markup — the same pattern
`conceptscheme_list_item.html` already uses for a vocabulary's own row). The
`#142`-naming comment came out. `VocabularyDetailView.setup()`'s queryset gained
`.select_related("scheme")`: the row renders in an isolated context holding only
`object` (`render_list_item`, `mvp/templatetags/mvp.py`, builds a fresh context
per row rather than inheriting the page's own `vocabulary` variable), so the href
can only be built from `object.scheme.slug`, and without the join that read costs
one query per row — this is D-015-04.

Two pre-existing tests needed a look before writing anything new.
`test_a_concepts_row_carries_only_its_label` (`TestVocabularyDetailConceptList`)
asserted `soup.find("a") is None`, true under 014 when no concept page existed;
US-4's whole point is to make that false. Updated in place per D-015-04 — kept
every other assertion (no definition, no note, no identifier, no relation-text)
and replaced only the link assertion, renaming the test to say what it now
proves. `test_query_count_is_flat_regardless_of_how_many_concepts_the_vocabulary_holds`
(`TestVocabularyDetailConceptLabel`) was left untouched and re-run as the guard
against the new `object.scheme` read: still green with `select_related` in place.

Added `TestVocabularyDetailConceptListLinksToConceptPages` to test_views.py (2
tests: a concept in the full list, and one reached through a search-narrowed
result — US-4 scenarios 1 and 3 — each asserting the row's href and that
following it returns 200 with `response.context["object"]` equal to the target
concept). Added `TestConceptRowPartialLinksToItsOwnPage` to test_templates.py (2
tests, mirroring `TestRowPartialLinksToTheVocabulary`'s own source-level checks
for `conceptscheme_list_item.html`): the row partial's source reverses
`concept-detail` and contains no `local_url` reference.

Verified: RED first — `poetry run pytest tests/test_ui/test_views.py -q -k
"test_a_concepts_row_carries_only_its_label_and_a_link_to_its_own_page or
TestVocabularyDetailConceptListLinksToConceptPages" tests/test_ui/test_templates.py
-k TestConceptRowPartialLinksToItsOwnPage --no-cov` before any production change
— 4 failed (`assert None is not None`, two `StopIteration`s from no matching
anchor, and the source-scan assert), 1 passed (the "no local_url" half, true
before and after). Same command after the template and view change — 5 passed.
Then narrowest scope: `poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailConceptList
tests/test_ui/test_views.py::TestVocabularyDetailConceptListLinksToConceptPages
tests/test_ui/test_views.py::TestVocabularyDetailConceptLabel
tests/test_ui/test_templates.py -q --no-cov` — 24 passed. `poetry run ruff check`
and `poetry run ruff format --check` on the four changed files — clean (ruff
format rewrote the reformatted `select_related` chain in views.py once, then
verified clean). `poetry run mypy controlled_vocabularies/ui/views.py` — no
issues. `poetry run python manage.py makemigrations --check --dry-run` — no
changes detected (no model touched).

Next: T020 (a vocabulary's collections link to their own pages).
Watch: `test_nothing_links_to_a_collection` (`TestVocabularyDetailCollections`)
is the same shape of pre-existing "no link" assertion, for T020 to update the
same way — recorded ahead of time as D-015-04's forward pointer to D-015-05.

## 2026-08-24T20:41:00Z · Implementer US4 · T020

Did: `conceptscheme_detail.html`'s collections loop entry is now an anchor
(`{% url 'controlled_vocabularies_ui:collection-detail' vocabulary.slug
collection.slug %}`). Unlike T019's row partial, this loop renders inline in
the page template (not through `render_list_item`'s isolated context), so
`vocabulary` is already in context and the href needs no extra query — the
already-loaded `collections` queryset supplies `collection.slug` directly. The
`#142`-naming production comment came out, replaced by one naming the actual
mechanism (this is D-015-05).

`test_nothing_links_to_a_collection` (`TestVocabularyDetailCollections`)
predates this feature the same way T019's test did, for the same reason
(D-015-05): replaced with `test_each_collection_links_to_and_reaches_its_own_page`,
asserting the opposite — the entry's href reverses to the collection's page and
following it returns 200 with `response.context["object"]` equal to the
collection. Updated the class docstring to say the section now links, not just
names. Added `TestConceptSchemeDetailCollectionsLinkToTheirOwnPages` to
test_templates.py (2 tests, the same `TestRowPartialLinksToTheVocabulary`
source-level pattern used for T019): the page source reverses
`collection-detail` and contains no `local_url` reference.

Verified: RED first — `poetry run pytest
"tests/test_ui/test_views.py::TestVocabularyDetailCollections::test_each_collection_links_to_and_reaches_its_own_page"
tests/test_ui/test_templates.py::TestConceptSchemeDetailCollectionsLinkToTheirOwnPages
-q --no-cov` before the template change — 2 failed (`StopIteration` from no
matching anchor; the source-scan assert), 1 passed (the "no local_url" half).
Same command after the template change — 3 passed. Then narrowest scope:
`poetry run pytest tests/test_ui/test_views.py::TestVocabularyDetailCollections
tests/test_ui/test_templates.py -q --no-cov` — 23 passed. `poetry run ruff
check` and `poetry run ruff format --check` on the two changed test files —
clean. No production Python file changed, so no mypy/deptry run beyond
pre-commit's own. `poetry run python manage.py makemigrations --check
--dry-run` — no changes detected.

Next: none — Story US-4 (T019-T020) is complete.
Watch: nothing outstanding.
