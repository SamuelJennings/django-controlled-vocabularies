# Decisions — 008 Run an import from the command line

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.
The spec is the contract. This file is why the contract reads the way it does.

## D1 — The command takes a URL as well as a path, and that is a scope addition

The issue says "a command that takes a file". At intake the maintainer widened it: a vendored
vocabulary is pointed at by filesystem path, and one taken straight from its publisher is pointed
at by the address it is served from.

This is worth recording rather than absorbing quietly, because [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50)
put "importing from a URL rather than a file" explicitly out of scope. The exclusion was not an
oversight there. It was the right call for a feature whose subject was reading SKOS. But it means
this feature carries the package's first outbound network request, with failure modes no other
part of the codebase has: an address that does not resolve, a server that answers with an error or
with a landing page, a redirect chain, a connection that never completes. Those are the substance
of US-2, and they are why it is a story of its own rather than a second argument shape inside US-1.

**ADR:** none — a scope note about how this feature's boundary was set, not a standing rule anything downstream abides by.

## D2 — The command offers no way to name a target vocabulary

The issue says the command takes "a target vocabulary", and the programmatic entry point accepts
one. It is not exposed.

The maintainer's ruling at intake was direct: the source declares which vocabulary it is, and a
source declaring no `skos:ConceptScheme` is not SKOS, so it is refused. Two behaviours the
existing `resolve_scheme` supports therefore become unreachable from the command line, and both
were considered and dropped:

- **Supplying a vocabulary for a source that declares none.** `FatalReason.VOCABULARY_UNDETERMINED`
  fires when no scheme is declared and no target is given. With no flag, every such source is
  refused. That is now the intended outcome rather than a gap.
- **Refusing a run whose source declares a vocabulary other than the one expected.**
  `FatalReason.VOCABULARY_TARGET_MISMATCH` exists to catch a deployment script pointed at the
  wrong address. The maintainer ruled that pointing at the wrong file is a downstream mistake and
  not this package's to prevent.

The wider instruction behind the second is recorded because it reaches past this feature: the
implementation so far has put too much weight on controlling what an operator might do. This spec
takes the narrower position deliberately, and the same position should be taken across the rest of
R2's surface rather than treated as a local exception. It is also why the "operator is trusted"
assumption is stated in `spec.md` rather than left implicit — an unstated position reads as an
omission to a reviewer, and gets filed as a finding.

Neither entry point changes: `import_skos` keeps its `scheme` parameter for programmatic callers
who have a genuine reason to use it. What is decided here is what the command exposes.

**ADR:** docs/adr/0004-operator-error-is-not-this-packages-to-prevent.md

## D3 — A source is a path or a URL, told apart by the value

No flag chooses between the two forms. A value beginning `http://` or `https://` is fetched, and
anything else is opened from disk. A value carrying any other scheme is refused as unsupported.

A flag was rejected as making the operator restate what the value already carries.

The classification is a prefix test on `http://` and `https://`, not "does this value parse as
having a scheme". Planning research found the looser test wrong: `urlsplit("C:/vocab/skos.ttl")`
reports a scheme of `"c"`, so a Windows path would be sent down the network path. The refusal of
other schemes therefore applies only to a parsed scheme longer than one character, which is what
keeps a drive letter a path (`research.md` R3).

Refusing an unrecognised scheme, rather than falling through to the filesystem, is the one place
this spec adds a check rather than removing one, and it is not a guard against operator error. A
value like `ftp://example.org/vocab.ttl` is a clearly stated intention that this feature does not
serve. Handing it to the filesystem produces "no such file or directory: ftp://example.org/vocab.ttl",
which is true, useless, and points the operator at the wrong problem. Naming the real reason costs
one branch.

**ADR:** none — the classification rule is sealed inside `SourceResolver.classify`, and the Windows drive-letter trap is recorded at the code that avoids it.

## D4 — A dry run is a real run inside a transaction that is abandoned

The alternative is a predictive dry run: read the source, work out what would happen, report it,
never touch the database.

It was rejected on two grounds. First, it is a second implementation of the import, and it drifts
from the first the moment either changes — the classic failure of a preview that stops matching
what it previews. Second, and decisively, it is silent about exactly the outcomes an operator runs
a dry run to find. Several of the reasons a value is set aside are refusals by the models
themselves at write time: `EMPTY_SLUG` when no usable slug can be derived, `VALUE_TOO_LONG` when a
field rejects a value on length, `STORED_SLUG_INVALID` when an already-stored slug no longer passes
validation. A prediction that never writes discovers none of them, so it would report a clean run
for a file that will not import.

