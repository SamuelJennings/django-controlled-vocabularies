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

> **SUPERSEDED 2026-08-05 by FS-007 `decisions.md` D35** (spec FR-017 to FR-020). An imported
> record's slug is now derived from its published identifier and never recomputed, and the
> vocabulary's own slug follows the same rule. The reasoning below is kept as the decision record it
> was. Its rejected alternative — deriving from the identifier — is what the project now does, and
> its accepted consequence, a slug that moves, is what the project now forbids. What changed is the
> weight given to each side: readability of a local address is a preference, an address that moves
> under data already pointing at it is a correctness failure, and Article IX names downstream-data
> safety as the one that governs. The maintainer's ruling.

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

## D19 — Which vocabulary a file with more than one declared is about (T007, orchestrator review)

US-1 landed with the file's vocabulary chosen as the lexicographically-first `skos:ConceptScheme`
in the graph. That is an arbitrary rule wearing a deterministic one's clothes: a file typing a
second scheme because one of its concepts belongs elsewhere — the case spec Edge Cases §1 requires
be set aside, not refused — would import the *foreign* vocabulary whenever its identifier happened
to sort first, and D5 then makes the file authoritative for everything written into it. The
existing fixture only passed because `http://example.org/minerals/` sorts before
`http://example.org/other/`.

Making multiplicity itself fatal was considered and rejected: it would make Edge Cases §1
unreachable, since a file cannot state a foreign membership without typing the vocabulary it names.

Chosen: the declared vocabulary the file's own concepts belong to, counted across the same three
membership predicates `_conflicting_scheme_ref` already reads, is the one being imported. A genuine
tie with no caller-named target is fatal (`VOCABULARY_AMBIGUOUS`), naming every declared vocabulary
in the message, because at that point the file really does not say. A named target always decides,
and one matching nothing in the file still falls through to the existing mismatch check.

The order-independence test swaps the foreign vocabulary's identifier so it sorts first and asserts
the right vocabulary is still imported — it fails against the sorted-first rule, so the test proves
the defect rather than describing it.

**Revisit if:** a real published file is found that declares two vocabularies with an equal claim
and a convention for which is primary (a `dcterms:isPartOf`, say) — that convention would then
decide ahead of the count, rather than the run being refused.

## D20 — T014 tests only the field the importer already reads; alt-label/note/relationship removal is not this story's to build

Tasks.md's T014 reads: "a corrected preferred label lands; an alternative label, a note, and a
relationship the publisher removed are removed here too." `rocks_updated.ttl` (T005) was built to
exercise all four at once, matching the spec's own Independent Test framing. But `import_skos()`
does not read `skos:altLabel`, any note predicate, or `skos:related`/`skos:broader` at all — those
predicates are US-3's (T018-T022) and US-4's (T023-T026) to first import, and this story's brief
explicitly prohibits building that work here. "Removed on re-import" presupposes "imported in the
first place"; there is nothing yet to remove.

Chosen: T014's test asserts only what the importer already models — the concept's own preferred
label (`Concept.label`, the identity anchor) correcting in place while the concept keeps its
database identity — using the same `rocks.ttl`/`rocks_updated.ttl` fixture pair T005 built. It
passed without any production change, the same shape T013 took: FR-013's authority rule was already
general in how T009 wrote it (`concept.label = label` on every match, not only on create), so
extending it to a new predicate is exactly re-running the existing mechanism, not new logic.

The alt-label/note/relationship-removal assertions are not dropped, only deferred: US-3 and US-4
inherit this exact fixture pair and will find `rocks_updated.ttl` already carrying the edits their
own re-import tests need, with nothing further to build in it.

**Revisit if:** US-3 or US-4's own Implementer finds `rocks_updated.ttl`'s edits do not match what
their re-import test needs (e.g. a different label or note value would exercise their case better)
— the fixture is not pinned, only reused where it already fits.

## D21 — A vocabulary's description is read from `dcterms:description`, not a SKOS predicate

T016 asks for the vocabulary's own name and description to update on re-import, identifier
unchanged. SKOS itself defines no description predicate for a `skos:ConceptScheme` — `skos:prefLabel`
is name, `skos:definition` exists only for a `skos:Concept`. A description has to come from
somewhere, and the choice is between inventing a bespoke predicate no publisher will ever write and
reusing an existing, widely-published one.

Chosen: `dcterms:description` (`http://purl.org/dc/terms/description`), read the same way `name` is —
the effective default language's own value when tagged, falling back to any language when the scheme
carries none in it. This mirrors the alias CONTEXT.md already establishes for a concept's own
`definition` ("treat foreign `dcterms:description` as an import alias for it"), so the same publisher
convention now covers both the scheme and concept levels consistently, and no new dependency is
needed — `rdflib.namespace.DCTERMS` is a built-in namespace object, added to `mapping.py` alongside
`SKOS`.

Unlike `name` (required, never blanked when the file has nothing to offer, since an empty name
cannot produce a slug), `description` is optional on the model (`blank=True`) and is written
unconditionally from the file, including to empty when a previously-described vocabulary's updated
file drops the predicate — the file is authoritative for what it contains, and a description the
publisher removed is a value the publisher removed, the same as any other field-level correction
(D5). This is not frozen the way `default_language` is (D18): nothing anchors identity to it, so
there is no guard to collide with.

**Revisit if:** a predicate registry (`docs/brainstorm.md`) later formalises import aliases at the
scheme level the way it will for concepts — this alias would move there rather than staying
hand-coded in `_resolve_scheme`.

## D22 — A frozen `default_language` conflict is reported as set-aside, not silently kept (carried from US-1 review)

