# Decisions — 006 Import a published SKOS vocabulary from a file

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking. Each
entry says what was unclear, what was chosen, and why the choice is defensible. Written at S1;
extended at S3 and during implementation as further decisions are taken.

## D1 — The escrow promise is deferred, and the report carries its weight meanwhile

`CONTEXT.md` and constitution Article XI both promise that nothing imported is dropped: unknown
predicates are held verbatim as escrow in a JSON document and re-emitted on export. R1 shipped no
such document. `Concept` holds a scheme, a label, a slug, and an identifier; labels and notes are
relational rows; there is no notation, no mapping, and nowhere for a predicate the models do not
model.

A real published vocabulary carries all of those. So this feature had two possible shapes: build
the document store as part of import, or import what the models hold and report the rest.

Chosen: report the rest. Three reasons.

1. Escrow only pays for itself when something reads it back out, and that is export (R4). Verbatim
   storage with no export is a write-only column.
2. The document store is a storage redesign of the concept model — `CONTEXT.md` describes a shared
   and a translated document with a predicate registry driving routing. Folding that into the
   feature that first reads a file makes both harder to review and couples a reading capability to
   a schema migration.
3. The promise Article XI actually makes a curator is that nothing disappears *silently*. A report
   that names every set-aside value, with its reason, keeps that promise. It does not keep the
   round-trip promise, which is G4's business and R4's feature.

Confirmed with the maintainer at grilling. The consequence to carry forward: **Article XI's escrow
clause is not satisfied by this feature and must not be described as satisfied.** The escrow store
is its own feature, sequenced with export.

## D2 — Language filtering lands here whether or not it was meant to, and that narrows #51

`ConceptLabel.clean()` and `ConceptNote.clean()` each refuse a `language` outside
`settings.LANGUAGES`, and `Concept.add_label` / `Concept.add_note` — the write path R1 built for
this — call `full_clean()` before saving. An import that wanted to keep every language a published
file carries would have to bypass those helpers and write rows directly, defeating a stated model
invariant to store content nothing in the app can display.

So the filtering #51 was written to own happens here, mechanically, as a consequence of the models.
What #51 is left owning:

- the curator-facing quality of the report — "told plainly what was left behind", grouped and
  counted rather than a raw list of set-aside entries;
- the explicit guarantee, tested, that adding a language to the site and re-importing populates it
  for concepts already present. This feature makes that true as a side effect of D5 (the file is
  authoritative for records it contains), but true-by-accident is not the same as guaranteed, and
  the guarantee is what a curator relies on.

This is flagged at the Spec gate rather than absorbed, because it changes what a sibling issue is
for and that is the maintainer's call, not this feature's.

## D3 — A blank-node concept or collection fails the run rather than being set aside

Every other unusable thing in a file is set aside so the rest can import. An identity is different.
The whole re-run contract is "match each record by the identifier it was published under", and a
blank node supplies no identifier that survives re-serialization — it is scoped to one parsing of
one file. Inventing an identifier would produce a record that cannot be matched next time, so the
next run would create a second copy of it, which is precisely the duplicate-on-re-import failure
the upsert rule exists to prevent.

Silently skipping it is not better: a curator whose file uses blank nodes for concepts would get a
partial vocabulary with no signal proportionate to the problem. Failing the run and naming what was
wrong is the honest outcome, and it is consistent with the maintainer's rule at grilling — a
concept whose identity is missing or refused is fatal.

The exception is structural: an ordered collection's members are carried by an RDF list, which is
made of blank nodes by construction. Those are not identities and are read normally.

## D4 — The vocabulary's default language comes from the file

`Concept.label` is the preferred label in the vocabulary's effective default language, it is
required, and the slug derives from it. `ConceptLabel` additionally *refuses* a preferred row in
that same language, because that would plant a second identity anchor. So the default language is
not a cosmetic setting — it decides which of a concept's preferred labels becomes the concept's own
name and which are stored beside it.

If the default language were simply the site's, importing a vocabulary published only in French
into a site whose default is English would leave every concept with no label in the anchor
language, and by FR-006 every one of them would be set aside. The import would "succeed" and
produce nothing.