Running the real import and abandoning the transaction gets all of this for free, because
`SkosImporter.run` already wraps its work in `transaction.atomic()`. The dry run is the same code
producing the same report, which is what makes SC-003 — dry run report equals live report — a
meaningful assertion rather than a check that two implementations agree today.

The cost is that a dry run takes as long as a real import and does the same database work before
discarding it. For a vocabulary of any realistic size that is seconds, and an operator who asked
for a dry run has already accepted waiting.

**ADR:** docs/adr/0005-a-preview-is-the-real-operation-rolled-back.md

## D5 — Set-asides exit zero, and only a refusal exits non-zero

A deployment script needs one bit from the exit status, and the question it can act on is whether
the vocabulary is present. A run that stored the vocabulary and set aside four hundred French
labels has answered yes.

Exiting non-zero on any set-aside was rejected because it makes the normal outcome look like a
failure: [#51](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/51) exists
precisely because importing a published vocabulary into a site configured for a subset of its
languages *always* sets values aside. A script that halts on that halts on every import it will
ever run.

A strictness flag — exit non-zero if anything was set aside — was also considered and dropped. It
is a guard against a situation nobody has, and it is the shape of over-specification the maintainer
ruled against at intake. If a deployment ever genuinely needs to fail on set-asides, the report is
available programmatically and the caller can decide.

**ADR:** none — a command-line exit-status convention, local to this command and obvious once stated.

## D6 — Counts by default, entries on request, carried by `--verbosity`

An import of a large external vocabulary can set aside several hundred values. Printing them all
answers "what happened" and buries "what should I change", which is the question #51 was written to
make answerable — its per-language account exists so that adding one language to a site is a
decision made from evidence.

So the default output is counts: per bucket, and within the set-aside bucket per reason, with the
per-language breakdown. Individual entries print at raised verbosity.

Django's `--verbosity` already means exactly this and every management command an operator has ever
run supports it, so it carries the choice rather than a new flag. A bespoke `--detail` would be a
second thing to learn for the same idea.

`report.set_aside_by_reason()` and `report.language_account()` already return this grouped, so the
rendering reads structured data and parses no rendered message — the constraint `report.py`'s own
module docstring names for this feature.

**ADR:** none — a rendering default carried by Django's own `--verbosity`, nothing downstream inherits it.

## D7 — Records the source no longer mentions are reported apart from set-asides

`ImportReport.absent_from_source` and `ImportReport.set_aside` are different kinds of fact and are
rendered separately. A set-aside value is incoming content that was refused. An absent-from-source
record is existing data that was left exactly as it was, because other data may already reference
it and retiring a concept properly is deprecation, which arrives with R4.

Collapsing them into one number would tell an operator that something is wrong with their file when
nothing is. The distinction is #50's, not this feature's. What is decided here is that the
rendering preserves it.

**ADR:** none — this feature renders a distinction #50 already established; the decision is upstream, not here.

## D8 — Retrieval is assumed to need no new runtime dependency

The package's runtime dependencies are Django, `rdflib` and `defusedxml`. Article VII asks for a
stated justification before a fourth, and the standard library covers fetching bytes over HTTP for
one call site.

This is recorded as an assumption rather than a decision because it is a planning question, and it
has one real constraint attached: the bytes must reach the existing safety scan before anything
parses them, so handing a URL straight to `rdflib`'s own remote parsing is not available — that
would skip the scan `UnsafeRdfXmlError` and `UnsafeJsonLdError` exist to raise. Whatever fetches
must return bytes to the path a local file already takes.

**ADR:** none — an assumption that held. No dependency was added, so there is nothing for a future engineer to relitigate.

## D9 — The dry run names itself in its own output

A dry run's report is, by construction, identical to a live run's. That is the point, and it is
also the risk: an operator scrolling back through a terminal sees "created 212 concepts" and has no
way to tell which kind of run produced it.

So FR-010 requires the output to say that nothing was kept. It is one line, and it is the only
difference between the two renderings, which is why it has to be deliberate rather than assumed.

**ADR:** none — folded into 0005, which states it as the consequence of previewing by rollback.

## D10 — A fetched document's identifiers resolve against the address it came from

Found during planning research, after the Spec gate, and it corrects text drafted here rather than
anything the maintainer approved.

`rdflib` resolves relative identifiers against the base URI, and the base URI is wherever the
document was read from. Published SKOS routinely uses relative forms — `<>` for the scheme,
`<concept-a>` for a concept — so the choice is load-bearing. Measured on the project's own rdflib,
the same bytes give `file:///tmp/tmpa1b2c3/concept-a` when parsed from a temporary file and
`https://example.org/concept-a` when parsed with the publisher's address as base.

The first is wrong in a way this package cannot tolerate. Article IX makes a concept's URI its
identity, #49 built every matching path on the identifier a publisher assigned, and a temporary
directory name is neither stable across runs nor meaningful to any other system. A re-import would
create a second copy of every concept rather than updating the first.

So the fetch is not merely "download, then import the file". The address has to travel with the
bytes into the parse. `rdflib.Graph.parse` takes `publicID` for exactly this, which means
`SkosGraph.from_file` gains an optional base-URI argument threaded through `SkosImporter` and
`import_skos`. It defaults to today's behaviour, so no existing caller changes and a local file
still takes its base from its own location, which is #50's D13 and stays true.

This is the one place the feature touches the exchange layer, and the spec's "adds no import
behaviour" line survives it: what a source *means* is unchanged, and what is added is the ability
to tell the reader where a source came from when the reader cannot work it out for itself.

The same keyword also decides what a refusal calls the source, which the design review caught. Every
`SkosImportError` in `from_file` names `str(path)`, and `SkosImporter.run` builds `source_label` from
the same value, so without this a fetched document's every refusal — not found, unsupported
serialization, unparsable, ambiguous scheme, undetermined scheme — would name a temporary file that
no longer exists by the time the operator reads the message. Both take `base_uri or file`, which is
today's value whenever no base URI is given. FR-014 asks for a refusal that names the source, and
this is where that is delivered rather than in the fetch.

SC-002 was amended in the same pass. As gated it required a URL import and a disk import of
identical bytes to produce identical records, which is precisely false for a relative-URI document
and false in the direction where the URL form is the correct one. It now requires the publisher's
URIs either way, and identical results only where the identifiers are absolute.

**ADR:** docs/adr/0006-a-document-identity-comes-from-where-it-was-published.md

## D11 — T001's relative-URI fixtures are built under `tmp_path`, not committed under `tests/fixtures/skos/`

Found implementing T001. `tasks.md` names three committed files —
`tests/fixtures/skos/relative-uris.ttl/.rdf/.jsonld` — and that is what was tried first. Committing
them there breaks `TestEverySkosPredicateIsReadOrReported` (`tests/test_exchange/test_skos.py`,
T033/FIX 13), which walks every file in the directory and runs a plain `import_skos()` (no
`base_uri`) against each, requiring `report.fatal == []`.

That failure is not incidental. A document whose every identifier is relative can only ever resolve,
with no `base_uri` given, to a `file://`-scheme identity — D13's own documented behaviour, and
exactly what T001's second Given/When/Then scenario requires as its "no base URI" branch. `file` is
not in `conf.DEFAULT_ALLOWED_URI_SCHEMES`, so `validate_static_uri` refuses it every time
(`REFUSED_IDENTITY`). No content for these three fixtures avoids this: it is what "relative
identifiers, no base URI" *means*, not a fixable defect in the fixtures. The corpus already carries
this exact shape nine times over (`refused_uri_scheme.ttl`, `no_scheme_declared.ttl`,
`two_vocabularies.ttl`, and six more), each registered by name in that test's own
`_PREDICATE_COVERAGE_EXCLUDED_FIXTURES`, with a comment naming the dedicated test class that
exercises it instead — but registering a tenth entry there means editing a pre-existing test, which
this story's own governing rule forbids outright: the base-URI change is proven additive by the
*entire* pre-existing suite passing with zero edits to any existing test, not most of it.

So the three documents are built as string constants in `tests/test_exchange/test_skos.py`
(`TestBaseUriThread`) and written to `tmp_path` per test, the same pattern this file already uses
for `TestPreferredLabelTagCounts.test_counts_reflect_the_whole_file_not_any_one_concept` and the
missing/unparseable-file cases in `TestReadGraph`. This satisfies every clause of T001's own
Given/When/Then (all three serializations, both with and against a given `base_uri`, the refusal
messages naming the URL) without touching a file `TestEverySkosPredicateIsReadOrReported` walks.

**Revisit if:** a later story wants these three documents committed as reusable fixtures for its own
tests (US-2's URL/disk parity test, T011, is the likely candidate — it already needs a served,
relative-identifier document). At that point the right fix is a fixtures subdirectory `ALL_FIXTURES`
does not walk (or an explicit opt-out on that constant), decided with the story that needs it rather
than pre-built here on spec.

**ADR:** none — a test-fixture placement choice inside one story, not a production-code rule. Nothing outside this feature's own tests inherits it.

## D12 — US0's tamper flag on `tests/test_exchange/test_skos.py` is approved as additive-only

`forge tamper-check --base a3769f5 --head <US0 tip>` raised one flag,
`modified_preexisting_test` on `tests/test_exchange/test_skos.py`. Triaged and approved.

The check classifies from `git diff --name-status` alone, so any file matching the test pattern that
carries an `M` status is flagged — appending a new test class to an existing test file is
indistinguishable, at that granularity, from rewriting one. The diff here is 186 insertions and zero
deletions: no pre-existing test function, assertion or fixture was touched, and no weakening
construct (`skip`, `xfail`, commented assertion) was introduced. The additive claim T001 rests on is
independently confirmed by the full suite passing at 910 with no edits to any existing test.

Two additions were made to that file: `TestBaseUriThread` (new class, appended) and
`TestImportSkosVocabulary::test_a_refusal_names_the_base_uri_when_given` (new method inside an
existing class, which is what makes the status `M` rather than a clean append).

**Revisit if:** a later story in this feature raises the same flag for a different reason. The
recurring-flag shape itself — every story that adds a method to an existing test class trips this —
is a kit observation for the S8 retro, not a change to make mid-feature.

**ADR:** none — a guardrail triage local to this run, nothing downstream inherits it.

## D13 — T004's unreadable-path check lives in `Command`, not in `exchange/skos.py`

Found implementing T004. The brief requires a message distinct from "not found" for a path that
exists but cannot be opened for permission reasons, and separately prohibits editing `skos.py`
without stopping the story.

`SkosGraph.from_file`'s own `is_file()` check returns `True` for an unreadable file (`Path.is_file`
needs execute permission on the parent directory, not read permission on the file itself), so a
0o000 file reaches the parse. Depending on serialization, that parse fails inside the pre-flight
scan's `read_bytes()` (RDF/XML, JSON-LD) or inside rdflib's own file open (Turtle), and either way
is caught by `from_file`'s generic `except Exception` and reported as `"could not be parsed as
%(format)s: %(error)s"` with the raw `OSError` text interpolated — confirmed against a real 0o000
file before writing anything (`[Errno 13] Permission denied: '<path>'`). That message is factually
distinct from "could not be found" already, but it says "could not be parsed," not "is not
readable" — an accident of which stage the OS raised in, not a designed distinction, and fragile
against a future change to the scan/parse order.

