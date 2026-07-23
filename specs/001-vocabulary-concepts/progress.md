# Progress: 001-vocabulary-concepts

Append-only run log. Newest last.

- 2026-07-23 — S0 INTAKE: grilled to shared understanding; issue #15 accepted, labelled `feature`.
- 2026-07-23 — S1 SPECIFY: spec.md (4 stories, FR-001–008, SC-001–005), decisions.md, requirements checklist. No unresolved clarifications.
- 2026-07-23 — S2 SETUP: epic #15 promoted (FS-001); stories #20–#23; branch pushed; draft PR #24; title lint green.
- 2026-07-23 — GATE_SPEC: approved by Sam.
- 2026-07-23 — S3 PLAN: plan.md, research.md (R1–R8), data-model.md, contracts/python-api.md, quickstart.md, tasks.md (T001–T013). Constitution Check passed (Article IX lifecycle bits deferred to #19 by ruling). Analyze: green, no CRITICAL. feature-state.json initialised (all tasks `todo`). Awaiting Plan gate.
- 2026-07-23 18:15 — US1 T001–T005 (Implementer, subagent). **Did**: T001 added `CONTROLLED_VOCABULARIES_BASE_URI` to `tests/settings.py`; T002 added `controlled_vocabularies/conf.py` (`get_base_uri()`, `DEFAULT_BASE_URI = "http://localhost:8000/vocabularies"`); T003 wrote failing `tests/test_scheme.py` (11 cases: slug-from-name, rename→slug, empty+whitespace name→ValidationError, non-Latin "Wärmefluss"→"wärmefluss", collision refused, uri composition/rename, `__str__`, delete); T004 implemented `ConceptScheme` (slug via `slugify(allow_unicode=True)`, empty→ValidationError, collision→ValidationError, `uri` property); T005 generated `0001_initial`. **Verified**: baseline `poetry run pytest` = 2 passed (green before start); T003 failed correctly with `ModuleNotFoundError: controlled_vocabularies.models`; after T004 `poetry run pytest tests/test_scheme.py` = 11 passed; full gate `poetry run pytest` = 13 passed, `ruff check .`/`ruff format --check .`/`mypy` all clean, `makemigrations --check --dry-run` = "No changes detected". **Next**: US2 (T006–T008) — `Concept` model + `test_concept.py` + `0002` migration.
