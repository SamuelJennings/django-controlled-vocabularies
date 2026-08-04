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

## 2026-08-03T21:30:00Z · Implementer US1 · T006

**Did**: `controlled_vocabularies/exchange/skos.py` — `_read_graph(file, *, serialization=None)`:
resolves the serialization from the caller or `rdflib.util.guess_format`, restricted to the
three FR-002 names (`turtle`/`xml`/`json-ld` — an explicit but unsupported format, e.g. `n3`, is
refused just as an undetermined one is); routes RDF/XML through T004's `scan_rdf_xml` pre-flight
before rdflib reads the file itself. Raises the new `SkosImportError` (a `ValidationError`
subclass, translatable, named placeholders) for a missing file, an undetermined/unsupported
serialization, or an unparseable one. `mapping.py` lands alongside it per decisions.md D11/D12 —
currently just the `SKOS` namespace constant; no predicate table yet, since Phase US-1 reads
fixed predicates directly and nothing yet needs a lookup table (Article II — no speculative
abstraction). `rdflib` moved from `[tool.poetry.group.dev.dependencies]` to
`[tool.poetry.dependencies]` in this commit, ran `poetry lock`.

**Deviation** (renamed a parameter, no decisions.md entry needed — mechanical): tasks.md/plan.md
never fixed the caller-stated-serialization parameter's name; `format` was the natural first
choice but `ruff` (`A002`) flags it as shadowing the builtin, so it is `serialization` instead.

