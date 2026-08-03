# Quickstart — 005-concepts-keep-identifier

## Bringing in a vocabulary someone else published

Give the record the identifier its publisher assigned. It is held exactly as supplied and never
recomputed.

```python
scheme = ConceptScheme.objects.create(
    name="Rock types",
    static_uri="http://vocabs.example.org/rock",
)
granite = Concept.objects.create(
    scheme=scheme,
    name="Granite",
    static_uri="http://vocabs.example.org/rock/granite",
)

granite.uri          # "http://vocabs.example.org/rock/granite"  — the publisher's
granite.local_url    # "https://mysite.org/vocabularies/rock-types/granite" — yours
```

Renaming it, or moving your site to a different address, changes `local_url` and leaves `uri` alone.

## Building a vocabulary of your own

Supply nothing. The record reports the identifier it will publish under, composed from your configured
address and its slugs.

```python
scheme = ConceptScheme.objects.create(name="Field methods")
sampling = Concept.objects.create(scheme=scheme, name="Sampling")

sampling.static_uri      # None — the identifier is still dynamic
sampling.uri                # "https://mysite.org/vocabularies/field-methods/sampling"
sampling.uri == sampling.local_url   # True
```

Rename it and both follow. The identifier is dynamic at this stage and turns static when the
vocabulary is published, which is a later feature (roadmap R4). From that moment it never moves again.

## Finding a record by its identifier

Works for identifiers of either kind, on all three models.

```python
Concept.objects.get_by_uri("http://vocabs.example.org/rock/granite")   # the imported one
Concept.objects.get_by_uri(sampling.uri)                              # your own
ConceptScheme.objects.get_by_uri("http://vocabs.example.org/rock")
```

An identifier no record holds raises the model's `DoesNotExist`, the same way for both kinds.

## Configure your site's address

Unchanged from before. It composes your local URLs and the provisional identifiers of anything you
author, and has no bearing on an identifier that arrived from somebody else.

```python
CONTROLLED_VOCABULARIES_BASE_URI = "https://mysite.org/vocabularies"
```

## What is refused

An identifier has to be absolute and carry a scheme, cannot use `javascript:`, `data:`, or `vbscript:`,
and cannot exceed 500 characters. `urn:` identifiers are fine — published vocabularies do use them.

```python
Concept.objects.create(scheme=scheme, name="Bad", static_uri="javascript:alert(1)")
# ValidationError
```

## Upgrading

Nothing to do. Records created before this change hold no static identifier, so they compose exactly
what they composed before and every reference to them still resolves.
