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

## 2026-08-04T12:05:00Z · Implementer US3 · T022

**Did**: `TestNoPreferredLabelFinishedByUS3` in `test_skos.py` — two tests: the concept with no
preferred label in the vocabulary's default language is set aside under `NO_PREFERRED_LABEL`,
named with its subject and language, and never created; the rest of the vocabulary imports with
*its own* US-3 content intact, not only its identity — `no_default_language_label.ttl`'s concept
"b" now carries an alternative label, proving labels built in this same phase (T018) land normally
for a concept in the same run as one that gets set aside. No production change: T009's own
`NO_PREFERRED_LABEL` handling (decisions.md D17) already `continue`s before any concept is created
or its content imported, so nothing about US-3's own additions (T018-T021) could have disturbed it,
and both tests passed on first execution — the third task across this feature's two most recent
phases to do so (with T013/T014/T017 in US-2), each proving a piece of behaviour a prior task
already built generally rather than needing new code of its own.

**Verified**: `poetry run pytest -q` — 453 passed (451 + 2 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 21 files already formatted. `poetry run mypy`
— success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python
-m django makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Phase US-3 complete (T018-T022).** A concept's labels — preferred labels in every configured
language beyond the default, alternative and hidden labels — and its documentary notes — the
definition and the six SKOS note kinds, plus a foreign `dcterms:description` read as a definition
and reported as a normalisation — all land through the models' own `add_label`/`add_note` write
path. A value in a language the site is not configured for is set aside and named, filtered ahead
of the write. A notation, a mapping to another vocabulary, and a predicate from outside SKOS
entirely are each set aside under the reason that fits, and a concept with no preferred label in
the default language remains set aside and the rest of the vocabulary imports around it. `models.py`
was not touched. Deferred to US-4/US-5 by design: relationships and collection membership are
recognised SKOS predicates with a model home, so they are silently skipped rather than reported as
unmodelled (decisions.md D27) — those stories build the read paths that will finally consume them.

**Watch**: US-4's Implementer should read decisions.md D27 before starting — once relationships are
read, `skos:broader`/`narrower`/`related` stop being "not yet built" and become genuinely handled;
`_import_unheld_values()`'s own SKOS-namespace check will keep silently skipping them either way
(nothing breaks if `_HANDLED_CONCEPT_PREDICATES` is left as-is), but adding them there too would
make the set of predicates this module actually reads match what the constant claims to name.

## 2026-08-04T12:20:00Z · Implementer US4 · T023

**Did**: `skos.py` gains `_resolve_relation_concept` and `_import_relations`, called once from
`_import_concepts` after every concept in the file has a primary key. `skos:broader` and
`skos:narrower` both resolve to the single canonical `ConceptRelation.Kind.BROADER` row
(`source` the narrower end, `target` the broader end, per models.py/research.md R4), keyed by a
deduplicated `(narrower, broader)` pair so both directions stated for one pair collapse to one
row (FR-010). The whole file's worth of pairs is read before any of them is written, and the
whole reconciliation runs as one pass over every concept this run wrote — not incrementally per
concept — because a relation is commonly asserted from only one of its two ends, and an
incremental per-concept delete-and-recreate would delete a row a sibling concept's own pass had
only just written (decisions.md D29). `_HANDLED_CONCEPT_PREDICATES` now names `skos:broader`/
`skos:narrower` explicitly, finishing decisions.md D27's own "Revisit if." New fixture
`relation_both_directions.ttl` proves the same pair stated from both ends produces exactly one
row.

decisions.md D29 (new): the whole-graph-pass design, why an incremental per-concept version would
lose data depending on iteration order, and why a relation end resolving to a concept in a
*different* vocabulary is treated as unresolved (`MISSING_RELATION_END`) rather than left to raise
an uncaught `ValidationError` from `ConceptRelation`'s own cross-scheme refusal.

**Concern carried forward, not resolved here**: `TestIdempotentReimport::test_a_reference_made_between_two_runs_still_resolves_after_the_second`
(T013) manually creates a `ConceptRelation` between granite and basalt that neither fixture states,
as a stand-in for "an arbitrary foreign key survives a re-import" — written before this importer
read relations at all. Now that `skos:broader`/`narrower` are genuinely reconciled per FR-013, a
plain re-import of `rocks.ttl` correctly removes that unstated relation, and this pre-existing test
fails. This story's brief prohibits modifying a test authored in an earlier story; the failure is
named here and in the story report rather than resolved quietly.

**Verified**: `poetry run pytest -q` — 460 passed, 1 failed (the pre-existing conflict above;
453 baseline + 4 new tests in `test_skos.py`'s new `TestBroaderAndNarrowerRelations` + 4 new
fixture-discovery cases). `poetry run ruff check .` — all checks passed. `poetry run ruff format
--check .` — 21 files already formatted. `poetry run mypy` — success, 9 source files. `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected.

**Next**: T024 — `skos:related` stored once as a symmetric relationship, including when the file
states it in both directions.

**Watch**: the `TestIdempotentReimport` conflict above; T024 will introduce a second, matching
conflict in `TestRecordsAbsentFromSource` once `skos:related` is reconciled the same way, for the
same reason.

## 2026-08-04T12:30:00Z · Implementer US4 · T024

**Did**: `_import_relations` gains a second, parallel branch for `skos:related`: a symmetric
association keyed by an unordered pair (a `frozenset` of the two URIs, then of the two resolved
primary keys) rather than `BROADER`'s directed `(narrower, broader)` tuple. Reuses
`_resolve_relation_concept` unchanged. `_HANDLED_CONCEPT_PREDICATES` now also names
`skos:related`. A `skos:related` triple naming the same node twice is skipped rather than stored
or reported (decisions.md D29, extended). `relation_both_directions.ttl` (built at T023) already
carries a related pair stated from both ends, so this task needed no new fixture.

decisions.md D29 extended: the prediction that `skos:related` would reuse the same
whole-pass/resolve/reconcile shape held exactly, and a second pre-existing test
(`TestRecordsAbsentFromSource`, T015) now conflicts with FR-013 for the identical reason
`TestIdempotentReimport` did at T023 — a manually-created `ConceptRelation` (kind `related`,
basalt-quartz) that neither fixture states is correctly removed by the same reconciliation.

**Concern carried forward, not resolved here**: the same as T023's, now affecting two tests total
(`TestIdempotentReimport` for `BROADER`, `TestRecordsAbsentFromSource` for `RELATED`). Neither
modified, per this story's brief. Both named in the story report's `concerns`.

**Verified**: `poetry run pytest -q` — 462 passed, 2 failed (the two pre-existing conflicts above;
460 + 3 new tests in `test_skos.py`'s new `TestRelatedRelations`, reusing T023's fixture, no new
fixture-discovery cases). `poetry run ruff check .` — all checks passed. `poetry run ruff format
--check .` — 21 files already formatted. `poetry run mypy` — success, 9 source files. `poetry run
deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected.

**Next**: T025 — a relationship end neither in the file nor in the database is set aside and
reported with both ends; an end already in the database from an earlier import is stored.

**Watch**: the two pre-existing test conflicts above remain open for orchestrator review.

## 2026-08-04T12:38:00Z · Implementer US4 · T025

**Did**: No production change — T023's `_resolve_relation_concept`/`_import_relations` already
had to make the missing-end/known-end/cross-scheme distinctions to avoid crashing on an ordinary,
partial published file (decisions.md D29), the same shape decisions.md D17/T022 established for
this story's predecessor (build the general mechanism where correctness requires it, finish it
with acceptance coverage later). New fixture pair `relation_endpoints.ttl` /
`relation_endpoints_updated.ttl`: alpha and beta both land on the first import with a broader
relationship between them; the re-import drops beta from the file entirely (already in the
database, so the relationship still lands) and adds a related edge to a URI that has never existed
anywhere (set aside naming both ends, run still succeeds). A third fixture,
`relation_cross_scheme_target.ttl`, exercises D29's cross-scheme guard directly: a concept in a
second vocabulary stating a relationship to `rocks.ttl`'s granite is set aside rather than
crashing on the model's own cross-scheme refusal.

