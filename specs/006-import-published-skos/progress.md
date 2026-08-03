# Progress — 006 Import a published SKOS vocabulary from a file

Append-only log of stage transitions and gate outcomes.

## 2026-08-03

- **S0 INTAKE** — issue #50 grilled. Four questions, all answered: escrow deferred to its own
  feature sequenced with export; the file is the authority for which vocabulary is imported; the
  import is authoritative for records the file contains and silent about those it does not; a run
  applies in full or not at all, with a small fatal set. Feature statement confirmed. Issue
  labelled `accepted`.
- **S1 SPECIFY** — branch `006-import-published-skos` created. `spec.md` written: 6 user stories
  (2×P1, 3×P2, 1×P3), FR-001..018, SC-001..018. Clarify scan run and self-answered — five
  ambiguities resolved into the spec, rationale in `decisions.md` (D1–D8). Spec lint green: no
  unresolved markers, every FR carried by a story scenario, goal ids cited (G4, G6, G8).
- **S2 SETUP** — spec committed and pushed as `forge-aeo[bot]`. Issue #50 promoted to the epic in
  place (intake paragraph preserved). Story sub-issues #61–#66 created and linked, no lifecycle
  labels, milestone `v0.1.0`. Draft PR #67 opened by the bot, title byte-identical to the epic,
  `Closes` block covering the epic and all six stories, milestone set. `check-issue-titles` green.
- **Spec gate — APPROVED** by Sam (SamuelJennings), 2026-08-03, in session. Scope as specified,
  including the four self-resolved decisions surfaced in the brief: escrow deferred, language
  filtering landing here rather than in #51, blank-node identity fatal, and the imported
  vocabulary's default language taken from the file. Proceeding to S3 PLAN.

## 2026-08-03T20:00:03Z · Implementer US0 · T002

**Did**: Scaffolded the `controlled_vocabularies/exchange/` package (docstring-only `__init__.py`, no
re-exports yet) and its mirroring `tests/test_io/` directory, with a failing-first test that the
package imports and carries a module docstring. Created `tests/fixtures/` (empty; populated by
T005). Dropped the redundant `mypy_path = "controlled_vocabularies/"` mypy config entry — it made
the new `io/` package collide with the stdlib `io` module ("Source file found twice"); removing it
changes nothing else (mini-ADR: `decisions.md` D10).

**Verified**: `poetry run pytest -q` — 287 passed (285 baseline + 2 new). `poetry run ruff check .`
— all checks passed. `poetry run ruff format --check .` — 15 files already formatted. `poetry run
mypy` — success, 5 source files (baseline 4 + `io/__init__.py`). `poetry run deptry .` — no issues,
11 files scanned. `poetry run pre-commit run --all-files` — all hooks passed.

**Next**: T003 — `report.py` (`ImportReport`, `SetAsideEntry`, the reason vocabulary).

**Watch**: the `mypy_path` removal is repo-wide config, not story-scoped — flag it in review since
it touches the shared toolchain config rather than only this feature's new files.

## 2026-08-03T20:15:00Z · Implementer US0 · T003

**Did**: `controlled_vocabularies/io/report.py` — `ImportReport` (four buckets: `created`,
`updated`, `set_aside`, `absent_from_source`, plus `set_aside_by_reason()` for grouping/counting)
and `SetAsideEntry` (`reason`, `subject`, `params`, frozen, with a `render()` that substitutes at
call time rather than baking the message in at creation time). `SetAsideReason` is a
`TextChoices` closed vocabulary of eight reasons covering FR-014 and the spec's Key Entities
(language not configured, predicate not modelled, notation, mapping, missing relation end,
missing collection member, no preferred label in default language, vocabulary mismatch); fatal
findings (missing/blank-node identity) are deliberately excluded — D3/D8 fail the whole run for
those rather than setting them aside. Re-exported from `io/__init__.py`.

