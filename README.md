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
  language is set aside rather than refused at the database. A label that yields no usable slug is
  set aside naming the slug as the problem, not the label. None of these stops the rest of the
  vocabulary from importing.
- `absent_from_source` — the URIs of records that exist here but that the file no longer mentions.
- `normalized` — a `NormalizedEntry` per value the run stored, but under a different predicate than
  the one the file asserted (a foreign `dcterms:description` read as a concept's definition, for
  example).
- `fatal` — populated only on a failed run: a `FatalFinding` per reason the whole import was
  refused (a missing or blank-node identity, or a vocabulary that could not be resolved). A failed
  run raises `SkosImportFailed`, carrying this same report, and leaves the database exactly as it
  was before the run started.

A run either succeeds in full or changes nothing: every problem in a file is collected before any
of it is written, and a fatal one rolls the whole run back. There is no command-line or web-facing
entry point yet — `import_skos()` is a programmatic call only.

Reading a file never reassigns identity. A concept or collection whose URI is already held by a
different vocabulary stays where it is. So does one whose URI is held by a record of another kind,
such as a collection in one file and a concept in another. Both are set aside and reported. Moving
a record between vocabularies is a curatorial decision, not a side effect of reading a file.

An imported file is treated as untrusted input. RDF/XML is scanned for entity expansion and
external references before a parser sees it, and a JSON-LD document whose `@context` names a remote
location is refused rather than fetched. Importing a file never makes a network request. A JSON-LD
document that carries its context inline imports normally.

## Relationship to other packages

Supersedes and retires `skos-builder` and `django-research-vocabs`, consolidating vocabulary
authoring, management, and Django consumption into one app.

## License

MIT — see [LICENSE](LICENSE).