All four tests passed on first execution, confirming T023's design already covers this task's
acceptance criteria in full.

**Verified**: `poetry run pytest -q` — 466 passed, 2 failed (the two pre-existing conflicts named
at T023/T024, unchanged and not touched; 462 + 4 new tests in `test_skos.py`'s new
`TestRelationEndpointsMissingOrKnown` + 3 new fixture-discovery cases). `poetry run ruff check .`
— all checks passed. `poetry run ruff format --check .` — 21 files already formatted. `poetry run
mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run
python -m django makemigrations --check --dry-run --settings=tests.settings` — no changes
detected.

**Next**: T026 — a re-import with a relationship removed removes it, leaving both concepts.

**Watch**: the two pre-existing test conflicts remain open for orchestrator review; unaffected by
this task.

## 2026-08-04T12:45:00Z · Implementer US4 · T026

**Did**: No production or fixture change. Checked `rocks_updated.ttl` against the task's own
instruction before writing anything: it already drops granite's `related` edge to quartz (D20),
and it fits this task exactly, so nothing further was needed. `TestRelationRemovalOnReimport`:
re-importing `rocks.ttl` then `rocks_updated.ttl` removes the granite-quartz related row while
both concepts remain in the database, and granite's still-stated broader edge to igneous survives
the same re-import — proving the removal is selective (T023/T024's reconciliation), not a
wholesale wipe of every relation touching a concept the file still contains.

Both tests passed on first execution, the fourth task across this story's two most recent phases
to do so (with T013/T014/T017/T022 in earlier phases), each proving a piece of behaviour a prior
task already built generally rather than needing new code of its own.

**Phase US-4 complete (T023-T026).** `skos:broader`, `skos:narrower`, and `skos:related` all land
as the single canonical `ConceptRelation` row the models define, reconciled in one whole-graph
pass per run so both directions of a hierarchy pair and both directions of a related pair each
collapse to exactly one row (FR-010). A relationship end resolves against this run's own writes
first, then an earlier import's, then is set aside and reported by both ends when neither resolves
— including when the resolved match belongs to a different vocabulary (decisions.md D29). A
re-import removes a relationship the file no longer restates while leaving every relationship it
still states, and leaves both concepts in place either way (FR-013). `models.py` was not touched.

**Concerns not resolved in this story, carried to the story report**: two pre-existing tests
(`TestIdempotentReimport::test_a_reference_made_between_two_runs_still_resolves_after_the_second`,
T013; `TestRecordsAbsentFromSource::test_a_concept_dropped_from_the_file_is_untouched_and_named_absent`,
T015) each manually created a `ConceptRelation` not stated by any fixture, as a stand-in for
"an arbitrary foreign key survives a re-import" written before this importer read relations at
all. FR-013's authority over relationships, which this story is required to build, now correctly
removes both manually-injected rows on re-import — decisions.md D29 records the full reasoning and
a suggested fix. Neither test was modified, per this story's brief.

**Verified**: `poetry run pytest -q` — 468 passed, 2 failed (the two pre-existing conflicts above,
unchanged since T023/T024; 466 + 2 new tests in `test_skos.py`'s new
`TestRelationRemovalOnReimport`, no new fixtures). `poetry run ruff check .` — all checks passed.
`poetry run ruff format --check .` — 21 files already formatted. `poetry run mypy` — success, 9
source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django
makemigrations --check --dry-run --settings=tests.settings` — no changes detected.

**Next**: US-5 (T027-T030) — collections arrive, ordered ones in order.

**Watch**: US-5's Implementer inherits the two open pre-existing-test conflicts above unless they
are resolved before then; they are unrelated to collections and should not block US-5's own work.

## Relation-deletion design fault corrected (D30)

**Did**: fixed the "either end" defect D29 named and left open at the end of US-4:
`_import_relations`'s deletion queries selected an existing `ConceptRelation` row when *either*
its source or its target belonged to this run's own writes, and removed it if the run's resolved
pairs no longer included it. That deletes an edge between a concept the file mentions and one it
does not mention at all — only half spoken about — which contradicts FR-013/D5's authority rule
and, worse, does it silently, which D1 forbids. Both the `BROADER` and `RELATED` deletion queries
in `controlled_vocabularies/exchange/skos.py` now require **both** ends to be in
`successful_ids`, not either. Recorded as decisions.md D30, including what it means for a curator:
a re-import of a partial export no longer severs the imported slice from the rest of the
vocabulary the export never retracted.

`TestIdempotentReimport::test_a_reference_made_between_two_runs_still_resolves_after_the_second`
(T013) is modified, minimally: its illustrative reference moved from granite-basalt (an edge
`rocks.ttl` itself states and the importer is correctly authoritative over) to a concept created
locally in granite's own scheme that the file never mentions. Its name, assertions, and place in
the class are unchanged; only the prop and its docstring changed.
`TestRecordsAbsentFromSource::test_a_concept_dropped_from_the_file_is_untouched_and_named_absent`
(T015) needed no change — it already asserted exactly the behaviour D30 introduces.

`TestRelationRemovalOnReimport` (T026) is rebuilt on a new dedicated fixture pair,
`relation_lifecycle.ttl`/`relation_lifecycle_updated.ttl` (decisions.md D28 counsels against a
third edit to the shared `rocks.ttl`/`rocks_updated.ttl` corpus): one test for the genuine
retraction the class is named for, one new test for the D30 survival case its old scenario used to
get backwards, and one carried-over selectivity check, all three now correctly targeted.

Mutation-probed before closing: widened both deletion queries back to `Q(...) | Q(...)`, confirmed
`TestRecordsAbsentFromSource`'s test fails (`ConceptRelation.DoesNotExist` on the manually-created
reference), then restored the `&`-equivalent filter. The rule bites; it is not a test that would
pass either way.

**Verified**: `poetry run pytest -q` — 473 passed, 0 failed. `poetry run ruff check .` / `ruff
format --check .` / `mypy` / `deptry .` — all clean. `makemigrations --check --dry-run` — no
changes detected. `pre-commit run --all-files` — all hooks passed. `forge verify --base
origin/main` — conformance, lint, typecheck, test, and build all passed.

**Next**: US-5 (T027-T030) — collections arrive, ordered ones in order. No longer blocked by any
open relation-deletion conflict.

**Watch**: D30's "Revisit if" — a future story needing a relation reconciled against only one
rewritten end (e.g. a bulk downstream-retirement operation) would be new, deliberately-asymmetric
behaviour, not a further correction to this rule.

## 2026-08-04T12:55:00Z · Implementer US5 · T027

**Did**: `skos.py` gains `_import_collections`, called from `_import_concepts` right after
`_import_relations` (needs the same `concepts_by_uri` this run's own writes give the pk's a
membership resolves against). Every `skos:Collection`/`skos:OrderedCollection` node in the graph is
matched or created by `static_uri` (research.md R6, the same upsert rule every other record uses),
written through the model's own `save()`, and its `skos:member` set resolved through a renamed,
generalised `_resolve_concept_reference` (was `_resolve_relation_concept`, T023) — decisions.md D30's
own text calls collection membership "the same shape of problem" a relation end already is, so the
same resolution rule (this run's own writes first, then `get_by_uri` for an earlier import, `None`
for neither) now serves both callers rather than being duplicated. Membership is written only
through `Collection.add()`/`Collection.remove()` — never a `CollectionMember` row constructed
directly — so the model's own cross-scheme check always runs, per this task's own acceptance text.
`models.py` was not touched.

**Deviation** (decisions.md D32, new): implementing this correctly means a `Collection` now lands in
`report.created`/`report.updated`, exactly as `ConceptScheme` and `Concept` already do (it is an
identified record with its own `static_uri`, not content of one). `rocks.ttl` has carried two
collections since Phase 0 (T005), so `TestReportPopulatedByARealRun` (T012, merged in US-1)'s two
exact-set assertions over a plain import went stale the moment collections started being reported —
not a defect this story introduced, a bucket correctly reporting more of what the fixture always
held. This story's brief is explicit that a pre-existing test is not this Implementer's to modify
without saying so; D32 records why the two assertions were widened (not weakened — both remain exact
equality, still catch a missing, duplicated, or wrong URI) rather than left failing for a separate
pass, since no such pass is described for this story and the closing gate requires a green suite.

**Mutation probe**: commented out the `_import_collections` call in `_import_concepts`. Six tests
failed — this task's own four new `TestCollectionsAndMembership` tests, plus exactly the two widened
`TestReportPopulatedByARealRun` assertions — nothing else. Restored; 477 passed.

**Verified**: `poetry run pytest -q` — 477 passed (473 + 4 new in `test_skos.py`'s new
`TestCollectionsAndMembership`). `poetry run ruff check .` — all checks passed. `poetry run ruff
format .` — 1 file reformatted (`skos.py`) then clean. `poetry run mypy` — success, 9 source files.
`poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations
--check --dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: T028 — ordered collections: `skos:memberList` walked in order (research.md R2), `ordered`
set, positions assigned; a re-import that changes the order updates positions to match.

**Watch**: `_import_collections` does not track a collection absent from this run's file at all (no
`report.absent_from_source` entry for a collection an earlier import created that this file no
longer mentions) — T027-T030's own acceptance scenarios never name this case, only a *member*
missing from a collection that is itself still present, so it is left unbuilt rather than invented
speculatively. Flagged as a concern in the story report for the next pass to weigh against FR-013's
general "left untouched and named" wording for any record.

