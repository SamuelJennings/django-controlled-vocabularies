# Public ORM contract — 004-collections-group-concepts

The programmatic surface a downstream developer touches. Acceptance tests drive exactly this
(Integration-First). All refusals raise `django.core.exceptions.ValidationError` with a translatable,
named-placeholder message.

## `Collection`

```python
c = Collection.objects.create(scheme=vocab, name="Common igneous rocks")   # unordered by default
c = Collection.objects.create(scheme=vocab, name="Reading order", ordered=True)
c.uri        # "{scheme.uri}/collection/{slug}"  — property, composed on read
c.slug       # derived from name on save; unique within the scheme
```

- Creating two collections with names that slugify to the same value **in one scheme** is refused
  (`slug` collision) — the same behaviour `Concept`/`ConceptScheme` already have.

### `Collection.add(concept) -> CollectionMember`

Add `concept` to the collection as a member. Appends: the new member's `position` is the current
maximum in the collection plus one.

- Refused if `concept.scheme_id != self.scheme_id` — a collection groups only its own vocabulary's
  concepts (FR-005).
- Adding a concept already in the collection is a no-op that returns the existing membership — the
  concept is held once (FR-004); it is never duplicated and does not raise.

### `Collection.remove(concept) -> None`

Remove `concept`'s membership if present; a no-op if it is not a member. The concept itself is
untouched (only the membership row is deleted). Other collections holding the concept are unaffected
(FR-003).

### `Collection.members() -> Sequence[Concept]`

The collection's member concepts.

- When `self.ordered`: returned in ascending `position` — the deliberate sequence (FR-006). Removing a
  member leaves the survivors in their original relative order (FR-007).
- When not ordered: returned as a set (no promised sequence).
- Empty when the collection has no members — never an error.

### `Collection.set_member_order(concepts) -> None`

Reassign the members' positions to the given sequence (`concepts[0]` first, and so on).

- Valid only when `self.ordered`; on an unordered collection it is refused with a translatable message
  (FR-006 — ordering is meaningless for a set).
- `concepts` must be exactly the collection's current member set (same elements, no more, no fewer);
  otherwise refused. After it returns, `members()` reflects the new sequence (FR-007).

## `Concept` (extended)

### `Concept.collections() -> Sequence[Collection]`

The collections this concept is a member of. Empty when it belongs to none. Reading or changing
membership never alters the concept's `slug`, `uri`, labels, or relations (FR-008).

## Orthogonality to relations (#17)

Adding two concepts to a collection creates no `broader`/`narrower`/`related` link between them, and
leaves any existing relation between two members unchanged. Collections (`CollectionMember`) and
relations (`ConceptRelation`) are independent tables sharing no state (FR-008).