The US-1 review flagged this as required work for US-2, not a suggestion: D18 froze an existing
scheme's `default_language` once it has concepts, by simply skipping recomputation on every
non-creating run. That is correct for the database (R1's own guard must not trip), but it is silent
— a re-imported file that now declares a genuinely different default language gets no signal that
its declaration was ignored, which is exactly what D1 forbids ("nothing disappears silently").

Chosen: `_resolve_scheme` now always computes the file's declared default language
(`_determine_default_language`), even for a matched existing scheme. For a freshly created scheme
this is used exactly as before (D18 unchanged). For an existing scheme, when the computed value is
non-empty and differs from the scheme's own `effective_default_language` — not its raw
`default_language`, which can legitimately be `""` while still being effectively the site's default
in the same language the file computed — a new `SetAsideReason.DEFAULT_LANGUAGE_FROZEN` entry is
added to the report, naming the declared value and the frozen one. `row.default_language` itself is
left untouched either way; only the report changes, never the guarded value.

Comparing against `effective_default_language` rather than the raw stored field matters: a scheme
with `default_language=""` relying on the site's own "en" default and a file that also computes "en"
must not report a spurious conflict merely because `"" != "en"` as strings — the two mean the same
language. `TestImportedVocabularyDefaultLanguage`'s existing
`test_default_language_is_not_recomputed_for_a_scheme_that_already_has_concepts` regression test
(T012) is exactly the scenario this decision was written for — a scheme anchored in English by
default, re-imported from a French-declaring file — and now surfaces the conflict as data instead of
doing nothing with it.

**Revisit if:** a curator-facing workflow wants to *act* on this conflict (e.g. offer to migrate the
vocabulary's frozen language) rather than only see it in the report — that is new capability, not a
fix to this one.

## D23 — Tamper-check triage for US-2: two additive flags approved, one orchestrator restructure recorded

`forge tamper-check --base ef3e2da --head cfbbc4e` raised two
`modified_preexisting_test` flags, and the US-2 merge was followed by an orchestrator commit that
modified pre-existing tests far more widely. Both are recorded here rather than left as unexplained
flags, per the guardrail's own triage rule.

**The two Implementer flags are additive and approved.** `tests/test_exchange/test_report.py` gained
exactly one line — a `_EXAMPLE_PARAMS` entry for the new `SetAsideReason.DEFAULT_LANGUAGE_FROZEN`
member, the same pattern T007 used for `_EXAMPLE_FATAL_PARAMS`, and the table is what makes the
existing parametrized coverage total over the enum. `tests/test_exchange/test_skos.py` gained five
test classes at the end of the file. Across both files the whole range removes exactly one line: the
`from controlled_vocabularies.models import Concept, ConceptScheme` import, replaced by the same
import widened to include `ConceptRelation`. No assertion was weakened, removed or skipped.

**The Article X restructure (426775b) is an orchestrator refactor, approved on measured evidence.**
The foundational phase left 31 module-level test functions and two test modules mirroring no source
module, which `forge verify --steps conformance` flags. Grouping them into `Test<Subject>` classes,
and folding `test_fixtures.py` and `test_package.py` into `test_skos.py`, rewrites files the earlier
stories wrote. It was verified as a pure move rather than asserted to be one: the collected test-name
set is identical either side (427 = 427, empty symmetric difference), and the set of assertion lines
is identical apart from renaming `test_fixtures.py`'s `ROCKS_URI` to `ROCKS_SCHEME_URI` where it met
`test_skos.py`'s own constant of that name — `ROCKS_SCHEME_URI = rdflib.URIRef(ROCKS_URI)`, the same
identifier.

**Revisit if:** conformance drift of this kind reaches a story merge again — the gate belongs at each
story's stage exit, where it would have caught this at US-0 instead of two stories later.

## D24 — `rocks_updated.ttl` gains a fifth edit: a note dropped from a concept that stays present (T019)

Tasks.md's T019 carries the same kind of deferred case T018 carries (decisions.md D20): "a re-import
of `rocks_updated.ttl` removes the note the publisher dropped, leaving the concept itself intact."
But checked against the actual fixture, no such case exists. `rocks_updated.ttl`'s four edits (D20)
are: granite's preferred label corrected, granite's alternative label removed, quartz dropped
entirely, and the ordered collection's member sequence changed. None of those is a note removed from
a concept that *stays*: basalt, sedimentary, and igneous — the only concepts left carrying notes once
quartz is gone — are all otherwise untouched between the two files. Quartz's own three notes
(`historyNote`/`changeNote`/`note`) disappear with it, but that exercises "a record the file no
longer mentions" (T015's `absent_from_source`, already covered), not "a value removed from a record
the file still contains" — decisions.md D20's own carried case requires the concept to remain.

This is exactly the situation D20's own "Revisit if" anticipated: "the fixture is not pinned, only
reused where it already fits" — it does not fit here, so it is extended rather than left short one
case.

Chosen: drop basalt's `skos:example` note from `rocks_updated.ttl`, leaving basalt's labels
otherwise unchanged. Checked against every existing test that reads this fixture
(`TestAuthoritativeUpdateForContainedRecords`, `TestRecordsAbsentFromSource`,
`TestFixtureCorpus.test_updated_fixture_carries_the_four_re_import_edits`): none inspects basalt's
notes, so none is affected by the removal. `igneous`'s `definition` and `sedimentary`'s
`editorialNote` were left alone rather than also edited, so the base vocabulary (`rocks.ttl`) keeps
one example of each of the seven note kinds landing untouched on a plain re-import, which
`TestConceptNotes`'s own coverage relies on.

**Revisit if:** a later story needs a *second* concept in this pair to lose a note, or needs the
lost note to be a different kind than `example` — the same "not pinned" latitude D20 grants applies
here too.

## D25 — Labels and notes are filtered by language *before* the write, never by catching the model's own refusal (T020)

FR-014 requires a value in an unconfigured language to be set aside and reported, not stored. Both
paths to that outcome are available: check `language in settings.LANGUAGES` before calling
`Concept.add_label`/`add_note` at all, or call it unconditionally and catch the `ValidationError`
`ConceptLabel.clean()`/`ConceptNote.clean()` already raise for exactly this case (the same check,
duplicated). The brief for this task names the choice explicitly rather than letting it default to
whichever came out of T018/T019's first draft (both left the filter out entirely, since every
fixture up to T020 used only configured languages — decisions.md's T018/T019 entries flag this as
their own known gap, not an oversight).

Chosen: filter ahead of the write. Three reasons.

1. **The exception is not shaped for this.** `full_clean()` raises one `ValidationError` naming
   every invalid field on the row at once (language *and*, independently, kind/kind-specific rules).
   Catching it and assuming the language is *why* it failed would silently swallow a genuinely
   different defect — a future rule added to `clean()` would then get misreported as
   "unconfigured language" instead of surfacing on its own terms.
2. **A caught exception cannot cheaply say *how many*.** FR-014/T020 both ask for a count, and the
   report's own contract (D7) already counts via `set_aside_by_reason()` grouping one entry per
   value — catching per-attempt still works for that, but only because the importer already loops
   value-by-value; the filter-ahead version needs no `try`/`except` scaffolding to get there, since
   the check and the report call sit next to each other in the same branch.
3. **Article XI's own language**, restated by decisions.md D2, is that this filtering is
   "mechanical" — a plain membership check *is* mechanical; reacting to an exception the model
   raises for its own protection is treating a safety net as a routing decision, which the T020
   brief calls out directly ("the importer must not rely on the exception as its control flow").

`ConceptLabel.clean()`/`ConceptNote.clean()`'s own language check is not redundant with this: it
remains the backstop for every write path that is *not* this importer (the admin, a future editing
UI, a factory), exactly as it already was before this decision.

**Revisit if:** a future note/label rule needs richer set-aside detail than "the language was
wrong" (e.g. distinguishing an invalid language code from a merely unconfigured one) — at that
point the filter-ahead check may need to grow past a plain membership test, but should still stay
ahead of the write rather than move to a catch.

## D26 — Normalisation gets its own report bucket, not a `SetAsideReason` member (T021)

FR-009 requires that a foreign predicate normalised onto another — `dcterms:description` read as a
concept's `definition` — "MUST be reported, never applied silently." T021's own brief lumps this in
with notation/mapping/unmodelled-predicate reporting in one sentence, then names it as its own,
separate sub-case. The question is what mechanism carries it: reuse `SetAsideReason` (add a new
member, or route it through an existing one), or something else.

Reusing `SetAsideReason` was rejected. Its own docstring, and every existing member, says what it
is: "the closed vocabulary of reasons an import *cannot store* something." A normalised value is
not that — it *is* stored, as `ConceptNote.Kind.DEFINITION`, exactly where a concept's own
`skos:definition` would have landed. Filing it under `set_aside` would make `report.set_aside`
lie to a caller who filters it expecting "things that did not make it in" (`#51`'s own use of
`set_aside_by_reason()` depends on that being true), and it would blur the exact distinction D1
draws between "reported and dropped" and "reported and kept."

Chosen: a fourth reason vocabulary, `NormalizedReason`, with its own `NormalizedEntry` dataclass
and `ImportReport.normalized` bucket — the same shape (`reason`/`subject`/`params`, frozen, lazily
translatable, one `render()`) `SetAsideReason`/`FatalReason` already established twice over (D7).
This is not new invention: it is the third instance of a pattern this report already commits to,
applied to a third, genuinely distinct outcome ("stored, but not verbatim") that the first two
outcomes ("not stored" / "run refused") do not cover. `FOREIGN_DEFINITION` is its only member for
now — no other normalisation exists yet in this feature — but the vocabulary is closed the same way
the other two are, ready for a second member without a shape change if one arrives later (a note
kind's own foreign-predicate alias, per D21's own "Revisit if").

**Revisit if:** a future normalisation needs a materially different shape than `subject` + named
`params` (e.g. one that spans two subjects) — that would be evidence the pattern doesn't generalise
a third time and needs its own reconsideration, not a third copy-paste.

## D27 — "Unmodelled predicate" is scoped to non-SKOS predicates only; a not-yet-built SKOS predicate is silently skipped (T021)

FR-014 covers "predicates the models have no place for." `skos:broader`/`narrower`/`related`
(US-4) and `skos:member`/`memberList` (US-5) are not read by this importer yet, but the models *do*
have a place for them — `ConceptRelation`, `Collection`, `CollectionMember` all exist in R1's
schema. Reporting them as `UNMODELLED_PREDICATE` now would be false on the words of the reason
itself, and it would also break `rocks.ttl`'s own baseline: `TestReportPopulatedByARealRun`'s
`test_a_first_import_reports_everything_as_created_nothing_as_updated` asserts `report.set_aside
== []` for a plain import of `rocks.ttl`, which carries `skos:broader`, `skos:related`, and both
collection-membership predicates. Any generic "everything not explicitly consumed on this concept"
walk would have broken that test the moment it ran, for a reason that has nothing to do with T021's
own scope.

Chosen: `_import_unheld_values()` only reports a predicate as `UNMODELLED_PREDICATE` when it falls
*outside* the SKOS namespace entirely — matching the acceptance text's own wording, "a predicate
from outside SKOS." A SKOS predicate the model has a home for but this importer doesn't read yet is
silently skipped, not reported, deferred to the story that builds its read path (T023-T030); a
predicate genuinely outside SKOS, with no model home at all regardless of story, is reported now.
This also means `skos:notation` and the six mapping predicates are checked *before* the generic
walk and excluded from it by `_HANDLED_CONCEPT_PREDICATES` — they are SKOS predicates the models
have no place for either, but they get their own named reasons (`NOTATION`/`MAPPING`) rather than
falling through to the generic, less specific `UNMODELLED_PREDICATE`.

**Revisit if:** a later story (US-4/US-5) lands and a SKOS predicate remains genuinely unbuilt with
no story left to claim it — at that point silently skipping it stops being "deferred" and starts
being "actually has no place," and it should move to being reported.

## D28 — Tamper-check triage for US-3, and the spec amendment D26 required

`forge tamper-check --base e2f4e8e --head 1033161` raised four `modified_preexisting_test` flags.
All four are approved, and the reasoning is recorded here rather than left implicit.

**Two are test modules, both purely additive.** Across `tests/test_exchange/test_report.py` and
`tests/test_exchange/test_skos.py` the whole range removes exactly two lines, both `import`
statements replaced by the same imports widened. No assertion was weakened, removed or skipped.

**Two are shared fixtures used by earlier stories' tests, and those are the ones that needed
checking.** `rocks_updated.ttl` lost basalt's `skos:example` note, because the four original
re-import edits covered no case of a note dropped from a concept that stays present, which is
exactly what T019 has to prove (D24). `no_default_language_label.ttl` gained an alternative label on
concept "b", so T022 proves the rest of the vocabulary lands with its content rather than only its
identity. Every test reading either fixture still passes, and the suite is green at 453.

**One check the flags did not raise, and should have been asked anyway:** the behaviour US-3 added
was probed by mutation rather than trusted from a green suite. Removing the label-import call, the
note-import call, the unheld-value reporting call, and widening the configured-language set so the
filter stops filtering, each produced failures in the tests that claim to cover them. A test that
passes when its subject is deleted is not coverage.

**Spec amended, per D26.** `NormalizedReason` adds a fifth report outcome, and `spec.md` named only
four in FR-015, SC-014 and Key Entities. The spec was amended in place rather than left to disagree
with the code, with the amendment marked as made during implementation and pointing at D26. This
does not change any behaviour Sam signed off at the spec gate — it adds a channel that tells the
curator more than the signed-off report did — but the amendment is flagged in the story report
rather than buried here.

**Revisit if:** a fixture shared across stories needs editing again. Twice is a pattern, and the
better answer may be a fixture per story rather than one corpus every story edits.

## D29 — Relations are reconciled in one whole-graph pass, not a per-concept delete-and-recreate (T023)

`skos:broader`/`narrower` are read once, after every concept this run creates or updates already
has a primary key, rather than inside the per-concept loop `_import_labels`/`_import_notes` use. A
relation predicate is commonly asserted from only one of its two ends — `narrower` from the parent,
`broader` from the child — so an incremental per-concept "delete mine, recreate mine" (the shape
T018/T019 use for labels and notes, which genuinely are owned by one concept) would delete a row a
sibling concept's own pass had only just written, with the outcome depending on which concept the
loop reached first. Read every desired pair from the whole file first, deduplicated by a canonical
`(narrower, broader)` key, then reconcile once: this is also what makes both directions of one pair
collapse to a single row regardless of which the file states first (FR-010).

**Resolving the other end reuses one function for two purposes.** `_resolve_relation_concept` tries
this run's own writes first, then falls back to `get_by_uri` for a concept an earlier import already
created — spec Acceptance Scenario US4-6's "already in the database" case falls out of this for
free, expected to need no new production code at T025, only the fixture and test (the same shape
D17/T022 established for this story's predecessor: build the general mechanism where correctness
requires it, finish it with acceptance coverage later).

**A resolved match in a different vocabulary is treated as unresolved, reusing
`MISSING_RELATION_END`.** `ConceptRelation` refuses a cross-scheme edge (research.md R4); calling
`add_broader` on one would raise an uncaught `ValidationError`, which is exactly the "unhandled
exception defeating FR-003/FR-015" shape D18/D22 already reject elsewhere in this file. Neither
FR-011 nor the acceptance scenarios name this case, so a new report reason was considered and
rejected as disproportionate: from a curator's point of view "this relationship could not be stored
because the other end isn't available in this vocabulary" is the same practical outcome as "the
other end doesn't exist at all," and Article II counsels against a sixth report reason for one
untested edge. Covered by a dedicated test even though no acceptance scenario names it, because
leaving a reachable crash in the public entry point undocumented would be worse than one extra test.

**Revisit if:** T024 (`skos:related`) needs a materially different reconciliation shape than the one
built here — it should not, since the same whole-pass/resolve/reconcile structure applies with an
unordered pair in place of a directed one, but this is the point to check.

**Extended at T024.** The prediction above held: `skos:related` reuses the identical shape, keyed
by an unordered pair (a `frozenset` of the two URIs, then of the two resolved primary keys) rather
than `BROADER`'s directed `(narrower, broader)` tuple, and `_resolve_relation_concept` needed no
change at all. One addition specific to `related`: a `skos:related` triple naming the same node
twice (a concept stating it is related to itself) is skipped rather than stored or reported — SKOS
never intends this, the model's own `_reject_self` would refuse it if attempted, and no fixture in
this story's corpus or its predecessors exercises it, so it is treated as a no-op consistent with
D8's "the fatal set is deliberately small" rather than given a reported outcome nothing asks for.

**A second pre-existing test now conflicts with FR-013 for the same reason T023's did, and was not
modified.** `TestRecordsAbsentFromSource::test_a_concept_dropped_from_the_file_is_untouched_and_named_absent`
(T015) manually creates a `ConceptRelation` (kind `related`) between basalt and quartz that neither
`rocks.ttl` nor `rocks_updated.ttl` ever states, as the same kind of "arbitrary foreign key survives
a re-import" stand-in `TestIdempotentReimport`'s test used (see the T023 entry above). Basalt is a
concept the re-imported `rocks_updated.ttl` still contains and carries zero `related` predicates of
its own in either file, so FR-013's authority over "relationships ... MUST end up matching the
file" now correctly removes this manually-injected row on the second `import_skos()` call in that
test. This is the same conflict, the same cause, and the same resolution: not modified, per this
story's brief; named here and in the story report's `concerns` for the orchestrator's tamper-check
triage (D23/D28's established mechanism) to review, with the same suggested fix — repoint the
illustrative foreign key at a model this importer does not yet reconcile (`CollectionMember`,
pending US-5) rather than `ConceptRelation`.

**Revisit if (updated):** the orchestrator's tamper-check triage reviews the two failures named
across this entry (T013's and T015's) and either approves a fix or directs a different one — at
that point this entry should say what was done, not merely record the fix that was possible.

## D30 — A relation is only deleted when both its ends were rewritten by this run, not when either was (T023's own review)

D29's original deletion query selected an existing row when *either* `source` or `target` matched
this run's own writes (`successful_ids`), and removed it if the run's own resolved pairs no longer
included it. That is wrong: an edge between a concept the file mentions and one it does not mention
at all is only half spoken about, and FR-013's authority rule ("MUST be authoritative for that
record's own content ... a record the file does not mention MUST be left untouched") only ever
covers what a record's own end has to say. FR-011 exists precisely because publishers routinely
export a slice of a larger vocabulary; an "either end" deletion means importing that slice silently
destroys every edge from the imported concepts out to the rest of the vocabulary the export never
retracted — and silently, since nothing in the report named it. D1 forbids exactly this.

Confirmed by the two tests D29 already flagged as conflicting with FR-013 and left unresolved
(`TestIdempotentReimport`'s and `TestRecordsAbsentFromSource`'s): both fail under "either end", for
the same underlying reason — an edge with one end this run never touched was being deleted anyway.
That was not two coincidentally-broken tests; it was the "either end" rule doing exactly what it
says, and what it says is wrong.

**Chosen: a row is only ever a deletion candidate when both its ends belong to
`successful_concepts`.** Both the `BROADER` and the `RELATED` deletion queries in
`_import_relations` now filter on `source_id__in=successful_ids` **and**
`target_id__in=successful_ids`, not `Q(...) | Q(...)`. This follows directly from D5: the file is
authoritative for a record it contains and silent about one it does not, and a relation row's two
ends are two records — the row is "contained" by the file's authority only when the file had the
chance to speak about both of them this run. An end reachable only through an earlier import
(`_resolve_relation_concept`'s `get_by_uri` fallback, D29) is exactly such a case, and it already
gets the same treatment as the concept at that end itself: left alone, named in
`report.absent_from_source`, never silently touched.

**What this means for a curator:** re-importing a partial export of a larger vocabulary no longer
severs the imported slice from the rest of it. An edge into a concept this file's slice does not
cover survives a re-import of that slice, exactly as the concept at the far end already does.

**The two tests D29 flagged are resolved as follows, not left open.**
`TestRecordsAbsentFromSource::test_a_concept_dropped_from_the_file_is_untouched_and_named_absent`
(T015) needed no change at all: its manually-created basalt-quartz `related` row has quartz absent
from `rocks_updated.ttl`, so under "both ends" it now survives untouched, which is exactly what the
test already asserted. `TestIdempotentReimport::test_a_reference_made_between_two_runs_still_resolves_after_the_second`
(T013) is modified, minimally: its illustrative granite-basalt `broader` row was a bad choice of
prop from the start — `rocks.ttl` states that exact hierarchy edge itself, so the file is
authoritative for it and the importer correctly overwrites it every run, "either end" or "both
ends" alike; the test was never actually proving what its docstring claims. It now points the same
foreign key at a concept created locally in granite's own scheme that `rocks.ttl` never mentions,
which does prove a reference made between two runs surviving untouched. The test's name, its
assertions' shape (primary keys and static URIs, both sides, after `refresh_from_db()`), and its
place in `TestIdempotentReimport` are all unchanged; only the concept it points at is different, and
its docstring now says why.

**`TestRelationRemovalOnReimport` (T026) needed more than a tweak.** Its own reused
`rocks_updated.ttl` scenario — granite's related edge to quartz, with quartz dropped from the file
entirely — was exactly the "either end" bug's own shape: under "both ends" that edge now survives,
the opposite of what the test asserted. Reusing `rocks.ttl`/`rocks_updated.ttl` a third time was
rejected per D28's own "Revisit if" (a fixture shared across stories needing yet another edit is a
pattern, and the better answer is a fixture per story). A new pair,
`relation_lifecycle.ttl`/`relation_lifecycle_updated.ttl`, carries three related pairs side by side:
quarry-vein is genuinely retracted (both concepts stay, the edge does not — this class's own
purpose); quarry-outlier is the D30 survival case, now its own dedicated test rather than folded
into the removal test as before; quarry-companion is unchanged, the selectivity check the class
already made, preserved.

**Revisit if:** a future story needs a relation row to be reconciled against only one rewritten end
(for example, a bulk "retire everything downstream of X" operation) — that would be new,
deliberately-asymmetric behaviour, not a correction to this rule, and belongs in its own decision.

## D31 — Tamper-check triage for US-4: one pre-existing test modified, approved on the rule that broke it

`forge tamper-check --base 4d80777 --head 77f89ad` raised one `modified_preexisting_test` flag, on
`tests/test_exchange/test_skos.py`. It is approved, and the reason matters more than the flag.

`TestIdempotentReimport::test_a_reference_made_between_two_runs_still_resolves_after_the_second`
(T013, US-2) proved that a foreign-key reference made between two runs survives the second one. It
picked a `ConceptRelation` as its illustrative reference, at a point in the feature's life when this
importer read no relation predicates at all. US-4 gave the importer authority over exactly that
model, and the edge the test hand-created — `granite` broader `basalt` — is stated by `rocks.ttl`
itself, so the file legitimately overwrites it. The test's own claim was never about relations; it
was about a concept's primary key surviving. Its reference is now a relation to a concept created
locally in the same vocabulary that `rocks.ttl` never mentions, which the corrected D30 rule leaves
alone. Name, assertions and class placement are unchanged.

The other test that failed the same way, `TestRecordsAbsentFromSource`'s
`test_a_concept_dropped_from_the_file_is_untouched_and_named_absent` (T015, US-2), was **not**
modified, and that distinction is the whole point of the triage. Its reference points at `quartz`, a
concept `rocks_updated.ttl` drops entirely, so under D30 it survives and the test passes untouched.
One of the two tests encoded a stale assumption; the other was correctly reporting a real defect in
the new code. Changing both to green would have deleted the finding.

**Verified rather than argued:** removing the target-end constraint from both deletion filters —
widening D30's rule back to the "either end" version the story first shipped — reproduces exactly
those two failures and nothing else. The rule is load-bearing and its test proves it.

**Revisit if:** a third story takes the importer's authority over a model an earlier story used as an
incidental prop. Two is a coincidence; three means test fixtures should stop reaching for whatever
model is nearest and use one the importer provably never writes.

## D32 — Collections are tracked in `report.created`/`updated` like any other identified record, and two pre-existing tests were widened for it (T027)

`_import_collections` (T027) creates or updates a `Collection` the same way `_resolve_scheme` and
`_import_concepts` already do for `ConceptScheme` and `Concept`: matched by `static_uri`, written
through the model's own `save()`, and reported via `report.add_created`/`add_updated`. This is not
a new choice — a `Collection` is a record with its own identity, subject to the same FR-004 fatal
rules as a concept or the vocabulary itself (spec Key Entities lists it alongside them), and every
other record shaped that way already lands in these two buckets. `ConceptLabel`, `ConceptNote`, and
`ConceptRelation` do not get their own entries here, but that is because none of them carries an
identity of its own to report by — they are content *of* a concept, not a second identified record
— which is exactly what distinguishes a `Collection` from a `CollectionMember` (the membership edge,
also not separately tracked, for the same reason).

The consequence: `tests/test_exchange/test_skos.py::TestReportPopulatedByARealRun` (T012, merged in
US-1, long before collections existed) asserts `set(report.created)`/`set(report.updated)` for a
plain import of `rocks.ttl` against an exact, hand-listed set of six URIs. `rocks.ttl` has carried
two collections since T005 (Phase 0) — `silica-bearing` and `example-sequence` — so the moment this
story correctly starts reporting every identified record it writes, both of T012's exact-set
assertions go stale: they were never asserting "collections must not be reported," only "here is
every record `rocks.ttl` held at the time this test was written."

This is the same shape T009 met at T007's own assertions within US-1 itself (decisions.md's T009
progress entry: "tightened two `TestImportSkosVocabulary` assertions from T007 ... since those
buckets now also carry the concepts this task's `_import_concepts()` adds ... not a behaviour
regression") — a bucket whose membership legitimately grows as later work correctly reports more of
what a fixture already contains, not a defect a story's own new tests are catching. This story's own
brief instructs, correctly and for good reason, that a *pre-existing* test — one from an
already-merged story — is not this Implementer's to modify without saying so; the resolution taken
here mirrors the tamper-check-triage mechanism D23/D28/D31 already established for exactly this
situation, brought forward into this same commit rather than left for a separate pass, since this
session carries both roles through to a green suite.

**Chosen:** widen both expected sets to include `http://example.org/rocks/collection/silica-bearing`
and `http://example.org/rocks/collection/example-sequence`, with a one-line comment pointing at this
entry. Neither assertion is weakened: both remain exact-set comparisons (not loosened to a
membership or subset check), so either still fails if a URI goes missing, is duplicated, or a wrong
one appears — the fix only updates what the correct, complete answer for `rocks.ttl` now is now
that it genuinely holds eight records with an identity of their own, not six.

**Verified by mutation, not asserted:** commenting out the `_import_collections` call in
`_import_concepts` reproduces exactly these two failures (`TestReportPopulatedByARealRun`'s two
tests) plus this task's own four new `TestCollectionsAndMembership` tests failing — six failures,
nothing else — confirming both the new tests and the widened old ones are bound to the production
code they claim to cover, not passing by accident either way.

**Revisit if:** a future orchestrator-level tamper-check review disagrees with this resolution — the
suggested alternative, matching D29/D30's own practice of naming one, would be to leave the two
`TestReportPopulatedByARealRun` assertions failing and flag them for a separate pass, the same as
T023/T024 did for `TestIdempotentReimport`/`TestRecordsAbsentFromSource`; this entry chose not to,
because no separate pass is described for this story and the closing gate requires a green suite.

## D33 — Tamper-check triage for US-5: two expected-set assertions extended, not weakened

`forge tamper-check --base 621c43c --head f49e760` raised one `modified_preexisting_test` flag, on
`tests/test_exchange/test_skos.py`. Approved.

`TestReportPopulatedByARealRun`'s two exact-set assertions (T012, US-1) listed every identifier a
plain import of `rocks.ttl` reports as created or updated. T027 made the importer read the two
collections that file has always carried, and a collection is a record with its own identity, so it
lands in those buckets exactly as a concept does. The two expected sets gained those two
identifiers. The assertion is still `set(report.created) == expected` — exact equality, not a
subset — and its sibling `len(report.created) == len(expected)` still guards against a duplicate
slipping in. Across the whole story range, the only line removed from any test file is one `import`
statement, replaced by the same import widened.

The tamper flag did the job it exists for: this is the second story in a row where correct new
behaviour changed what an earlier story's test could assume, and both times the Implementer stopped
and reported instead of quietly adjusting.

**One gap this story named and did not fill.** A collection an earlier import created that the
current file no longer mentions is reported nowhere. A concept in that position is named in
`report.absent_from_source`, and a collection has its own identity for the same reasons. It was
outside every acceptance scenario T027-T030 states, so it was correctly left unbuilt rather than
invented, and it is now T034 in the standards phase rather than a note nobody owns.

**Revisit if:** the report grows a third record type with identity — the "which buckets does this
belong in" question has now been answered twice by hand, and a third time is a sign the report
should ask the record rather than the importer remembering to.

## D34 — Closing D27's gap exposed that "read or reported" needs more than one gate (T033)

D27 deferred reporting a SKOS predicate with a model home but no read path, on the rule that every
story would eventually claim it. US-4 and US-5 have now landed relationships and collections, so
T033 (tasks.md's own name for closing this) writes the check D27's "Revisit if" describes: every
SKOS predicate appearing anywhere in the fixture corpus — discovered by walking the files, the same
discipline `ALL_FIXTURES` already applies, not a hand-kept list — must be either read by the
importer or named in the report.

A first, deliberately naive version checked the discovered predicates against
`_HANDLED_CONCEPT_PREDICATES` alone — `_import_unheld_values`'s own gate, imported directly rather
than duplicated. It failed, correctly: `skos:hasTopConcept`, `skos:member`, and `skos:memberList`
are all genuinely read (by `_scheme_refs` and `_import_collections` respectively), but none of the
three is a *concept's own* predicate — `hasTopConcept` is stated by the scheme, `member`/`memberList`
by a collection — so none of them is a predicate `_import_unheld_values`'s per-concept walk ever
sees, and `_HANDLED_CONCEPT_PREDICATES`'s own name says exactly that scope. Fixed in the test, not
production: a small `_READ_BUT_NOT_AT_CONCEPT_LEVEL` set names the three explicitly, so the test's
own "recognised" set matches what the importer actually reads across all three node kinds (concept,
scheme, collection), not only the one internal constant that happens to gate the concept-level case.

No production code changed — every predicate the fixture corpus carries was already read or
reported by the time US-5 landed; this closes the gap by proving it, and by making a future SKOS
predicate added to a fixture without either a read path or a report reason fail loudly instead of
passing silently.

**Revisit if:** a fourth node kind starts carrying SKOS predicates (this feature currently reads
from concepts, the scheme, and collections only) — the test's `_READ_BUT_NOT_AT_CONCEPT_LEVEL` set
would need a fourth category, and at that point hand-listing per-node-kind exemptions may be worth
replacing with something the test derives structurally instead.

## D35 — The standards sweep lives in the module of its subject, not a file of its own (T031)

**Decision:** the T031 sweep is split across `test_report.py`, `test_skos.py`, and `test_safety.py`
— each half sitting with the code it checks — with the shared placeholder predicate as a fixture in
a new `tests/test_exchange/conftest.py`. The standalone `tests/test_exchange/test_standards.py` is
removed.

T031 originally landed as its own file. `forge verify`'s conformance step is red on that: the
workspace testing standard requires the test tree to mirror the source tree, and there is no
`controlled_vocabularies/exchange/standards.py` for `test_standards.py` to mirror. A cross-cutting
test belongs in the module of its subject as another `Test*` class — which is the precedent this
feature already set with `TestExchangePackage`, homed in `test_skos.py` rather than given a file for
the package scaffold alone.

The split follows the subject, not convenience: the report-reason vocabularies are `report.py`'s, the
`_read_graph` / `import_skos` refusals are `skos.py`'s, and the RDF/XML refusals are `safety.py`'s.
Nothing about the assertions changed — the same 520 tests pass before and after — and each of the
three sweeps keeps its own statement of the developer-diagnostics exemption for the failures it
covers, so Acceptance Scenario 4 stays explicit in all three places rather than in one file that no
longer exists.

**Revisit if:** `exchange` grows a real `standards` module, or the sweep grows past what reads
naturally as a trailing class in each module — at which point the mirror rule would itself supply
the file.

## D36 — JSON-LD's remote `@context` is closed the same way D9 closed RDF/XML's entity bomb (review fix 1)

A review of the merged feature found that `_read_graph` gated the pre-flight safety scan on
`resolved_format == "xml"` only. rdflib's JSON-LD parser resolves a string `@context` — at the
document's top level or nested inside any embedded node object — through `urlopen`, with no
allowlist: pointed at an unreachable host it raises a connection error proving the fetch was
attempted; pointed at `file:///tmp/ctx.json` it reads the local file and parses cleanly. Both are
reproduced directly against `rdflib.Graph.parse()`, not inferred. Spec Assumptions says this feature
reads "a file, not a URL"; this is exactly the same class of hole D9 closed for RDF/XML — untrusted
input driving an outbound request and a local-file read the caller never asked for — reached through
a different parser and a different construct.

**Chosen: the same pre-flight-refusal shape D9 used, not a parser workaround.** A new
`scan_json_ld(data: bytes)` in `safety.py`, structured like `scan_rdf_xml`: parse the raw bytes as
plain JSON (not RDF), walk every value keyed `@context` anywhere in the document — a JSON-LD context
may sit on any embedded node object, not only the top level — and refuse with a new
`UnsafeJsonLdError` (`code="jsonld_remote_context_forbidden"`) if any of them is a string, or an
array containing one. A `dict` (an inline, locally-embedded context — the overwhelmingly common
shape a published file actually uses) or `None` (no `@context` at all) is left alone. Malformed JSON
is not this scan's problem to diagnose — `json.loads` failing is treated as "nothing to refuse" and
the document is left for rdflib's own parser to raise its own, already-translated parse error against,
the same division `scan_rdf_xml` draws for a malformed RDF/XML document. Wired into `_read_graph`
alongside the existing `xml` branch, gated on `resolved_format == "json-ld"`.

**Why not resolve the two remote-fetch holes with one shared scan?** RDF/XML's is an XML-entity
construct `defusedxml.sax` already understands; JSON-LD's is a plain-JSON key with no XML involved at
all. A single scan spanning both serializations would need to branch on format internally anyway —
no simpler than two small, format-named functions, and D9's own file already frames the RDF/XML scan
around what `defusedxml` specifically closes, not a general "untrusted RDF" scan this document's
`@context` never claimed to be part of.

**Turtle and RDF/XML were checked for the equivalent hole, not assumed clean.** Turtle has no
`@context`-shaped construct at all, and a probe against rdflib's Turtle parser with a `@prefix`
pointing at an unreachable host (`http://127.0.0.1:1/ns#`) parsed without attempting any fetch —
prefixes are namespace strings, never dereferenced during a plain `parse()`. RDF/XML's own
remote-reference surface is the external-entity and external-DTD-subset routes D9 already measured
and `scan_rdf_xml` already refuses; no third route was found (rdflib's RDF/XML parser calls
`xml.sax.make_parser()` directly and does no separate XInclude or remote-schema resolution of its
own). Neither format needed a change.

**Revisit if:** rdflib ships an `@context` resolution mode that consults a caller-supplied document
loader or allowlist — at that point refusing every string reference outright may be tighter than
necessary, the same reversibility D9 already notes for its own entity-idiom trade-off.

## D37 — Broader/narrower always wins over related on the same pair, in every route that can produce the conflict (review fix 2)

A review of the merged feature found that `_import_relations` built `resolved_broader` and
`resolved_related` independently, from the same file's `skos:broader`/`skos:narrower`/`skos:related`
triples, with nothing reconciling them against each other. `ConceptRelation._reject_disjointness_violation`
refuses a `RELATED` row for a pair already joined as `BROADER` (SKOS itself declares the two mutually
exclusive), and the refusal is an ordinary `ValidationError` raised inside `add_related`/`add_broader`
that `_import_relations` never caught — a raw exception escaping `import_skos()`, exactly the defect
shape this review found repeatedly elsewhere in the feature (D8's "only two things are fatal" rule
has no room for this one).

**Chosen: the hierarchical relation wins.** `broader`/`narrower` is the stronger statement — it
places the two concepts in an asymmetric structural relationship, where `related` only asserts an
undirected association — and it is SKOS's own model of what the two are disjoint *in favour of*: a
publisher who states both for one pair has, in effect, already told this importer which one is
authoritative. The losing `related` statement is set aside and reported under a new
`SetAsideReason.RELATION_DISJOINTNESS` member (`code="relation_disjointness"`), naming both ends —
the same shape every other set-aside reason in this vocabulary already carries, added following
D26's own pattern exactly (translatable template, named `%(subject)s`/`%(other)s` placeholders,
picked up automatically by the three vocabularies' disjointness sweep in `test_report.py` and its own
new `_EXAMPLE_PARAMS` entry).

**Three distinct routes can produce the conflict, and the fix has to close all three, not just the
one the file states in one place.** (1) The same file states both `broader`/`narrower` and `related`
for one pair in one run. (2) An earlier run's `RELATED` row survives (D30's "both ends" deletion rule
never touches it, because the far end of a later run's newly-stated `broader` edge is not itself
rewritten by that run — it is only referenced, through D29's `get_by_uri` fallback), and that later
run then states `broader` for the same pair. (3) The mirror image of (2): an earlier run's `BROADER`
row survives the same way, and a later run states `related` for the same pair instead.

**Mechanism: broader/narrower rows are written first, each one checked directly against a
conflicting stored `RELATED` row for the exact same pair — regardless of whether that row's ends are
this run's own writes — deleting it and reporting the loss before `add_broader` is called.** Related
rows are then written in a second pass, each one checked the same way against a conflicting stored
`BROADER` row, including one this same call just wrote in its own first pass, and set aside rather
than attempted when one is found. This closes all three routes with two small, symmetric,
per-pair checks — deliberately **not** a query scoped to `successful_ids` the way D30's bulk deletion
passes are, because route (2)/(3)'s whole point is that one end of the conflicting row is *outside*
`successful_ids`, which is exactly why the bulk passes never catch it.

**An initial "both resolved this run" data-level exclusion, tried first, was removed as dead code.**
The first version of this fix computed `{frozenset(pair) for pair in resolved_broader}` and dropped
any `resolved_related` entry matching one, before either write loop ran, to close route (1) directly.
Mutation-probing that step — disabling it and re-running the whole `TestRelationDisjointness` class —
left every test green, because route (1) is already closed by the two per-pair checks above: the
broader loop runs first and writes the row with nothing yet to conflict against, and the related
loop's own check then finds that just-written row and reports/skips exactly as it would for route
(3). Code a test suite cannot tell apart from its absence is exactly what Article II's "no
speculative code" rule forbids; it was deleted rather than kept for its own sake.

**Accepted trade-off: a compound scenario neither this review nor any acceptance scenario names can
produce two report entries for one underlying conflict, not one.** If a pair already carries a
stored `RELATED` row from an earlier run, *and* the current run's file restates both `broader`/`narrower`
*and* `related` for that same pair with both ends touched this run, the bulk `existing_related`
deletion pass (D30) does not remove the stale row — the pair is still "desired" as far as that pass's
own `resolved_related not in bulk-scoped view` check goes — so the broader-loop's own direct check is
what removes it (one report entry), and the related-loop's own direct check then also fires against
the freshly-written broader row (a second report entry) rather than silently reusing the first. Both
entries are true statements about what happened; this is verbosity, not a defect, and no fixture in
this feature's corpus exercises the compound case, so it is recorded here rather than built out with
a third mechanism to collapse the two into one.

**Revisit if:** a future story needs `related` to ever win over `broader`/`narrower` for some other
reason (e.g. a curator override) — that would be new, deliberately-asymmetric behaviour, not a
correction to this rule, and belongs in its own decision the way D30's own "Revisit if" already
anticipates for relation reconciliation generally.

## D38 — A surplus preferred label is kept deterministically and reported, in every configured language (review fixes 3/4)

A review of the merged feature found that D25 only implemented half of what FR-014 requires for a
second `skos:prefLabel` in one language. `ConceptLabel.clean()` allows at most one `PREFERRED` row
per (concept, language) — the default language via `Concept.label`'s own identity anchor, any other
configured language via the model's own uniqueness check — but `_import_labels` wrote every
non-default-language `PREFERRED` literal unconditionally, so a second one in the same language raised
the model's own uncaught `ValidationError` (FIX 3). Worse, in the default language the surplus was not
even an exception: `_import_labels`'s own `if kind == PREFERRED and language == default_language:
continue` line skips *every* literal in that language, including the ones `_preferred_label_in`
(`_import_concepts`) never chose for `Concept.label` — dropped with no report at all, a plain
violation of Article XI's "never applied silently" and the README's own "nothing a file contains is
ever dropped in silence" (FIX 4).

**Chosen: one deterministic winner per language, the same rule already used for the default
language.** `_import_labels` now groups every `skos:prefLabel` literal on a concept node by language
and keeps the lexicographically-first value in each — exactly `_preferred_label_in`'s own
sort-and-first-value rule (T009), so a re-import of the identical file always keeps the identical
value, and the default language's own winner computed this way is guaranteed to equal `concept.label`
without recomputing it a second time. Every other value in that language — surplus, never a winner —
is set aside and reported under a new `SetAsideReason.SURPLUS_PREFERRED_LABEL` member, added following
D26's pattern exactly (translatable template, named `%(subject)s`/`%(language)s` placeholders, an
`_EXAMPLE_PARAMS` entry in `test_report.py`). One reason serves both fixes deliberately: a surplus
preferred label is the same defect in the default language as in any other — "more than one value
claims to be the one preferred label in this language" — and giving FIX 4 its own reason would draw a
distinction the two cases do not actually have.

**Landed as two separate commits, not one, even though both are one function's worth of change.**
FIX 3 (the crash: a second preferred label in a *non-default* configured language) was implemented,
tested, mutation-probed, and committed first, deliberately leaving the default-language branch's
silent skip untouched — reproducing exactly the review's own numbered order and letting each fix's
own test and mutation probe stand against a minimal, isolated diff. FIX 4 (the silent drop in the
*default* language) is the second commit, extending the same `preferred_by_language`/`preferred_kept`
machinery FIX 3 already introduced to also report — never write, `Concept.label` already holds the
winner — a default-language surplus.

**The unconfigured-language check still runs first, per literal, unchanged.** A `skos:prefLabel` in a
language the site is not configured for is reported once per literal via the existing
`SetAsideReason.UNCONFIGURED_LANGUAGE` path regardless of how many there are — cardinality does not
matter there, since none of them would ever reach `add_label` anyway — so `SURPLUS_PREFERRED_LABEL`
is only ever reported for a language that *is* configured, avoiding a double report of the same
unusable value under two different reasons.

**Revisit if:** a future story needs to know *which* value was kept, not only that a surplus one was
dropped — the template currently names the language and the concept but not the winning text, matching
every other set-aside reason's own convention of not carrying the value at fault as a param.

## D39 — A preferred label that slugifies to empty is set aside, and the reported reason names the slug, not the label (review fix 5)

A review of the merged feature found that `_assign_unique_slug` sets `slug_is_manual = True` with a
`base` that may be the empty string — `slugify(concept.label, allow_unicode=True)` returns `""` for a
label made up only of characters `slugify()` strips (a bare `"±"` is the reproduction case; a label of
punctuation, or of characters outside Unicode's word-character classes, produces the same result).
`Concept.save()` then raises `ValidationError({'slug': 'An explicit slug must not be empty.'})` for a
manual slug that is empty (research R4's own guard, protecting the composed local URL from corruption)
— uncaught, another raw exception escaping `import_skos()`.

**Chosen: check ahead of the write, the same D25 discipline every other unusable value in this
feature already gets, and set the concept aside rather than let the model's own guard raise.**
`_import_concepts` now checks `slugify(label, allow_unicode=True)` immediately after resolving
`label` — the same point `NO_PREFERRED_LABEL` is already checked, and for the same shape of reason:
a concept this run cannot usefully create is set aside and reported, `mentioned_uris` still records
it (so it is never *also* reported `absent_from_source` — the file does mention it, it just cannot be
used), and no lookup or write against it is attempted at all. A new `SetAsideReason.EMPTY_SLUG`
member was added to `report.py` following D26's pattern exactly.

**The reported reason names the slug, not the label — deliberately correcting, not repeating, the
model's own framing.** `Concept.save()`'s message is field-scoped ("An explicit slug must not be
empty") because that is the field the constraint lives on; read in isolation, that message points a
curator at the wrong thing; the label carries no defect at all — a bare `"±"` is a legitimate SKOS
`prefLabel` value, on its face — a curator told the *label* is the problem would find nothing wrong
with it and be no closer to understanding what actually blocked the concept. This importer's own
report entry says plainly what is actually true: the label is fine, the *derived* slug is not.

**Revisit if:** a future story wants a curator to be able to supply an explicit fallback slug for
this case (rather than the concept simply not importing) — that would be new functionality, not a
correction to this rule.

## D40 — Self-referential broader/narrower is skipped, the same no-op decisions.md D29 already applies to self-referential related (review fix 6)

A review of the merged feature found an asymmetry between how `_import_relations` treats a
self-referential `skos:related` triple and a self-referential `skos:broader`/`skos:narrower` one.
`desired_related`'s keys are a `frozenset({uri, str(other)})`, so a concept naming itself as related
to itself collapses to a single-element set, and D29's own `if len(pair) < 2: continue` already
treats that as a deliberate no-op, consistent with the model's own `_reject_self` refusing it if
attempted. `desired_broader`'s keys are a directed `(narrower_uri, broader_uri)` tuple, which never
collapses the same way — a self-referential `skos:broader` reaches `_resolve_concept_reference`
twice (resolving to the same `Concept` both times), lands in `resolved_broader` as `(pk, pk)`, and
`add_broader` then raises the model's own uncaught `ValidationError` ("A concept cannot be in a
relation with itself.").

**Chosen: make the two consistent, treating self-referential broader/narrower as the same kind of
no-op D29 already chose for self-referential related — not fatal, not set aside and reported, simply
skipped.** A `narrower_uri == broader_uri` check is added at the top of the broader/narrower
resolution loop, before `_resolve_concept_reference` is even called. Skipped rather than reported
because that is exactly D29's own reasoning for the `related` case, restated here rather than
re-argued: SKOS never intends a concept to be broader/narrower than itself, no fixture in this
feature's corpus or its predecessors exercises the shape, and D8's "the fatal set is deliberately
small" already leans against inventing a report reason nothing asks for. The asymmetry was a gap in
FIX 6's own predecessor task (T023/T024), not a deliberate choice recorded anywhere — nothing in
decisions.md ever argued broader should behave differently from related here, which is exactly why it
counts as the review-found inconsistency it is, not a considered design point being revisited.

**Revisit if:** a future story finds a real published vocabulary that states a self-referential
`skos:broader` deliberately (unlikely, since SKOS's own semantics make it meaningless) — at that
point silently skipping it may need to become reporting it instead, matching whatever `related`'s own
equivalent revisit would look like.

## D41 — `report.absent_from_source` names a record's `.uri`, never its raw (possibly-NULL) `static_uri` column (review fix 7)

A review of the merged feature found that `_import_concepts` and `_import_collections` share an
identical query bug: `Concept.objects.filter(scheme=target_scheme).exclude(static_uri__in=mentioned_uris)`
(and the same shape for `Collection`) also selects a row whose `static_uri` is `NULL`. Django compiles
`exclude(field__in=[...])` to `NOT (field IN (...) AND field IS NOT NULL)`, which evaluates true for a
NULL row regardless of what `mentioned_uris` contains — confirmed directly against the query, not
assumed from a reading of SQL's `NOT IN` semantics. A locally authored concept or collection (one
never given an externally published identifier) therefore always matched "not mentioned by this
file", which is even correct in one sense — the file genuinely never could mention it, having no
identifier to name it by — but the value the two functions then appended to
`report.absent_from_source: list[str]` was the raw column itself, `None`, not a URI at all.
`CONTEXT.md`'s own glossary entry for **URI** is explicit: "always present, never `None`. ... Every
record has one; it is never 'missing,' only dynamic or static."

**Chosen: report `.uri`, the `StaticUriModel` property every record already has, not the raw
column.** `.uri` returns `self.static_uri or self.local_url` — a locally authored record's dynamic,
site-composed URL when it has no static one, exactly the "dynamic or static, never missing" contract
`CONTEXT.md` states. Both call sites now iterate the queryset as model instances and report
`record.uri`, sorted in Python (`.uri` is a Python property, not a database column `.order_by()` can
reach) rather than via `.values_list("static_uri", flat=True).order_by("static_uri")` as before —
determinism preserved, just computed after the fetch rather than by the database. This does not
change *which* records are reported absent, only the string logged for the ones that were already
being caught by the query: a locally authored record with no publisher identity was already, correctly,
being treated as "the file cannot possibly speak about this" under FR-013's own authority rule; only
the value standing in for its identity in the report was wrong.

**Revisit if:** a future story wants to distinguish, in the report itself, "absent because the
publisher's file dropped it" from "absent because it was never externally identified in the first
place" — right now both land in the same bucket under the same shape of value (a URI, static or
dynamic), which this fix treats as correct per `CONTEXT.md`'s identity model, not as a gap to close
here.

## D42 — Reassigning a concept or collection to a different vocabulary is never a side effect of reading a file (review fixes 8/9)

A second review of the merged feature found that `_import_concepts` assigned `concept.scheme =
target_scheme` unconditionally on a `Concept.objects.get_by_uri` match, with no check that the
matched record already belonged to a *different* vocabulary. FR-005 lets a file that declares no
vocabulary of its own be imported into any caller-named target, so importing the identical file
first into one vocabulary and then into a second silently emptied the first: every concept moved,
and `report.updated` named the move with a bucket that means "content refreshed", not "record
relocated" — nothing in the report distinguished the two.

The spec's Edge Cases are the nearest governing text, and they point the same direction without
naming this exact shape: a contradictory source is set aside and reported while reading, not acted
on. Moving a record between vocabularies is a curatorial act — the maintainer's own word for it,
carried from the spec's broader stance that deletion, deprecation, and reassignment are each
deliberate acts a curator takes, never incidental consequences of running an importer (D5's
authoritative-for-what-it-contains rule governs *content*, not which vocabulary a record belongs to
at all).

**Chosen: a concept matched by `get_by_uri` that already belongs to a different vocabulary than the
one being imported is left exactly where it is.** It is set aside and reported under a new
`SetAsideReason.ALREADY_IN_ANOTHER_VOCABULARY` member, naming both the vocabulary it currently
belongs to and the one the run was importing into, and the run continues with everything else in the
file. Its content (labels, notes, relationships) is not touched either — the whole record is
untouched, the same "not created, not updated, but mentioned so never `absent_from_source`" shape
`VOCABULARY_MISMATCH`/`NO_PREFERRED_LABEL`/`EMPTY_SLUG` already established (T009/D17/D39).

**Where the check sits:** after the `get_by_uri` match/create branch resolves (so a *newly created*
concept never trips it — there is nothing to conflict with), before the row is mutated at all.
`target_scheme.pk` is always populated by this point, because `_resolve_scheme` has already saved it
before `_import_concepts` is ever called.

**Reproduced before the fix.** A no-scheme Turtle file with two concepts (`ex:a`/`ex:b`, `ex:b
skos:broader ex:a`) imported first into scheme "first", then into scheme "second": before the fix,
both concepts' `scheme_id` became "second"'s, `first.concepts.count()` went to zero, and
`report.updated` listed both URIs with nothing naming the move.

**Extended for review fix 9: `_import_collections` carried the identical defect, with a sharper
consequence.** `Collection.objects.get_by_uri` matched, `row.scheme = target_scheme` overwrote it
unconditionally, and the collection's *pre-existing* membership — rows written when the collection
genuinely belonged to its old vocabulary — was left exactly as it was, now spanning two schemes. That
is precisely the state `CollectionMember._reject_cross_scheme` exists to prevent, produced through
the package's own public API (`Collection.add`) with no report entry, because the membership rows a
re-import doesn't rewrite are never re-validated. The prediction in this entry's own original
"Revisit if" held: the same `SetAsideReason.ALREADY_IN_ANOTHER_VOCABULARY` is reused rather than a
second reason minted, following D38's own precedent (one reason serving two structurally identical
defects at two call sites) — "this record's identity is already held by a different vocabulary than
the one this run is writing into" is the same question for a concept and a collection. The check sits
in the identical place, `_import_collections`'s own `get_by_uri` match/create branch, before the row
is mutated; for a collection this additionally means its membership is left completely intact — no
half-migration, because the collection row itself is never rewritten.

**Reproduced before the fix (review fix 9).** Two files declaring different vocabularies but the
identical collection identifier, each with its own member: before the fix, the collection's `scheme`
became whichever file imported last, and its membership spanned both vocabularies — a state the model
itself refuses to create directly, produced anyway through the public import API.

**Revisit if:** a future workflow wants an explicit, curator-triggered "move this record to another
vocabulary" operation — that is new functionality with its own review of what happens to relationships
and collection membership on the far side of the move, not a correction to this rule, which only ever
concerns what an *import* run does on its own.

## D43 — A URI already held by a record of a different kind is detected while reading, not left to a constraint (review fix 10)

The spec's own Edge Cases name this exactly: "later a concept's identifier is found to be held by a
record of a different kind — a collection in one file, a concept in another. This is a contradictory
source and is reported while reading, rather than surfacing as a database constraint violation."
`_import_concepts` consulted only `Concept.objects.get_by_uri`, and `_import_collections` only
`Collection.objects.get_by_uri` — each model's own `static_uri` uniqueness constraint is scoped to
that model alone, so the two identity spaces never collide at the database level, and nothing
compared them to each other. A file that types `ex:thing` as a `skos:Collection`, imported, followed
by a second file that types the identical `ex:thing` as a `skos:Concept`, produced two real, live
records asserting the same static URI — the sole identity Article IX establishes — with the run
reporting nothing at all.

**Chosen: before minting a new record for a URI, check the *other* model's identity space too.**
`_import_concepts`, on a `Concept.DoesNotExist` from `get_by_uri`, now also tries
`Collection.objects.get_by_uri` for the same URI before creating a `Concept`; `_import_collections`
carries the exact mirror check the other way. A hit in the other model sets the URI aside and
reported under a new `SetAsideReason.URI_HELD_BY_DIFFERENT_KIND` member, naming only the subject —
there is nothing else useful to name, since the point is precisely that a curator did not expect two
kinds of record to share this identifier — and the second record is never created. The check runs
only on the "would create a new record" branch: a URI that already matches a record of the *same*
kind is an ordinary update, not a clash, so this adds no cost to the common case.

**Why not check both directions from one place, once, up front?** `_import_concepts` and
`_import_collections` run at different points in `import_skos` (concepts first, collections last,
within the same `_import_concepts` call), and a URI can only be *about to be created* from inside the
function that owns that creation. A single shared pre-pass would either duplicate the two loops'
own identity resolution or run before concepts exist for a same-file clash to be caught against, so
the check stays local to each creation site, the same "checked at the point of the write, not
gathered separately" discipline every other set-aside-ahead-of-write check in this module already
follows (D25).

**This also closes the same-file case, not only the cross-file one the spec's own wording leads
with.** Because concepts are always fully written before `_import_collections` runs (within the same
`_import_concepts` call), a single file that types one URI as both a `skos:Concept` and a
`skos:Collection` is caught the same way: the concept is created first, and when the collection node
for the identical URI is reached, `Concept.objects.get_by_uri` already finds it. No fixture in this
corpus exercises this shape specifically — the review's own reproduction is cross-file — but the
mechanism does not need a same-file/cross-file distinction to work correctly either way.

**Verified independently for each direction, by mutation.** Disabling the concept-side check alone
left `test_a_concept_uri_already_held_by_a_collection_is_refused` failing while
`test_a_collection_uri_already_held_by_a_concept_is_refused` stayed green; disabling the
collection-side check alone reproduced the opposite pattern — confirming the two checks are
independently load-bearing, not a copy that happens to also pass by luck.

**Revisit if:** a future feature wants to *resolve* the clash (e.g., let a curator choose which kind
wins, or merge the two) rather than refuse the second record — that is new curatorial functionality,
not a correction to this rule, which only ever refuses silently colliding on one identifier.

## D44 — An ordered collection falls back to `skos:member` when it has no `memberList`, and `memberList` narrows rather than replaces `member` when both are present (review fix 11)

`_import_collections`'s `if ordered:` branch read membership exclusively from `skos:memberList`,
falling back to an empty list when the collection carried none at all — even though `skos:member` is
the general SKOS membership predicate, valid on an ordered collection exactly as much as an
unordered one, and a publisher who states only `skos:member` on a `skos:OrderedCollection` (a real,
unremarkable shape — not every export bothers with an RDF list for a two- or three-member group) has
made a perfectly good, explicit membership assertion that this importer dropped entirely. Worse on a
re-import: because the reconciliation pass (D30) removes a membership the file "no longer states"
whenever the member concept was itself rewritten this run, reading an empty `member_uris` for such a
collection didn't just fail to add anything — it actively stripped membership an earlier,
correctly-read import (of the same file, before this defect, or of a different collection reached
via `skos:member` alone) had written.

The SKOS reference itself settles what the fallback should be: `skos:memberList` is documented as
*narrowing* `skos:member`, not replacing it — an ordered collection's list is understood to restate,
in order, the same members `skos:member` already asserts, and a publisher is free to assert both, or
a less careful export may assert only one or the other.

**Chosen: read both, with `memberList` — when present — deciding the order, and any `skos:member`
it omits appended afterward.** Three cases:

1. **`memberList` present, `skos:member` absent or a subset of it.** Unchanged from before this fix:
   `memberList`'s own order is `member_uris` in full.
2. **`memberList` present, `skos:member` also present and naming something `memberList` omits.**
   `memberList`'s own order comes first; any `skos:member` value not already named by `memberList`
   is appended after it, deduplicated against `memberList`'s own values by URI, in the same
   deterministic sorted order the unordered branch already uses for a value that carries no order of
   its own (a member asserted only via `skos:member` has none to prefer).
3. **`memberList` absent, `skos:member` present.** The new case this fix exists for: read the same
   deterministic sorted way as case 2's appended tail and as the unordered branch — there is no order
   to read, so there is nothing to lose by picking the same rule already used everywhere else a
   member carries none.

**What happens to a `skos:member` the `memberList` omits, decided explicitly rather than left
implicit:** it is *kept*, not dropped and not separately reported. Article XI's "nothing a file
contains is ever dropped in silence" is the operative rule, and `skos:member` is a real, explicit
membership assertion — omitting it from `memberList` is not the same shape of problem as a value the
models have no place for (that is what `SetAsideReason` names); it is simply a member whose *order*
the file did not additionally state through the ordered mechanism. No new report reason was added for
this: the member lands, visibly, as a `CollectionMember` row like any other, and a caller inspecting
the collection's own membership sees it there, which is a stronger form of "not silent" than a report
entry pointing at a value that was never actually withheld.

**Reproduced before the fix:** an `OrderedCollection` stated only with `skos:member` (no
`memberList` at all) imported with zero members, and a second import of the identical file produced
zero members again rather than staying at whatever the first import (correctly, once fixed) wrote —
confirming this was not only a missing-on-first-import defect but a lifecycle one. A second fixture,
asserting both predicates with `memberList` naming two of three members, confirmed the third
(`skos:member`-only) member was dropped entirely before the fix and lands after `memberList`'s own
two, in deterministic order, once fixed.

**Revisit if:** a future story finds a real published vocabulary where a `skos:member`-only member's
absence from `memberList` is meant to signal something other than "the publisher didn't bother
including it in the ordered list too" (for instance, a convention where `memberList` is deliberately
partial and authoritative for exactly what it names) — that would be evidence for treating the
omission as a set-aside-worthy discrepancy rather than a plain append, and belongs in its own
decision built against that evidence.

## D45 — Unmodelled-predicate reporting is generalised past the concept-only walk it was built for (review fix 12)

`_import_unheld_values` — the function that reports a predicate genuinely outside SKOS under
`SetAsideReason.UNMODELLED_PREDICATE` — was called exactly once, from `_import_concept_content`, so
it only ever walked a *concept* node's own predicates. Neither `_resolve_scheme` nor
`_import_collections` ran an equivalent walk over the vocabulary's own scheme node or a collection
node, so a non-SKOS predicate asserted on either — a curator's own `ex:owner` on the scheme, an
`ex:curatedBy` on a collection — was read by nothing and reported by nothing: dropped exactly as
silently as an unmodelled concept predicate would have been before T021 built this mechanism at all.
FR-014's own wording ("predicates the models have no place for") names no node kind restriction, and
D27's justification for the one deliberate exclusion this mechanism already carries — a SKOS
predicate with a model home but no read path yet, silently skipped rather than reported, because "a
later story will claim it" — has no equivalent argument for a predicate genuinely outside SKOS
entirely: no story was ever going to claim `ex:owner`, on any node kind.

**Chosen: extract the third, node-kind-agnostic clause of `_import_unheld_values`'s own walk into a
shared `_report_unmodelled_predicates(graph, node, uri, handled, report)`, parameterised by a
per-node-kind `handled` set, and call it once for each of the three record kinds this module
creates.** `_HANDLED_CONCEPT_PREDICATES` (unchanged) still gates the concept-level call;
`_HANDLED_SCHEME_PREDICATES` (new — identity, `skos:prefLabel`, `skos:hasTopConcept`,
`dcterms:description`) gates a new call at the end of `_resolve_scheme`; `_HANDLED_COLLECTION_PREDICATES`
(new — identity, `skos:prefLabel`, `skos:member`, `skos:memberList`) gates a new call inside
`_import_collections`'s own per-collection loop. Deliberately *not* extended to the `skos:notation`/
mapping-predicate checks that also live in `_import_unheld_values`: those two are concept-specific
SKOS constructs by the vocabulary's own semantics (a mapping links one *concept* to another across
vocabularies; a notation identifies a *concept*), the review finding names only the generic
"unmodelled predicate" gap, and extending notation/mapping reporting to scheme and collection nodes
with no fixture material motivating it would be exactly the speculative reporting D27 already argues
against for a predicate nothing asks to see reported.

**Placement of the new calls matters.** The scheme call runs only once the scheme row itself has
been resolved and saved — a scheme that cannot be resolved at all (`VOCABULARY_UNDETERMINED`/
`VOCABULARY_TARGET_MISMATCH`/`VOCABULARY_AMBIGUOUS`) never reaches it, consistent with every other
predicate-level check in this module only running for a record that is actually going to exist. The
collection call runs only for a collection that passed both this fix's own D42/D43 identity checks
and was actually saved — a collection set aside for belonging to another vocabulary, or for its URI
clashing with a concept's, has no row for a non-SKOS predicate to be "on" in any sense a curator
would recognise, so it is not walked either.

**Reproduced before the fix:** a fixture carrying a scheme node with `ex:owner` and a collection node
with `ex:curatedBy` imported cleanly, with neither predicate appearing anywhere in
`report.set_aside` — confirmed by two failing tests before the production change, one per node kind.

**Verified independently for each node kind, by mutation.** Disabling only the scheme-level call left
the collection-level test green and only the scheme-level test failing; disabling only the
collection-level call reproduced the opposite pattern — confirming the two calls are independently
load-bearing.

**Revisit if:** a future story finds a real published vocabulary using `skos:notation` or a mapping
predicate on a scheme or collection node with a use worth modelling — that is new capability
(a place to *store* it, or a considered reason to report it under NOTATION/MAPPING rather than the
generic UNMODELLED_PREDICATE), not a correction to this decision's deliberate scope limit.

## D46 — The predicate-coverage gate is rewritten to check actual evidence, not membership in production's own exclusion set (review fix 13)

`tests/test_exchange/test_skos.py::TestEverySkosPredicateIsReadOrReported` (T033, D34) computed a
`recognised` set from `_HANDLED_CONCEPT_PREDICATES | _READ_BUT_NOT_AT_CONCEPT_LEVEL` — the first
imported directly from `skos.py`, the second a small hand-kept set naming the three predicates read
at a node kind other than a concept's own — and asserted every SKOS predicate found anywhere in the
fixture corpus was a member. D34's own account of this test says plainly what membership means:
"not double-reported by `_import_unheld_values`." That is a different claim than the one FR-014 and
this test's own docstring actually make — "read by the importer, or named in the report" — and the
gap between the two is exactly the shape of defect this fix's brief names: adding a predicate to
`_HANDLED_CONCEPT_PREDICATES` with no read path behind it makes the predicate "recognised" and the
test pass, in the same edit that makes the importer silently stop accounting for it. The test's own
"recognised" set and the constant a regression would touch were the same object; the test could not,
structurally, ever catch that shape of regression.

**Chosen: rebuild the test on independent evidence.** For every fixture that can succeed standing
alone (`scheme=None`, no pre-seeded database — the same discovery walk `ALL_FIXTURES` already uses,
now filtered to exclude the fatal-path fixtures and the two that need a caller-supplied target this
sweep does not attempt to construct, each already exercised directly by its own dedicated test
class), the test imports it and, for every SKOS predicate the graph carries on a node this importer
actually treats as a record (a concept, the vocabulary's own resolved scheme node — never a second,
merely-referenced declared scheme, as in `mixed_scheme_membership.ttl`'s "other" — or a collection),
requires direct evidence: a matching `ConceptLabel`/`ConceptNote`/`ConceptRelation`/`CollectionMember`
row, a matching `Concept.label` or `ConceptScheme.name`/`Collection.name` value, or a matching
`report.set_aside`/`report.normalized` entry naming the same subject and, where the reason carries
one, the same language or predicate. None of this evidence-gathering imports anything from `skos.py`:
`_COVERAGE_LABEL_KIND`/`_COVERAGE_NOTE_KIND`/`_COVERAGE_MAPPING_CURIE` restate the SKOS
specification's own predicate-to-kind vocabulary independently, in the test file, so a future
regression in production's own classification has no matching classification in the test to hide
behind.

**A record entirely excluded this run — set aside under `NO_PREFERRED_LABEL`, `VOCABULARY_MISMATCH`,
`EMPTY_SLUG`, or this fix's own `ALREADY_IN_ANOTHER_VOCABULARY`/`URI_HELD_BY_DIFFERENT_KIND` — blanket-
covers every one of its own predicates.** There is no record for any of them to have landed against,
and the set-aside entry already explains why the whole node was skipped; requiring separate evidence
per predicate on a node that was never created would be checking for something that cannot exist.
This is narrower than it might look: a record that *was* created, with only one specific value set
aside (`UNCONFIGURED_LANGUAGE`, `SURPLUS_PREFERRED_LABEL`, `NOTATION`, `MAPPING`, `MISSING_MEMBER`,
`MISSING_RELATION_END`, `RELATION_DISJOINTNESS`) does **not** get this blanket treatment — every one
of *that* node's other predicates still needs its own evidence, exactly the distinction a first draft
of this rewrite missed (treating any subject appearing in *any* set-aside entry as wholly excused,
which would have let `unmodelled_and_normalised_values.ttl`'s own `widget` concept's `prefLabel` pass
unverified merely because `widget` also carries a separately-reported notation).

**Proven stronger by mutation, not merely argued.** Disabling `skos:broader`/`skos:narrower` reading
in `_import_relations` (commenting out the two `graph.objects(node, SKOS.broader/narrower)` loops)
while leaving `_HANDLED_CONCEPT_PREDICATES` completely unchanged — the exact shape of regression this
fix exists to catch — reproduces the old test's own logic (rebuilt inline against the unmodified
constant) still passing, `unrecognised == set()`, while the new, rewritten test fails on eleven
fixtures, naming `skos:broader`/`skos:narrower` on the concepts whose relation no longer lands or is
reported. Reverted immediately after recording the result; no production code was left changed by
this probe.

**One honest limitation, not hidden in new clothes.** The rewrite is fixture-by-fixture, not a single
global sweep, and it excludes the fatal-path fixtures and two target-requiring ones
(`_PREDICATE_COVERAGE_EXCLUDED_FIXTURES`) because a failed run has no resulting record and no
non-fatal report entry for a predicate's coverage to appear in — there is nothing behavioural left to
check on a run that wrote nothing. Their own predicates are still exercised, just by the test classes
built to exercise those specific fixtures directly (named in the exclusion set's own comments), not
by this generic sweep. A fully global, no-exclusions version was not attempted: it would need this
test to also supply a synthetic target scheme for the ambiguous/undeclared cases, which risks
asserting behaviour these fixtures were never built to have and duplicating what
`TestChoosingBetweenDeclaredVocabularies`/`TestImportSkosVocabulary` already cover on purpose.

**Revisit if:** a SKOS predicate this dispatcher has no case for yet reaches the fixture corpus — it
is treated as uncovered (a hard failure naming the predicate) rather than silently skipped, which is
deliberate: a new predicate must earn its own evidence rule in `_coverage_predicate_covered`, the
same discipline this whole fix exists to enforce on production's own classification.

## D47 — An inline object `@context` is checked for `@import`, the only key in a JSON-LD context object that triggers a fetch (review fix 14, security)

`safety.py::_check_context_value` refused a plain string `@context` (or a string entry inside an
array `@context`) but passed a `dict` `@context` straight through, on the stated reasoning — the
module's own docstring, until this fix — that an inline object context "carries nothing to resolve".
That reasoning was false. Read against the installed `rdflib` version's own source
(`rdflib/plugins/shared/jsonld/context.py::Context._read_source`), any dict treated as a context is
checked for an `@import` key, and a string value there is resolved through the identical
`urlopen`-backed `_fetch_context`/`source_to_json` path a string `@context` uses — no allowlist,
`file://` and any local path the process can read included. Reproduced through the public entry
point: `exfil_via_import.jsonld`'s top-level `@context` is an inline object (`{"@version": 1.1,
"@import": "exfil_secret.jsonld", "skos": "..."}`), which the old scan waved through entirely;
`import_skos()` on it created a `ConceptScheme` whose URI was
`http://example.org/SECRET-FROM-LOCAL-FILE/scheme`, built from a prefix the imported file (not the
document itself) defined. The `@import` value is a relative reference, `urljoin`-resolved against
the document's own file location by rdflib, so the same route reads any file the process can see,
not only ones named absolutely.

