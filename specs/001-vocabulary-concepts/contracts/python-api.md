# Contract: Public Python / ORM API

The surface this feature exposes to downstream code. This is a library, so the "contract" is the
importable models and their behaviour. Semantic-versioned under Article VIII.

## Imports

```python
from controlled_vocabularies.models import ConceptScheme, Concept
```

## ConceptScheme

- `ConceptScheme.objects.create(name="Geothermics", description="")` → saved scheme with
  `slug == "geothermics"`.
- `scheme.uri` → `"{CONTROLLED_VOCABULARIES_BASE_URI}/geothermics"`.
- `scheme.name = "Geothermal Science"; scheme.save()` → `scheme.slug == "geothermal-science"`.
- `scheme.concepts.all()` → the scheme's concepts.
- `scheme.delete()` → removes the scheme and its concepts.
- Creating a second scheme whose name slugifies to an existing slug → refused (validation/integrity
  error), not auto-suffixed.

## Concept

- `Concept.objects.create(scheme=scheme, label="Heat flow")` → saved concept with
  `slug == "heat-flow"`, `scheme == scheme`.
- `concept.uri` → `"{scheme.uri}/heat-flow"`.
- `concept.label = "Terrestrial heat flow"; concept.save()` → `slug == "terrestrial-heat-flow"`,
  and `concept.uri` reflects it.
- `Concept.objects.get_by_uri(concept.uri)` → returns exactly that concept.
- Two concepts in one scheme whose labels slugify equally → refused.
- Concepts in *different* schemes may share a slug (the scheme slug disambiguates the URI).

## Guarantees (asserted by tests)

- A concept's URI does not depend on label wording beyond the slug it derives — renaming a label
  changes the slug (this slice, unpublished), but the composition rule is fixed.
- No two concepts in the system compose the same URI.
- Identity is the URI; the database primary key is never the identity.

## Configuration

- `settings.CONTROLLED_VOCABULARIES_BASE_URI` (str) — full base, e.g. `https://example.org/vocabularies`.
  Optional; defaults to a documented value. Trailing slash ignored.

## Not in this contract (sibling features)

Multilingual labels, relations, collections, lifecycle/deprecation, RDF import/export, served URLs,
admin/UI. Adding those is additive under semver.