`Command.handle()` checks `path.is_file() and not os.access(path, os.R_OK)` before calling
`import_skos()` at all, and raises `CommandError` with its own `"'%(file)s' exists but is not
readable."` directly. A missing path still falls through to `import_skos()`/`from_file`'s own
check — one source of truth for "absent," not duplicated.

**Revisit if:** US-2 makes a fetched URL's temporary file hit this same branch — a downloaded copy
is written by the command itself and should always be readable, but if that ever changes the
distinct message no longer applies only to a local path.

**ADR:** none — a targeted fix within this task's own file, nothing downstream inherits it.

## D14 — US-1's two tamper flags are triaged as additive, and the permission test's skip guard is approved

`forge tamper-check --base 7ca2621` raised two flags on US-1's diff. Both are approved; neither is a
weakened test.

**`modified_preexisting_test` on `tests/test_management/test_commands/test_import_skos.py`.** The file
existed at the story base because T002 created it as the skeleton's own test. The gate classifies on
git file status alone, so appending classes to a file it did not create always flags — the same
mechanism as D12. The diff is 117 insertions and zero deletions: the two skeleton tests are untouched,
their assertions unchanged, and four new classes sit below them. Verified by reading the diff, not
inferred from the insert/delete ratio.

**`weakening_patterns_added`, one occurrence.** It is
`@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0)` on
`test_an_unreadable_path_is_reported_distinctly_from_a_missing_one`. A process running as uid 0
ignores the file mode entirely, so `os.access(path, os.R_OK)` returns `True` for a 0o000 file and the
scenario the test describes cannot be constructed — the guard prevents a false failure, it does not
excuse one. Confirmed it does not fire where the suite actually runs: `pytest -rs` on this file
reports 10 passed and zero skipped locally, and GitHub Actions' Ubuntu runners execute as `runner`,
not root. A conditional skip that silently swallowed the case on the machines we test on would not
have been approved.

