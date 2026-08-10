# django-controlled-vocabularies

A Django app for **managing, publishing, and consuming SKOS controlled vocabularies** — built for
research organisations. Curators create and edit vocabularies through a web interface; developers
attach concepts to their own models and serve standards-compliant RDF at stable URIs. No hand-edited
RDF, no code releases to add a term, no triplestore to operate.

> **Status:** early development (pre-`0.1`). The data model and design are sketched out (see
> [`docs/brainstorm.md`](docs/brainstorm.md)); the first release targets **consumption** (import,
> models, a concept relationship field, and RDF export) ahead of the editing interface. See
> [`GOALS.md`](GOALS.md).

## Scope & philosophy

Research data infrastructure runs on controlled vocabularies, but Django has no native way to manage
or consume them, and the existing editors are foreign stacks, unmaintained, or deployment-heavy.
This app closes that gap by treating a vocabulary as **relational data, not a document**: concepts
are Django models, the database is the source of truth, and RDF is a projection produced only at the
import/export boundary. That turns everything Django already does well (forms, permissions, indexed
search, referential integrity) onto vocabulary management, and lets vocabularies scale to tens of
thousands of concepts and evolve as data rather than code.

**It deliberately is:**

- SKOS-focused.
- A Django app — installable into any Django project (notably FairDM) and runnable standalone.
- Both a **manager** (author, edit, version, publish) and a **consumer** (attach concepts to your
  models via a field; serve RDF at stable URIs).
- Multilingual — a concept holds labels and definitions in any number of languages, with one
  preferred label per language. Each vocabulary picks the language that anchors its concept URIs,
  and a curator can override any concept's slug.
- A graph, not a flat list — concepts link to one another through a broader/narrower hierarchy
  (navigable both ways, and a concept may sit under several broader concepts) and a symmetric
  related association, all within one vocabulary.
- Organisable into collections — a curator can gather a vocabulary's concepts into named
  collections, optionally in a deliberate order, separate from the hierarchy and from any other
  collection a concept belongs to.

**It deliberately is not:**

- A general RDF/OWL toolkit — the SKOS-only scope is intentional.
- A triplestore or SPARQL endpoint — the relational database is the store.
- A replacement for rdflib — rdflib is used only to parse and serialize at the boundary.
- A reasoner — no OWL inference.
- An editor for external vocabularies — imported external vocabularies are read-only references.
- A way to extend a published vocabulary with your own terms — that is out of scope.
- A faithful mirror of imported external vocabularies — imports are normalised to what the app
  supports (e.g. its configured languages); unsupported languages and constructs are not stored.

**Tie-breaks, when principles collide:** the database is the source of truth over RDF fidelity in
memory · lossless round-tripping over schema neatness · stable concept URIs over convenient
identifiers · vocabulary-as-data over vocabulary-as-code · SKOS fidelity over generality.

## Configuration

Every vocabulary, concept, and collection has a URI — its identity, always present. It is static,
held exactly as given and never recomputed by the app, once it is fixed: a record imported from an
external vocabulary keeps the identifier its publisher assigned it. A record authored here instead
has a dynamic URI, composed from a base address, until it is published, at which point that becomes
static too. Set the base address in your Django settings:

```python
CONTROLLED_VOCABULARIES_BASE_URI = "https://vocab.example.org/vocabularies"
```

If you leave it unset, the app falls back to `http://localhost:8000/vocabularies` so it still
runs out of the box — set a real address before you rely on it anywhere it is seen. This site's own
address for viewing a record is always composed from this base and the record's slugs — a concept's
is `{base}/{scheme-slug}/{concept-slug}` — even when that record's static URI points elsewhere, and
the slugs follow the labels while a vocabulary is unpublished.

A record's place in its vocabulary is what keeps its URI distinct, and the database enforces that:
a vocabulary's slug is unique across the site, and a concept's or collection's slug is unique
within its vocabulary. A composed URI therefore cannot collide, because the parts it is built from
cannot. A stored `static_uri` carries its own unique index per model on top of that.

Nothing stops you changing a `static_uri` once it is set. That is deliberate. A published
identifier is not supposed to move, but keeping it still is a matter of not editing it, rather than
of the model refusing every write path. Make the field non-editable wherever you expose it once a
record is published, and treat a value that differs between two imports of the same vocabulary as a
problem with the source file.