**Verified**: `poetry run pytest -q` — 351 passed (339 + 12 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 23 files formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python
-m django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.
`poetry run pre-commit run --all-files` — all hooks passed (after `poetry lock`, required once
`rdflib` moved dependency groups).

**Next**: T007 — the vocabulary: `import_skos()`'s public entry point, matched via `get_by_uri`,
created/updated/target-mismatch/no-target handling.

**Watch**: none.

## 2026-08-03T21:50:00Z · Implementer US1 · T007

**Did**: `import_skos(file, *, serialization=None, scheme=None)` — the public entry point,
wrapping the whole run in `transaction.atomic()`. `_resolve_scheme()` reads the file's declared
`skos:ConceptScheme` (deterministically the lexicographically-first when a file somehow declared
more than one — not itself a tested case), matches or creates the `ConceptScheme` via
`get_by_uri` (research.md R6), and writes its `name`/`static_uri`. A caller-named `scheme` target
is used directly when the file agrees with it, or is fatal (`VOCABULARY_TARGET_MISMATCH`) when it
does not; a file declaring none at all is fatal (`VOCABULARY_UNDETERMINED`, subject = the file's
own path, since there is no RDF node to name) unless a target was given, in which case that
target is used untouched.

`report.py` gains `FatalReason`/`FatalFinding` (mirrors `SetAsideReason`/`SetAsideEntry`'s shape,
kept as a separate closed vocabulary per decisions.md D3/D8 — a fatal finding is never a
set-aside reason) and `ImportReport.fatal`/`add_fatal()`. `SkosImportFailed` (skos.py) is the
exception a fatal run raises — it carries the run's (partial) `ImportReport` so a caller can
inspect exactly what was wrong, per FR-004's "MUST fail the run and be named in the report",
even though `transaction.atomic()` has already rolled back everything written before the raise.

`_identify()` checks any RDF node's usable identity: a `BNode` is always fatal
(`MISSING_IDENTITY`, decisions.md D3), a `URIRef` is checked through the models' own
`validate_static_uri` (`REFUSED_IDENTITY` on failure — the same rule the models enforce on save,
reused rather than reimplemented). `_first_literal()` picks a literal deterministically
(lexicographically first), never "whichever rdflib yields first" — needed here for the scheme's
`name` and reused by T008/T009. New fixture `tests/fixtures/skos/no_scheme_declared.ttl`: two
concepts, no `skos:ConceptScheme` at all, for the "declares no vocabulary" fatal/succeeds-with-a-
target pair.

**Verified**: `poetry run pytest -q` — 373 passed (351 + 22 new: 12 in `test_skos.py`'s new
`TestImportSkosVocabulary`, 10 in `test_report.py`'s new fatal-reason coverage). `poetry run ruff
check .` — all checks passed. `poetry run ruff format --check .` — 23 files formatted. `poetry
run mypy` — success, 9 source files (two rounds of fixes: `rdflib.term.Node` rather than
`Identifier` as the RDF-term type hint — `graph.subjects()`'s actual return type — and `sorted(...,
key=str)` rather than bare `sorted(...)` over a mixed node iterable). `poetry run deptry .` — no
issues, 15 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Next**: T008 — the imported vocabulary's default language (FR-005): declared language, else
commonest preferred-label language, else site default.

**Watch**: the concept walk (T009) is not wired into `import_skos()` yet — a successful T007-era
call writes at most the one `ConceptScheme` row and never touches `Concept`.

## 2026-08-03T22:05:00Z · Implementer US1 · T008

**Did**: `_determine_default_language()` (decisions.md D4, FR-005): the vocabulary's own declared
language when its `skos:prefLabel` carries exactly one and the site is configured for it; else
the commonest language among `concept_nodes`' own `skos:prefLabel` values (ties broken by
language code, for a result that doesn't depend on graph iteration order); else `""`, which
`ConceptScheme.default_language` already treats as "fall back to `effective_default_language`" —
R1's own mechanism, reused rather than reimplemented (D4 names this explicitly). `import_skos()`
now also computes `concept_nodes` (sorted, deterministic) ahead of T009's own use of it, since
T008's algorithm needs to see the concepts' labels too. `_resolve_scheme()`'s scheme-`name`
selection now prefers the resolved default language's own label, falling back to any language
when the scheme carries none in it (unchanged outcome for `rocks.ttl`, since English is both
declared and configured).

New fixtures: `french_vocabulary.ttl` (declares itself in French, a configured non-default
language) and `unconfigured_language_vocabulary.ttl` (declares itself in Spanish, which the test
site's `LANGUAGES` does not include at all — falls back to the site default).

**Verified**: `poetry run pytest -q` — 375 passed (373 + 2 new in `test_skos.py`'s new
`TestImportedVocabularyDefaultLanguage`). `poetry run ruff check .` — all checks passed. `poetry
run ruff format --check .` — 23 files formatted. `poetry run mypy` — success, 9 source files
(one round of fixes: `graph.objects()` yields the general `rdflib.term.Node`, which has no
`.language` attribute — only `rdflib.Literal` does; added `_label_languages()` as the one place
that narrows with `isinstance`, rather than repeating the check at each call site). `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: T009 — concepts: created inside the vocabulary, each holding its published identifier
and its default-language preferred label; scheme membership via `inScheme`/`topConceptOf`/
`hasTopConcept`; a concept claiming a different vocabulary set aside and reported.

**Watch**: none.

## 2026-08-03T22:25:00Z · Implementer US1 · T009

**Did**: `_import_concepts()` wired into `import_skos()`, walking `concept_nodes` (already computed
at T008) in the same deterministic order. Each concept's identity is checked with the same
`_identify()`/`_FatalIdentity` the vocabulary itself uses (D3 applies identically to a concept).
`_conflicting_scheme_ref()` checks all three SKOS scheme-membership predicates
(`skos:inScheme`/`skos:topConceptOf` on the concept, `skos:hasTopConcept` from the scheme) against
the target scheme's own URI; a concept with no scheme reference at all is read as belonging to the
vocabulary being imported (decisions.md D16 — new, since neither the spec nor tasks.md said what
"no reference at all" should do), and one naming a *different* scheme is set aside
(`VOCABULARY_MISMATCH`) rather than imported. `_preferred_label_in()` picks the default-language
`skos:prefLabel` deterministically. A matched or new `Concept` is written through the model's own
`save()` (slug auto-derives from `label` for now; T010 layers deterministic disambiguation on top).

**Deviation** (decisions.md D17, new): implemented "a concept with no preferred label in the
default language is set aside" now, rather than leaving it for T022 (Phase US-3) as `tasks.md`'s
phase split implies. FR-006 — T009's own governing requirement — states this in the same sentence
as concept creation itself, and the alternative was an unhandled crash on ordinary real-world
input. One fixture/test added (`no_default_language_label.ttl`); T022 is free to extend without
needing new implementation.

Also recorded, retroactively, two decisions this task's work exposed as unsettled but that were
actually taken back at T006/T007: **D14** (`serialization`, not `format`, as the parameter name —
`ruff` `A002`) and **D15** (`import_skos`'s target-vocabulary parameter takes a `ConceptScheme`
instance, not a string — `#52` resolves whatever a curator types before calling in).

Tightened two `TestImportSkosVocabulary` assertions from T007 (`report.created ==
[ROCKS_URI]`/`report.updated == [ROCKS_URI]`) to membership checks (`ROCKS_URI in report.created`),
since those buckets now also carry the concepts this task's `_import_concepts()` adds — the same
report object, exercised further by the next task in the same phase, not a behaviour regression on
what T007 itself asserts.

New fixtures: `mixed_scheme_membership.ttl` (exercises all three scheme-membership predicates plus
a concept explicitly claiming a different vocabulary) and `no_default_language_label.ttl` (a
concept with no preferred label in the vocabulary's declared default language, "en").

**Verified**: `poetry run pytest -q` — 380 passed (375 + 5 new in `test_skos.py`'s new
`TestImportConcepts`, all four gate commands re-run clean afterward too). `poetry run ruff check .`
— all checks passed. `poetry run ruff format --check .` — 23 files formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m
django makemigrations --check --dry-run --settings=tests.settings` — no changes detected. `poetry
run pre-commit run --all-files` — all hooks passed.

**Next**: T010 — slugs: derived by the model's own rule, disambiguated by a deterministic suffix
within the vocabulary.

**Watch**: none.

## 2026-08-03T22:40:00Z · Implementer US1 · T010

**Did**: `_assign_unique_slug()` (FR-007, decisions.md D6): computes `slugify(label)` and appends a
deterministic numeric suffix (`-2`, `-3`, …) only when that value already belongs to a *different*
concept in the same scheme — `Concept.save()`'s own auto-derivation only refuses a collision, never
disambiguates it, which is correct for curator-authored content but not for a published file where
two source concepts commonly share a preferred label. `slug_is_manual` is set so a later plain
`save()` never silently re-derives over the computed value; the importer itself recomputes it fresh
on every re-import, so a slug still moves on a rename (D6) — it is importer-managed, not
curator-pinned the way a curator's own manual slug is. `concept_nodes`' stable, URI-sorted
processing order (already established at T008/T009) is what makes which of two colliding concepts
gets the plain slug deterministic and stable across repeated imports of the identical file.

New fixture: `duplicate_slug.ttl` — two concepts, distinct identifiers (`quartz-a`/`quartz-b`,
alphabetically ordered on purpose), both preferring "Quartz".

**Verified**: `poetry run pytest -q` — 383 passed (380 + 3 new in `test_skos.py`'s new
`TestConceptSlugs`). `poetry run ruff check .` — all checks passed. `poetry run ruff format
--check .` — 23 files formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .`
— no issues, 15 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Next**: T011 — fatal findings and atomicity: an absent identifier, a blank-node concept, and an
identifier the identity rules refuse each fail the run; every problem in a file is collected rather
than raised at the first; the transaction rolls back.

**Watch**: none.

## 2026-08-03T22:55:00Z · Implementer US1 · T011

**Did**: no new production code. `_resolve_scheme()`/`_import_concepts()` already collect every
fatal finding into `report.fatal` rather than raising at the first (T007/T009), and `import_skos()`
already raises `SkosImportFailed` only once nothing further can be checked, inside
`transaction.atomic()` (T007) — the collect-then-raise-once, roll-back-on-raise pattern
research.md R7 calls for was built in from the start rather than deferred to this task. T011 is
therefore pure test coverage: a blank-node concept and a refused-URI-scheme concept each proven to
fail the run and write nothing; `multiple_fatal_problems.ttl` (new fixture — a blank-node concept,
a refused-scheme concept, and one perfectly ordinary concept together) proving both fatal findings
are reported in one run rather than stopping at the first, and that the rollback undoes a scheme
field write made *before* the fatal concepts were even reached (an existing scheme's `name` is
provably unchanged after the failed run), not only concept creation.

**Verified**: `poetry run pytest -q` — 388 passed (383 + 5 new in `test_skos.py`'s new
`TestFatalFindingsAndAtomicity`). `poetry run ruff check .` — all checks passed. `poetry run ruff
format --check .` — 23 files formatted. `poetry run mypy` — success, 9 source files. `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: T012 — the report, populated by a real run: created and updated records and set-aside
entries all present with their reasons, as data.

**Watch**: none.

## 2026-08-03T23:00:00Z · Implementer US1 · T012

**Did**: `TestReportPopulatedByARealRun` — a first import against an empty database reports every
record (scheme + concepts) as created and nothing as updated, with no duplicate URIs in the
bucket; a re-import reverses that (everything updated, nothing created); a set-aside entry
(`no_default_language_label.ttl`) carries its reason/subject/params directly, groupable via
`set_aside_by_reason()` without ever rendering a message; a single run against a pre-seeded
partial state (`mixed_scheme_membership.ttl`, one concept already present under the file's
scheme) produces created, updated, *and* set-aside entries together correctly.

**Deviation** (decisions.md D18, new): writing the last of those tests surfaced a real bug, not a
test-authoring accident. `_resolve_scheme` (T008) unconditionally recomputed and assigned
`default_language` on *every* matched scheme, including one that already had concepts from an
earlier run — colliding with `ConceptScheme.save()`'s own R1 guard, which refuses to change
`default_language` once a scheme has concepts (it anchors their identity). The collision raised an
undecorated `django.core.exceptions.ValidationError` straight out of the transaction, bypassing
this feature's own translatable-report contract entirely (FR-003/FR-015) — not a set-aside, not a
fatal finding, just a crash. Fixed: `default_language` is now set from the file only when the
scheme is being freshly created (`row.pk is None`, so it provably has no concepts yet); an
existing scheme's already-frozen value is left untouched, which is also the only reading of D4's
algorithm consistent with R1's own guard (that value cannot legitimately have changed since first
frozen). The scheme-name language selection now reads `row.effective_default_language` instead of
a value this function only computes on create. One dedicated regression test added directly
(`test_default_language_is_not_recomputed_for_a_scheme_that_already_has_concepts`) alongside the
`TestReportPopulatedByARealRun` coverage.

**Verified**: `poetry run pytest -q` — 393 passed (388 + 5 new: 4 in `test_skos.py`'s new
`TestReportPopulatedByARealRun`, 1 regression test in `TestImportedVocabularyDefaultLanguage`).
`poetry run ruff check .` — all checks passed. `poetry run ruff format --check .` — 23 files
formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15
files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Phase US-1 complete (T006–T012).** `import_skos()` reads a Turtle/RDF-XML/JSON-LD file, resolves
or refuses the vocabulary it declares, imports its concepts with deterministic slugs, collects
every fatal and set-aside finding, and rolls back the whole transaction on any fatal one. `models.py`
was not touched. T013+ (US-2, re-import behaviour) is the next Implementer's scope — this
Implementer stops here.

**Watch**: US-2's re-import work should read decisions.md D18 before touching `_resolve_scheme`
again — the guard it works around (R1's frozen-`default_language`-once-populated rule) is exactly
the kind of thing US-2's "the file is authoritative for what it contains" (D5) could collide with
a second time if a vocabulary's *declared* default language genuinely changes between two
publications of the same file. That scenario is not handled here (D18's own "Revisit if").

## Phase US-1 review (orchestrator)

**Did**: reviewed T006–T012 and re-ran the full gate independently — 393 passed, mypy/ruff/deptry
clean, `models.py` confirmed untouched against the phase base. D14–D18 accepted as written; D18's
fix (default language frozen once a scheme has concepts) is correct against R1's own guard.

One defect fixed, recorded as D19: the file's vocabulary was chosen as the lexicographically-first
declared `skos:ConceptScheme`, so a file naming a foreign vocabulary whose identifier sorted first
would have imported the wrong one. Now chosen by which declared vocabulary the file's own concepts
belong to, with a genuine tie and no named target fatal (`VOCABULARY_AMBIGUOUS`). New fixture
`two_vocabularies.ttl`; the order-independence test fails against the old rule.

Also made `tests/test_exchange/test_fixtures.py` discover fixtures by walking the directory rather
than a hand-kept list — six fixtures added during US-1 were not in it — with a guard test so an
empty directory cannot parametrize to nothing and read as a pass.

**Verified**: `poetry run pytest -q` — 409 passed. ruff check, ruff format --check, mypy (9 source
files), deptry, `makemigrations --check --dry-run`, `pre-commit run --all-files` — all clean.

**Carried to US-2**: D18's open question is now required work, not a suggestion. A re-imported file
whose declared default language differs from the one frozen on the existing vocabulary must be
reported as set aside, not silently ignored — silence is what D1 forbids. D17's `NO_PREFERRED_LABEL`
set-aside is minimal and belongs to T022 to finish.

## 2026-08-04T09:50:00Z · Implementer US2 · T013

**Did**: `TestIdempotentReimport` in `test_skos.py` — two tests: every scheme and concept primary key
is stable across two identical runs of `rocks.ttl` (5 concepts, no duplication); a `ConceptRelation`
created directly between two runs (granite→basalt, `BROADER`) still resolves to the same rows after
the second run. No new production code — `import_skos()`'s upsert-by-`static_uri` path (`get_by_uri`
matching, T007/T009) already gives every record a stable PK across an identical re-run, so both tests
passed on first execution. This is confirmatory acceptance coverage for FR-004/FR-013's already-built
behaviour, the same shape T011 was for atomicity — not every task in this phase needs new code, and
forcing a contrived failure first would mean writing a deliberately-broken test rather than a real one.

**Verified**: `poetry run pytest -q` — 411 passed (409 + 2 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 23 files already formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m
django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Next**: T014 — authoritative update for records the file contains.

**Watch**: T014's acceptance text (tasks.md) names alternative-label/note/relationship removal
alongside the preferred-label correction; those predicates are not read by `import_skos()` at all yet
(US-3/US-4 scope, explicitly prohibited here) — see the decision recorded at T014 for how that's
scoped.

## 2026-08-04T10:05:00Z · Implementer US2 · T014

**Did**: One test — `rocks.ttl` imported, then `rocks_updated.ttl` (T005's re-import edit) imported —
asserting granite's `Concept.label` corrects to "Granite (revised)", the concept keeps the same
primary key, and the URI lands in `report.updated` not `report.created`. No production change: T009
already writes `concept.label = label` on every match, not only on create, so FR-013's field-level
authority for a corrected preferred label was already general.

**Deviation** (decisions.md D20, new): scoped T014 to only the predicate `import_skos()` currently
reads (`skos:prefLabel`). Tasks.md's T014 also names an alternative label, a note, and a relationship
the publisher removed, all present in `rocks_updated.ttl`'s edits — but the importer reads none of
`skos:altLabel`, any note predicate, or `skos:related`/`skos:broader` yet (US-3/US-4, explicitly
prohibited in this brief). "Removed on re-import" presupposes "imported in the first place"; those
assertions are deferred to the stories that build those read paths, which inherit the same fixture
pair with nothing further to add to it.

**Verified**: `poetry run pytest -q` — 412 passed (411 + 1 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 23 files already formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m
django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Next**: T015 — records the file no longer mentions: untouched, named in the report's
absent-from-source bucket.

**Watch**: `report.absent_from_source` exists (T003) but nothing populates it yet — T015 is genuine
new production code, unlike T013/T014.

## 2026-08-04T10:20:00Z · Implementer US2 · T015

**Did**: `_import_concepts()` now tracks every successfully-identified concept URI it sees this run
(`mentioned_uris`, added the moment `_identify()` succeeds — before the vocabulary-mismatch/
no-preferred-label checks, so a concept set aside for either reason still counts as "mentioned", not
absent) and, after the walk, reports every existing concept of `target_scheme` whose URI was never
seen as `absent_from_source` — left completely untouched, only named (FR-013). Two tests:
`rocks_updated.ttl` drops quartz entirely; quartz keeps its primary key and label, is named in
`report.absent_from_source`, is in neither `created` nor `updated`, and a `ConceptRelation` created
against it *between* the two runs (basalt→quartz, standing in for D5's "something downstream may
already reference it") still resolves afterward. A second test confirms a still-mentioned concept
(granite) is never reported absent merely because it happened to update.

**Verified**: `poetry run pytest -q` — 414 passed (412 + 2 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 23 files already formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m
django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Next**: T016 — the vocabulary's own name and description update from the file, identifier
unchanged; also D22 (carried from US-1 review): a re-imported file whose declared default language
conflicts with the one frozen on an existing scheme must be reported as set-aside.

## 2026-08-04T10:40:00Z · Implementer US2 · T016

**Did**: two pieces, both in `_resolve_scheme`. (1) `row.description` is now read from
`DCTERMS.description` the same way `name` is read from `SKOS.prefLabel` (effective default language
first, any language as fallback), written unconditionally including to `""` when the file no longer
carries one (decisions.md D21 — SKOS has no scheme-level description predicate, so this reuses the
`dcterms:description` alias CONTEXT.md already names for a concept's own `definition`).
`mapping.py` gains `DCTERMS = rdflib.namespace.DCTERMS`, a built-in namespace object, no new
dependency. New fixtures: `vocabulary_metadata.ttl`, `vocabulary_metadata_updated.ttl` (name and
description both changed, identifier unchanged), `vocabulary_metadata_description_removed.ttl`
(description predicate dropped entirely). (2) D22 (carried from the US-1 review): `_resolve_scheme`
now always computes the file's declared default language, even for a matched existing scheme; when
it disagrees with the scheme's `effective_default_language` a new `SetAsideReason.DEFAULT_LANGUAGE_FROZEN`
set-aside entry is added, naming the declared and frozen values — `default_language` itself stays
untouched (D18's guard is unchanged), only the silence is fixed. `test_report.py`'s
`_EXAMPLE_PARAMS` table (T003's parametrized "every reason renders" test) gets the new reason's
example params, the same extension T007 made for `FatalReason`.

**Verified**: `poetry run pytest -q` — 425 passed (414 + 11 new: 5 in `test_skos.py`'s
`TestVocabularyMetadataUpdate`/`TestFrozenDefaultLanguageConflictIsReported`, plus the parametrized
`test_report.py` case for the new reason and its fixture-discovery entries). `poetry run ruff check .`
— all checks passed. `poetry run ruff format --check .` — 23 files already formatted. `poetry run
mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run
python -m django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Next**: T017 — a failed re-import against an already-populated database leaves it exactly as it
was, including rolling back an *update* to an existing concept, not only a creation.

**Watch**: none.

## 2026-08-04T10:55:00Z · Implementer US2 · T017

**Did**: new fixture `reimport_rolls_back_an_update.ttl` — the "rocks" scheme, granite with a label
that must not land, and a blank-node concept (fatal, D3). One test: import `rocks.ttl`, then a
failed re-import of that fixture, asserting granite's label, primary key, and total concept count
are exactly as before, the scheme's `name` is unchanged, and the ghost concept was never created. No
production change: `import_skos()` already wraps the whole run — vocabulary resolution and every
concept write, create or update alike — inside one `transaction.atomic()` block (T007), and only
raises `SkosImportFailed` once nothing further can be checked (T011), so an update mid-run rolls
back exactly as a creation does. This is the third task this phase to pass on first execution
without new code (with T013, T014), each proving a piece of FR-013's upsert contract that T006-T012
already built generally rather than for the first-import case alone.

**Verified**: `poetry run pytest -q` — 427 passed (425 + 2: 1 new test, 1 new fixture-discovery
case). `poetry run ruff check .` — all checks passed. `poetry run ruff format --check .` — 23 files
already formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues,
15 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Phase US-2 complete (T013–T017).** Re-running `import_skos()` on an unchanged file duplicates
nothing; a corrected preferred label, and a vocabulary's own name and description, land on re-import
while identifiers stay fixed; a concept the file drops is left untouched and named in
`report.absent_from_source`; a failed re-import rolls back an update exactly as it rolls back a
creation. D18's silent skip of a frozen `default_language` conflict is now reported (D22). `models.py`
was not touched. Deferred to US-3/US-4 by design (decisions.md D20): alternative-label, note, and
relationship import — and therefore their removal on re-import — do not exist yet to defer *from*;
`rocks_updated.ttl`'s edits to those predicates are already staged and waiting for those stories.

**Watch**: US-3's Implementer should read decisions.md D20 and D21 before starting — D20 explains why
`rocks_updated.ttl`'s alt-label/note edits are untested here and what's expected of the story that
finally reads them; D21 sets the `dcterms:*` alias precedent (scheme description → concept
definition) a note-kind mapping may want to follow for its own foreign-predicate aliases.

**Watch**: none.

## 2026-08-04T11:10:00Z · Implementer US3 · T018

**Did**: `mapping.py` gains `LABEL_PREDICATES` (`skos:prefLabel`/`altLabel`/`hiddenLabel` ->
`ConceptLabel.Kind`). `skos.py`'s new `_import_labels()` writes every one of a concept's labels
through `Concept.add_label` (research.md R5), replacing whatever the concept already held — a
label carries no identifier of its own to upsert by, unlike the concept itself, so the file's
current content is written fresh on every run rather than diffed against what was there before.
The preferred label in the vocabulary's effective default language is skipped: it is already
`Concept.label` (T009), and `ConceptLabel.clean()` refuses a second preferred row in that language,
so the importer must not attempt one either. Wired in through a new `_import_concept_content()`,
called once per created-or-updated concept right after `concept.save()` — a thin wrapper today,
built to grow one call per US-3 task (T019, T021 add to it next) rather than threading each new
piece of concept content through `_import_concepts()` directly.

Language filtering is deliberately not built yet — every fixture this task reads from already
uses a configured language, and tasks.md scopes that filtering to T020 as its own increment (the
brief for T020 asks for a considered choice between filtering ahead of the write and catching the
model's own refusal, which is exactly the kind of decision worth its own task rather than folded
in here as a side effect).

**Verified**: `poetry run pytest -q` — 431 passed (427 + 4 new in `test_skos.py`'s new
`TestConceptLabels`). `poetry run ruff check .` — all checks passed. `poetry run ruff format
--check .` — 21 files already formatted. `poetry run mypy` — success, 9 source files. `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: T019 — notes: the definition and the six SKOS documentary note kinds, each with its
language, via `Concept.add_note`.

**Watch**: `rocks_updated.ttl` does not yet drop a note from a concept that stays present — only
granite's alternative label and quartz's whole removal are covered, so T018's own carried case
(decisions.md D20) had fixture material to test against, but T019's equivalent carried case does
not yet. Recorded as a new decision (D24) rather than left implicit.

## 2026-08-04T11:25:00Z · Implementer US3 · T019

**Did**: `mapping.py` gains `NOTE_PREDICATES` (the seven SKOS documentary-note predicates ->
`ConceptNote.Kind`, `definition` included). `skos.py`'s new `_import_notes()` writes every one of a
concept's notes through `Concept.add_note` (research.md R5), replacing whatever the concept already
held — the same full-replace rule and rationale `_import_labels` (T018) established, reused rather
than duplicated. Wired into `_import_concept_content()` alongside the T018 label call.
`dcterms:description` as a `definition` alias is deliberately not built here — tasks.md scopes that
normalisation, and the report entry FR-009 requires for it, to T021.

decisions.md D24 (new): `rocks_updated.ttl` carried no case of "a note removed from a concept that
stays present" — the fixture's four existing edits don't include one, only quartz's whole removal,
which is a different case (absent-from-source, already covered by T015). Extended the fixture with a
fifth edit — basalt's `example` note dropped — checked against every existing test reading that
fixture to confirm none inspects notes and none is affected.

**Verified**: `poetry run pytest -q` — 433 passed (431 + 2 new in `test_skos.py`'s new
`TestConceptNotes`). `poetry run ruff check .` — all checks passed. `poetry run ruff format .` — 1
file reformatted (`test_skos.py`) then clean. `poetry run mypy` — success, 9 source files. `poetry
run deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected.

**Next**: T020 — a label or note in a language the site is not configured for: stored nowhere,
named in the report with its language and a count.

**Watch**: none.

## 2026-08-04T11:35:00Z · Implementer US3 · T020

**Did**: `_import_labels()` and `_import_notes()` now check each value's language against
`settings.LANGUAGES` before calling `Concept.add_label`/`add_note` at all, rather than calling
unconditionally and catching the model's own `ValidationError` refusal. An unconfigured-language
value is set aside (`SetAsideReason.UNCONFIGURED_LANGUAGE`, naming the language) one entry per
value — two alternative labels and a note in the same unconfigured language on one concept produce
three separate entries, so a caller counts them via `report.set_aside_by_reason()` without the
importer needing to pre-aggregate. New fixture `unconfigured_language_values.ttl`: a concept with a
configured-language preferred label plus two alternative labels and a scope note all in Spanish,
which the test site's `LANGUAGES` does not include.

decisions.md D25 (new): filtering ahead of the write, not catching the model's refusal, chosen for
three reasons — the exception isn't shaped to isolate "wrong language" from any other row defect a
future `clean()` rule might add, a caught exception per attempt still needs the same per-value loop
this importer already has, and Article XI/D2 both already call this filtering "mechanical," which a
plain membership check is and a caught exception is not.

**Verified**: `poetry run pytest -q` — 436 passed (433 + 2 new in `test_skos.py`'s new
`TestUnconfiguredLanguageValuesAreSetAside`, plus 1 new fixture-discovery case). `poetry run ruff
check .` — all checks passed. `poetry run ruff format --check .` — 21 files already formatted.
`poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned.
`poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` — no
changes detected.

**Next**: T021 — notation, mappings, and unmodelled predicates set aside and reported; the
`dcterms:description`-as-`definition` normalisation reported, never applied silently.

**Watch**: none.

## 2026-08-04T11:55:00Z · Implementer US3 · T021

**Did**: `mapping.py` gains `MAPPING_PREDICATES` (the six SKOS mapping predicates ->
their CURIEs). `report.py` gains a fourth reason vocabulary, `NormalizedReason`
(one member so far, `FOREIGN_DEFINITION`), its own `NormalizedEntry` dataclass, and
`ImportReport.normalized`/`add_normalized()` — kept apart from `SetAsideReason`/`set_aside`
because a normalised value *was* stored, just not verbatim under the file's own predicate
(decisions.md D26). `skos.py`'s new `_import_unheld_values()` sets aside a `skos:notation`
(`NOTATION`), each of the six mapping predicates (`MAPPING`, naming the predicate's CURIE), and
any predicate outside the SKOS namespace this module does not otherwise handle
(`UNMODELLED_PREDICATE`, naming the predicate's own URI) — one entry per value, not merged.
`_import_notes()` now also reads `dcterms:description` as a concept's definition when the concept
carries no `skos:definition` of its own in that language, reporting the substitution via
`add_normalized` rather than applying it silently (FR-009). decisions.md D27 (new): a SKOS
predicate this importer doesn't read yet (`broader`/`narrower`/`related`/`member`/`memberList`) is
deliberately *not* reported as unmodelled — the models do have a place for it, just not built yet
(US-4/US-5) — checked against `rocks.ttl`'s own baseline (`report.set_aside == []`), which carries
all of those predicates and would have broken under a broader "everything unconsumed" walk.

New fixture `unmodelled_and_normalised_values.ttl`: a "widget" concept carrying a notation, a
`skos:exactMatch`, and a custom non-SKOS predicate; a "gadget" concept carrying only
`dcterms:description`, no `skos:definition` of its own.

**Verified**: `poetry run pytest -q` — 451 passed (436 + 15 new: 7 in `test_skos.py`'s new
`TestUnheldValuesAndNormalisation`, 7 in `test_report.py`'s new `TestImportReportNormalizedBucket`/
`TestNormalizedReasonVocabulary`/`TestNormalizedReasonIsDisjointFromSetAsideAndFatal`, plus 1
fixture-discovery case). `poetry run ruff check .` — all checks passed (one `B007` unused-loop-
variable fix along the way). `poetry run ruff format .` — 1 file reformatted (`test_report.py`)
then clean. `poetry run mypy` — success, 9 source files (one fix: renamed a reused loop variable
so mypy did not infer a narrower type from an earlier loop in the same function). `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected.

**Next**: T022 — a concept with no preferred label in the vocabulary's default language: set aside,
reported, rest of the vocabulary imports (already built at T009, decisions.md D17 — this task
finishes it with acceptance coverage that confirms it still holds now that US-3 has built labels
and notes alongside it).

**Watch**: none.