**ADR:** none — a guardrail triage, not a design decision.

## D15 — `build_opener` does not give an http/https-only opener; `OpenerDirector` built by hand does

Found implementing T008. `research.md` R3 and `plan.md` "Source resolution" both name
`urllib.request.build_opener(HTTPHandler, HTTPSHandler, HTTPRedirectHandler, HTTPErrorProcessor)`
as the opener that carries no handler for any scheme but http/https, so a redirect onto `ftp`
fails before a connection is attempted. Built exactly as written and inspected
(`opener.handlers`), it still carries a live `FTPHandler`, `FileHandler`, `DataHandler` and
`UnknownHandler` — `build_opener`'s own docstring says why: "If any of the handlers passed as
arguments are subclasses of the default handlers, the default handlers will not be used," and it
always adds its own defaults for every default class not matched that way. None of the four
handlers named override `FTPHandler`.

Confirmed the consequence directly, once as a spike and once as this task's own failing test: a
`SourceResolver` fetch of a stub URL that 302-redirects to `ftp://10.255.255.1/vocab.ttl` (a
non-routable address, chosen so a real connection attempt would hang rather than fail
immediately) took 2.0s — the fetch's own socket timeout — meaning `FTPHandler.ftp_open` really
ran and really opened `ftplib`'s connection. That is the exact real network call this feature's
one security-motivated check exists to prevent (plan.md "Design", Article V), made worse by
`build_opener` supplying it silently.

