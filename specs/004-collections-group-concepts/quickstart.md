# Quickstart — 004-collections-group-concepts

Runnable validation scenarios. Each maps to acceptance scenarios in `spec.md` and is covered by a test.

```python
from controlled_vocabularies.models import ConceptScheme, Collection

vocab = ConceptScheme.objects.create(name="Rocks")
granite = vocab.concepts.create(label="Granite")
basalt  = vocab.concepts.create(label="Basalt")
quartz  = vocab.concepts.create(label="Quartz")
```

## 1 — Gather concepts into a named collection (US-1)

```python
igneous = Collection.objects.create(scheme=vocab, name="Common igneous rocks")
igneous.add(granite)
igneous.add(basalt)
assert set(igneous.members()) == {granite, basalt}      # quartz not a member

field_guide = Collection.objects.create(scheme=vocab, name="Field-guide rocks")
field_guide.add(granite)                                # same concept in two collections
igneous.remove(granite)
assert granite in field_guide.members()                 # removing from one leaves the other
assert granite not in igneous.members()

igneous.add(basalt)                                      # already a member -> held once
assert list(igneous.members()).count(basalt) == 1
assert list(Collection.objects.create(scheme=vocab, name="Empty").members()) == []
```

## 2 — A collection with a deliberate order (US-2)

```python
reading = Collection.objects.create(scheme=vocab, name="Reading order", ordered=True)
reading.add(basalt); reading.add(granite)               # appended in add order
gabbro = vocab.concepts.create(label="Gabbro"); reading.add(gabbro)
assert list(reading.members()) == [basalt, granite, gabbro]

reading.set_member_order([gabbro, basalt, granite])     # rearrange
assert list(reading.members()) == [gabbro, basalt, granite]

reading.remove(basalt)                                   # survivors keep relative order
assert list(reading.members()) == [gabbro, granite]

plain = Collection.objects.create(scheme=vocab, name="A set")   # unordered
# plain.set_member_order([...]) -> ValidationError (ordering is meaningless for a set)
```

## 3 — Membership stays inside the vocabulary and clear of the hierarchy (US-3)

```python
from django.core.exceptions import ValidationError

other = ConceptScheme.objects.create(name="Minerals")
mica = other.concepts.create(label="Mica")
try:
    igneous.add(mica)                                    # cross-vocabulary member -> refused
    assert False
except ValidationError:
    pass

igneous.add(granite); igneous.add(basalt)
assert basalt not in granite.related()                   # membership asserts no relation
assert basalt not in granite.broader() and basalt not in granite.narrower()
```
