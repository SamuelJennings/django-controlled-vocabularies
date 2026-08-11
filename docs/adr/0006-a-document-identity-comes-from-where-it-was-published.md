# ADR 0006 — A document's identifiers resolve against where it was published, not where it was read

**Status:** accepted

## Decision

When a SKOS document is obtained from a remote address and parsed from a local copy, the address it
was published at is passed into the parse as its base URI. Relative identifiers in the document
therefore resolve to the publisher's URIs, not to the copy's location.

`SkosGraph.from_file` takes an optional base URI, threaded through `SkosImporter` and `import_skos`.
Omitted — which is every local-file caller — the parse takes its base from the file's own location,
unchanged.

The same value decides what a refusal calls the source. A failure on a fetched document names the
address the operator typed, never the temporary file it happened to land in.

## Why

Published SKOS routinely states identifiers relative to the document carrying them: an empty
reference for the scheme, a bare segment for each concept. Resolution happens at parse time against
whatever the parser considers the document's location.

Measured on this project's own rdflib, the same bytes produce:

| Read from | Concept identity |
|---|---|
| a temporary file | `file:///tmp/tmpa1b2c3/concept-a` |
| the publisher's address as base | `https://example.org/concept-a` |

The first is unusable here, and not marginally. A concept's identity is its URI (ADR 0001 and the
constitution's URI-identity article), matching on re-import is by that URI, and a temporary
directory name is different on every run. A vocabulary imported twice from the same address would
produce two disjoint sets of concepts rather than one updated set, which is the exact failure that
upserting by URI exists to prevent. It is also meaningless to every other system, so nothing
downstream could reference it.

Downloading and importing the copy is the obvious implementation, and it is wrong for documents
that are, in practice, common. The defect is invisible in testing against absolute-URI fixtures,
which is most of them.

The narrower alternative — parse from the fetched bytes with `data=` — was already rejected in this
codebase for the same underlying reason: a `data=` parse silently changes the base URI. Passing the
address explicitly makes the base a stated input rather than an accident of how the bytes reached
the parser, which is why the parameter is named for what it is.

A consequence worth stating, because it corrects an intuition: a document fetched from a URL and
the identical bytes saved to disk and imported do **not** always produce the same records. Where
identifiers are absolute they do. Where they are relative, the fetched form is the correct one and
the saved copy is the degraded one.

## Revisit if

The package gains a way to import from a stream or a string with no meaningful address at all. Such
a caller has no publisher location to supply, and what a relative identifier should resolve to then
is a question this decision does not answer.