The opener that matches the stated design is `OpenerDirector()` with only
`HTTPHandler`, `HTTPSHandler`, `HTTPRedirectHandler` and `HTTPErrorProcessor` added via
`add_handler(...)`, bypassing `build_opener`'s default-class merging entirely. That opener alone
returns `None` from `.open()` for an unhandled protocol instead of raising (`OpenerDirector._open`
falls through to an empty `unknown_open` chain and returns nothing), so `UnknownHandler` is added
too — its `unknown_open` only raises `URLError('unknown url type: ...')`, never opens a socket.
Confirmed against the same redirect target: `URLError` raised in under a millisecond, not 2s.

**A second, related gap found implementing T010's own failing test.** The same hand-built opener,
still missing `HTTPDefaultErrorHandler`, turns a non-2xx response into `.open()` returning `None`
rather than raising `HTTPError`: `HTTPErrorProcessor.http_response` delegates to
`OpenerDirector.error()`, which calls a chain keyed on `self.handle_error` — empty for both the
`http` and `default` buckets with no `HTTPDefaultErrorHandler` registered — and returns `None`
when nothing in the chain handles it. `_fetch()`'s `with response:` on a `None` then raised
`TypeError`, caught immediately by `call_command("import_skos", <500-status URL>, ...)` in T010's
own test rather than the intended `CommandError`. `HTTPDefaultErrorHandler` opens no connection
of its own — it only turns a completed response's non-2xx status into `HTTPError` — so adding it
does not reopen the hole the rest of this decision closes. Final handler set: `HTTPHandler`,
`HTTPSHandler`, `HTTPRedirectHandler`, `HTTPErrorProcessor`, `UnknownHandler`,
`HTTPDefaultErrorHandler`.

**Revisit if:** a later change to this opener re-introduces `build_opener` for convenience —
`OpenerDirector` + explicit `add_handler` calls has to stay the shape as long as excluding a
scheme's handler is the control.

**ADR:** docs/adr/0007-outbound-fetches-are-restricted-by-removing-handlers.md — corrects a factual claim in `research.md`
R3, `plan.md` "Source resolution" and `tasks.md` T008, which name `build_opener` for this and
should be corrected alongside.

## D16 — The fetch timeout and byte ceiling are set against published vocabularies, not fixtures

**Stage:** S4 verification, US-2 · **Status:** accepted

T008 landed `_TIMEOUT_SECONDS = 2` and `_MAX_RESPONSE_BYTES = 10 MiB`. `plan.md` and `tasks.md`
both say "one constant, no configuration surface" and name no number, so these were the
implementer's own choice and were flagged for a maintainer decision in its report.

Both were set to what the tests needed rather than to what the feature is for. The command exists
to vendor a *published* vocabulary, and the published thesauri operators actually point it at fail
on both values: a large vocabulary is commonly serialized per request, so first-byte latency over
two seconds is ordinary rather than a fault, and the widely-vendored thesauri run to tens of
megabytes in RDF/XML. Shipping those numbers would have refused ordinary sources with a message
about a server that had stopped answering.

Raised to **30 seconds** and **50 MiB**. Both still bound what the remote server chooses — a
server that has stopped answering, or one that does not intend to stop sending — which is the
control's stated purpose, and neither is a guard against operator error.

The one test that consumed the real timeout (a non-responding socket) now monkeypatches it to
0.5s, as the byte-ceiling test already did for its own constant. A test's convenience is not a
reason to ship a value that is wrong in production.

