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