Chosen: take it from the file where the file says — the language the vocabulary declares itself in,
otherwise the language most of its preferred labels use — and fall back to the site's default when
neither is a language the site is configured for. `ConceptScheme.default_language` already exists,
is already validated against the configured languages, and already falls back to the site default
when blank, so this uses the mechanism R1 built rather than adding one.

## D5 — Authoritative for what it contains, silent about what it does not

The re-run rule has two halves that are easy to conflate. For a record the file contains, the file
wins outright: a label the publisher corrected away is removed here too, or a re-import can never
mean "bring up to date" and stale values accumulate with no way to clear them. For a record the
file does not mention, nothing is touched, because something downstream may already reference it
and removing it would break real data.

The asymmetry is deliberate and is the maintainer's decision at grilling. It also gives #51 its
additive behaviour for free: a concept present in the file gets every value the file carries in
every configured language, so configuring a new language and re-running fills it in.

Retiring a concept that has genuinely gone from the source is deprecation, which is R4's lifecycle
work (#19). Deletion is never a consequence of reading a file.

## D6 — Slugs are derived by R1's rule, disambiguated by suffix, and allowed to move

An imported concept has no slug in its source — SKOS has no such notion. R1 already derives one
from the label on save unless `slug_is_manual` is set, so the import needs no rule of its own
beyond collision handling: two concepts in one vocabulary can carry the same preferred label,
which derives the same slug, which the unique `(scheme, slug)` constraint refuses. A deterministic
numeric suffix resolves it, so the same file imported twice produces the same slugs.

Deriving the slug from the identifier's last segment was considered and rejected: it produces
unreadable local addresses for the many vocabularies whose identifiers are opaque codes, and it
couples a local display concern to an identity that must never be altered to suit it.

A slug moving on a later re-import, because the publisher renamed the concept, is accepted rather
than pinned. #49 established that a local URL follows a rename while the identifier does not, and
pinning imported slugs would contradict that for no gain — identity, and therefore every stored
reference, lives in the static URI.

## D7 — A structured report, not a log

FR-015 requires the report to be data rather than prose. #52 has to render both a summary and a
rehearsal preview from it, and #51 has to group and count what was set aside. Both become
string-parsing exercises if the report is text, and every improvement to the wording then breaks
them. The report is therefore the feature's public contract alongside the import itself, and its
shape is fixed here even though its rendering is not.

## D8 — Failure is all-or-nothing, and the fatal set is small

A partially applied import leaves a curator unable to answer "what state is my vocabulary in?"
without diffing it against the source by hand, which is worse than no import. So a run lands whole
or not at all.

The fatal set is deliberately small: a file that cannot be read, and an identity that is missing or
refused. Everything else — a concept with no usable name, a relationship pointing outside the file,
a value in an unsupported language, a predicate with no home — is set aside, because a published
vocabulary is routinely a partial export of a larger one and refusing those would make real files
unimportable. Problems are collected rather than raised at the first, so one run tells a curator
everything wrong with their file.

## D9 — RDF/XML is scanned before it is parsed, and that costs a dependency

Added at S3, from a measurement rather than a worry. Article V names imported RDF as untrusted
input, so rdflib's RDF/XML parser was probed rather than assumed safe (`research.md` R3).

External entities turned out to be closed already: a document referencing a canary file on disk
parsed cleanly and produced an empty string, with nothing leaked. Internal entity expansion is
open. Eight nested entity declarations in a document of roughly 400 bytes expanded to a single
literal of 781,250 characters, and the amplification grows without bound in the document's own
size. Any deployment that lets a curator supply a vocabulary file — which is precisely what this
feature enables — can be brought down by a small file.

Three ways to close it were considered. Refusing every document carrying a DTD is free but also
refuses legitimate published files, because entity declarations for namespace shortening are a
common idiom in hand-authored RDF/XML. Capping the input file size does nothing, since the
amplification starts from something already small. Parsing through `defusedxml` with entity
declarations forbidden closes it completely.

Chosen: `defusedxml`, as a pre-flight scan rather than a replacement parser. rdflib's RDF/XML
parser calls `xml.sax.make_parser()` internally and takes no parser argument, so a defused parser
cannot be injected and monkeypatching a third-party internal is not something to ship. Instead the
bytes go through `defusedxml.sax` with a do-nothing handler first, and only reach rdflib if that
returns cleanly. Verified both ways: the bomb raises `EntitiesForbidden` at the scan, an ordinary
RDF/XML document passes untouched.

The cost is one small single-purpose runtime dependency, one extra XML pass on RDF/XML input only,
and the loss of the namespace-entity idiom — those files now fail with a clear translatable
message naming the cause, rather than by exhausting memory. That trade favours safety, which is
where Article V points for untrusted input, and it is reversible if a real published vocabulary
turns out to need the idiom.

The test for this reinstates the measured bomb as its input, so the control is proven against the
actual defect rather than a stand-in.

## D10 — the package is named `exchange/`, not `io/`; `mypy_path` stays (T002, revised at convergence)

Creating `controlled_vocabularies/exchange/` made `poetry run mypy` fail immediately: "Source file found
twice under different module names: `controlled_vocabularies.io` and `io`". The repo's
`[tool.mypy]` carries `mypy_path = "controlled_vocabularies/"` from the scaffold, which adds that
directory itself as a search root — so every module inside it is reachable both as
`controlled_vocabularies.<name>` (via `files = ["controlled_vocabularies"]`) and as a bare
top-level `<name>` (via `mypy_path`). `conf.py`, `models.py`, and `apps.py` never collided because
nothing else on the path is named that; `io` does, because it is a stdlib module name.

The Implementer's first resolution was to drop `mypy_path`. That is overturned here. The line is
not local to this feature: the same setting is in `django-easy-icons`, `django-flex-menus` and
`django-content-license`, so removing it makes this repo the one package configured differently
from its siblings, for a reason recorded only in this feature's decision log. The collision is also
not confined to mypy — a subpackage that shadows a stdlib top-level name will keep meeting tools
that resolve modules by path (coverage, Sphinx autodoc, pytest import modes), and each will need
its own local exception.

Chosen: rename the package to `exchange/`, and `tests/test_io/` to `tests/test_exchange/`, with
`mypy_path` restored. The name still covers both directions — reading a published vocabulary now,
writing one at R4 export — which is what `io` was chosen for. Verified after the rename with
`mypy_path` present: mypy "Success: no issues found in 7 source files", 339 tests pass, ruff,
format, deptry and `makemigrations --check` all clean.

**Why:** the collision comes from a name this feature chose, and the cheap fix is to change the
thing this feature owns rather than shared toolchain config it does not. Five commits in is the
cheapest this rename will ever be.

**Revisit if:** the family standardises on dropping `mypy_path` across all packages, at which point
this repo follows that change rather than leading it.

## D11 — `rdflib` is not declared with T001/T004; only `defusedxml` is (Implementer US0)

Tasks.md's T001 reads as declaring both `rdflib` and `defusedxml` together, landing in the same
commit as T004. But T004's own scope is `safety.py` alone — the `defusedxml.sax` pre-flight scan —
and Phase 0 explicitly stops before `skos.py`/`mapping.py` (T006, Phase US-1), which is the code
that actually imports `rdflib`. Declaring `rdflib` now, with nothing in the codebase importing it
yet, is exactly the declared-but-unused case Article VII and T001's own rationale name: `poetry run
deptry .` failed immediately with `DEP002 'rdflib' defined as a dependency but not used`.

Chosen: declare only `defusedxml` in this commit, since `safety.py` is the only Phase 0 module that
imports a new dependency. `rdflib` is left undeclared until the task that first imports it (T006)
adds it in the same commit — the identical discipline T001 states, applied to the dependency whose
importing code has actually landed. Adding a `deptry` per-rule ignore for `rdflib` instead was
considered and rejected: it would suppress the exact gate T001 was written to rely on, for no
returned safety.

**Revisit if:** T006 turns out not to be the first task that imports `rdflib`, though nothing in
Phase 0 does, and no other phase precedes it.

## D12 — `rdflib` lands as a dev dependency at T005, ahead of T006 making it a runtime one

T005's fixtures need something to parse them with, to satisfy its own "each fixture is discoverable
from the suite and parses" test — and the natural tool is `rdflib` itself, the library the whole
feature is built around. But D11 just established that `rdflib` cannot be declared as a *runtime*
dependency until code under `controlled_vocabularies/` actually imports it (T006), on pain of
`deptry`'s `DEP002`.

Chosen: declare `rdflib` under `[tool.poetry.group.dev.dependencies]` now, used only by
`tests/test_exchange/test_fixtures.py`. Verified this does not trip `deptry`: `tests/` is already in
`[tool.deptry] extend_exclude`, and `poetry run deptry .` passes with `rdflib` present in the dev
group and nothing outside `tests/` importing it — the existing dev-toolchain packages (`pytest`,
`ruff`, `mypy`, …) already establish that pattern; a dev-only dependency used solely by the test
suite is not what `DEP002` is checking for. This is not a workaround: a test-only need for a parsing
library ahead of that library becoming a production dependency of the feature itself is an
ordinary, legitimate shape, distinct from Article VII's rule about *runtime* deps.

T006 moves the `rdflib = "^7.6.0"` line from the dev group to `[tool.poetry.dependencies]` in the
same commit as `skos.py`/`mapping.py` — the point at which it becomes a genuine runtime dependency
of the package. Flagged in `progress.md` so it isn't missed at that stage exit.

## D13 — the third fatal fixture is a blank-node *collection*, not a separate "missing identifier" case

The brief for this task named three malformed fixtures: "blank-node concept, missing identifier,
refused URI scheme." Read literally against FR-004's own wording — "identifier is absent, is a
blank node, or is refused by the identity rules" — "absent" and "blank node" look like they might be
two different things worth two different fixtures. They are not, in RDF: every asserted subject is
either a URI or a blank node, so "no identifier" and "a blank node" are the same shape read from two
angles, and the spec's own D3 clarification treats them as one condition ("a concept or collection
identified only by a blank node").

Confirmed empirically before committing to a fixture: an RDF/XML `rdf:about=""` (or Turtle/JSON-LD's
equivalent empty-relative-IRI forms) does **not** produce a literal empty identifier when `rdflib`
parses from a file — it resolves the empty reference against the parse call's base, which defaults
to the file's own path (`file:///…/tests/fixtures/skos/…`) unless the future importer (T006) passes
an explicit `publicID` override. A fixture built on this would have a meaning that shifts with a
parsing decision that has not been made yet — not a stable, portable fatal-path fixture.

Chosen: build `blank_node_collection.ttl` as the third fixture instead — the same blank-node-identity
mechanism `blank_node_concept.ttl` exercises, applied to a `skos:Collection` rather than a
`skos:Concept`. This is directly named in the spec (US-5 acceptance 5) and tasks.md (T030: "the same
rule that governs concepts"), so it is real, spec-grounded fatal-path material rather than a
substitution of convenience. `refused_uri_scheme.ttl` (an `ftp://` identifier, outside
`conf.DEFAULT_ALLOWED_URI_SCHEMES`) covers FR-004's separate "refused by the identity rules" clause.

**Revisit if:** T006 fixes the parse call's `publicID` to something stable (e.g. an empty string)
independent of the file's own path, at which point a genuine "absent identifier" fixture distinct
from the blank-node case becomes buildable and meaningful.

## D14 — the caller-stated-serialization parameter is named `serialization`, not `format`

Neither `plan.md` nor `tasks.md` fixed the name of `_read_graph`'s (and later `import_skos`'s)
caller-facing serialization argument. `format` was the obvious first choice — it matches
`rdflib.util.guess_format`'s own vocabulary — but `ruff`'s `A002` rule refuses it as shadowing the
`format` builtin, and the repo's `ruff` configuration does not suppress `A002` the way it
suppresses `A003` (class-attribute shadowing) for the model layer. Renamed to `serialization`
throughout `_read_graph`, `import_skos`, and their tests. No behavioural consequence; recorded
because a caller building on this Python API needs the real keyword name.

## D15 — `import_skos`'s target-vocabulary parameter takes a `ConceptScheme` instance, not a string

FR-005 says the caller "MAY name a target vocabulary" but neither `plan.md` nor `research.md`
fixes what "naming" one means as a Python parameter — a slug, a URI string, or an already-resolved
model instance. A string is ambiguous (a slug and a URI look the same at the type level, and only
one of `Concept`/`ConceptScheme`/`Collection`'s `get_by_uri` variants would apply), and resolving
either would duplicate lookup logic `#52` (the CLI wrapper this feature's entry point exists for)
will need to do anyway when it turns a command-line argument into something concrete.

Chosen: `import_skos(..., scheme: ConceptScheme | None = None)` — the caller resolves (or
constructs) the target vocabulary itself before calling in, the same shape a programmatic caller
already uses for every other cross-reference in this package. Simpler than adding a second
resolution path inside this feature, and it is `#52`'s job, not this one's, to turn a CLI argument
into a model instance (spec's own scope note: "any command-line or web-facing entry point" is out
of scope here).

## D16 — a concept's scheme-membership predicates are read leniently: no reference at all is not a conflict

FR-006 requires concepts to land "inside the vocabulary being imported"; the spec's Edge Cases §1
separately requires a concept that *explicitly* claims a different vocabulary to be set aside
rather than silently reassigned. Neither text says what a concept with **no**
`skos:inScheme`/`skos:topConceptOf`/`skos:hasTopConcept` reference at all should do — real
published files are not always fully annotated, especially a single-vocabulary file where scheme
membership is implicit from context.

Chosen: absence of any scheme reference is read as belonging to the vocabulary being imported
(the same node the file also declares as `skos:Concept`, with nothing else naming it elsewhere),
not as a set-aside or fatal condition. Only an *explicit* reference to a different scheme URI
triggers `VOCABULARY_MISMATCH`. This keeps the base fixture's default behaviour permissive for the
common case (`tests/fixtures/skos/rocks.ttl`'s concepts all declare `inScheme` anyway, so this
choice is not exercised by that fixture) while still catching the case the spec names by name
(`mixed_scheme_membership.ttl`'s `foreign` concept).

## D17 — a concept with no preferred label in the default language is set aside starting at T009, not T022

`tasks.md` assigns the acceptance test for this case to T022 (Phase US-3, "The concepts arrive
with their labels and notes"). But FR-006 — T009's own governing requirement — states concept
creation and this exact fallback in one sentence: "each holding ... its preferred label in the
vocabulary's default language. A concept carrying no preferred label in that language MUST be set
aside and reported, and MUST NOT fail the run." Leaving it unhandled at T009 would mean a concept
lacking a default-language label crashes the run with an unhandled exception on real, unremarkable
input — the opposite of what FR-006 requires — rather than the translatable, reported outcome. The
`SetAsideReason.NO_PREFERRED_LABEL` value already existed from Phase 0 for exactly this case.

Chosen: implement it now, with one covering fixture/test (`no_default_language_label.ttl`), and
leave T022 free to add whatever richer acceptance coverage it wants without needing new
implementation — it will simply find the behaviour already correct. This is judged necessary for
T009's own correctness, not scope creep into US-3's territory (US-3's remaining scope — alternative/
hidden labels, notes of every kind, unmodelled-predicate reporting — is untouched).

**Revisit if:** the US-3 Implementer's own design for this disagrees with the shape chosen here
(e.g. a different set-aside reason, or additional context in `params`) — the fixture and test
added at T009 are minimal and meant to be extended, not treated as the final word.

## D18 — an existing scheme's `default_language` is recomputed only when the scheme is freshly created

Found by a T012 test, not by inspection: `_resolve_scheme` (T008) unconditionally recomputed and
assigned `row.default_language` from the file on every run, including one matching an *existing*
scheme via `get_by_uri`. `ConceptScheme.save()` itself (R1) refuses to change `default_language`
once the scheme has concepts — it anchors every concept's identity, so changing it after the fact
would silently reinterpret them — and raises a `ValidationError` the moment the freshly computed
value differs from what a previous run already froze. That `ValidationError` is not one of this
feature's own translatable, reported outcomes; it would surface as an unhandled exception,
defeating FR-003's "collect every problem" and FR-015's "report as data" for no reason tied to the
file itself.

Chosen: only a freshly created scheme (`row.pk is None`, so it provably has no concepts yet to
protect) has `default_language` set from the file at all. An existing scheme's already-stored
value stands untouched — which is also the *correct* reading of decisions.md D4's own algorithm,
since R1's guard means that value cannot legitimately have changed since it was first frozen. The
scheme's `name` selection (which language's `prefLabel` to prefer) now reads
`row.effective_default_language` — the actually-anchoring language, frozen or freshly chosen —
rather than a value this function only computes when creating.

**Revisit if:** US-2 (re-import) needs a vocabulary's default language to be changeable after the
fact under some deliberate, separate mechanism — that is a new capability, not a fix to this one,
and R1's guard would need its own reconsideration first.
