# Quickstart — 003-relationships-between-concepts

Runnable validation of the feature through the ORM. Assumes a scheme with a few concepts (see the
test factories). Every call below is exercised by the test suite.

```python
from controlled_vocabularies.models import ConceptScheme, Concept

rocks = ConceptScheme.objects.create(name="Rock types")
igneous = Concept.objects.create(scheme=rocks, label="Igneous rock")
granite = Concept.objects.create(scheme=rocks, label="Granite")
plutonic = Concept.objects.create(scheme=rocks, label="Plutonic rock")
quartz = Concept.objects.create(scheme=rocks, label="Quartz")

# --- hierarchy, navigable both ways (US-1) ---
granite.add_broader(igneous)
assert igneous in granite.broader()
assert granite in igneous.narrower()          # derived, never asserted

granite.add_broader(plutonic)                 # polyhierarchy
assert set(granite.broader()) == {igneous, plutonic}

# --- symmetric related (US-2) ---
granite.add_related(quartz)
assert quartz in granite.related()
assert granite in quartz.related()            # same association, either side

# --- integrity (US-3) ---
from django.core.exceptions import ValidationError

for bad in (lambda: granite.add_broader(granite),      # self-relation
            lambda: granite.add_broader(igneous),      # duplicate
            lambda: granite.add_related(igneous)):     # disjointness (already hierarchical)
    try:
        bad(); raise AssertionError("should have been refused")
    except ValidationError:
        pass

# cross-vocabulary is refused
minerals = ConceptScheme.objects.create(name="Minerals")
mica = Concept.objects.create(scheme=minerals, label="Mica")
try:
    granite.add_related(mica); raise AssertionError("cross-vocabulary should be refused")
except ValidationError:
    pass

# a cycle is *not* prevented this slice (recorded non-guarantee)
rock = Concept.objects.create(scheme=rocks, label="Rock")
igneous.add_broader(rock)
rock.add_broader(granite)                     # closes granite -> igneous -> rock -> granite; accepted

# --- removal (US-1/US-2) ---
granite.remove_broader(plutonic)
assert plutonic not in granite.broader()
```

Run the suite: `poetry run pytest`. Migrate from zero: `poetry run python -m django migrate`
(`makemigrations --check` clean).