**Revisit if:** an operator reports a legitimate source refused by either ceiling, which is the
signal that this should become configurable rather than a larger constant.

**ADR:** no — an internal constant, recorded here.

## D17 — The absent-from-source detail section is not gated by verbosity

**Stage:** S4 implementation, US-4 (T017/T018) · **Status:** accepted

FR-007 restricts verbosity to one specific thing: "Individual entries [of the set-aside account]
MUST be printed only at raised verbosity, and MUST NOT be printed by default." FR-008, which
governs `absent_from_source`, states only that it must be reported separately from set-asides; it
says nothing about volume or verbosity. `plan.md` "Rendering" lists "the records absent from the
source" as its own pipeline stage, distinct from the sentence naming the verbosity-gated set-aside
detail.

The distinction FR-007 draws is about volume: a large external vocabulary can set aside several
hundred *incoming* values, which is what raised verbosity exists to let an operator opt into.
`absent_from_source` names *existing* records the run left untouched — ordinarily few, since it
requires records already in the database that a re-import's file stopped mentioning — and D7's own
point is that this bucket needs to be visible precisely so an operator does not mistake "nothing
changed here" for "something is wrong". Hiding it behind a flag would work against that.

So `_render_absent_from_source_detail()` is unconditional: every URI in `absent_from_source` is
named every time the report renders one, regardless of `verbosity`.

**Revisit if:** a re-import of a very large vocabulary against a site that already holds many more
records than the file mentions produces an absent-from-source section long enough to bury the rest
of the report — the same problem FR-007 solved for set-asides, arriving late for this bucket.

**ADR:** no — a rendering-only interpretation of FR-007/FR-008, recorded here.

## D18 — `--verbosity` is wired into the renderer at convergence, and a command-level test holds it there

**Decided by:** convergence, after US-4 · **Tasks:** T018 (and T019, deleted)

T018 gave `ReportRenderer` a `verbosity` argument and gated per-entry set-aside detail on it,
exactly as FR-007 and D6 specify. Nothing passed it. `handle()` constructed the renderer with
`dry run=` alone, so `--verbosity 2` changed nothing an operator could see, and the option
FR-007 names as its own mechanism was inert.

The gap is planning's, not the story's. T019 was the task that wired the renderer into `handle()`;
it was deleted when T015 moved into the foundational phase, on the reasoning that with the renderer
already in place there was no US-1 output left to replace. That reasoning held for the call site
and not for its arguments, and the argument T018 added later had nowhere to be passed from. US-4's
brief prohibited touching `commands/import_skos.py` — US-5 owned `handle()` in parallel — so the
implementer could not have closed it, and its own tests construct the renderer directly, which is
why they passed against an inert option.

`handle()` now passes `verbosity=options["verbosity"]`, which Django populates for every command.
Two tests in `test_import_skos.py` go through `call_command` rather than the renderer: the default
prints no per-entry line, and `verbosity=2` prints every entry's own `render()`. Reverting the one
argument fails the second, which is the property that makes them a gate rather than a restatement
of T018's own tests.

**Revisit if:** a future option of this command needs the same treatment — the lesson is that
deleting a wiring task after moving the thing it wires leaves later arguments unrouted.

**ADR:** no — a wiring defect and its regression test, recorded here.

## D19 — The JSON-LD context scan walks nested arrays, because rdflib does

**Decided by:** S6 review, security lens (SEC-701) · **Files:** `exchange/safety.py`

`_check_context_value`'s array branch checked `str` entries and `dict` entries and silently
ignored anything else. `Context._prep_sources` ends with `if isinstance(source, list):
self._prep_sources(...)` — it recurses into a nested array to any depth and hands every string
it reaches to `_fetch_context`, the same `urlopen`-backed path a bare string `@context` uses.
So `{"@context": [["http://…"]]}` passed the scan and was fetched, `[["file:///…"]]` read a
local file into the graph, and `[[{"@import": …}]]` reached the other fetch-triggering key the
same way — while the flat forms either side of them were correctly refused. Measured on the
branch before the fix, not inferred.

The remedy is a recursion rather than a second hard-coded level: every entry of an array goes
back through `_check_context_value` whatever its type, so a string is refused, a dict is checked
for `@import`, and an array is walked. Two fixtures and a depth-4 case pin it, and an inline
term map nested in an array is the control that the walk did not become a blanket refusal.

This is a pre-existing hole in D36/D47's scan, not something #52 introduced. What #52 changed is
who chooses the document: until this feature the file came from a curator's own disk, and now it
can come from a remote server. That is why the lens caught it here, and why it is high rather
than a note.

