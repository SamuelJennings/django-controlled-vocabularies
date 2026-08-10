# Progress — 008 Run an import from the command line

Append-only. Each stage transition and gate outcome is written at the moment it happens, so a
crashed run resumes from fact rather than from inference.

## 2026-08-10 — S0 INTAKE

Issue [#52](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/52) claimed.
Dependency #50 checked: closed and merged, so nothing blocked. Sibling issues citing R2 read
(#49, #50, #51, all closed) to fix this feature's boundary against them.

Grilling agreed with the maintainer. Two decisions widened the issue as written:

- the source may be an `http`/`https` URL as well as a local file path, which #50 had put out of
  scope;
- the command exposes no target-vocabulary argument, and a source declaring no concept scheme is
  refused.

The second came with a wider instruction: the implementation so far has put too much weight on
guarding against what an operator might do, and that posture should be dropped across R2's
surface rather than only here.

Issue labelled `accepted`.

## 2026-08-10 — S1 SPECIFY

`specify` created branch `008-run-skos-vocabulary`, renamed to `008-import-from-command-line` to
match the family's spec-slug style. `spec.md` written: 6 user stories, 16 functional requirements,
6 success criteria. `clarify` taxonomy scan run over the draft and self-answered — 5 further
ambiguities resolved, recorded under `## Clarifications` and integrated into the requirements they
affect. Rationale too long to inline sits in `decisions.md` (D1–D9).

Spec lint green: every FR maps to a story, every story carries acceptance scenarios, the spec
cites G4 and G8, no unresolved markers.

## 2026-08-10 — S2 SETUP

Spec artifacts committed and pushed as `forge-aeo` (push actor = bot). #52 promoted to epic in
place, intake body preserved. Six story sub-issues created and linked: #78–#83, no lifecycle
labels, milestone v0.1.0. Draft PR [#84](https://github.com/SamuelJennings/django-controlled-vocabularies/pull/84)
opened bot-authored, title byte-identical to the epic, `Closes` block covering the epic and all six
stories, milestone v0.1.0.

`forge check-issue-titles` green.

Spec gate brief posted to #52 as a bot comment and sent to the maintainer.

## 2026-08-10 — Spec gate APPROVED

Approved by the maintainer in session, without changes to the spec or the story set. Recorded here
at the moment of approval, ahead of the ledger, so a crash between the gate and S3 cannot lose it.

## 2026-08-10 — S3R DESIGN REVIEW

One reviewer, three lenses, one round. Verdict `request_changes`, risk medium, seven findings, all
`verified`. Every one accepted and remedied in the artefacts before the plan notification; each was
re-checked against the code it cites first.

- **ARCH-001 (high) and SPEC-003** — `ReportRenderer` was US-4's, but US-3's rehearsal line is a
  flag on it and US-1 printed its own output for US-4 to replace, which would have meant editing
  another story's tests. T015 moved to Foundational, T003 renders through it from its first line,
  T019 deleted.
- **SPEC-002 (medium)** — US-2, US-3, US-4 and US-5 were declared independent while four of them
  edited `handle()`. US-4 no longer touches the command; the other three are now sequenced.
- **SPEC-001 (medium)** — verified in `skos.py:216-248` and `:1923`: every refusal names
  `str(path)`, so a fetched document's failures would have named a dead temporary file. Two lines
  added to T001, recorded in D10.
- **SEC-001 (medium)** — the redirect check ran on the response, i.e. after an `ftp://` redirect had
  already been connected and transferred. Replaced with an opener carrying no other handler.
- **SEC-002 (low)** — `urlopen`'s timeout is per read, not per transfer, and nothing bounded the
  fetch size. Byte ceiling added to T008.
- **SPEC-004 (medium)** — FR-003 and SC-002 name no serialization but only Turtle was to be proved.
  T001 now carries a relative-identifier fixture per serialization.
- **ARCH-002 (low)** — the temporary file's serialization-carrying suffix was never consulted.
  Dropped.

## 2026-08-10 — S4 IMPLEMENT — US0 (Foundational, T001/T002/T015), Implementer

`craft-tdd` and `craft-increments` loaded by name, receipts verified against the brief before any
task started. Baseline confirmed green (895 tests, HEAD `a3769f5`) before touching anything. Three
commits, one per task, tree green and clean after each:

- **T001** — `SkosGraph.from_file`, `SkosImporter` and `import_skos` gain a keyword-only `base_uri`,
  passed to rdflib as `publicID`. Measured against the project's own rdflib (7.6.0) across all three
  supported serializations before writing anything: each honours `publicID` identically, so the
  "stop and report" branch in the brief was never reached. Every existing call site is unaffected —
  proven by the whole pre-existing suite (895 tests) passing with zero edits, not just the new tests
  passing. `SkosGraph.from_file`'s three refusals and `SkosImporter.run`'s `source_label` both take
  `base_uri or file`, so a fetched document's refusal names the URL (FR-014).

  The task's own three relative-URI fixtures (one per serialization, tasks.md's own naming) turned
  out to conflict with a pre-existing test: committed under `tests/fixtures/skos/`, they are swept
  by `TestEverySkosPredicateIsReadOrReported`'s directory walk and fail its plain `import_skos()`
  (no `base_uri`) with `REFUSED_IDENTITY` — a `file://` identity is never one of
  `conf.DEFAULT_ALLOWED_URI_SCHEMES`, which is exactly D13/D10's own documented "no base URI"
  behaviour, not a defect. Registering them in that test's own exclusion table would have meant
  editing a test this story does not own, which the brief rules out directly. Built as string
  constants under `tmp_path` in the new tests instead — the same pattern already used elsewhere in
  this file for the missing/unparseable-file cases — so the full suite stays green without touching
  anything pre-existing. Recorded as decisions.md D11.

- **T002** — `controlled_vocabularies/management/__init__.py` and `management/commands/__init__.py`,
  empty, with mirrored `tests/test_management/__init__.py` and `test_commands/__init__.py` (Article
  XIV). The failing-first test is an import check (`ModuleNotFoundError` before, clean import after)
  — the only behaviour a pure package skeleton has to prove. `tests/test_standards.py` unaffected.

- **T015** — `ReportRenderer` in `management/rendering.py`: one translated, `ngettext_lazy`-pluralized
  line per bucket (created, updated, set aside, normalized, absent from source), always yielded, so
  an empty report reads five zero-lines rather than omitting any section (FR-007/FR-008's own
  reasoning, applied here across every bucket, not only the language account). Exercised entirely
  against hand-built `ImportReport`s, per the brief's own acceptance — no import run. Set-aside
  grouping by reason/language, per-entry detail at raised verbosity, and the rehearsal line are
  US-4's and US-3's own tasks, added to this same class later; not anticipated here.

Full verify green throughout: `poetry run pytest -q` (910 passed), `ruff check .`, `ruff format
--check .`, `mypy` (`controlled_vocabularies/exchange/skos.py`, `controlled_vocabularies/management/`
— whole-package `mypy controlled_vocabularies` run once more at the end), `deptry .`. Worktree clean.
One naming/placement choice not dictated by the brief recorded as D11. Next: US-1 (T003–T005) wires
`Command` around `SourceResolver`/`ReportRenderer`.

## 2026-08-10 — S4 IMPLEMENT — US1 (T003/T004/T005), Implementer

`craft-tdd` and `craft-increments` loaded by name, receipts verified against the brief before any
task started. Baseline confirmed green (910 tests) before touching anything — the venv was stale
against the lock file (`rdflib`/`defusedxml` missing); `poetry install` synced it, no source touched.

- **T003** — `Command` in `management/commands/import_skos.py`: one positional `source`, a
  `--format` option, `handle()` calling `import_skos(source, serialization=options["format"])` and
  writing every line through `ReportRenderer` — the command never formats a report itself.
  `Command.help` and both arguments' `help` are `gettext_lazy` from the first line (Article XII);
  Django's own base arguments (`--verbosity` etc.) are excluded from that test since their help text
  isn't this story's to translate. `SkosImportError`/`SkosImportFailed` caught and re-raised as
  `CommandError` — minimal for now, T020 (US-5) is where every fatal finding prints, not this task.

  Tests: `call_command` against `tests/fixtures/skos/rocks.ttl` on an empty database creates the
  scheme and its 5 concepts, output names "8 records created." (scheme + 5 concepts + 2
  collections — confirmed against a throwaway script before writing the assertion, not guessed); a
  second run against the same file reports "8 records updated." / "0 records created." and no
  duplicate concept.

`Command.help = gettext_lazy(...)` fails `mypy` against django-stubs, which types `BaseCommand.help`
as plain `str` — the proxy satisfies Django itself (`str()` runs wherever it's printed) but not the
stub. Wrapped in `cast(str, ...)` for the type checker only, runtime value unchanged; the same
`str | _StrPromise` mismatch models.py already works around for field `help_text`. Not a
decisions.md-worthy choice — a known django-stubs gap, not a design decision.

Verified: `poetry run pytest tests/test_management/test_commands/test_import_skos.py
tests/test_management/test_rendering.py -q` (8 passed), `ruff check` + `ruff format --check` + `mypy`
on the two changed files (clean after one auto-format pass and the `cast` fix).

- **T004** — A missing path is left to `import_skos()`/`from_file`'s own `is_file()` check, already
  wrapped into `CommandError` by T003's handling; one source of truth for "absent." A path that
  *exists* but cannot be opened for permission reasons has no distinct message from that path —
  confirmed against a real 0o000 file before writing anything: it reaches `from_file`'s generic
  parse-failure branch and reports "could not be parsed... Permission denied," not "unreadable."
  `handle()` checks `os.access(path, os.R_OK)` itself, before calling `import_skos()`, and raises its
  own `CommandError` — no edit to `exchange/skos.py`. Recorded as decisions.md D13.

  Tests: a missing path names itself in the message and leaves the database empty; an unreadable
  path (`tmp_path`, `chmod(0o000)`, restored in a `finally`) gets a message distinct from the missing
  one and also leaves the database empty. Permission test skipped under uid 0, which ignores file
  permissions entirely.

Verified: `poetry run pytest tests/test_management/test_commands/test_import_skos.py -q` (8 passed),
`ruff check` + `ruff format --check` (one auto-format pass) + `mypy` on the two changed files.

- **T005** — `--format` reaching `from_file` as `serialization` needed no new production code: T003's
  `handle()` already passes `options["format"]` straight through with no guessing of its own. Both
  new tests passed on first run against the existing `import_skos.py` — not tautological (checked
  before accepting it per `craft-tdd`): each `call_command` genuinely exercises the Command's own
  `handle()`, and a fixture built with an extension `guess_format` cannot resolve (`vocab.mysteryext`,
  real `rocks.ttl` bytes, `tmp_path`-only per decisions.md D11's own precedent — never committed
  under `tests/fixtures/skos/`) either imports when `--format turtle` is given or is refused with
  `from_file`'s existing "not in a serialization this application reads" message when it is not,
  unchanged from #50.

  Tests: the mystery-extension fixture imports with `--format turtle`, asserted on the stored
  `ConceptScheme`; the same fixture without `--format` raises `CommandError` carrying `from_file`'s
  own unsupported-serialization wording and leaves the database empty.

Verified: `poetry run pytest tests/test_management/test_commands/test_import_skos.py -q` (10
passed), `ruff check` + `ruff format --check` + `mypy` on the changed test file (no production file
touched). Full-repo verify (pytest, ruff, mypy, deptry) still to run once, per protocol, immediately
before the completion report.

## 2026-08-10 — S4 IMPLEMENT — US2 (T006-T011), Implementer

`craft-tdd`, `craft-increments` and `craft-security` loaded by name, receipts verified against the
brief before any task started. Baseline confirmed green (918 tests) before touching anything.

- **T006** — `http_stub` (`ThreadingHTTPServer` on port 0, a background thread, `set_response(path,
  status=, body=, content_type=, headers=)` per path so one running server answers several scenarios
  in one test) and `hanging_socket` (a bound, listening socket with nothing accepting or answering,
  for the timeout case) added to `tests/conftest.py`, additive only. Standard library only.

  Tests: `TestHTTPStubFixture` in the new `tests/test_management/test_sources.py` exercises the stub
  directly with plain `urllib.request.urlopen` — a configured 200 with body/content-type, a
  configured 404, an unconfigured path also answering 404, and a second `http_stub` instance getting
  its own fresh port. `hanging_socket` is proven in T010, where the timeout case needs it.

Verified: `poetry run pytest tests/test_management/test_sources.py -q` (4 passed), `ruff check` +
`ruff format --check` (one `A002`/`S310` fix pass) + `mypy` on the two changed files.

- **T007** — `SourceResolver.classify()` in the new `controlled_vocabularies/management/sources.py`:
  a value beginning `http://`/`https://` (case-insensitive) is `"url"`; else `urlsplit(source).scheme`
  of length ≤ 1 is `"path"` (a Windows drive letter parses as a one-character scheme); anything else
  raises `CommandError` naming the scheme. `SourceResolver.__init__` takes `serialization`, not
  `format` — `format` shadows the builtin (`ruff` `A002`), and `serialization` is the name
  `from_file`/`import_skos` already use for the same value.

  Tests: `TestSourceResolverClassification` — `http://…` and `HTTPS://…` as URLs, a bare relative
  filename, `C:/vocab/skos.ttl` and an absolute Unix path as paths, `ftp://host/v.ttl` refused naming
  `ftp`. No fetch, no filesystem access — classification only.

Verified: `poetry run pytest tests/test_management/test_sources.py -q` (10 passed), `ruff check` +
`ruff format --check` + `mypy` on the two changed files.

- **T008** — `SourceResolver.resolve()`/`_fetch()`: for a URL, fetches to a temporary file
  (`tempfile.mkstemp`) in chunks under `_TIMEOUT_SECONDS = 2` and `_MAX_RESPONSE_BYTES = 10 MiB`
  (both plain module constants, no configuration surface), returns a `ResolvedSource(path, base_uri,
  serialization)` with the URL as `base_uri`. `cleanup()` unlinks the temp file; the caller (T011)
  calls it once in a `finally` around resolve-and-import, matching plan.md "the temporary file is
  removed when the command finishes, whether or not the import succeeded" — not tied to `_fetch()`
  itself, so a fetch failure's partial file is also removed by that same `finally`, never by
  `_fetch()` catching its own exception.

  **Deviation from the brief's own design doc, found by this task's own test (decisions.md D15):**
  `research.md` R3 and `plan.md` name
  `build_opener(HTTPHandler, HTTPSHandler, HTTPRedirectHandler, HTTPErrorProcessor)` as the
  http/https-only opener. Built exactly as written, `opener.handlers` still carries `FTPHandler`,
  `FileHandler`, `DataHandler` and `UnknownHandler` — `build_opener` always merges its own defaults
  for any default class not *subclassed* by an argument, and none of the four named handlers
  subclass `FTPHandler`. The redirect-to-ftp test caught this directly: against a non-routable
  target it took 2.0s (this fetch's own timeout) rather than failing immediately, proving
  `FTPHandler.ftp_open` really opened a connection — the exact real network call this opener exists
  to prevent. Fixed by building `OpenerDirector()` by hand and adding only `HTTPHandler`,
  `HTTPSHandler`, `HTTPRedirectHandler`, `HTTPErrorProcessor` and `UnknownHandler` via
  `add_handler(...)`, which bypasses `build_opener`'s default-merging entirely; `UnknownHandler` is
  needed too, since without any handler for `unknown_open`, `OpenerDirector.open()` returns `None`
  for an unhandled scheme rather than raising. Re-run of the same test: `URLError` in under a
  millisecond, no connection. This is a correction to `research.md`/`plan.md`/`tasks.md`'s own text,
  not a new design decision — flagged for Forge in `concerns`.

  Tests: `TestSourceResolverFetch` — a served document fetched to a temp file with the URL as
  `base_uri`; the temp file gone after `cleanup()`; a redirect to another `http` URL followed and its
  body fetched; a redirect to `ftp://10.255.255.1/…` (deliberately non-routable, so a real attempt
  would hang rather than fail fast) refused in under a second, proving no connection was opened; a
  response exceeding the byte ceiling (patched to 16 bytes via `monkeypatch` so the test does not
  transfer 10 MiB) abandoned with `CommandError` naming the URL, temp file gone after `cleanup()`.

Verified: `poetry run pytest tests/test_management/test_sources.py -q` (15 passed), `ruff check` +
`ruff format --check` + `mypy` on the two changed files.

- **T009** — `SourceResolver._resolve_serialization()`: explicit `serialization` (from `--format`)
  first; else `rdflib.util.guess_format(urlsplit(source).path)`, the same function `from_file` uses
  for a local path, applied to the URL's own path; else the response `Content-Type` (captured before
  the fetch's temp-file-writing `with response:` block closes it) mapped through a small dict for the
  three formats this application reads; else `CommandError` naming the source and pointing at
  `--format`. `resolve()` now calls this for a fetched document instead of passing `self.serialization`
  straight through unresolved.

  Tests: `TestSourceResolverSerializationLadder` — explicit `--format` wins even when the URL's own
  extension would guess differently (`.rdf` → `xml`, explicit `turtle` given); the URL extension
  alone decides when no `Content-Type` is sent at all; `Content-Type` decides for a URL with no
  recognisable extension, for both `application/rdf+xml` and `application/ld+json`; neither present
  is refused, message naming `--format`.

Verified: `poetry run pytest tests/test_management/test_sources.py -q` (20 passed), `ruff check` +
`ruff format --check` + `mypy` + `deptry .` on the two changed files (rdflib is already a runtime
dependency; no new import surface for deptry to flag).

- **T010** — Fetch failures, tested through `call_command` per FR-014's own wording ("MUST fail...
  MUST exit non-zero"), which needs `Command.handle()` actually routing through `SourceResolver` to
  produce a `CommandError`. **Deviation from tasks.md's own ordering (see `concerns`):** the minimal
  wiring tasks.md assigns to T011 — `handle()` builds a `SourceResolver`, calls `.resolve()`, passes
  `resolved.path`/`serialization`/`base_uri` to `import_skos()`, and calls `resolver.cleanup()` in a
  `finally` around both — landed in this commit instead, because T010's own acceptance ("it raises
  `CommandError`") is unreachable without it: `import_skos()` raises `SkosImportError`/
  `SkosImportFailed`, and only `Command.handle()`'s existing `except` clause turns those into
  `CommandError`. T011 is left to add the parity and relative-URI proof the spec actually gates on
  (SC-002, FR-003) on top of this same wiring, plus updating `Command.help` and the `source`
  argument's help text to mention a URL (still `gettext_lazy`, Article XII).

  This task's own failing tests caught a second opener gap beyond D15's: without
  `HTTPDefaultErrorHandler`, a non-2xx response makes `.open()` return `None` rather than raise
  `HTTPError`, and `_fetch()`'s `with response:` on `None` raised `TypeError` instead of the
  intended `CommandError`. Added to the opener's handler set and recorded as part of D15 — it opens
  no connection of its own, so it does not reopen the hole the rest of D15 closes. A regression test
  for this (`SourceResolver` returning a 500 directly, not through the command) was added to
  `TestSourceResolverFetch` in `test_sources.py` alongside T010's own command-level tests.

  Tests (`TestImportSkosCommandURLFailureModes`, `test_import_skos.py`): an unreachable host (a
  bound-then-closed local socket — connection refused locally, no real network call), a non-2xx
  status, an HTML body served with a `.ttl`-extensioned URL (extension rung of T009's ladder wins,
  reaches `from_file`'s own parser, which raises `SkosImportError` naming the format and the parse
  error rather than importing an empty graph — confirmed the raw HTML bytes fail `rdflib`'s Turtle
  parser directly before writing the test), and a connection that never answers (`hanging_socket`,
  T006) — each asserts `CommandError` naming the URL and `ConceptScheme.objects.count() == 0`.

Verified: `poetry run pytest tests/test_management/test_commands/test_import_skos.py
tests/test_management/test_sources.py -q` (34 passed), `ruff check` + `ruff format --check` + `mypy`
+ `deptry .` on all four changed files.

- **T011** — The wiring itself, and the `Command.help`/`source`-argument help text mentioning a
  URL, both landed with T010 (see that entry's own deviation note) — nothing left to change in
  production code. This task is the two tests the spec actually gates on. Both passed on first run
  against the already-wired `handle()` — checked before accepting, per `craft-tdd`: each genuinely
  exercises `SourceResolver`'s fetch-then-import path through `call_command`, not a tautology, and
  a manual check that dropping `base_uri` from the flow would resolve `<concept-a>` against a
  temporary file rather than the stub's own address confirms the second test is not vacuously true.

  Tests (`TestImportSkosCommandURLParity`, `test_import_skos.py`): `rocks.ttl` (absolute
  identifiers) imported once over the stub and once from disk in the same test — `Concept`
  `static_uri` set, the scheme's `name`, and the rendered report text are compared equal after
  deleting the URL import's records before the disk import (SC-002). A document whose every
  identifier is relative (`<>`, `<concept-a>`, string constants local to this test class — not
  committed to `tests/fixtures/skos/`, so `TestEverySkosPredicateIsReadOrReported`'s directory walk
  never sees it; served straight from `http_stub`'s in-memory response, so unlike T001's own
  `tmp_path` fixtures (decisions.md D11) no file on disk is involved on the served side at all) is
  imported over the stub and its scheme and concept are found at the stub's own address, with no
  `file://`-prefixed `static_uri` anywhere (FR-003).

  **"Nothing anywhere records the URL"** (FR-003's closing clause) is satisfied by construction
  rather than by a dedicated test: `ConceptScheme`/`Concept` carry no field this story adds or
  writes to (`models.py` untouched — out of scope, per the brief's prohibitions), and the only
  place a fetched document's address appears in the database is as `static_uri` itself, which is
  the document's own declared identity, not metadata about the fetch. The two tests above already
  cover every write path this story adds.

Verified: `poetry run pytest tests/test_management/test_commands/test_import_skos.py
tests/test_management/test_sources.py -q` (37 passed), `ruff check` + `ruff format --check` + `mypy`
on the one changed test file (no production file touched).

## Gates

- **Spec gate:** approved 2026-08-10 by SamuelJennings. No conditions.

### US-1 verification (Forge, independent of the implementer's own run)

- `forge check-receipts --brief dcv-us1-FS008-TASK_BRIEF.json` — green, both receipts verbatim.
- `forge verify --base 7ca2621` — conformance, lint, typecheck, test, build all passed. Full suite
  918 passed (910 at the US-1 base, 8 new).
- `forge tamper-check --base 7ca2621` — two flags, both triaged and approved in decisions.md D14:
  the test file existed at base because T002 created it (117 insertions, zero deletions, skeleton
  tests untouched), and the one "weakening pattern" is a uid-0 guard on the permission test, which
  does not fire where the suite runs (`pytest -rs`: 10 passed, 0 skipped).
- Deviation D13 accepted: the unreadable-path check belongs in `Command.handle()`. Relying on
  `from_file`'s generic parse-failure branch to distinguish an unreadable file would depend on which
  stage the OS happened to raise in.
- Implementer's typing note reviewed: `Command.help = cast(str, _(...))` is a django-stubs gap, not a
  design choice — the runtime value is still the lazy proxy, and the test asserts that directly.
  No decision recorded, correctly.