## 2026-08-04T13:05:00Z · Implementer US5 · T028

**Did**: No new production code. T027's `_import_collections` already had to walk
`skos:memberList` in order via `graph.items()` (research.md R2), set `ordered` from the node's own
`rdf:type`, and call `Collection.set_member_order()` to make a re-import's changed order match the
file — the general "resolved (file order) + survivors" reconciliation built for the D30-equivalent
survivor case (T029's own concern, built ahead of its own acceptance coverage the same way T023 built
`_resolve_relation_concept`'s cross-scheme guard ahead of T025) already gives an ordinary reorder for
free. Four tests against `rocks.ttl`'s existing `example-sequence` collection (Phase 0, T005) and its
already-staged `rocks_updated.ttl` reordering: marked ordered; members returned in the file's own
order; a re-import with a changed `skos:memberList` updates positions to match; the collection's own
identifier and primary key are unchanged by the reorder.

**Mutation probe**: replaced the `row.set_member_order(...)` call with a no-op. The reorder test
failed (`Basalt` where `Granite (revised)` was expected — the stale first-import order), the other
three passed unaffected (order-marking, initial order, and identity are independent of the reorder
call). Restored; full suite green again.

**Verified**: `poetry run pytest -q` — 481 passed (477 + 4 new in `test_skos.py`'s new
`TestOrderedCollectionMemberOrder`). `poetry run ruff check .` — all checks passed. `poetry run ruff
format --check .` — 21 files already formatted. `poetry run mypy` — success, 9 source files.
`poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations
--check --dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: T029 — a collection member neither in the file nor already in the database: collection
still created, member set aside and reported; a re-import that adds and removes members leaves
membership matching the file, and a member's concept the file no longer mentions at all survives
(decisions.md D30's rule, applied here).

**Watch**: none.

## 2026-08-04T13:15:00Z · Implementer US5 · T029

**Did**: No new production code. T027's `_import_collections` already had to resolve every member
URI through `_resolve_concept_reference` and set aside a `None` result under
`SetAsideReason.MISSING_MEMBER` (naming both the member and the collection), and already only ever
removes an existing membership when its concept belongs to `successful_concepts` — exactly the
brief's own D30-equivalent rule, applied from the start rather than re-derived here, per the story
brief's explicit instruction. New fixture pair `collection_lifecycle.ttl`/
`collection_lifecycle_updated.ttl` (decisions.md D28's own "prefer a new fixture" counsel, rather
than a third edit to `rocks.ttl`/`rocks_updated.ttl`): four members side by side in one collection —
alpha stays a member across both files, beta stays present as a concept but is genuinely dropped
from the collection statement (removed), gamma leaves the file entirely (survives, per D30), delta
is added on the second run, and "missing" never exists anywhere (set aside on the first run). Seven
tests, all passing on first execution — the same shape T025 was for relationship endpoints, this
task's own acceptance criteria proving a mechanism the previous task already had to build correctly
to avoid crashing on an ordinary, partial file.

**Mutation probe, two separate**: (1) dropped the `successful_ids` guard from the removal condition
(widening it back to "membership not in resolved_pks", the pre-D30-equivalent "either end" shape) —
the survivor test and the "final membership" test both failed (gamma wrongly removed), the other five
unaffected; restored. (2) dropped the `report.add_set_aside(MISSING_MEMBER, ...)` call — the
missing-member test failed (`0 == 1`), the other six unaffected; restored. Full suite green again
after each restore.

**Verified**: `poetry run pytest -q` — 490 passed (481 + 7 new in `test_skos.py`'s new
`TestCollectionMembershipMissingOrAbsentEnds`, + 2 new fixture-discovery cases). `poetry run ruff
check .` — all checks passed. `poetry run ruff format --check .` — 21 files already formatted.
`poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned.
`poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` — no
changes detected. `poetry run pre-commit run --all-files` — all hooks passed.

**Next**: T030 — a blank-node collection fails the run, on the same rule as concepts (D3); an
ordered collection's blank-node list cells are read normally.

**Watch**: none.

## 2026-08-04T13:25:00Z · Implementer US5 · T030

**Did**: No new production code. `_import_collections` (T027) already runs every collection node
through the same `_identify()` a concept or the vocabulary itself uses, so a blank-node collection
was already fatal (`FatalReason.MISSING_IDENTITY`) from the moment collections started importing —
`blank_node_collection.ttl` (built at Phase 0, T005, decisions.md D13, ahead of any code that could
exercise it) is exercised for the first time by this task. Three tests: the run fails naming the
collection by its `skos:prefLabel` hint ("Nameless collection", since it has no URI to show); nothing
is written, including the ordinary concept the same file also carries (atomicity, T011's existing
mechanism); and, the other half of D3's own carve-out, `rocks.ttl`'s ordinary ordered collection
(`example-sequence`) imports with `report.fatal == []` even though its `skos:memberList` is an RDF
list made of blank nodes by construction (research.md R2) — those cells never reach `_identify()` at
all, since `graph.items()` (T028) yields the member URIs the list carries, never the list's own
cells.

**Mutation probe**: bypassed `_identify()`'s blank-node check for collections specifically (treating
the blank node's hint as if it were a usable URI, the same shape a missing check would produce). Both
blank-node tests failed — not with a clean assertion mismatch but with an uncaught
`django.core.exceptions.ValidationError` from `Collection.save()` itself
(`'Nameless collection' is not a well-formed absolute identifier with a scheme`), confirming the test
is bound to a real safety check rather than passing by construction. The third test (ordinary ordered
collection) was unaffected, as expected — it exercises no blank-node collection at all. Restored;
full suite green again.

**Phase US-5 complete (T027-T030).** A `skos:Collection`/`skos:OrderedCollection` lands as a
`Collection` inside the vocabulary being imported, matched by its published identifier, its
`skos:member`/`skos:memberList` membership written only through the model's own `Collection.add`/
`remove`/`set_member_order` API. An ordered collection's members come back in the file's own order,
and a re-import that changes that order updates positions to match. A member neither in the file nor
already in the database is set aside and reported, naming both the member and the collection, and
the run still succeeds; a re-import that adds and drops members keeps the collection's membership in
line with the file, except that a member whose concept the file no longer mentions *at all* — as
opposed to one the collection statement explicitly excludes — survives, per decisions.md D30's own
rule, carried here rather than re-derived (decisions.md D32 records why, along with the one
pre-existing test this correctness required widening). A collection identified only by a blank node
fails the run on the same rule as a concept (D3); an ordered collection's own list cells, blank nodes
by construction, are read normally. `models.py` was not touched.

**Verified**: `poetry run pytest -q` — 493 passed (490 + 3 new in `test_skos.py`'s new
`TestBlankNodeCollectionFails`). `poetry run ruff check .` — all checks passed. `poetry run ruff
format --check .` — 21 files already formatted. `poetry run mypy` — success, 9 source files.
`poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations
--check --dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run
--all-files` — all hooks passed.

**Next**: US-6 (T031/T031a/T032) — standards and documentation sweep. Out of this Implementer's
scope.

**Watch**: (1) `_import_collections` does not track a collection itself absent from a run's file —
see the T027 entry's own Watch, carried forward, unaffected by T028-T030. (2) decisions.md D32
widened two pre-existing `TestReportPopulatedByARealRun` assertions (T012, US-1) to include
collections in the created/updated bucket; flagged for the next tamper-check triage pass to review
alongside D23/D28/D31's own precedent, even though this session applied and verified the fix itself
rather than leaving it open, since no separate orchestrator pass is described for this story.

## 2026-08-04T12:50:00Z · Implementer US6 · T031

**Did**: `tests/test_exchange/test_standards.py` — a closed-world standards sweep (FR-016, spec
User Story 6 Acceptance Scenarios 1 and 4) that complements the many per-message assertions already
scattered across `test_report.py`/`test_skos.py`/`test_safety.py`. `TestReportReasonTemplatesUseOnlyNamedPlaceholders`
parametrizes over `list(SetAsideReason) + list(FatalReason) + list(NormalizedReason)` — every member
of all three closed report-reason vocabularies, so a reason added later without its own dedicated
test is still caught — and asserts each template carries *only* named `%(name)s` placeholders, never
a bare positional one (the existing tests check `%(subject)s` is present; this additionally checks
nothing else in the string is un-named). `TestFailureMessagesUseOnlyNamedPlaceholders` exercises
every `raise …Error(_("…"), …)` call site in the `exchange` package once (the four `SkosImportError`/
`SkosImportFailed` messages in `skos.py`, the two `UnsafeRdfXmlError` messages in `safety.py`) with
the same check. Acceptance Scenario 4's developer-diagnostics exemption — the raw upstream `rdflib`/
`defusedxml` exception each of the two chained refusals carries on `__cause__` — is asserted present
explicitly rather than left an unstated gap, naming it as the one thing this feature shows a person
that Article XII does not hold to a translatable, named-placeholder standard.

No new production code: every message the earlier US0-US5 Implementers wrote already meets the
standard this sweep checks (matching T013/T014/T017/T022/T028/T029's own precedent of an
acceptance-coverage-only task). Proven a real check with a mutation probe: temporarily reverted
`SkosImportError`'s "could not be found" message from `%(file)s` to a bare `%s`; the new sweep's
`test_missing_file_message` failed naming the positional placeholder, the other 20 new tests were
unaffected; reverted, full suite green again.

**Verified**: `poetry run pytest -q` — 514 passed (493 + 21 new in the new `test_standards.py`).
`poetry run ruff check .` — all checks passed. `poetry run ruff format .` — 1 file reformatted
(`test_standards.py`) then clean. `poetry run mypy` — success, 9 source files. `poetry run deptry .`
— no issues, 15 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all
hooks passed.

**Next**: T033 (was T031a in tasks.md prose) — every SKOS predicate in the fixture corpus is either
read or reported, closing decisions.md D27's own gap.

**Watch**: `specs/006-import-published-skos/feature-state.json`'s US6 story only lists tasks T031
and T032 — T033 and T034 (added mid-run by the US4/US5 Implementers as T031a/T031b, per this
story's own brief) are not yet entries in the ledger. Restructuring `stories[].tasks` is Forge's own
job, not an Implementer's (feature-state.schema.json's own description), so this Implementer flips
status/attempts/evidence only on the two task ids the ledger already has and records T033/T034's own
progress here in prose instead — flagged for Forge to reconcile the ledger's task list with
tasks.md's own T031/T033/T034/T032 numbering.

## 2026-08-04T13:00:00Z · Implementer US6 · T033

**Did**: `TestEverySkosPredicateIsReadOrReported` in `test_skos.py` — closes decisions.md D27's own
gap. Discovers every SKOS predicate appearing anywhere in the fixture corpus by walking the files
(the same discipline `ALL_FIXTURES` already applies, not a hand-kept list) and asserts each one is
either read by the importer or named in the report, now that US-4/US-5 have landed every read path
D27 deferred to.

**Deviation** (decisions.md D34, new): a first, deliberately naive version checked the discovered
predicates against `_HANDLED_CONCEPT_PREDICATES` alone (`_import_unheld_values`'s own gate, imported
directly rather than duplicated) and failed, correctly, naming `skos:hasTopConcept`,
`skos:member`, and `skos:memberList` — all three genuinely read (`_scheme_refs`,
`_import_collections`), but never at concept-node level, so they never reach that gate. Fixed in the
test with a small `_READ_BUT_NOT_AT_CONCEPT_LEVEL` set naming the three explicitly, not in
production — no predicate in the corpus was actually unhandled.

**Verified**: `poetry run pytest -q` — 515 passed (514 + 1 new). `poetry run ruff check .` — all
checks passed. `poetry run ruff format --check .` — 22 files already formatted. `poetry run mypy` —
success, 9 source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m
django makemigrations --check --dry-run --settings=tests.settings` — no changes detected. `poetry
run pre-commit run --all-files` — all hooks passed.

**Next**: T034 (was T031b in tasks.md prose) — a collection an earlier import created that the
current file no longer mentions is reported in `report.absent_from_source`, the way a concept in
that position already is. The only task in this story expected to need new production code.

**Watch**: none beyond the feature-state.json ledger gap already flagged at T031.

## 2026-08-04T13:10:00Z · Implementer US6 · T034

**Did**: closes the gap decisions.md D33 named rather than invented at the end of US-5. New fixture
pair `collection_absent_from_source.ttl`/`_updated.ttl` (D28's own "prefer a new fixture" counsel):
"kept" is restated by both files, "dropped" exists only in the first. `TestCollectionAbsentFromSource`
in `test_skos.py` — three tests, the first genuinely failing against the pre-existing code (`_import_collections`
never tracked which collections a run's own file mentioned, per the Watch note carried since T027):
the dropped collection's primary key and name are unchanged after the re-import, it is named in
`report.absent_from_source` and in neither `created` nor `updated`, and its membership (the concept
`alpha`) survives untouched — the same three assertions `TestRecordsAbsentFromSource` (T015) makes
for a concept in the same position.

Production change (`_import_collections`, `skos.py`): a `mentioned_uris` set, populated the moment
each collection node's identity is successfully checked (mirroring `_import_concepts`'s own
`mentioned_uris`, T015) — a collection that fails identity (D3, T030) is never added, since it never
gets a usable URI to report absence by. After the per-collection loop, every existing `Collection` of
`target_scheme` whose URI was never seen is reported via `report.add_absent_from_source()`, the same
tail `_import_concepts` already runs. Nothing about an absent collection's own row or its membership
is touched — only named, per FR-013's "left untouched."

**Mutation probe**: replaced the new absent-reporting block with a no-op. The first
`TestCollectionAbsentFromSource` test failed exactly as it had before this task's fix (`'…/dropped'
in []`), the other two were unaffected (they don't depend on the absent bucket). Restored; full
suite green again.

**Verified**: `poetry run pytest -q` — 520 passed (515 + 3 new in `TestCollectionAbsentFromSource` +
2 new fixture-discovery cases). `poetry run ruff check .` — all checks passed. `poetry run ruff
format --check .` — 24 files already formatted. `poetry run mypy` — success, 9 source files. `poetry
run deptry .` — no issues, 15 files scanned. `poetry run python -m django makemigrations --check
--dry-run --settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files`
— all hooks passed.

**Next**: T032 — documentation (README, CHANGELOG, docstrings) in the same PR as the code.

**Watch**: none beyond the feature-state.json ledger gap already flagged at T031.

## 2026-08-04T13:20:00Z · Implementer US6 · T032

**Did**: documentation in the same PR as the code (Article VI). README gains a new "## Importing a
published vocabulary" section (inserted between "## Configuration" and "## Relationship to other
packages"): what `import_skos()` reads and writes, the upsert/absent-from-source re-import rule
(FR-013), a walkthrough of the `ImportReport`'s six buckets, and the "programmatic only, no
CLI/web entry point yet" note FR-001 states. Written plainly and factually, per this story's own
brief — the humanizer pass is the orchestrator's, not this Implementer's, to run. CHANGELOG's
`[Unreleased]` → `### Added` gains one entry for the whole feature, in the same descriptive style as
the existing FS-002/003/004/005 entries above it.

Two stale docstrings fixed along the way, both public per Article VI and both directly contradicted
by the finished feature: `skos.py`'s module docstring still said "this module currently covers
reading a file into a graph (T006)" and named only Phase US-1's own scope; `exchange/__init__.py`'s
said the reader and `import_skos()` "are a later story" and that the module "grows its re-exports
one task at a time" — both written at T002/T006 and never updated as the other five stories landed.
Rewrote both to describe the finished module. `import_skos()`'s own docstring (already present,
T007) gains two paragraphs summarising what it imports beyond the vocabulary itself (concepts,
labels, notes, relationships, collections) and the re-import/set-aside contract (FR-013/FR-014) —
the rest of its detail (transaction/rollback semantics) was already accurate and is left as T007
wrote it. `ImportReport`'s own docstring (T003, extended at T021) was already accurate and complete;
not touched.