An externally assigned static URI must use one of a small set of accepted schemes — `http`,
`https`, `urn`, `doi`, `info`, `ark`, `tag`, `hdl`, and `oai` by default, since those are what real
SKOS vocabularies actually use. If your vocabularies carry identifiers in another scheme, add it
explicitly:

```python
CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES = [
    "http", "https", "urn", "doi", "info", "ark", "tag", "hdl", "oai", "my-custom-scheme",
]
```

A stored identifier is later rendered as a link, so schemes that can carry executable content
(`javascript`, `data`, `vbscript`) are refused even if you add them to this setting.

## Importing a published vocabulary

`import_skos()` reads a SKOS file — Turtle, RDF/XML, or JSON-LD — and creates or updates the
vocabulary it declares, along with every concept it contains: identity, labels, documentary notes,
broader/narrower and related relationships, and collection membership. Every record is matched by
its static URI, never by name, so importing the same file twice updates the same rows rather than
duplicating them.

```python
from controlled_vocabularies.exchange import import_skos

report = import_skos("rocks.ttl")
```

The caller may name a target `ConceptScheme` for a file that declares no vocabulary of its own, or
have it checked against one the file does declare:

```python
report = import_skos("rocks.ttl", scheme=my_scheme)
```

Re-running an import upserts rather than deleting and recreating. For a record the file still
contains, the file is authoritative for that record's own content — labels, notes, relationships,
and collection membership end up matching the file exactly, including the removal of a value the
file no longer carries. A record the file does not mention at all is left completely untouched and
named in the report instead, never deleted.

Labels and notes are matched by language, not only by predicate. A file's `en` value fills a site
configured for `en-gb`, and a file's `en-gb` value fills a site configured for `en`. Matching runs
on the base language, the first subtag of the tag, case-insensitively and in both directions, and
an exact tag match always wins over a variant.

Where a file offers several variants of one configured language, what happens next depends on how
many values that kind of label or note can hold:

- A preferred label holds one per language, so the variant the vocabulary predominantly publishes
  in is the one kept, with ties broken by language code. Each variant that lost is named in the
  report under its own published language.
- Alternative labels, hidden labels, and notes have no such limit, so every variant the file offers
  is stored.

A value stored under a variant match is named in the report as a substitution rather than applied
silently. That matters most where two variants differ by script. A site configured for `zh-Hans`
importing a vocabulary published only as `zh-Hant` receives that content, in a script its readers
may not be able to read. The report is what makes that visible, so a curator can decide what to do
about it.

The package stores content for every language code in `settings.LANGUAGES`. A project that declares
none inherits Django's own default list of 99 languages, so a vocabulary published in sixty
languages imports into all sixty. Narrowing `LANGUAGES` is how a site limits what an import stores.

A vocabulary's slug and a concept's slug are both derived from their own published identifier —
its fragment where it has one, otherwise the last segment of its path — assigned once, on first
import, and never recomputed by a later one. Renaming a record, or a vocabulary's name arriving in
a different language on a later import, never moves that record's local address; only the
publisher reassigning the identifier itself does. A record authored on this site rather than
imported has no published identifier to derive from, and keeps deriving its slug from its label,
as it always has.

That permanence has a cost worth naming: a vocabulary published under opaque codes gets an opaque
local address — `/v-113/00123` rather than `/soil-types/clay`. It is accepted because the address
is correct and stays correct, which is what every consumer of a URL needs from it, and because a
readable address that can move under data already pointing at it is worse than a stable one that
cannot.

The call returns an `ImportReport`, a plain dataclass rather than rendered text, so a caller can
inspect what happened without parsing anything:

- `created` / `updated` — the URIs of every vocabulary, concept, and collection the run wrote.
- `set_aside` — a `SetAsideEntry` per value the run could not store, each carrying a closed,
  translatable reason (an unconfigured language, a notation, a mapping to another vocabulary, a
  predicate the models have no place for, a missing relationship or collection member, and so on)
  and the data needed to render a message about it. Nothing a file contains is ever dropped in
  silence — a value the app cannot store is always named here.

  Published files are often not well-behaved, and the reasons cover that too. Where a pair of
  concepts is stated as both broader and related, the hierarchical statement wins, because SKOS
  declares the two disjoint, and the related one is set aside. A second preferred label in one
  language is set aside rather than refused at the database. An identifier whose own segment
  yields no usable slug is set aside naming the slug as the problem, not the identifier. None of
  these stops the rest of the vocabulary from importing.