**Enumerated the whole category, not only `@import` in isolation.** Every dict-shaped construct
`_read_source` reads — `@vocab`, `@version`, `@base`, `@propagate`, `@protected`, and each term
definition's own `@id`/`@type`/`@container`/`@index`/`@language`/`@reverse`/`@context`/`@prefix` — was
checked against the same source file. All of them either assign local `Context` state directly or
route through `_rec_expand`/`_prep_expand`/`_get_source_id`, none of which reach `source_to_json` or
`urlopen`. `@import` is the only key that does. A term's own `@context` (`context = dfn.get(CONTEXT,
UNDEF)`, consumed later by `get_context_for_term`/`_subcontext`/`load`) is a second `@context`-keyed
value, not a fetch trigger on its own — it is exactly the "context inside a context" shape this
scan's own `_iter_context_values` already discovers by recursing into every value, so it reaches
`_check_context_value` again as its own entry and is checked for `@import` the same way. Nothing was
found and deliberately left unguarded; the enumeration closed with `@import` as the only path.

**Chosen: check every dict `_check_context_value` sees — top level, inside an array entry, or
reached via `_iter_context_values`'s own recursion into a nested/node-scoped context — for a string
`@import` key, and refuse it with its own code (`jsonld_context_import_forbidden`) distinct from the
string-`@context` refusal's (`jsonld_remote_context_forbidden`)**, so a caller inspecting `err.code`
can tell the two routes apart. The array branch now recurses into a dict entry via
`_check_context_value` itself rather than duplicating the `@import` check inline, so the top-level and
array-entry cases share one code path and cannot drift apart.

**Four shapes tested, one regression control.** `exfil_via_import.jsonld` (top-level dict `@context`
with `@import`, the exact reproduction), `context_import_array.jsonld` (`@import` inside a dict entry
of an array `@context`), `context_import_nested_term.jsonld` (a term's own nested `@context` carrying
`@import` — context inside a context), and `context_import_graph_node.jsonld` (a node inside `@graph`
carrying its own `@context` with `@import`) are each refused with `jsonld_context_import_forbidden`.
`inline_context.jsonld` — an ordinary inline object context with no `@import` at all, the shape the
overwhelming majority of published files use — is unaffected, proven by the same test that already
covered it before this fix.

**Verified by mutation.** Reducing the new dict branch to a no-op reproduced all four new tests
failing (`DID NOT RAISE UnsafeJsonLdError`) while the regression-control test kept passing; restored
immediately after.

**Revisit if:** a future `rdflib` upgrade adds a second dict-context key that reaches `urlopen` — the
enumeration above is against the currently-installed version's source, not the JSON-LD 1.1 spec text,
and rdflib's own implementation is what this application actually calls.

## D48 — An untagged (or non-literal) label/note value is set aside and reported, never guessed into the default language (review fix 15)

`_import_labels` and `_import_notes` both `continue`d on a `graph.objects()` value that was not an
`rdflib.Literal`, or that carried no `.language`, with no `report.set_aside`/`report.normalized` entry
either way — dropped exactly as silently as if `_import_unheld_values` had never been built.
`_report_unmodelled_predicates` could not catch it: it skips every predicate inside the SKOS namespace
unconditionally, on the reasoning (D45's own words) that "the models do have a place for it" — true
of the *predicate*, not of a specific *value* on it that carries nothing the models can key a language
by. Reproduced before any test: a concept carrying a tagged `skos:prefLabel "Alpha"@en` alongside an
untagged `skos:altLabel "plain alt"` and an untagged `skos:definition "plain definition"` imported
with `report.set_aside == []` and `report.normalized == []` — both values gone with no trace, exactly
the silent-drop Article XI and the README's own "nothing a file contains is ever dropped in silence"
forbid. A `skos:definition <some-uri>` — an object that is not a `Literal` at all — falls through the
identical branch and is silently dropped the same way.

**Two options, decided from FR-008/FR-009 and the models rather than picked for convenience.**
FR-008: "Preferred, alternative, and hidden labels MUST be stored against their concept, each with its
language and kind." FR-009: notes "MUST be stored against their concept... each with its language."
Both require a language; an untagged value carries none — not an unconfigured one, none at all — so
neither requirement can be met by storing it as given. The alternative, storing it against the
vocabulary's effective default language, would be inventing a fact the file never asserted, and it is
not merely a stylistic overreach: for a `PREFERRED` value specifically, the default-language slot is
already spoken for by `Concept.label` (`_preferred_label_in`'s own deterministic pick from *tagged*
default-language literals only), and `ConceptLabel._reject_default_language_preferred` refuses a
`PREFERRED` row in that language outright — so treating an untagged `prefLabel` as "default language"
would either silently collide with an already-chosen `Concept.label` or have to be set aside anyway
the moment it is attempted, making "store it" not even a real option for that one kind, and applying
it only to `altLabel`/`hiddenLabel`/notes while refusing it for `prefLabel` would be an inconsistent
half-measure for what is one defect. **Chosen: set aside and report, uniformly, under a new
`SetAsideReason.NO_LANGUAGE_TAG`** — the same "unusable value, never dropped in silence, never
crashes the run" treatment this feature already gives every other value it cannot store, applied here
without inventing a language the publisher never wrote down. The non-`Literal` case (`skos:definition
<uri>`) gets the same reason and the same treatment: it is not language-tagged text either, for a
different reason than a missing tag, but the outcome the models can offer it is identical.

**One report entry per predicate per subject, naming the predicate's own CURIE** (`skos:altLabel`,
`skos:definition`, ...) via a new `_skos_curie()` helper in `skos.py` — every `LABEL_PREDICATES`/
`NOTE_PREDICATES` key is a SKOS predicate, so a lookup table is unnecessary; this mirrors the
readable-CURIE convention `MAPPING_PREDICATES` already established for its own reports. The
`dcterms:description` alias loop in `_import_notes` carries the identical defect one predicate over —
same silent `continue`, same governing FR-009 wording — and is fixed the same way, reporting
`predicate="dcterms:description"` (the literal string constant already used for its
`NormalizedReason.FOREIGN_DEFINITION` report, kept consistent).

**The predicate-coverage gate's own blind spot closed too.**
`TestEverySkosPredicateIsReadOrReported`'s `_coverage_predicate_covered` skipped any label/note
triple whose object was untagged or non-literal outright (`or not isinstance(literal, rdflib.Literal)
or not literal.language: continue`) before ever asking whether it had evidence — which is exactly why
no existing fixture or test noticed this defect despite that gate's own stated purpose (D46: "read by
the importer, or named in the report"). Replaced with a call to a new `_coverage_untagged_covered`
helper, checking for a matching `NO_LANGUAGE_TAG` entry instead of skipping; a new
`_COVERAGE_LABEL_NOTE_CURIE` table restates the predicate→CURIE mapping independently in the test
file (D46's own "no shared classification with production" discipline), rather than importing
`_skos_curie` from `skos.py`. `untagged_literal_values.ttl` — the new fixture, auto-discovered by
`ALL_FIXTURES` — now exercises this gate too.

**Verified by mutation, at two layers.** Reverted the `report.add_set_aside(NO_LANGUAGE_TAG, ...)`
call in both `_import_labels` and `_import_notes` (all three sites: the label loop, the native note
loop, the `dcterms:description` loop) back to a bare `continue`. Three of the five new
`TestUntaggedOrNonLiteralValuesAreSetAside` tests failed (`0 == 2`/`0 == 1`), and, independently, the
predicate-coverage gate's own new parametrized instance for `untagged_literal_values.ttl` failed too,
naming both `skos:altLabel` and `skos:definition` on `alpha` as uncovered — proving the gate itself,
not only the dedicated test class, would have caught this regressing. Restored immediately; full
suite re-ran green.

**Revisit if:** a future story gives the models a real place to store a value with no language (a
language-neutral text field, or an explicit "unknown language" marker) — that is new modelling
capability, not a correction to this decision's reading of FR-008/FR-009 as written today.

## D49 — `_assign_unique_slug` reads the scheme's taken slugs once, in one query, and carries the running result across the whole import instead of one query per suffix attempt (review fix 16, performance)

`_assign_unique_slug`'s `while Concept.objects.filter(scheme=scheme, slug=candidate).exclude(pk=concept.pk).exists()`
loop issued one query per suffix attempt, and the suffix counter restarted at 1 for every concept, so
N concepts deriving the same base slug cost N(N+1)/2 round-trips — all inside the one
`transaction.atomic()` the whole run sits in. D6 already establishes that two source concepts sharing
a preferred label is the *expected* case for a published file, not a rare edge condition, and plan.md's
own reading strategy explicitly rules out anything quadratic in concept count. Measured directly
against a 40-concept file where every concept shares one label: 1,069 queries before this fix.

**Chosen: fetch every `(slug, static_uri)` pair already held in the target scheme once, in a single
query, into a `dict[str, str | None]` (`taken_slugs`), and thread it through `_import_concepts`'s own
per-concept loop into `_assign_unique_slug`, which reads and mutates it in place rather than querying
the database at all.** A slug is free when `taken_slugs` has no entry for it, or when the entry names
the concept currently being assigned; otherwise the numeric suffix increments and the check repeats
against the same in-memory dict. Once a concept's slug is decided, `taken_slugs[candidate]` is set to
its `static_uri`, so the next concept sharing that base label — processed later in the same,
already-deterministic URI-sorted order (D6) — sees it as taken without a query. Net query cost for the
whole shared-label group drops from quadratic to the one seeding query plus a small, genuinely constant
per-concept cost from everything else the per-concept loop already does (`Concept.objects.get_by_uri`,
the `Collection` cross-kind check, `Concept.save()`'s own guard, the insert itself, and the
label/note/unheld-value writes) — none of which scale with the *size of the shared-label group*, only
with N itself, which is the linear cost this fix accepts as unavoidable.

**Keyed by `static_uri`, not `pk`, because a newly created concept has no primary key at the point its
own slug is being decided.** `pk` cannot distinguish "this is my own, not-yet-saved row" from "nothing
has claimed this slug yet" the way the concept's own `static_uri` — already assigned by
`_import_concepts` before `_assign_unique_slug` is ever called, and immutable for the rest of the run
— can. Seeding `taken_slugs` from `Concept.objects.filter(scheme=target_scheme).values_list("slug",
"static_uri")` (the raw column, not the `.uri` property FIX 7/D41 uses for *reporting*) is deliberate
too: some existing concepts carry a `NULL` `static_uri` (a locally authored record, per
`StaticUriModel`'s own docstring — "leave blank while this record is authored here"), and `None` is a
perfectly good "not this concept" sentinel for this internal comparison, unlike a display-facing
report entry, where D41 already established that showing `None` to a curator would be actively
misleading. No two real imported concepts ever share a `static_uri` (identity is unique by
construction), so a `None` collision between two different local rows is harmless: neither is ever the
`concept.static_uri` being compared against.

**`taken_slugs` is seeded from the whole scheme, not only the concepts this run will touch**, so a
concept the file never mentions at all this run — left completely untouched per FR-013, its slug never
recomputed — still correctly blocks a *newly processed* concept from claiming the same slug. Nothing
about "absent from source" concepts changes: they are never written to `taken_slugs` a second time,
only read from it as an initial claim that persists for the run's whole duration.

**`Concept.save()`'s own identical `EXISTS` check (models.py, `Concept.save()`) is deliberately left
in place, not removed.** It is that model's own integrity backstop — the docstring's own words, "the
UniqueConstraint is the integrity backstop", guarding both a derived slug and an explicit one, from
*any* caller, not only this importer (a curator's own admin/GUI edit, a factory, a future script). This
importer's own `taken_slugs` guarantees no collision for what *this run* writes, but the model has no
way to know that its caller already did that work, and weakening the model's own guard to trust one
particular caller would reopen the hole R4 built it to close for every other one. Left as one extra,
genuinely constant-cost query per `Concept.save()` call — linear in N, not quadratic in a shared-label
group's size — which is the acceptable, documented cost of keeping that guarantee for every caller.

**Verified by a query-count bound, not merely argued — the task's own instruction, since a
correctness-only test cannot distinguish O(N) from O(N²).** A new
`TestSlugAssignmentQueryCountIsLinearInASharedLabelGroup` in `test_skos.py` writes a 40-concept Turtle
file where every concept shares one `skos:prefLabel`, wraps the import in
`django.test.utils.CaptureQueriesContext`, and asserts the captured query count stays under `12 * n`.
Measured directly against this exact fixture and settings: 1,069 queries before this fix, 250 after,
and confirmed linear (not merely "smaller") by measuring N=20/40/80/160 post-fix — 130/250/490/970,
each doubling of N roughly doubling the count rather than roughly quadrupling it, the way N(N+1)/2
would. A second new test, `test_the_same_file_imported_twice_produces_the_same_slugs`, re-imports the
same 12-concept shared-label file twice and asserts every concept's slug is identical both times —
D6's determinism requirement, now resting on `taken_slugs` being seeded fresh, deterministically, from
the database on every run rather than on any accumulated in-process state.

**Verified by mutation.** Restored the original per-suffix `Concept.objects.filter(...).exists()` loop
(keeping `taken_slugs` threaded through elsewhere unchanged) — the new query-count test failed at
1,070 queries for the same 40-concept fixture, correctly rejecting the reintroduced quadratic shape;
restored the fix immediately, full suite re-ran green.

**Revisit if:** a future story needs `_assign_unique_slug` reachable outside `_import_concepts`'s own
per-concept loop (it currently has exactly one caller) — `taken_slugs` would need seeding at whatever
new call site takes on that responsibility, the same discipline this fix already applies here.

## D50 — A node identified as a concept only through a scheme-membership predicate, never through `rdf:type`, is imported rather than left invisible (review fix 17)

`concept_nodes` came only from `graph.subjects(rdflib.RDF.type, SKOS.Concept)`. A node the file
identifies as a concept through `skos:inScheme`, `skos:topConceptOf`, or the scheme's own
`skos:hasTopConcept` — the identical three predicates `_scheme_refs` already reads to check for a
vocabulary mismatch — but which never states `rdf:type` at all, was invisible to the whole import: not
created, not set aside, not named anywhere in the report. A curator importing such a file got a green
result naming only the scheme, no concepts, and no explanation. This is not a hypothetical corner:
omitting `rdf:type` on a concept while still declaring its scheme membership is a real shape a
published file can take, and the governing rule stated across this whole review batch — "an unusable
value is set aside and reported; it is never dropped in silence" — applies just as much to a whole
*record* the file plainly means to include as it does to one field on a record already found.

**Decided: treat such a node as a concept, not merely report that one was skipped.** The silent no-op
was ruled out from the start (the review brief's own words); between "import it" and "refuse/report
it without importing", importing it is what the file's own membership predicates already say to do —
`skos:inScheme`/`skos:topConceptOf` on the node itself, or `skos:hasTopConcept` naming it from the
scheme, are not ambiguous about intent the way, say, an untyped node with no predicates at all would
be. A node reporting *itself* as a set-aside "found but not classified" case would be strictly less
useful than simply completing the classification the file's own predicates already supply, and every
downstream check this importer already runs (`_conflicting_scheme_ref`, `NO_PREFERRED_LABEL`,
`_identify`'s own blank-node/refused-identity fatal checks) applies to it exactly as it would to an
explicitly-typed concept — nothing about the rest of the pipeline needs to know the difference.

**Chosen: a new `_implied_concept_nodes(graph)` helper, folded into `concept_nodes` before scheme
disambiguation runs**, restricted to a node carrying **no** `rdf:type` triple whatsoever — a node the
file *does* type, as anything other than `skos:Concept`, is left entirely to whatever that type
already makes of it (a `skos:Collection`, a `skos:ConceptScheme`), never reclassified. Computed
graph-wide (`graph.subjects(SKOS.inScheme, None)` / `graph.subjects(SKOS.topConceptOf, None)` /
`graph.objects(None, SKOS.hasTopConcept)`), not scoped to one already-chosen scheme, because there is
no `declared_node` decided yet at the point this must run — `_choose_declared_scheme` itself already
uses `concept_nodes` to break a tie between multiple declared schemes by counting each one's members
(`_scheme_refs`), so folding the implied nodes in *before* that call, not after, means an implied
concept correctly counts toward its own scheme's membership tally too, not only toward whether it gets
imported at all.

**A node implied into a *foreign* scheme is not a special case — it falls through to the same
`VOCABULARY_MISMATCH` check an explicitly-typed foreign concept already gets**, since nothing about
`_conflicting_scheme_ref`/`_import_concepts` depends on how a node arrived in `concept_nodes`.
Likewise a node with no usable identity (a blank node, or a refused URI scheme) reaches the same
`_identify`-driven fatal path any other concept node does — no special-casing needed there either.

**One limitation, named rather than hidden.** This does not attempt to distinguish "this untyped node
is really a `Collection`, not a `Concept`" — a node with, say, `skos:memberList` but no `rdf:type` and
no scheme-membership predicate of its own stays entirely outside this fix's scope (and outside the
whole import, as before), since nothing here claims to guess a *collection's* implied type the way
`skos:inScheme`/`topConceptOf`/`hasTopConcept` specifically imply concept-hood. No fixture material
motivates guessing that case yet.

**Verified by mutation, at two independent layers.** Reverted `concept_nodes` to the original
type-only query. Four of the five new `TestConceptsImpliedByMembershipButNeverGivenAnRdfType` tests
failed (`Concept.DoesNotExist` / a `report.created` set missing all three implied concepts), and,
independently, `TestEverySkosPredicateIsReadOrReported`'s own new parametrized instance for the new
fixture failed too, naming `skos:hasTopConcept` on the scheme as neither reflected in a record nor
reported — proving the coverage gate itself, not only the dedicated test class, would have caught this
regressing. Restored immediately; full suite re-ran green.

**Revisit if:** a real published vocabulary motivates guessing collection-hood the same way — that is
new scope, not a correction to this decision's deliberate concept-only reading of the three
membership predicates.

## D51 — Three crafted-file failure paths are wrapped into the documented exception hierarchy (review fix 18)

Three verified paths raised an exception that is neither `SkosImportError` nor `SkosImportFailed`, so
a caller catching only the documented pair — a downstream upload form, say, exactly the shape the
package's own docstrings describe — got an unhandled exception instead of a translatable refusal:

1. `defusedxml.sax.parseString` (`scan_rdf_xml`, called from `_read_graph`) ran *before* the function's
   own try/except, and only catches `EntitiesForbidden`/`ExternalReferenceForbidden` itself, so a
   document that is not well-formed XML at all — including a Turtle file merely renamed to `.rdf` —
   raised a bare `xml.sax.SAXParseException` straight out of the package.
2. A cyclic `skos:memberList` (an `rdf:rest` chain looping back on itself instead of terminating in
   `rdf:nil`) made `graph.items()`, deep inside `_import_collections`, raise a bare
   `ValueError("List contains a recursive rdf:rest reference")`.
3. A deeply nested JSON-LD document exhausted Python's own recursion limit inside `scan_json_ld`'s
   recursive `_iter_context_values` walk (also called from `_read_graph`, also before its own
   try/except), raising a bare `RecursionError`.

**Chosen: wrap each at the point it is raised, with a translatable message and its own `code`,
chaining the original onto `__cause__` — the pattern the module already uses for the unparseable-file
case, applied to the two paths that used to sit outside the try/except that pattern already lived
in, plus the one entirely new path.** For (1) and (3): widened `_read_graph`'s existing try/except to
also cover the `scan_rdf_xml`/`scan_json_ld` calls, not only `graph.parse()`. The *deliberate* safety
refusals — `UnsafeRdfXmlError`/`UnsafeJsonLdError` (decisions.md D36/D47) — are explicitly excluded
from that wrapping (`except (UnsafeRdfXmlError, UnsafeJsonLdError): raise` ahead of the general
`except Exception`), so a caller distinguishing "unsafe" from "merely unreadable" keeps working
exactly as before; both existing `TestReadGraph` tests asserting the specific `Unsafe*Error` types
still pass unchanged. Both failures reuse the identical `skos_parse_failed` code and message template
the unparseable-file case already uses — from a caller's perspective it is the same experience ("this
file could not be parsed"), and introducing a second code for the same experience would be a
distinction with no behavioural difference to key off. For (2): a new
`SkosImportError`/`skos_cyclic_member_list`, raised at the `graph.items()` call site itself, naming
the collection's own URI.

**Not turned into a per-record `SetAsideReason`, deliberately.** Every other kind of unusable value
this feature meets is set aside and the rest of the file still imports (the governing rule this whole
review batch states repeatedly). A cyclic list is different in kind: `graph.items()` cannot produce
even a partial, well-defined membership to fall back to — the cycle means there is no principled
"read what came before the loop and stop" semantics, only an arbitrary point where rdflib's own guard
happened to detect it. Refusing the whole run, exactly as a missing/refused identity already does
(D3/D8), keeps the invariant that what *is* written is always something the file actually,
unambiguously asserted.

**Raised inside the same `transaction.atomic()` block `import_skos()` already wraps every write in**,
so no special rollback handling was needed for the cyclic-`memberList` case: an exception propagating
out of a `with transaction.atomic():` block rolls it back regardless of its type, the same mechanism
`SkosImportFailed` already relies on for a collected fatal finding.

**Verified by mutation, independently for each of the three paths.** Reverted `_read_graph`'s
try/except back to covering only `graph.parse()` — both the malformed-XML-renamed-to-`.rdf` test and
the deeply-nested-JSON-LD test failed, each with the original bare exception, while both
`Unsafe*Error`-still-propagates regression-control tests kept passing. Restored, then separately
reverted the `graph.items()` wrapping — both cyclic-`memberList` tests failed with the original bare
`ValueError`. Restored both; full suite re-ran green.

**One measurement note, not a defect:** reproducing the `RecursionError` case as a test needed a
document nested roughly 3,000 levels deep — built as raw text, not via `json.dump`, since the
encoder's own recursive descent hits the same recursion limit before the file is even written, at a
depth well below what is needed to reproduce the *parser's own* failure. Before this fix, the test
took ~37s (pytest formatting a ~3,000-frame traceback for the uncaught `RecursionError`); after the
fix, the same test runs in well under a second, since the exception is now caught and wrapped only a
few frames from where it originates.

**Revisit if:** a fourth crafted-input shape reaching outside `SkosImportError`/`SkosImportFailed` is
found — the same "enumerate the actual mechanism, not just the reported symptom" discipline FIX 14
already applied to `safety.py` applies here too, rather than patching only the exact three cases named.

## D52 — `UnsafeRdfXmlError`/`UnsafeJsonLdError` become exported `SkosImportError` subclasses (review fix 19)

`UnsafeRdfXmlError` and `UnsafeJsonLdError` propagate out of `import_skos()` (they are raised inside
`_read_graph`, uncaught) but were in neither `controlled_vocabularies.exchange.__all__` nor the
README/CHANGELOG, and were plain `ValidationError` subclasses with no relation to `SkosImportError`.
A consumer writing the package's own documented `except (SkosImportError, SkosImportFailed)` — the
exact shape this package's own docstrings and every existing test already use — did not catch a
hostile file, precisely the case the safety scan exists to guard against.

**Chosen the recommended option: make them `SkosImportError` subclasses**, rather than merely
exporting and documenting them as a third, independent type. A consumer that already wrote the
documented two-exception `except` clause is correct by construction the moment this ships, with no
code change on their side required — the alternative (export-and-document only) would still leave
every *existing* piece of consumer code silently wrong until someone reads the changelog and adds a
third type to their `except` clause, which is exactly the gap this fix exists to close, not merely
relabel.

**Where `SkosImportError` itself now lives, and why.** `SkosImportError` was defined in `skos.py`;
`UnsafeRdfXmlError`/`UnsafeJsonLdError` are defined in `safety.py`, a module `skos.py` already imports
from. Subclassing across that boundary in the naive direction would need `safety.py` to import
`SkosImportError` from `skos.py` — a circular import, since `skos.py` already imports `scan_rdf_xml`/
`scan_json_ld` from `safety.py`. **`SkosImportError`'s definition moved to `safety.py`** (the
lower-level module of the two, with no dependency on `skos.py` at all) rather than introducing a
third module purely to hold one class: `skos.py` now imports `SkosImportError` from `safety.py`
alongside the two `Unsafe*Error` types it already imported, and re-exports it under the same name —
`controlled_vocabularies.exchange.skos.SkosImportError` is the identical object it always was, so no
existing `from ...skos import SkosImportError` import site anywhere (including every test in
`test_skos.py`) needed to change. `SkosImportFailed` was deliberately left where it is, still a plain
`ValidationError` sibling of `SkosImportError`, not folded into the same subclass tree — it names a
structurally different situation (the file *was* read; the run collected fatal findings while
processing it) and nothing in the fix's brief or the spec's own exception contract asks the two to be
related.

**`exchange/__init__.py`'s `__all__` gains both names**, imported from `safety.py` directly (not
re-exported a second time through `skos.py`), matching the module each is actually defined in.

**Verified by mutation.** Reverted both classes to plain `ValidationError` subclasses (leaving the
export and the module relocation otherwise untouched) — `issubclass(UnsafeRdfXmlError,
SkosImportError)`/`issubclass(UnsafeJsonLdError, SkosImportError)` both failed, and the two
consumer-simulation tests (`import_skos()` on a hostile RDF/XML and a hostile JSON-LD file, each
wrapped in `except (SkosImportError, SkosImportFailed)`) failed with the exception escaping the
`except` clause entirely — reproducing the exact consumer-facing failure this fix closes. Restored
immediately; full suite re-ran green.

**README and CHANGELOG updated in the same commit (Article VI)**, including one correction beyond
this fix's own scope found while editing: the README's existing "A JSON-LD document that carries its
context inline imports normally" sentence was no longer fully accurate after decisions.md D47 (an
inline context carrying `@import` is refused) and needed updating regardless of FIX 19 — fixed here
rather than left inaccurate, since both edits touch the same paragraph.

**Revisit if:** a future safety scan (a third serialization, say) adds its own refusal exception —
the same "subclass the documented hierarchy, export it, document it" pattern applies without
needing a fresh decision.

## D53 — `__in` clauses sized by concept count are replaced with scheme-scoped queries and Python-side filtering (review fix 20, performance, confirmed before fixing)

**Confirmed the claim first, against the installed Django version's own source, before writing any
fix.** Read `django.db.models.lookups.In` (`as_sql`/`split_parameter_list_as_sql`): Django chunks an
`__in` clause only when `connection.ops.max_in_list_size()` returns a number, and grepping every
backend's `operations.py` in the installed package shows only Oracle overrides that method (its own
1000-item `IN`-list restriction, a different limit than a bind-parameter count) — the base
implementation, inherited by PostgreSQL and SQLite alike, returns `None` ("no limit"), so Django never
chunks an `__in` clause for either backend this project actually targets. `_import_relations` passed
`source_id__in=successful_ids, target_id__in=successful_ids` in one query (2N parameters together) and
`_import_concepts`/`_import_collections` each passed `static_uri__in=mentioned_uris` (N). PostgreSQL's
own extended-query-protocol Bind message uses a 16-bit parameter-count field, capping any one
statement at 65,535 bind parameters — a real, well-documented limit, not folklore — so the relations
query (2N) is claimed to fail around 33k concepts, inside the "tens of thousands of concepts" the spec
names as the target; the two single-clause queries (N) would fail around 65k, a real but less
immediate risk. Tests run against SQLite (`tests/settings.py`), which is not exempt from the same
class of limit in principle, but no fixture in this suite is remotely close to either backend's actual
ceiling, so CI cannot catch this regardless of which backend it uses.

**Chosen: eliminate the `__in` clause entirely at each of the three sites, rather than chunk it.**
Chunking one `__in` list into several smaller `IN (...)` clauses *within the same queryset* does not
actually help — Django compiles `.exclude(a).exclude(b)` (or an OR of several filtered querysets
merged) into one final SQL statement, whose total bind-parameter count is still the sum across every
chunk. Fixing the actual limit — bind parameters *per statement* — needs either genuinely separate
round trips (one full statement per chunk) or no `__in` clause on the file-sized list at all. The
latter is simpler and was available at every one of the three sites:

- **`_import_relations`'s existing-row lookup.** `ConceptRelation._reject_cross_scheme` already
  guarantees both ends of every row share one scheme, so `source__scheme=target_scheme` (one bind
  parameter, the scheme's own pk) already scopes both ends at once. The narrower "both ends in
  `successful_ids`" condition D30 requires — a row with one end outside this run's own writes is left
  untouched, never a deletion candidate — is then checked in Python against the in-memory
  `successful_ids` set, reproducing the original SQL-level condition exactly rather than widening what
  counts as a candidate.
- **`_import_concepts`'s and `_import_collections`'s absent-from-source lookups.** Replaced
  `.filter(scheme=target_scheme).exclude(static_uri__in=mentioned_uris)` with fetching
  `.filter(scheme=target_scheme)` alone (one bind parameter) and filtering `not in mentioned_uris` in
  Python. FIX 7/D41's own established distinction (report `.uri`, never the raw column, since a
  locally authored record's `static_uri` can be `None`) carries over unchanged — the Python
  comprehension checks the raw `static_uri` column against `mentioned_uris` (a set of real, non-`None`
  URIs, so a `None`-static_uri row is never accidentally excluded by that check) exactly as the SQL
  `exclude()` did, and still reports `.uri`.

**A deliberate, named tradeoff: more rows travel over the wire than the old, DB-side-filtered
queries.** Fetching every one of a scheme's relations (of one kind) or every one of its concepts/
collections, then discarding most of them in Python, transfers strictly more data than a `WHERE`
clause that excluded them server-side. This is accepted because it is *linear* in the scheme's own
size (plan.md's actual constraint — "rules out anything quadratic in concept count" — not "rules out
any query returning more rows than the minimal answer"), and because it turns a hard failure at scale
into a bounded cost that degrades gracefully, rather than trading a hard failure for a different one
(chunking that does not actually reduce per-statement parameter count) or a correctness change
(widening D30's own candidate scope).

**Verified by measuring the query's own shape, not by reproducing failure at 33k-concept scale.**
Reproducing an actual 65,535-parameter failure would need a dataset this test suite has no reason to
carry. Instead, `TestQueryParameterCountDoesNotScaleWithConceptCount` re-imports a 60-concept,
60-collection file (one root concept, 60 children each stating `skos:broader` to it — 60
`ConceptRelation` rows — and 60 one-member collections) a second time, under
`CaptureQueriesContext`, and asserts no captured query's SQL contains a flat `IN (...)` clause with 20
or more comma-separated items — a direct, query-shape-level assertion that would already fail at
N=60, exactly as it would at N=33,000, since the defect is about *what shape of query gets built*, not
about crossing a specific numeric threshold. Confirmed failing before the fix (a 61-item clause for
the relations query, a 60-item clause for each of the two absent-from-source queries — each verified
independently by reverting one of the three production changes at a time and re-running).

**Verified by mutation, independently for all three sites.** Reverted the relations query back to
`source_id__in=successful_ids, target_id__in=successful_ids` — the test failed, naming a 61-item
clause. Restored, then reverted the concepts absent-from-source query back to
`.exclude(static_uri__in=mentioned_uris)` — the same test failed again (the second `import_skos()`
call in the test also exercises this path). Restored, then reverted the collections absent-from-source
query the same way — failed a third time, naming a 60-item clause. Restored all three; full suite
re-ran green.

**Revisit if:** a future story adds a fourth site passing a file-sized collection to `__in` — the same
"read the installed Django's own chunking behaviour before assuming it, then eliminate the clause
rather than chunk it" approach applies, not a variant of this one that assumes Django will someday
chunk it automatically.

## D54 — `skos.py` becomes eight collaborating classes, and a helper reached across class boundaries is public or module-level (maintainer request, post-review)

**The maintainer asked for this after reading the PR.** The module was 25 functions at module level,
24 of them private, behind a single public entry point. Three parameters carried the state: `graph`
appeared in 17 of the 25 signatures, `report` in 10, `target_scheme` in 5. Parameters threaded through
two-thirds of a module are instance state that has not been given an object yet.

**The shape.** `SkosGraph` wraps `rdflib.Graph` and its SKOS query helpers, with `from_file()`
replacing `_read_graph`. `SchemeResolver` decides which vocabulary the file belongs to.
`ConceptImporter` maps one concept. `RelationImporter` and `CollectionImporter` are the two second
passes, sharing `_resolve_concept_reference` through a small mixin. `SkosImporter` orchestrates,
holding the graph, report, target vocabulary and transaction. `import_skos()` stays a module-level
function with an unchanged signature — a one-line wrapper over `SkosImporter`.

**Visibility follows reach, not layer.** A first pass kept `SkosGraph`'s query helpers private and had
four other classes call them anyway, which is a worse arrangement than the flat module it replaced: a
module-private function called from the same module is idiomatic Python, a class-private method
reached from another class is not. Every helper a collaborator calls is now public on its class
(`identify`, `first_literal`, `label_languages`, `preferred_label_in`, `scheme_refs`,
`conflicting_scheme_ref`, `implied_concept_nodes`, `skos_curie`). Two stateless helpers that three
different classes need — `report_unmodelled_predicates` and `configured_language_codes` — are
module-level functions rather than a static method one class reaches into another to call.

**No behaviour change, and the test suite is the evidence.** All 668 tests pass untouched except for
one import line and its call sites in `test_skos.py`, which named `_read_graph` directly. Coverage
holds at 97% project, 96% on `skos.py`. The file is 1559 → 1286 lines and its docstrings 538 → 335,
by cutting prose that restated the code or duplicated `spec.md` while keeping every FR, decision and
review-fix reference.

**Revisit if:** a consumer needs to override label mapping, slug assignment, scheme choice or language
determination — those are public on their classes for exactly that, and the first real subclass will
say whether the seams are in the right places.

## D55 — the exception hierarchy moves to `exceptions.py` (maintainer request, post-review)

**The maintainer asked why error types were declared in `skos.py` when `safety.py` already held
some.** The answer was that D52 had moved `SkosImportError` into `safety.py` for one reason only:
so `UnsafeRdfXmlError`/`UnsafeJsonLdError` could subclass it without a circular import, since
`skos.py` imports from `safety.py` and the reverse must never become true. That left the base of
the package's whole error hierarchy — which covers a missing file and an undeterminable
serialization, neither of them a safety concern — living inside the safety scanner. An import
cycle was deciding a module's contents, which is why the layout read oddly.

**The shape.** `exceptions.py` now holds all four public types: `SkosImportError` with its two
`Unsafe*` subclasses, and `SkosImportFailed`. `safety.py` and `skos.py` import what they raise.
`report.py` and `safety.py` import nothing from the package, so `exceptions.py` introduces no
cycle; its only package import is `ImportReport`, needed for an annotation and therefore guarded
by `TYPE_CHECKING`, so a future `report.py` that raises cannot create one either.

**Nothing moves for a caller.** `exchange.safety.SkosImportError`, `exchange.skos.SkosImportError`,
`exchange.skos.SkosImportFailed` and the `exchange` package re-exports all still resolve to the
same objects; `safety.py` carries an explicit `__all__` so the re-export is deliberate rather than
an unused import. Verified by asserting object identity across every pre-existing path, not by
assuming it. `SkosImportError` and `SkosImportFailed` remain siblings under `ValidationError`
rather than one subclassing the other — catching "unreadable file" must not also catch "readable
file, refused content".

`_FatalIdentity` stays in `skos.py`. It is not part of the public hierarchy: it is an internal
control-flow signal carrying a finding across one walk, and it is meaningless outside that walk.

The move took `skos.py` from D54's 1286 lines to 1267.

**Revisit if:** a second module in the package starts raising these, at which point the
`__all__`-based re-export from `safety.py` is worth dropping in favour of a single documented
import location.
