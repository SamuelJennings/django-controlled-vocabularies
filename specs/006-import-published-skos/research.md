# Research — 006 Import a published SKOS vocabulary from a file

Questions the plan needed answered before it could commit to an approach. Everything below was
established by running it against `rdflib` 7.6.0 in this project's environment, not from memory.

## R1 — Does rdflib read all three serializations out of the box?

Yes, with no extra plugin. `rdflib` 7.6.0 resolves `turtle`, `xml`, and `json-ld` natively —
JSON-LD stopped being a separate `rdflib-jsonld` package at rdflib 6.

`rdflib.util.guess_format` maps the extensions a curator will actually have:

| Filename | `guess_format` |
|---|---|
| `.ttl` | `turtle` |
| `.rdf` | `xml` |
| `.xml` | `xml` |
| `.jsonld` | `json-ld` |
| `.json` | `json-ld` |

So FR-002's "determined from the file" is satisfied by extension for the ordinary case. A file
with an unhelpful extension needs the caller to state the serialization, which FR-002 already
allows. Sniffing content is not attempted: guessing between Turtle and JSON-LD by inspecting bytes
is a heuristic that fails silently, and a wrong guess produces a parse error whose message points
at the wrong problem.

## R2 — How is an ordered collection's member list carried?

`skos:memberList` points at an RDF list, which is a chain of blank nodes by construction. `rdflib`
exposes it directly: `Graph.items(head)` yields the members in order.

Verified:

```
<http://x.org/c> a skos:OrderedCollection ;
    skos:memberList ( <http://x.org/1> <http://x.org/2> ) .
```

→ the `skos:memberList` object is a `BNode`, and `g.items(o)` returns
`[URIRef('http://x.org/1'), URIRef('http://x.org/2')]`.

This is the structural blank-node case D3 carves out of the fatal rule: the list nodes are not
identities and are read normally. Only a `skos:Concept` or `skos:Collection` that is *itself* a
blank node fails the run.

## R3 — Is parsing untrusted RDF/XML safe? **No, not entirely.**

Article V names imported RDF as untrusted input, so this was probed rather than assumed. Two
separate attacks, two different answers.

**External entities: not exploitable.** A document declaring
`<!ENTITY xxe SYSTEM "file:///path/to/secret">` and referencing it parses without error, and the
entity resolves to the empty string. A canary file written to disk and referenced this way did not
appear in the parsed graph. rdflib's RDF/XML parser does not retrieve external entities.

**Internal entity expansion: exploitable.** The classic billion-laughs shape is expanded in full.
A document of a few hundred bytes, declaring eight nested entities each repeating the previous one
five times, produced a single literal of **781,250 characters**. The amplification is unbounded in
the document's own size — a few more levels is gigabytes of memory, and nothing in rdflib or
Python's `xml.sax` caps it.

This is a denial-of-service route into any deployment that lets a curator upload a vocabulary
file, which is exactly what this feature enables. It has to be closed here rather than left to a
consumer.

**Options considered:**

1. **Refuse any document carrying a DTD.** One line, no dependency. Rejected: entity declarations
   for namespace shortening (`<!ENTITY skos "http://www.w3.org/2004/02/skos/core#">`) are a common
   idiom in hand-authored RDF/XML, so this would refuse legitimate published files.
2. **Cap the input file size.** Does not help — the amplification happens during parsing, from an
   input that is already small.
3. **Parse RDF/XML through `defusedxml`, with entity declarations forbidden.** Closes the bomb
   completely and leaves external entities closed too. Costs one small, single-purpose runtime
   dependency, and refuses the namespace-entity files from option 1 — but refuses them with a
   clear, translatable message rather than by exhausting memory.

**Chosen: option 3.** Article V treats imported RDF as untrusted, and a memory-exhaustion route
that a curator can trigger with a 400-byte file is not something to leave open for the convenience
of an authoring idiom that a re-serialization fixes. The refusal message names the cause, so a
curator meeting it knows what to do. Recorded as decisions.md D9 and surfaced in the plan
notification, since it adds a dependency and narrows what files import.

