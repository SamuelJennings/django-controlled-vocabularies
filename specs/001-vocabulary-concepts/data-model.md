# Phase 1 Data Model: Represent a vocabulary and its concepts

Two models in `controlled_vocabularies/models.py`. Field types are the intended shape; the Implementer
owns exact declarations.

**Propagated**: 2026-07-23 — Refinement (US-5): every field additionally declares a translatable
`verbose_name` + non-empty `help_text` (`gettext_lazy`); both models declare translated
`Meta.verbose_name`/`_plural`; validation messages are translatable with named placeholders.
Indexing record: `ConceptScheme.slug` unique-indexed, `Concept.scheme` FK-indexed, `(scheme, slug)`
composite-constrained; `name` and `label` deliberately unindexed this slice (no query path — label
search belongs to #16).

## ConceptScheme (a vocabulary)

| Field | Type | Rules |
|---|---|---|
| `name` | `CharField` | required; non-empty after strip (else `ValidationError`) |
| `description` | `TextField` | optional (`blank=True`) |
| `slug` | `SlugField(allow_unicode=True)` | unique app-wide; derived from `name` on save; empty-after-slug → `ValidationError` |

- **`uri`** (computed property): `f"{base}/{self.slug}"`, where `base` comes from
  `controlled_vocabularies.conf` (R2). Not stored.
- **`save()`**: set `slug = slugify(name, allow_unicode=True)`; validate non-empty; then super().
- **`__str__`**: `name`.
- Relationships: has many `Concept` (reverse `concepts`).

**FRs**: FR-001 (create/rename/delete), FR-002 (slug derived, synced, unique), FR-005 (scheme URI).

## Concept (a term within a vocabulary)

| Field | Type | Rules |
|---|---|---|
| `scheme` | `ForeignKey(ConceptScheme, on_delete=CASCADE, related_name="concepts")` | required; deleting the scheme deletes its concepts (spec edge case) |
| `label` | `CharField` | required; non-empty after strip; the default-language preferred label (R8; #16 extends) |
| `slug` | `SlugField(allow_unicode=True)` | derived from `label` on save; unique **within** the scheme |

- **Constraint**: `UniqueConstraint(fields=["scheme", "slug"], name="unique_concept_slug_per_scheme")`.
- **`uri`** (computed property): `f"{self.scheme.uri}/{self.slug}"`. Not stored.
- **`save()`**: set `slug = slugify(label, allow_unicode=True)`; validate non-empty; then super().
- **`__str__`**: `label`.

**FRs**: FR-003 (add/retrieve/relabel/delete, belongs to one scheme), FR-004 (slug derived, synced,
unique-in-scheme), FR-005 (concept URI), FR-006 (retrieve by URI / scheme+slug / listing),
FR-007 (non-ASCII slugs, collisions refused).

## Identity & lookup

- Identity is the **URI**, never the PK (Article IX). The PK stays an internal detail.
- `Concept.objects.get_by_uri(uri)` (custom manager, R6): strip the configured base, split
  `scheme-slug/concept-slug`, return `get(scheme__slug=…, slug=…)`; raise `Concept.DoesNotExist`
  on no match (standard ORM behaviour).
- Global URI uniqueness is structural: unique scheme slug × unique-in-scheme concept slug ⇒ no two
  concepts compose the same URI (satisfies FR-006 / SC-002 without a stored column).

## Configuration

`controlled_vocabularies/conf.py`: `get_base_uri()` returns
`getattr(settings, "CONTROLLED_VOCABULARIES_BASE_URI", <default>).rstrip("/")`. One read site; the
default is documented in the README. `tests/settings.py` sets it to a fixed value so URI assertions are
deterministic.

## Validation summary (for the test matrix)

- Empty/whitespace `name`/`label` → `ValidationError`.
- Non-Latin `name`/`label` → non-empty Unicode slug.
- Duplicate scheme slug (app-wide) or duplicate concept slug within a scheme → refused (validation/
  integrity error), never auto-suffixed.
- Rename `name`/`label` → slug and composed URI change accordingly.
- Delete scheme → its concepts go too.

## Explicitly not modelled here (sibling features)

Multilingual labels/definitions/notes (#16); `broader`/`narrower`/`related` relations (#17);
collections (#18); lifecycle status, deprecation, `on_delete=PROTECT`, upsert-by-URI (#19 + import);
notation codes; stored/frozen URIs and publishing.
