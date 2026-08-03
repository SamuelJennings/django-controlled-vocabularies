# Data model — 005-concepts-keep-identifier

No new models. Three existing models each gain one column and two accessors, and their managers gain a
shared lookup. Names follow the glossary split this feature lands: **permanent URI** and **local URL**.

## The column: `permanent_uri`

Added identically to `ConceptScheme`, `Concept`, and `Collection`.

| Attribute | Value | Why |
|---|---|---|
| type | `CharField(max_length=500)` | 500 is the bound settled at S1 (`decisions.md` D5) — beyond any real vocabulary's identifiers, inside MySQL's 3072-byte unique-index limit on `utf8mb4`. |
| `null` | `True` | A nullable *unique* text column must use `NULL`, not `""`. Empty strings all collide under a unique constraint, so the usual "no `null=True` on char fields" convention is deliberately not followed here. |
| `blank` | `True` | Nothing requires a curator to supply one; it arrives with imported content. |
| `verbose_name` | `_("permanent URI")` | Article XII. |
| `help_text` | translatable, states that it holds the identifier assigned by the vocabulary's publisher and is fixed once set | Article XII. |
| validators | `validate_permanent_uri` | FR-004. |
| constraint | `UniqueConstraint(fields=["permanent_uri"], condition=Q(permanent_uri__isnull=False), name="<model>_permanent_uri_unique")` | FR-006. Partial so the index holds only real identifiers rather than a row per unpublished record. |

**Empty means provisional.** A row with no value composes its identifier on read. A row with a value is
fixed and never recomputed. That presence *is* the explicit record of fixedness FR-003 asks for
(research R2) — no companion boolean, which could only ever disagree with the column.

## Accessors (all three models)

| Name | Kind | Returns |
|---|---|---|
| `uri` | property (existing name, existing meaning) | `self.permanent_uri` when set, otherwise `self.local_url`. This is the permanent URI: the publisher's when there is one, the provisional composition otherwise. |
| `local_url` | property (new) | The R1 composition, always: `{base}/{slug}` for a scheme, `{scheme.local_url}/{slug}` for a concept, `{scheme.local_url}/collection/{slug}` for a collection. Always this site's own address. |
| `has_permanent_uri` | property (new) | `bool(self.permanent_uri)` — whether the identifier is fixed. |

`local_url` composes from `local_url` up the chain rather than from `uri`, so a concept in an imported
vocabulary still gets a local address on this site even though its scheme's identifier points elsewhere.
That is the whole point of US-4 and the one place where composing from the wrong accessor would silently
produce an address on the publisher's domain.

## Validation

`validate_permanent_uri(value)` — a module-level function, used both as a field validator and called
from `save()`:

1. Parses with `urllib.parse.urlsplit`.
2. Requires a non-empty scheme and a non-empty remainder (absolute, not a bare path).
3. Refuses `javascript`, `data`, `vbscript` (case-insensitive).
4. Refuses anything over 500 characters.

Every refusal raises `ValidationError` with a translatable message and named placeholders (FR-010).

**It runs in `save()` as well as on the field.** Django's `save()` never calls `full_clean()`, so a
field-only validator would leave the import path — the path this feature exists to serve — accepting
values the specification says can never be stored. R1 defended `Concept.slug` from the same trap.

`clean()` and `save()` additionally refuse a `permanent_uri` already held by a record of a *different*
model. Within one model the database constraint is the guarantee; across the three tables no portable
constraint exists (research R4), so this check covers it. Two indexed `.exists()` queries, and only when
the column is set, so nothing is paid for locally authored records.

## Manager lookup

A `PermanentUriLookupMixin` on the three managers provides `get_by_uri(uri)`:

1. Exact match on `permanent_uri` → return it.
2. No match → fall back to the model's existing base-relative parse (R1's behaviour, unchanged).
3. Neither → raise the model's `DoesNotExist`, with the message R1 already uses.

Stored is tried first so an external identifier that happens to sit under this site's configured address
still resolves to the record that holds it (FR-003, and the first edge case in the spec). `Concept`
already has `get_by_uri`; it keeps its name and gains step 1. `ConceptScheme` and `Collection` gain the
method, because #50 upserts vocabularies and collections by identifier as well as concepts.

## Indexing decision (Article XIII, recorded)

- `permanent_uri` **is indexed**, by its partial unique constraint. It is the column every external
  identity lookup runs against, and the constraint's index serves both jobs.
- No index is added for `local_url` or `uri` — neither is a column. They compose from `slug` fields that
  R1 already indexed and constrained.
- No index is added for `has_permanent_uri`; it is a property, and the partial constraint already
  distinguishes rows that have an identifier from rows that do not.

## Migration

One migration (`0005_*`): three `AddField` operations and three `AddConstraint` operations. **No data
migration and no backfill.** A pre-existing row gets `NULL`, so it composes exactly the identifier it
composed before the upgrade, which is what FR-009 and Article IX require. Squashed at convergence per the
standing rule, though it is expected to be a single file already.