**Verified**: `poetry run pytest -q` — 317 passed (287 + 30 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format .` — 2 files reformatted (report.py, test_report.py) then
clean. `poetry run mypy` — success, 6 source files. `poetry run deptry .` — no issues, 12 files
scanned. `poetry run pre-commit run --all-files` — all hooks passed.

**Next**: T001+T004 together — declare `rdflib`/`defusedxml` and write `safety.py`'s pre-flight
scan in the same commit (deptry ordering rule).

**Watch**: none.

## 2026-08-03T20:35:00Z · Implementer US0 · T001/T004

**Did**: `controlled_vocabularies/io/safety.py` — `scan_rdf_xml(data: bytes)`, a pre-flight
`defusedxml.sax` scan (do-nothing content handler) that stands in front of `rdflib`'s RDF/XML
parser, which calls `xml.sax.make_parser()` itself and accepts no parser argument. Raises
`UnsafeRdfXmlError` (a `ValidationError` subclass, translatable with named placeholders) for a
document that declares any entity (`EntitiesForbidden` — covers both the internal-expansion bomb
and, since declaring is enough, an external-entity reference) or that points its DOCTYPE at an
external subset (`ExternalReferenceForbidden`); returns `None` untouched for an ordinary document.
Declared `defusedxml` as a runtime dependency in the same commit (T001), per Article VII.

Test fixtures added under `tests/fixtures/security/`: `entity_bomb.rdf` reinstates the exact
research.md R3 shape — 8 nested entity declarations (`e0`..`e8`), each the previous repeated 5
times from a 2-character base, matching R3's measured 781,250-character expansion — rather than a
mock; `external_entity.rdf` reinstates R3's own canary-file XXE probe; `external_dtd.rdf` is a
second, distinct route to the same untrusted-fetch problem (no entity declared, but the DOCTYPE
itself names an external system id); `ordinary.rdf` is a plain SKOS RDF/XML document with no DTD.

**Deviation** (decisions.md D11): tasks.md's T001 reads as declaring both `rdflib` and `defusedxml`
together. `rdflib` is not declared — nothing in Phase 0 imports it (Phase 0 stops before
`skos.py`/`mapping.py`, T006), and declaring it early failed `deptry` (`DEP002` unused dependency),
the exact case Article VII exists to catch. Only `defusedxml` is declared now; `rdflib` lands with
T006.

**Verified**: `poetry run pytest -q` — 321 passed (317 + 4 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 19 files already formatted. `poetry run mypy`
— success, 7 source files. `poetry run deptry .` — no issues, 13 files scanned (confirmed both with
`rdflib` declared, where it failed `DEP002`, and without, where it passed). `poetry run pre-commit
run --all-files` — all hooks passed.

**Next**: T005 — fixture vocabularies under `tests/fixtures/` (Turtle/RDF-XML/JSON-LD, re-import
edits, malformed fatal-path cases).

**Watch**: T006 must declare `rdflib` in its own commit alongside `skos.py`/`mapping.py` — flagged
here so it isn't missed at that stage exit.

## 2026-08-03T21:00:00Z · Implementer US0 · T005

**Did**: `tests/fixtures/skos/` — a "Rock types" vocabulary (`rocks.ttl` canonical, `rocks.rdf` and
`rocks.jsonld` hand-written to the same triples, not auto-generated, for readability; verified
isomorphic across all three via `rdflib.compare.isomorphic`, 53 triples each, including the ordered
collection's member sequence). Carries multilingual preferred labels (en/de/fr), an alternative and
a hidden label, all seven `ConceptNote.Kind` values spread across concepts, a broader/narrower pair,
a symmetric related pair, and an unordered plus an ordered collection.

`rocks_updated.ttl` — one edited copy carrying all four US-2 re-import edits at once (matching the
spec's own Independent Test framing): granite's preferred label corrected, its alternative label
removed, quartz dropped from the file entirely (its related edge and collection membership go with
it), the ordered collection's member sequence changed. Edited copies are Turtle-only — format
parsing correctness is already covered by the base vocabulary's three serializations.

`blank_node_concept.ttl`, `blank_node_collection.ttl`, `refused_uri_scheme.ttl` — the fatal-path
fixtures. **Deviation** (decisions.md D13): the brief named a third case, "missing identifier",
distinct from "blank-node concept". Verified empirically that this isn't buildable as a stable,
parser-context-independent fixture — `rdf:about=""` (and Turtle/JSON-LD's equivalent empty-relative-
IRI forms) resolves against the parse call's default base (the file's own path) rather than to a
literal empty identifier, unless a future `publicID` override changes that. Built
`blank_node_collection.ttl` instead — the same blank-node rule applied to a `Collection`, which is
directly named in the spec (US-5 acceptance 5) and tasks.md (T030) — so all three fatal fixtures are
real, spec-grounded material rather than one being invented to round out a count.

`rdflib` declared as a dev dependency (not runtime) for this task alone — decisions.md D12 — used
only by `tests/test_exchange/test_fixtures.py`; confirmed `deptry` does not flag it (`tests/` is already
excluded from its scan, and unused dev-group packages aren't what `DEP002` checks for, matching the
existing `pytest`/`ruff`/`mypy` pattern). Also ran `makemigrations --check --dry-run`: no changes
detected, confirming Phase 0 added no schema drift.

**Verified**: `poetry run pytest -q` — 339 passed (321 + 18 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 20 files already formatted. `poetry run mypy` —
success, 7 source files (fixtures/tests untouched by mypy's `files` scope). `poetry run deptry .` —
no issues, 13 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Next**: Phase 0 complete. T006+ (Phase US-1, `skos.py`/`mapping.py`, the reader itself) is out of
this Implementer's scope.

**Watch**: T006 promotes `rdflib` from the dev group to `[tool.poetry.dependencies]` in the same
commit as the code that first imports it at runtime (decisions.md D12, reiterated from the
T001/T004 entry above).

## Phase 0 review (orchestrator)

**Did**: reviewed the Implementer's five tasks, reproduced the mypy collision behind D10 by
restoring `mypy_path = "controlled_vocabularies/"` and re-running mypy, and overturned that
decision. The package is renamed `controlled_vocabularies/io/` → `controlled_vocabularies/exchange/`
and `tests/test_io/` → `tests/test_exchange/`, with `mypy_path` restored. Rationale in the rewritten
D10: three sibling packages carry the same setting, so dropping it here is silent toolchain drift,
and a subpackage shadowing a stdlib top-level name will keep colliding with other path-resolving
tools. D11 and D12 (the `rdflib` declaration ordering) are accepted as written. D13's fixture
substitution is accepted — the empirical finding that `rdf:about=""` resolves against the parse
base is correct, and `blank_node_collection.ttl` is grounded in US-5 acceptance 5.

**Verified after the rename, with `mypy_path` present**: `poetry run mypy` — success, 7 source
files. `poetry run pytest -q` — 339 passed. `poetry run ruff check .` — all checks passed.
`poetry run ruff format --check .` — 20 files already formatted. `poetry run deptry .` — no issues.

**Watch**: plan.md and tasks.md now say `exchange/`; any brief quoting `io/` is stale.
