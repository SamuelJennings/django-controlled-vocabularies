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
