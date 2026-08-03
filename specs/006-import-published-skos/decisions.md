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

## D10 — `mypy_path` is dropped; it collided with the new `io` package (T002, Implementer US0)

Creating `controlled_vocabularies/io/` made `poetry run mypy` fail immediately: "Source file found
twice under different module names: `controlled_vocabularies.io` and `io`". The repo's
`[tool.mypy]` carried `mypy_path = "controlled_vocabularies/"` from onboarding, which adds that
directory itself as a search root — so every module inside it is reachable both as
`controlled_vocabularies.<name>` (via `files = ["controlled_vocabularies"]`) and as a bare
top-level `<name>` (via `mypy_path`). `conf.py`, `models.py`, and `apps.py` never collided because
nothing else on the path is named that; `io` does, because it is a stdlib module name.

`--explicit-package-bases` was tried first and made it worse — it surfaced the identical collision
for `conf.py` too, showing the setting was already fragile and `io` only exposed it. `mypy_path` add
no behaviour `files` does not already provide (confirmed: `poetry run mypy` still reports "Success:
no issues found" across all five source files, baseline four plus `io/__init__.py`, with the line
removed), so it is dropped rather than worked around.

**Why:** the plan named this package `io/` (plan.md Project Structure) and that name is right for a
reader with no other job — inventing a different name to dodge a stdlib collision would be the tail
wagging the dog, and the actual fix costs one redundant config line.

**Revisit if:** a future module inside `controlled_vocabularies/` needs `MYPYPATH`-style resolution
that `files` alone does not give it — none of the existing modules do, and `io/` does not either.

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
