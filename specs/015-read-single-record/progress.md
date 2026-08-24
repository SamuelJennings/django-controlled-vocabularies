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