**Verified**: `poetry run pytest -q` — 520 passed (unchanged from T034 — no test asserts on exact
docstring text beyond non-emptiness, `TestExchangePackage::test_package_has_a_module_docstring`).
`poetry run ruff check .` — all checks passed. `poetry run ruff format --check .` — 24 files already
formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files
scanned. `poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` —
no changes detected. `poetry run pre-commit run --all-files` — all hooks passed.

**Phase US-6 complete (T031/T033/T034/T032).** Every message this feature puts in front of a person
— a report reason or a raised failure — is checked, in one closed-world sweep, to be translatable
and named-placeholder-only; the developer-diagnostics exemption is named explicitly rather than left
an unstated gap. Every SKOS predicate appearing anywhere in the fixture corpus is either read by the
importer or named in the report, closing decisions.md D27. A collection the file no longer mentions
is reported absent from source, the way a concept in that position already is, closing the gap D33
named. README, CHANGELOG, and the public callable's docstrings document the finished feature. This
is the last story before convergence; this Implementer stops here.

**Watch**: the feature-state.json ledger gap flagged at T031 is still open — Forge's own
reconciliation, not this Implementer's to restructure.

## 2026-08-04T14:10:00Z · Forge · US-6 convergence check

**Did**: reviewed the US-6 Implementer's completion report and re-ran the gates independently.
`forge verify --base origin/main` was **red on conformance** — `tests/test_exchange/test_standards.py`
mirrors no source module. Split the sweep into the three modules of its subjects, moved the shared
placeholder predicate into a new `tests/test_exchange/conftest.py` fixture, and deleted the
standalone file. Recorded as D35.