**Revisit if:** rdflib changes how it resolves contexts — the scan tracks `_prep_sources` and
`_read_source`, and a new fetch-triggering key would need its own branch.

**ADR:** no — implements ADR 0007's existing posture; the ADR needs no amendment for it.

## D20 — A fetched document's base URI is the address it was served from, not the one typed

**Decided by:** S6 review, correctness lens (CORR-001) · **Files:** `management/sources.py`

`resolve()` returned `base_uri=self.source`, the raw argument, and `_resolve_serialization`
guessed the extension from it. Both now come from `response.url`, the address urllib actually
landed on.

RFC 3986 §5.1.3 makes the final URL the base a relative identifier resolves against, and a
published vocabulary is very often behind a redirecting address — a PURL, a w3id, a `/latest`
alias. Taking the typed address stored every relative identifier under a URI its publisher never
assigned, so a later import from the canonical address created a second copy of the whole
vocabulary: exactly the outcome D10 exists to prevent, reintroduced along a path D10 never
covered. The existing redirect test asserted only on the returned bytes, so nothing pinned which
of the two addresses a redirected fetch reported.

The serialization ladder moves for the same reason and gains something: an extensionless PURL
redirecting to a `.ttl` used to fall through the extension rung to `Content-Type` or a refusal,
and now reads the extension straight off the served address.

Error messages still name `self.source`. An operator who typed an address should be told about
the address they typed, and that is unchanged.

**Revisit if:** a publisher is found whose canonical identity is the alias rather than the target.
The choice would then be per-source and would need an option, which no evidence yet asks for.

**ADR:** no — an RFC-conformance fix inside D10's existing decision, recorded here.

## D21 — A total transfer deadline, because neither existing bound catches a trickle

**Decided by:** S6 review, security lens (SEC-703) · **Files:** `management/sources.py`

`_TIMEOUT_SECONDS` is a per-socket-read timeout and `_MAX_RESPONSE_BYTES` counts bytes, so a
server that answers continuously but slowly resets the read timeout forever and never approaches
the ceiling. Measured: a stub trickling one byte every 20 seconds was still being read after 65
seconds having transferred 3 bytes, and would never have stopped. ADR 0007 named the byte ceiling
as the answer to a slow server, which was wrong in the one case where slowness is deliberate; the
ADR is corrected in the same change.

`_MAX_TOTAL_SECONDS = 600` bounds elapsed time in the same place the byte ceiling is checked. It
is generous against the same real vocabularies D16 sized the other two against — 50 MiB inside
ten minutes is 85 KiB/s — and it is a stop, not a rate limit. The reachable consequence was a
hung deployment or CI step rather than anything worse, which is why this is a low finding fixed
with one constant and one comparison.

**Revisit if:** a legitimate publisher is found that cannot deliver inside ten minutes. The
constant moves; the bound stays.

**ADR:** no — an amendment to ADR 0007, made in the ADR itself.

## D22 — Control characters are stripped from every document-supplied value in a report

**Decided by:** S6 review, security lens (SEC-702) · **Files:** `exchange/report.py`

A report entry's subject and params are text the source document chose — a `skos:prefLabel`,
a language tag, a predicate name — and since #52 that document can be one a remote server hands
over, rendered straight to an operator's terminal. `\x1b[2K\r` erases the line being written and
`\x1b[1A` moves the cursor over the one above, so a published label could overwrite the account
of itself. Measured on the branch: a refusal printed `'Innocent\x1b[2K\rALL CLEAR - 0 problems
found.\x1b[1A' has no identifier that survives re-serialization`, escapes intact. It matters most
under `--dry-run`, whose entire product is the text an operator reads before deciding to commit.

`_render_params` strips the C0 and C1 ranges from every string value. That function is the one
boundary all three entry kinds pass through, so fatal, set-aside and normalized entries are
covered by construction rather than one at a time — the same reason D64 put the empty-language
substitution there.

The range includes newline and tab, which the usual carve-out keeps. A report entry is one line
by construction, so an embedded newline both breaks the format and lets a document write a line
of the account itself.

This is not a guard against operator error, which ADR 0004 rules out of scope. It is the other
side of that ruling, which ADR 0007 states: content chosen by a remote server is untrusted.

**Revisit if:** a report value ever needs to carry a newline legitimately — a multi-line
definition rendered as a block rather than a line would need its own path.

**ADR:** no — implements ADR 0007's existing posture.

## D23 — `--verbosity 0` prints nothing, which is Django's own contract for it

**Decided by:** S6 review, correctness lens (CORR-004) · **Files:** `management/rendering.py`

