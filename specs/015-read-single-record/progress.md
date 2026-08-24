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
