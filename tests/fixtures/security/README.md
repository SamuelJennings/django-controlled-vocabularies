# Security fixtures

Hostile documents for the pre-flight safety scan in
`controlled_vocabularies/exchange/safety.py`, exercised by
`tests/test_exchange/test_safety.py`.

Every file here is either an attack the scan must refuse or a clean document it must
leave alone. The clean ones matter as much as the hostile ones: a scan that refuses
everything passes all the attack tests and is useless, so each format carries at least
one negative control. **Do not delete a file because it looks harmless — check the test
that reads it first.**

Nothing here reaches the network. The two remote-reference fixtures point at
`http://127.0.0.1:1`, a closed port on loopback, so a regression that let the fetch
through would fail locally rather than quietly making a real request.

## RDF/XML

Refused by `scan_rdf_xml`, which runs the bytes through `defusedxml.sax` before rdflib
sees them. rdflib's RDF/XML parser calls `xml.sax.make_parser()` itself and accepts no
parser argument, so a defused parser cannot simply be substituted (decisions.md D9).

| File | What it is | The vulnerability |
|---|---|---|
| `entity_bomb.rdf` | Eight nested entity declarations, each expanding the one below it five times | Exponential entity expansion, the "billion laughs" denial of service. A ~500-byte document expands to a single 781,250-character literal, unbounded in the document's own size (research.md R3). Refused as `EntitiesForbidden`. |
| `external_entity.rdf` | An entity declared `SYSTEM "file:///etc/hostname"`, referenced from `rdf:value` | Classic XXE local-file disclosure — the parser reads a server-side file into the graph. Also refused as `EntitiesForbidden`: declaring any entity is enough, so this route and the bomb above close together. |
| `external_dtd.rdf` | A `DOCTYPE` naming an external DTD subset over HTTP | Server-side request forgery. Parsing fetches an attacker-named URL, which leaks that the file was processed and can be pointed at internal hosts. Refused as `ExternalReferenceForbidden`. |
| `ordinary.rdf` | A valid one-concept SKOS document with no `DOCTYPE` at all | **Negative control.** Must pass untouched. |

## JSON-LD

Refused by `scan_json_ld`. rdflib resolves a context reference through `urlopen` with no
allowlist, against a remote host or a local `file://` path (decisions.md D36). This
feature reads a file, never a URL, so any reference that triggers a fetch is refused
before rdflib sees the document.

### Remote `@context`

| File | What it is | The vulnerability |
|---|---|---|
| `remote_context_string.jsonld` | `"@context"` as a bare string URL | The plainest form of the fetch. Refused with code `jsonld_remote_context_forbidden`. |
| `remote_context_array.jsonld` | The same URL as one entry in an `@context` array, alongside a legitimate inline term map | Proves the scan walks array contexts instead of only checking the top-level string form. |
| `remote_context_nested_array.jsonld` | The same URL one level deeper, inside an array *within* the `@context` array | `Context._prep_sources` recurses into a nested array to any depth and fetches every string it reaches; the scan's array branch used to check only string and object entries, so this shape passed it (SEC-701, decisions.md D19). |

### `@import` inside a context

`Context._read_source` in rdflib reads `@import` from *any* dict it treats as a context
and resolves a string value through the same `urlopen`-backed path a string `@context`
uses. An inline object context was previously waved through on the reasoning that it
"carries nothing to resolve", which was false — this is the measured defect behind
decisions.md D47. All five are refused with code `jsonld_context_import_forbidden`.

| File | Where the `@import` hides |
|---|---|
| `exfil_via_import.jsonld` | The document's own top-level `@context`. This is the measured exploit: read through rdflib directly it merges in `exfil_secret.jsonld` and the leaked prefix resolves the scheme's URI to `http://example.org/SECRET-FROM-LOCAL-FILE/scheme` — the contents of a file the caller never named, chosen by the uploaded document. |
| `context_import_array.jsonld` | An entry inside an `@context` array |
| `context_import_nested_array.jsonld` | An object inside an array inside the `@context` array — the same hole as `remote_context_nested_array.jsonld`, reached by the other of the two fetch-triggering keys (SEC-701) |
| `context_import_nested_term.jsonld` | A term definition's own scoped `@context` |
| `context_import_graph_node.jsonld` | A node's own `@context` inside `@graph` |

### Supporting files

| File | What it is |
|---|---|
| `exfil_secret.jsonld` | Not an attack on its own. It is the payload the four `@import` fixtures pull in, standing in for a server-side file the uploaded document must never be able to read. It defines a `leaked` term pointing at a marker URI, so the marker appearing in a parsed graph is the proof that an import was followed. |
| `inline_context.jsonld` | **Negative control.** A fully inline object context with a term definition and no `@import` — the overwhelmingly common shape of a published file. Must pass. |
