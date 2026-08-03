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
held exactly as given and never recomputed, once it is fixed: a record imported from an external
vocabulary keeps the identifier its publisher assigned it. A record authored here instead has a
dynamic URI, composed from a base address, until it is published, at which point that becomes
static too. Set the base address in your Django settings:

```python
CONTROLLED_VOCABULARIES_BASE_URI = "https://vocab.example.org/vocabularies"
```

If you leave it unset, the app falls back to `http://localhost:8000/vocabularies` so it still
runs out of the box — set a real address before you rely on it anywhere it is seen. This site's own
address for viewing a record is always composed from this base and the record's slugs — a concept's
is `{base}/{scheme-slug}/{concept-slug}` — even when that record's static URI points elsewhere, and
the slugs follow the labels while a vocabulary is unpublished.

That guarantee holds when a record is saved the normal way, through `save()` or validated with
`full_clean()`. Django's bulk write paths — `QuerySet.update()`, `bulk_create()`, `bulk_update()`,
and raw SQL — skip it, the same way they skip every other model-level rule. This matters most when
you import a vocabulary at scale: a bulk write is the natural choice there for speed, and it is also
the one path where a static URI can be rewritten or duplicated without a validation error to stop
it. Use `save()` for any record whose URI needs to stay fixed.

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

## Relationship to other packages

Supersedes and retires `skos-builder` and `django-research-vocabs`, consolidating vocabulary
authoring, management, and Django consumption into one app.

## License

MIT — see [LICENSE](LICENSE).