**Mechanism, since rdflib gives no injection point.** `rdflib.plugins.parsers.rdfxml.create_parser`
calls `xml.sax.make_parser()` itself and accepts no parser argument, so a defused parser cannot be
handed in, and monkeypatching a third-party internal is not something to ship. The fix is a
**pre-flight scan**: run the bytes through `defusedxml.sax` with a do-nothing content handler
first, and only hand them to rdflib if that returns cleanly. Verified — the bomb above raises
`EntitiesForbidden` at the scan and an ordinary RDF/XML document passes it untouched. The cost is
one extra XML pass, on RDF/XML input only.

## R4 — Which SKOS predicates map onto which models?

Fixed by what R1 built; no new modelling. The mapping the importer implements:

| SKOS | Lands as |
|---|---|
| `skos:ConceptScheme` | `ConceptScheme` |
| `skos:Concept` | `Concept` |
| `skos:prefLabel` (vocabulary default language) | `Concept.label` |
| `skos:prefLabel` (other languages) | `ConceptLabel`, kind `preferred` |
| `skos:altLabel` / `skos:hiddenLabel` | `ConceptLabel`, kinds `alternative` / `hidden` |
| `skos:definition` | `ConceptNote`, kind `definition` |
| `skos:scopeNote` / `skos:example` / `skos:editorialNote` / `skos:historyNote` / `skos:changeNote` / `skos:note` | `ConceptNote`, matching kind |
| `skos:broader` | `ConceptRelation` kind `broader`, source = narrower side |
| `skos:narrower` | the same row, with the ends swapped |
| `skos:related` | `ConceptRelation` kind `related`, stored once |
| `skos:Collection` / `skos:OrderedCollection` | `Collection`, `ordered` false / true |
| `skos:member` / `skos:memberList` | `CollectionMember`, with `position` from the list |
| `skos:inScheme` / `skos:topConceptOf` / `skos:hasTopConcept` | scheme membership |
| `skos:notation`, `skos:exactMatch` and the other mapping properties, anything else | set aside, reported |

`Concept.label` carrying the default-language preferred label is not a shortcut: `ConceptLabel`
actively **refuses** a `preferred` row in the scheme's effective default language, because that
would plant a second identity anchor. So the split is mandatory, not stylistic.

## R5 — Which write path must the importer use?

`Concept.add_label` and `Concept.add_note` run `full_clean()` before saving; `.objects.create()`
does not. The language check (`settings.LANGUAGES`), the one-preferred-per-language rule, and the
default-language-preferred refusal all live in `clean()`. The importer therefore goes through the
model helpers rather than bulk-creating rows, and treats a `ValidationError` from them as a
set-aside entry rather than a crash.

This costs per-row saves on a large vocabulary. It is the right default: correctness first, and
the invariants are the reason the models have helpers at all. If a real heat-flow vocabulary shows
this to be too slow, the fix is a deliberate, tested batching change with the same validation
applied, not a silent switch to `bulk_create` that skips it.

## R6 — Matching an existing record on re-import

`ConceptScheme.objects`, `Concept.objects`, and `Collection.objects` all carry `get_by_uri` from
the shared `StaticUriLookupMixin`, which #49 added specifically so this feature could upsert a
vocabulary, concept, or collection by identifier through one path. It tries the stored
`static_uri` first and falls back to parsing a base-relative local identifier, and it raises
`DoesNotExist` for a falsy or non-string argument rather than matching an arbitrary provisional
record.

So matching needs no new lookup. A record found this way is updated; a `DoesNotExist` means create.

## R7 — Atomicity

`django.db.transaction.atomic` around the whole run satisfies FR-003 directly. The one thing to
watch: collecting every problem rather than raising at the first (FR-003, second half) means the
run keeps going after a fatal finding, so the rollback is triggered deliberately at the end when
any fatal entry exists, rather than by letting the first exception escape. Set-aside entries never
trigger it.