- `absent_from_source` — the URIs of records that exist here but that the file no longer mentions.
- `normalized` — a `NormalizedEntry` per value the run stored, but under a different predicate than
  the one the file asserted (a foreign `dcterms:description` read as a concept's definition, for
  example).
- `fatal` — populated only on a failed run: a `FatalFinding` per reason the whole import was
  refused (a missing or blank-node identity, or a vocabulary that could not be resolved). A failed
  run raises `SkosImportFailed`, carrying this same report, and leaves the database exactly as it
  was before the run started.

A run either succeeds in full or changes nothing: every problem in a file is collected before any
of it is written, and a fatal one rolls the whole run back. The `import_skos` management command
wraps this for use from a terminal (see below). There is no web-facing entry point yet.

Reading a file never reassigns identity. A concept or collection whose URI is already held by a
different vocabulary stays where it is. So does one whose URI is held by a record of another kind,
such as a collection in one file and a concept in another. Both are set aside and reported. Moving
a record between vocabularies is a curatorial decision, not a side effect of reading a file.

An imported file is treated as untrusted input. RDF/XML is scanned for entity expansion and
external references before a parser sees it. A JSON-LD document is refused rather than fetched if
its `@context` names a remote location, whether that is a plain string reference or an `@import`
reference tucked inside an inline object context. `import_skos()` itself never makes a network
request when reading a file — the command's own URL fetch (see below) happens first, and only the
fetched or local bytes ever reach this scan. An ordinary inline JSON-LD context, carrying no such
reference, imports normally.

`import_skos()` raises one of two exceptions, both `ValidationError` subclasses carrying a
translatable message. `SkosImportError` covers every reason a file cannot be turned into usable SKOS
at all: not found, not in a supported serialization, unparseable, or refused by the safety scan
above. `SkosImportFailed` covers the case where the file parses but the run collects one or more
fatal problems (a missing or blank-node identity, or a vocabulary that cannot be resolved), and
carries the same `ImportReport` its `fatal` bucket names them in. `UnsafeRdfXmlError` and
`UnsafeJsonLdError`, the two exceptions the safety scan itself raises, are exported
`SkosImportError` subclasses, so code that only catches `(SkosImportError, SkosImportFailed)`
already catches a file the safety scan refuses too.

## Importing from the command line

The `import_skos` management command wraps `import_skos()` for use from a terminal or a
deployment script:

```bash
python manage.py import_skos rocks.ttl
```

The source can be a local filesystem path or an `http://`/`https://` URL, told apart by the value
itself rather than by a flag. A URL is fetched under a fixed 30-second timeout and a fixed 50 MiB
response ceiling, over a connection that only ever speaks http and https, and the fetched
document's identifiers resolve against the address it came from — so a re-import updates the same
concepts the first import created, rather than a second copy keyed by a temporary file path.

- `--format` names the source's serialization (`turtle`, `xml`, or `json-ld`), for a source whose
  extension or `Content-Type` does not.
- `--rehearse` performs the entire import and reports the outcome exactly as a live run would,
  then leaves the database exactly as it was beforehand — useful for seeing what a file would set
  aside before deciding whether to configure a language for it.
- `--verbosity`, Django's own option, prints bucket counts by default — how many records were
  created, updated, set aside, normalized, or absent from the source, plus the set-aside account
  grouped by reason and by language. At `2` or above, every individual set-aside entry prints too.

A refusal exits non-zero and prints every reason the run was refused. A run that sets values aside
still exits zero: importing a vocabulary published in more languages than a site is configured for
always sets some aside, so that outcome is treated as normal rather than as a failure a deployment
script should stop on.

## Relationship to other packages

Supersedes and retires `skos-builder` and `django-research-vocabs`, consolidating vocabulary
authoring, management, and Django consumption into one app.

## License

MIT — see [LICENSE](LICENSE).
