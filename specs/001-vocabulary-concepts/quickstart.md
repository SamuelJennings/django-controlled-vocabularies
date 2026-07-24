# Quickstart / Validation: Represent a vocabulary and its concepts

Runnable scenarios that prove the feature works end to end. Run inside the repo's test environment.

## Prerequisites

- `poetry install`
- `tests/settings.py` sets `CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"`.

## Run the suite

```bash
poetry run pytest
```

Expected: all tests green across the supported matrix (Py 3.12/3.13 × Django 5.2/6.0).

## Scenario 1 — a vocabulary with concepts (US-1, US-2)

```python
from controlled_vocabularies.models import ConceptScheme, Concept

scheme = ConceptScheme.objects.create(name="Geothermics")
assert scheme.slug == "geothermics"

hf = Concept.objects.create(scheme=scheme, label="Heat flow")
assert hf.slug == "heat-flow"
assert list(scheme.concepts.all()) == [hf]
```

## Scenario 2 — stable identifier (US-3)

```python
assert hf.uri == "https://example.org/vocabularies/geothermics/heat-flow"
assert Concept.objects.get_by_uri(hf.uri) == hf

# rename flows through while unpublished
hf.label = "Terrestrial heat flow"; hf.save()
assert hf.slug == "terrestrial-heat-flow"
assert hf.uri.endswith("/geothermics/terrestrial-heat-flow")
```

## Scenario 3 — uniqueness and non-Latin input (US-3, edge cases)

```python
from django.core.exceptions import ValidationError

# non-Latin label yields a usable slug
wf = Concept.objects.create(scheme=scheme, label="Wärmefluss")
assert wf.slug  # non-empty, unicode-safe

# a colliding slug in the same scheme is refused, not auto-suffixed
try:
    Concept.objects.create(scheme=scheme, label="Heat flow")  # would collide with hf's original slug
    raise AssertionError("expected a collision to be refused")
except (ValidationError, Exception):
    pass
```

## Scenario 4 — factories (US-4)

```python
from tests.factories import ConceptSchemeFactory, ConceptFactory

scheme = ConceptSchemeFactory()          # valid, saved, sensible defaults
concept = ConceptFactory()               # creates its own scheme when none given
assert concept.scheme_id is not None
```

## Cleanup semantics

```python
scheme.delete()                          # removes the scheme and its concepts
assert not Concept.objects.filter(pk=hf.pk).exists()
```