D6 justified carrying Django's `--verbosity` rather than inventing a flag on the grounds that it
"already means exactly this and every management command an operator has ever run supports it".
`render()` branched only at `>= 2`, so 0 printed the full report and the borrowed convention was
honoured in one direction and not the other. A deployment script silencing this command the
documented Django way got the whole account on stdout.

`render()` now yields nothing at 0, including the dry run line: at 0 there is no output for it
to qualify, and a dry run writes nothing anywhere regardless. A refusal is unaffected, because
it is raised as a `CommandError` rather than rendered.

**Revisit if:** an operator wants counts without detail and detail without counts, which would be
three levels rather than Django's four and would argue for a flag after all.

**ADR:** no — completing D6's stated convention, recorded here.

## D19 — The flag is `--dry-run`, not `--rehearse`

Renamed at the merge gate on the maintainer's instruction, and the reasoning is worth keeping
because the original name was chosen for a bad reason.

`--rehearse` came from the issue's own prose, which described wanting "a rehearsal mode". That was
the maintainer describing the idea, not naming the flag, and it was taken as though it were the
latter. Nothing else recommended it.

`--dry-run` is what this ecosystem already uses. Django's own `makemigrations` and `collectstatic`
both carry it, so an operator running a Django management command has met the name before and
expects it here. A package that spells the same idea differently makes its user learn a synonym for
no gain.

The one argument for the old name was that `--dry-run` can suggest a prediction, where this
performs the import in full and rolls it back. That distinction matters to a maintainer, and it is
recorded in ADR 0005 where a maintainer will find it. It does not matter to an operator at a
terminal, whose expectation of `--dry-run` — show me what would happen, keep none of it — is
exactly what the flag does.

The rename runs through the command, `ReportRenderer`'s keyword, the `_DryRun` sentinel, the tests,
the README, the CHANGELOG, and the `CONTEXT.md` glossary entry, which is now **Dry run**. The
output line reads "This was a dry run: nothing was kept." No message catalog has shipped, so no
translation is orphaned. The issue text quoted in `spec.md`'s Input line keeps the maintainer's
original wording, because a quotation is a record of what was said.

**ADR:** none — a naming decision recorded where it happened. ADR 0005 owns the mechanism and is
unaffected by what the flag is called.

## D20 — `--help` was broken, and the test that should have caught it enforced the break

Found at the merge gate while confirming the `--dry-run` rename had reached the operator-facing
help. `python manage.py import_skos --help` did not print. It raised:

```
TypeError: expected string or bytes-like object, got '__proxy__'
```

argparse lays out the parser description and every argument's help through `re.sub`
(`HelpFormatter._fill_text` and `_split_lines`). Neither accepts a `gettext_lazy` proxy. Django
hands `Command.help` straight to argparse as the parser `description` and never calls `str()` on
it, so the proxies survived into the formatter and the first thing an operator runs failed
outright.

The comment in the code asserted the opposite — that "str() is called wherever it's printed" —
which was never true of this path and was never checked.

**The fix** forces the proxies at parser-construction time, not at class definition. `create_parser`
runs once per invocation with the active language already set, so this is both the latest safe
moment and a correctly translated one. Forcing at import would bake in whichever language happened
to be active when the module loaded.

**What let it through is the more useful part.** This feature's own test asserted:

```python
assert isinstance(action.help, Promise), f"{dest} help is not lazily translatable"
```

That test passed for the entire run, and it passed *because* the command was broken. It had taken
"translatable" to mean "the object is still a lazy proxy at parse time", when Article XII asks that
the string be wrapped at its source and resolved in the active language when displayed. Forcing at
parser build satisfies the article exactly. The test encoded the mechanism it happened to observe
rather than the requirement, and then defended it.

Neither review lens caught this, and the reason is worth naming: every test exercised the command
through `call_command`, which builds no help output. Nothing in the suite had ever rendered
`--help`. A surface with no test is invisible to a reviewer reading tests for coverage.

The replacement asserts the behaviour instead: `format_help()` returns text containing the
description and each flag. It was proven against the defect — the fix was reverted, the test failed
with "source help reaches argparse as a proxy, which breaks --help", and the fix restored. The
source-level wrapping Article XII actually requires stays enforced by the AST sweep in
`tests/test_standards.py`, which reads the code rather than the runtime types, and is unaffected.

**ADR:** none — a defect and its regression test, recorded here. The general lesson (a test that
asserts a mechanism rather than a requirement can hold a bug in place) is not specific enough to
this codebase to constrain future work as a standing rule.
