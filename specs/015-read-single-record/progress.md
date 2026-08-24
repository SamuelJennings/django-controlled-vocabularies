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