Also reconciled the ledger gap the Implementer flagged: `feature-state.json`'s US6 story carried
only T031 and T032. T033 and T034 (tasks.md's T031a/T031b, renamed by the US-6 Implementer to match
its commit trail) are now ledger entries with their evidence, tasks.md and decisions.md use the
T033/T034 names throughout, and US6 is marked done.

**Verified**: `poetry run pytest -q` — 520 passed, unchanged by the move. `forge verify --base
origin/main` — conformance, lint, typecheck, test, build all green. `ruff format --check`, `deptry`,
`makemigrations --check`, `pre-commit run --all-files` all clean.

**Next**: convergence — merge US-6 to the feature branch and open the PR.

## 2026-08-04T11:40:00Z · Forge · review fix 1 — JSON-LD remote `@context`

**Did**: closed a critical security finding from the merged feature's review: `_read_graph` gated
the pre-flight safety scan on RDF/XML only, leaving JSON-LD's own remote-fetch route wide open —
rdflib's JSON-LD parser resolves a string `@context` through `urlopen` with no allowlist, against a
remote host or a local `file://` path alike. Reproduced directly against `rdflib.Graph.parse()`
before writing any test: a doc pointed at an unreachable port raised a connection error (proving the
fetch fired), and one pointed at `file:///tmp/...` read the local file and parsed cleanly. Wrote the
failing tests first — `TestScanJsonLd` in `test_safety.py` (a string `@context`, a string inside an
array `@context`, an inline-object `@context`, no `@context`, and malformed JSON) and
`TestReadGraph::test_json_ld_is_routed_through_the_safety_scan_before_rdflib_sees_it` /
`..._with_an_inline_context_is_unaffected...` in `test_skos.py` — confirmed they failed for the
right reason (`ImportError` for the not-yet-written `scan_json_ld`/`UnsafeJsonLdError`, then a real
connection-refused error once those existed but `_read_graph` wasn't wired to call them), then made
the production change: `safety.py` gains `scan_json_ld()`/`UnsafeJsonLdError`, structured exactly
like `scan_rdf_xml`/`UnsafeRdfXmlError` — refuses any string `@context` value found anywhere in the
document (including nested inside an embedded node object, not only at the top level), leaves an
inline object or absent `@context` alone, and leaves malformed JSON for rdflib's own parser to
report. `_read_graph` now calls it on the `json-ld` branch alongside the existing `xml` one. Mutation
probe: replaced the new `elif` branch with `pass`, re-ran the wiring test — it failed with the same
raw `urlopen error [Errno 111] Connection refused>` the reproduction showed, proving the test
actually detects the hole reopening; restored the fix, re-ran green. Checked Turtle and RDF/XML for
the same class of hole rather than assuming them clean (the brief asked for this explicitly): a
Turtle `@prefix` pointed at an unreachable host parsed without any fetch attempt (prefixes are never
dereferenced), and RDF/XML's own remote-reference surface is exactly the external-entity/DTD routes
D9 already closes — no third route found. Recorded as decisions.md D36, including the negative
findings for Turtle/RDF/XML rather than leaving them unstated.

New fixtures under `tests/fixtures/security/` (not `tests/fixtures/skos/` — a remote-context fixture
placed under the swept `skos/` corpus would make `TestFixtureCorpus`'s own parse sweep attempt the
real network fetch on every test run, exactly the outcome this fix exists to prevent):
`remote_context_string.jsonld`, `remote_context_array.jsonld`, `inline_context.jsonld`.

**Verified**: `poetry run pytest -q` — 528 passed (520 baseline + 8 new: 5 in `TestScanJsonLd`, 1
placeholder-sweep addition in `TestRefusalMessagesUseOnlyNamedPlaceholders`, 2 in `TestReadGraph`).
`poetry run ruff check .` — all checks passed (one
auto-fixable lint on the new code, applied). `poetry run ruff format --check .` — 22 files already
formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files
scanned. `poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` —
no changes detected. `poetry run pre-commit run --all-files` — all hooks passed.

## 2026-08-04T12:05:00Z · Forge · review fix 2 — broader + related on the same pair crashes the run

**Did**: closed a high-severity finding from the merged feature's review: `_import_relations` built
`resolved_broader` and `resolved_related` independently, so a pair the file (or an earlier and a
later run together) stated both ways raised the model's own disjointness `ValidationError`
(`ConceptRelation._reject_disjointness_violation`) uncaught out of `add_related`/`add_broader` —
a raw exception escaping `import_skos()`. Wrote the failing tests first — a new
`TestRelationDisjointness` in `test_skos.py` with three cases: both stated in one file
(`relation_disjointness_conflict.ttl`), an earlier run's `related` row surviving into a later run
that states `broader` for the same pair (`relation_disjointness_prior_related.ttl` /
`..._updated.ttl`), and the symmetric mirror — an earlier run's `broader` row surviving into a later
run that states `related` (`relation_disjointness_prior_broader.ttl` / `..._updated.ttl`) — confirmed
all three failed with the raw `ValidationError` before any production change. Decided the
hierarchical relation wins (it is the stronger statement, and what SKOS itself declares the two
disjoint in favour of): added `SetAsideReason.RELATION_DISJOINTNESS` to `report.py` following D26's
pattern exactly, then made `_import_relations` write broader/narrower rows first, each one checked
directly against — and clearing — a conflicting stored `RELATED` row for the same pair regardless of
whether that row's ends belong to this run's own writes (closes route 2, which D30's own
`successful_ids`-scoped bulk deletion pass cannot see, since the far end of a newly-stated broader
edge may only be *referenced* this run, not rewritten); related rows are then written second, each
one checked the same way against a conflicting stored `BROADER` row — including one this same call
just wrote — and set aside rather than attempted when found (closes route 3, and route 1 falls out of
the same two checks for free, discovered by mutation-probing an initial data-level exclusion step out
of existence — see decisions.md D37 for why that step was deleted rather than kept). Mutation probe:
disabled each of the two per-pair checks in turn and confirmed the test naming that exact route
failed with the model's raw `ValidationError` each time; restored both, re-ran green. Recorded as
decisions.md D37, including the one accepted trade-off found along the way (a compound scenario no
fixture exercises can produce two report entries for one conflict instead of one — verbosity, not a
defect).

**Verified**: `poetry run pytest -q` — 540 passed (528 baseline + 12 new: 3 in `TestRelationDisjointness`,
plus the four generic `SetAsideReason` sweep tests in `test_report.py` re-parametrizing automatically
over the new `RELATION_DISJOINTNESS` member, plus five `TestFixtureCorpus` parse-sweep instances for
the five new `relation_disjointness_*.ttl` fixtures). `poetry run ruff check .` — all checks passed.
`poetry run ruff format --check .` — 22 files already formatted. `poetry run mypy` — success, 9 source
files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django
makemigrations --check --dry-run --settings=tests.settings` — no changes detected. `poetry run
pre-commit run --all-files` — all hooks passed.

## 2026-08-04T12:35:00Z · Forge · review fix 3 — two preferred labels in one non-default language crashes the run

**Did**: closed a high-severity finding from the merged feature's review: D25 filtered an
unconfigured language ahead of the write for `skos:prefLabel`/`altLabel`/`hiddenLabel` alike, but
never implemented the cardinality half of the same discipline for `PREFERRED` labels — a second
`skos:prefLabel` in one non-default *configured* language reached `Concept.add_label` twice, and the
second raised `ConceptLabel.clean()`'s own uncaught `ValidationError` ("A preferred label in the
language 'de' already exists for this concept."), a raw exception escaping `import_skos()`. Wrote the
failing tests first — `TestSurplusPreferredLabelInAnotherConfiguredLanguage` in `test_skos.py`, using
a new `surplus_preferred_label.ttl` fixture (a concept with two German `skos:prefLabel` values,
"Gerät" and "Apparat") — confirmed both tests failed with that exact `ValidationError` before any
production change. Made the production change: `_import_labels` now groups every `skos:prefLabel`
literal by language and keeps the lexicographically-first value in each (the same rule
`_preferred_label_in` already uses for the default language, so the same file always imports the same
way); every other value in a *configured*, non-default language is set aside and reported under a new
`SetAsideReason.SURPLUS_PREFERRED_LABEL` member added to `report.py` following D26's pattern exactly.
The default-language branch is deliberately untouched by this commit — it still silently skips every
literal in that language, the FIX 4 gap named next. Mutation probe: disabled the new surplus check
(`if False and kind == PREFERRED and ...`), re-ran the new test class, confirmed both tests failed
with the same raw `ValidationError`; restored, re-ran green. Recorded as decisions.md D38 (covers both
FIX 3 and FIX 4, since one surplus-label mechanism serves both).

**Verified**: `poetry run pytest -q` — 547 passed (540 baseline + 7 new: 2 in
`TestSurplusPreferredLabelInAnotherConfiguredLanguage`, four generic `SetAsideReason` sweep tests
re-parametrizing over the new member, one `TestFixtureCorpus` parse-sweep instance for the new
fixture). `poetry run ruff check .` — all checks passed. `poetry run ruff format .` — one file
(`test_skos.py`, a line over length) reformatted, then `--check` clean. `poetry run mypy` — success, 9
source files. `poetry run deptry .` — no issues, 15 files scanned. `poetry run python -m django
makemigrations --check --dry-run --settings=tests.settings` — no changes detected. `poetry run
pre-commit run --all-files` — all hooks passed.

## 2026-08-04T12:50:00Z · Forge · review fix 4 — a surplus default-language preferred label is dropped silently

**Did**: closed a medium-severity finding from the merged feature's review, in the same family as
FIX 3: `_import_labels`'s `if kind == PREFERRED and language == default_language: continue` line
skips *every* `skos:prefLabel` literal in the default language, including the ones
`_preferred_label_in` (`_import_concepts`) did not choose as `Concept.label` — dropped with no
report at all, contradicting Article XI and the README's own "nothing a file contains is ever
dropped in silence." Wrote the failing test first —
`TestSurplusPreferredLabelInTheDefaultLanguage` in `test_skos.py`, using a new
`surplus_preferred_label_default_language.ttl` fixture (two English `skos:prefLabel` values,
"Widget" and "Doohickey", "en" being the default language) — confirmed the "kept as label" half
already passed (no crash, matching FIX 3's finding that this half was never the bug) but the
"reported" half failed (`0 == 1`, no set-aside entry at all) before any production change. Made the
production change: the same `preferred_by_language`/`preferred_kept` machinery FIX 3 introduced now
also drives the default-language branch — a literal matching `preferred_kept[default_language]` is
still skipped silently (it already lives as `concept.label`; writing it as a `ConceptLabel` row too
would duplicate the identity anchor, exactly what the model refuses), but every other literal in that
language is now reported under the same `SetAsideReason.SURPLUS_PREFERRED_LABEL` FIX 3 added.
Mutation probe: disabled the new report call in the default-language branch, re-ran the test class,
confirmed the "reported" test failed again (`0 == 1`) while the "kept as label" test stayed green
(proving the mutation is isolated to the reporting half, not the storage half); restored, re-ran
green. Recorded together with FIX 3 in decisions.md D38 — one mechanism, one decision, covering both.

**Verified**: `poetry run pytest -q` — 550 passed (547 baseline + 3 new: 2 in
`TestSurplusPreferredLabelInTheDefaultLanguage`, one `TestFixtureCorpus` parse-sweep instance for the
new fixture — no new `SetAsideReason` member this time, so no further sweep re-parametrization).
`poetry run ruff check .` — all checks passed. `poetry run ruff format --check .` — 22 files already
formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files
scanned. `poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` —
no changes detected. `poetry run pre-commit run --all-files` — all hooks passed.

## 2026-08-04T13:10:00Z · Forge · review fix 5 — a preferred label that slugifies to empty crashes the run

**Did**: closed a medium-severity finding from the merged feature's review: `_assign_unique_slug`
sets `slug_is_manual = True` with a `base` from `slugify(concept.label, allow_unicode=True)` that may
be empty (a label of only characters `slugify()` strips, e.g. `"±"`), and `Concept.save()` then
raises `ValidationError({'slug': 'An explicit slug must not be empty.'})` uncaught. Wrote the failing
test first — `TestEmptySlugLabelIsSetAsideNotCrashed` in `test_skos.py`, using a new
`empty_slug_label.ttl` fixture (one concept whose only default-language `skos:prefLabel` is `"±"`,
one normal sibling concept to prove the rest of the vocabulary still imports) — confirmed both tests
failed with exactly that raw `ValidationError` before any production change. Made the production
change: `_import_concepts` now checks `slugify(label, allow_unicode=True)` right after resolving
`label`, at the same point and in the same shape as the existing `NO_PREFERRED_LABEL` check —
`mentioned_uris` still records the concept (so it is never additionally reported
`absent_from_source`) but nothing is looked up or written for it — and sets it aside under a new
`SetAsideReason.EMPTY_SLUG` member. The reported message deliberately names the *slug*, not the
label, as the problem: the model's own message is field-scoped to `slug` and would misdirect a
curator into scrutinising a label that is not actually at fault. Mutation probe: disabled the new
check (`if False and not slugify(...)`), re-ran the new test class, confirmed both tests failed with
the same raw `ValidationError`; restored, re-ran green. Recorded as decisions.md D39.

**Verified**: `poetry run pytest -q` — 557 passed (550 baseline + 7 new: 2 in
`TestEmptySlugLabelIsSetAsideNotCrashed`, four generic `SetAsideReason` sweep tests re-parametrizing
over the new `EMPTY_SLUG` member, one `TestFixtureCorpus` parse-sweep instance for the new fixture).
`poetry run ruff check .` — all checks passed. `poetry run ruff format --check .` — 22 files already
formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no issues, 15 files
scanned. `poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` —
no changes detected. `poetry run pre-commit run --all-files` — all hooks passed.

## 2026-08-04T13:25:00Z · Forge · review fix 6 — self-referential broader crashes while related is skipped

**Did**: closed a low-severity finding from the merged feature's review: a self-referential
`skos:related` triple is already a deliberate no-op via decisions.md D29's `if len(pair) < 2:
continue` (a `frozenset({uri, uri})` collapses to one element), but the equivalent
`skos:broader`/`skos:narrower` shape had no such guard — `desired_broader`'s directed `(narrower_uri,
broader_uri)` tuple never collapses, so it reached `add_broader` and raised the model's own uncaught
`ValidationError` ("A concept cannot be in a relation with itself."). Wrote the failing test first —
`TestSelfReferentialBroaderIsSkippedLikeSelfReferentialRelated` in `test_skos.py`, using a new
`self_referential_broader.ttl` fixture (one concept stating `skos:broader` about itself) — confirmed
it failed with exactly that raw `ValidationError` before any production change. Made the production
change: a `narrower_uri == broader_uri` check at the top of the broader/narrower resolution loop in
`_import_relations`, skipping before `_resolve_concept_reference` is even called — the same
"deliberate no-op, not reported" treatment D29 already chose for the `related` case, applied here
consistently rather than re-argued. Mutation probe: disabled the new check, re-ran the test, confirmed
it failed with the same raw `ValidationError`; restored, re-ran green. Recorded as decisions.md D40,
naming this an inconsistency the predecessor task left rather than a considered design point being
revisited — nothing in decisions.md ever argued broader should behave differently from related here.

**Verified**: `poetry run pytest -q` — 559 passed (557 baseline + 2 new: 1 in
`TestSelfReferentialBroaderIsSkippedLikeSelfReferentialRelated`, one `TestFixtureCorpus` parse-sweep
instance for the new fixture — no new `SetAsideReason` member this time, so no sweep
re-parametrization). `poetry run ruff check .` — all checks passed. `poetry run ruff format --check .`
— 22 files already formatted. `poetry run mypy` — success, 9 source files. `poetry run deptry .` — no
issues, 15 files scanned. `poetry run python -m django makemigrations --check --dry-run
--settings=tests.settings` — no changes detected. `poetry run pre-commit run --all-files` — all hooks
passed.
