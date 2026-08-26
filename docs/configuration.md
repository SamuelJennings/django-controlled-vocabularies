# Configuration

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

---

Next: [attaching concepts to your models](fields.md).
