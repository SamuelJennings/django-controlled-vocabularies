# Python API contract — 005-concepts-keep-identifier

The surface this feature adds or changes. Everything already published keeps its name and meaning
(FR-014); this is additive.

## Unchanged, restated so the contract is explicit

```python
scheme.uri            # -> str   still the record's identity
concept.uri           # -> str
collection.uri        # -> str
Concept.objects.get_by_uri(uri)   # -> Concept, raises Concept.DoesNotExist
```

What changes is what they *can* return and accept, never their names. `uri` now returns a publisher's
identifier when the record holds one. `get_by_uri` now resolves identifiers outside this site's
configured base address, which it previously refused before reaching the database.

## Added

```python
# Field, on ConceptScheme, Concept and Collection.
record.static_uri        # -> str | None  the permanent URI once static; None while dynamic

# Properties, on all three.
record.local_url         # -> str         where the record is viewed on this site
record.has_static_uri    # -> bool        whether the permanent URI has turned static

# Manager lookup, now on all three.
ConceptScheme.objects.get_by_uri(uri)   # -> ConceptScheme, raises ConceptScheme.DoesNotExist
Collection.objects.get_by_uri(uri)      # -> Collection,    raises Collection.DoesNotExist

# Validation, importable so #50 can check a value before building a record.
from controlled_vocabularies.models import validate_static_uri
validate_static_uri(value)   # -> None, raises ValidationError
```

## Behaviour contract

```python
# A record that arrived from elsewhere keeps its identifier, verbatim and forever.
c = Concept.objects.create(scheme=s, name="Granite",
                           static_uri="http://vocabs.example.org/rock/granite")
c.uri                      # "http://vocabs.example.org/rock/granite"
c.has_static_uri           # True
c.name = "Granite (coarse)"; c.save()
c.uri                      # unchanged
# and unchanged again after settings.CONTROLLED_VOCABULARIES_BASE_URI changes.

# A record authored here carries the value it will publish under.
d = Concept.objects.create(scheme=s, name="Basalt")
d.static_uri               # None  — still dynamic
d.has_static_uri           # False
d.uri == d.local_url       # True — the ordinary case for local unpublished work
d.uri                      # "{base}/{scheme-slug}/basalt", and it follows a rename

# An imported record still has a place on this site.
c.local_url                # "{base}/{scheme-slug}/granite" — this site, not the publisher's
c.local_url != c.uri       # True

# Lookup answers for both kinds.
Concept.objects.get_by_uri("http://vocabs.example.org/rock/granite")   # -> c
Concept.objects.get_by_uri(d.uri)                                     # -> d
Concept.objects.get_by_uri("http://vocabs.example.org/nothing")       # raises Concept.DoesNotExist

# Refusals, each a ValidationError with a translatable, named-placeholder message.
validate_static_uri("not-absolute")                    # raises
validate_static_uri("javascript:alert(1)")             # raises
validate_static_uri("http://example.org/" + "x" * 500) # raises
validate_static_uri("urn:uuid:9f6c...")                # accepted — real vocabularies use these
```

## Guarantees the tests assert

- An externally assigned identifier is never rewritten, normalised, re-cased, or recomputed, by any
  operation including a re-import that matched the record by it (FR-002, FR-013).
- A static permanent URI never becomes dynamic again: nothing turns a record holding one back
  (FR-013).
- No two records of the same model may hold the same `static_uri`, and the refusal comes from the
  database constraint (FR-006). Across models the refusal comes from validation (research R4).
- A collection's `local_url` can never equal a concept's, because the `collection` segment separates
  them — the R1 rule, preserved (FR-008).
- Records created before this feature report exactly the identifiers they reported before, because they
  hold no `static_uri` and compose as they always did (FR-009).
