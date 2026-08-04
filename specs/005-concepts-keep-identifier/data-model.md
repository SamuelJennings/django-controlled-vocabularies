# Data model — 005-concepts-keep-identifier

No new models. Three existing models each gain one column and two accessors, and their managers gain a
shared lookup. Names follow the glossary split this feature lands: **static URI** and **local URL**.

## The column: `static_uri`

Added identically to `ConceptScheme`, `Concept`, and `Collection`.

| Attribute | Value | Why |
|---|---|---|
| type | `CharField(max_length=500)` | 500 is the bound settled at S1 (`decisions.md` D5) — beyond any real vocabulary's identifiers, inside MySQL's 3072-byte unique-index limit on `utf8mb4`. |
| `null` | `True` | A nullable *unique* text column must use `NULL`, not `""`. Empty strings all collide under a unique constraint, so the usual "no `null=True` on char fields" convention is deliberately not followed here. |
| `blank` | `True` | Nothing requires a curator to supply one; it arrives with imported content. |
| `verbose_name` | `_("static URI")` | Article XII. |
| `help_text` | translatable, states that it holds the record's permanent URI once that URI has turned static — assigned by an external publisher, or frozen at publication — and is never recomputed afterwards | Article XII. |
| validators | `validate_static_uri` | FR-004. |
| constraint | `UniqueConstraint(fields=["static_uri"], condition=Q(static_uri__isnull=False), name="<model>_static_uri_unique")` | FR-006. Partial so the index holds only real identifiers rather than a row per unpublished record. |

**Empty means the permanent URI is still dynamic.** A row with no value composes its identifier on
read; a row with a value has turned static and is never recomputed. Every row has a permanent URI
either way — the column records which of the two states it is in, which *is* the explicit record
FR-003 asks for (research R2). No companion boolean, which could only ever disagree with the column.

## Accessors (all three models)

| Name | Kind | Returns |
|---|---|---|
| `uri` | property (existing name, existing meaning) | `self.static_uri` when set, otherwise `self.local_url`. This is the permanent URI, static or dynamic: the publisher's when there is one, the composition otherwise. |
| `local_url` | property (new) | The R1 composition, always: `{base}/{slug}` for a scheme, `{scheme.local_url}/{slug}` for a concept, `{scheme.local_url}/collection/{slug}` for a collection. Always this site's own address. |
| `has_static_uri` | property (new) | `bool(self.static_uri)` — whether the permanent URI has turned static. |

`local_url` composes from `local_url` up the chain rather than from `uri`, so a concept in an imported
vocabulary still gets a local address on this site even though its scheme's identifier points elsewhere.
That is the whole point of US-4 and the one place where composing from the wrong accessor would silently
produce an address on the publisher's domain.

## Validation

`validate_static_uri(value)` — a module-level function, used both as a field validator and called
from `save()`:

1. Parses with `urllib.parse.urlsplit`.
2. Requires a non-empty scheme and a non-empty remainder (absolute, not a bare path).
3. Requires a scheme on the configured allowlist, and refuses `javascript`, `data`, `vbscript`
   outright even if a downstream override adds one of them.
4. Refuses anything over 500 characters.

Every refusal raises `ValidationError` with a translatable message and named placeholders (FR-010).

**It runs in `save()` as well as on the field.** Django's `save()` never calls `full_clean()`, so a
field-only validator would leave the import path — the path this feature exists to serve — accepting
values the specification says can never be stored. R1 defended `Concept.slug` from the same trap.

`clean()` and `save()` do nothing beyond this validation and normalising `""` to `None`
(decisions.md D18). Uniqueness is per model, a database `UniqueConstraint` and nothing else. There
is no cross-model probe, no read-back of the stored value, no row lock, and no refusal of a later
change to a stored identifier — the guard that did all of that was removed after four review rounds
each found a further way past it.

The reason it was never needed is that identity is already unique by construction. R1 gives
`ConceptScheme.slug` a site-wide unique constraint and gives `Concept` and `Collection` a unique
`(scheme, slug)` each, so a composed URI cannot collide: the parts it is built from cannot. A
collision between two *stored* identifiers across models needs a source file that declares the same
URI for a `skos:Concept` and a `skos:Collection`, which is malformed RDF, and #50's importer reports
it while reading the file.

Keeping a published identifier still is an interface concern: make the field non-editable wherever
it is exposed once the record is published. That belongs with whichever feature adds the admin, since
this package has no `admin.py` yet.

## Manager lookup

A `StaticUriLookupMixin` on the three managers provides `get_by_uri(uri)`:

1. Exact match on `static_uri` → return it.
2. No match → fall back to the model's existing base-relative parse (R1's behaviour, unchanged).
3. Neither → raise the model's `DoesNotExist`, with the message R1 already uses.

Stored is tried first so an external identifier that happens to sit under this site's configured address
still resolves to the record that holds it (FR-003, and the first edge case in the spec). `Concept`
already has `get_by_uri`; it keeps its name and gains step 1. `ConceptScheme` and `Collection` gain the
method, because #50 upserts vocabularies and collections by identifier as well as concepts.

## Indexing decision (Article XIII, recorded)

- `static_uri` **is indexed**, by its partial unique constraint. It is the column every external
  identity lookup runs against, and the constraint's index serves both jobs.
- No index is added for `local_url` or `uri` — neither is a column. They compose from `slug` fields that
  R1 already indexed and constrained.
- No index is added for `has_static_uri`; it is a property, and the partial constraint already
  distinguishes rows that have an identifier from rows that do not.

## Migration

One migration (`0005_*`): three `AddField` operations and three `AddConstraint` operations. **No data
migration and no backfill.** A pre-existing row gets `NULL`, so it composes exactly the identifier it
composed before the upgrade, which is what FR-009 and Article IX require. Squashed at convergence per the
standing rule, though it is expected to be a single file already.
