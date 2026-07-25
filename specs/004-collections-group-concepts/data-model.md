# Data model — 004-collections-group-concepts

Two new models in `controlled_vocabularies/models.py`, plus one reverse helper on `Concept`. No change
to any existing model's columns.

## `Collection`

A named grouping of concepts within one vocabulary — `skos:Collection` (or `skos:OrderedCollection`
when `ordered`).

| Field | Type | Notes |
|---|---|---|
| `scheme` | `ForeignKey(ConceptScheme, on_delete=CASCADE, related_name="collections")` | The vocabulary the collection belongs to. Auto-indexed. |
| `name` | `CharField(max_length=255)` | Human-readable name; the `slug` derives from it. `verbose_name` + `help_text`, translatable. |
| `slug` | `SlugField(max_length=255, allow_unicode=True)` | Derived from `name` on save (research R4). Unique within the scheme. |
| `ordered` | `BooleanField(default=False)` | Whether members carry a deliberate sequence (`skos:OrderedCollection`). |
| `members` | `ManyToManyField(Concept, through="CollectionMember", related_name="collections")` | The member concepts; the through model carries `position`. |

- **Meta.constraints**: `UniqueConstraint(fields=["scheme", "slug"], name="unique_collection_slug_per_scheme")`
  — two collections in one vocabulary are distinguishable (FR-009), mirroring `Concept`'s
  per-scheme slug uniqueness.
- **`uri` property**: `f"{self.scheme.uri}/collection/{self.slug}"` — namespaced under `/collection/`
  so it never collides with a concept URI (research R4). Property, composed on read (no stored column),
  like `ConceptScheme.uri`/`Concept.uri`.
- **`save()`**: derive `slug = slugify(name)`, refuse an empty slug, refuse a slug colliding with
  another collection in the same scheme — the exact pattern `ConceptScheme.save`/`Concept.save` use,
  with translatable named-placeholder messages.
- **`verbose_name = _("collection")`**, **`verbose_name_plural = _("collections")`**.

### Helper API (see `contracts/python-api.md`)

- `add(concept)` — validate and create a `CollectionMember`; appends (`position` = current max + 1).
- `remove(concept)` — delete the membership if present.
- `members()` — member concepts; ordered by `position` when `ordered`, else a plain set.
- `set_member_order(concepts)` — reassign positions to the given sequence; ordered collections only.

## `CollectionMember` (through model)

The membership edge joining a collection to one member concept.

| Field | Type | Notes |
|---|---|---|
| `collection` | `ForeignKey(Collection, on_delete=CASCADE, related_name="memberships")` | Auto-indexed. |
| `concept` | `ForeignKey(Concept, on_delete=CASCADE, related_name="collection_memberships")` | Auto-indexed (backs `Concept.collections()`). |
| `position` | `PositiveIntegerField(default=0)` | Sort key for ordered collections (research R2). Meaningful only when `collection.ordered`. |

- **Meta.constraints**: `UniqueConstraint(fields=["collection", "concept"], name="unique_collection_member")`
  — a concept is held once per collection (FR-004); this also provides the collection-leading membership
  index.
- **Meta.indexes**: `Index(fields=["collection", "position"], name="collectionmember_order_idx")` — backs
  the ordered `members()` read.
- **`clean()` / `save()`**: refuse a member whose `concept.scheme_id != collection.scheme_id` (FR-005)
  with a translatable named-placeholder message. Cross-table equality → application check, not a DB
  constraint (research R3). `save()` re-checks so the refusal holds on the `add()`/factory path, not
  only under `full_clean()` (the #15/#16/#17 pattern).
- **Field metadata**: `verbose_name` + `help_text` on every field, translatable (US-5).
- **`on_delete=CASCADE`** on both FKs: a membership is not consumer data and is meaningless without both
  endpoints — identical to #17's edge reasoning. Article IX's `PROTECT`/deprecation governs *consumer
  references* and concept *retirement* (#19), which this slice does not touch.

## `Concept` (extended)

- **`collections()`** — the collections this concept is a member of, read through the reverse
  `collection_memberships` relation. No new column; identity, labelling, and relations unchanged.

## Indexing decision (Article XIII, recorded)

- `UniqueConstraint(collection, concept)` — enforces held-once **and** indexes the primary membership
  lookup (a collection's members). Deliberate.
- `Index(collection, position)` — backs ordered reads. Deliberate.
- `concept` FK auto-index — backs `Concept.collections()` (the reverse read). Deliberate (relies on
  Django's automatic FK index; no extra index added).
- `Collection.scheme` FK auto-index — backs "collections in this vocabulary". Deliberate.
- `UniqueConstraint(scheme, slug)` on `Collection` — identity uniqueness + slug lookup. Deliberate.
- `position` carries no standalone index (only queried within a collection, covered by the composite).
  Deliberate omission.

## Migration

One migration adds both tables (`Collection`, `CollectionMember`) and their constraints/indexes. No
change to existing tables. Regenerated from zero and squashed to one file at convergence (S5);
`makemigrations --check` clean.
