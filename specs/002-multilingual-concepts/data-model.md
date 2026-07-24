# Phase 1 Data Model: Multilingual names and descriptions for concepts

Field types are the intended shape; the Implementer owns exact declarations. Every field declares a
translatable `verbose_name` + non-empty `help_text` (Article XII); indexing is deliberate (Article
XIII). All models live in `controlled_vocabularies/models.py`.

Two models are extended (`ConceptScheme`, `Concept`) and two are new (`ConceptLabel`, `ConceptNote`).
Storage rationale: `research.md` R1–R2 (relational child models; identity anchor stays a field).

## ConceptScheme (extended)

| Field | Type | Rules |
|---|---|---|
| `default_language` | `CharField(blank=True)` | choices bound to `settings.LANGUAGES`; empty = fall back to the app default |

- **`effective_default_language`** (property): `self.default_language or settings.LANGUAGE_CODE`.
- Everything from #15 (`name`, `description`, `slug`, `uri`) is unchanged.

**FRs**: FR-009 (per-vocabulary default), FR-011 (effective default resolution).

## Concept (extended / modified)

| Field | Type | Rules |
|---|---|---|
| `scheme` | `ForeignKey(ConceptScheme, CASCADE, related_name="concepts")` | unchanged from #15 |
| `label` | `CharField` | required; non-empty after strip; **the preferred label in the scheme's effective default language** — the identity anchor (was #15's single label, meaning clarified, not superseded) |
| `slug` | `SlugField(allow_unicode=True)` | unique within scheme; derived from `label` on save **unless** `slug_is_manual`; explicit slug pins the value |
| `slug_is_manual` | `BooleanField(default=False)` | set when a caller supplies an explicit slug; gates re-derivation |

- **`save()`**: if not `slug_is_manual`, `slug = slugify(label, allow_unicode=True)`; validate
  non-empty and unique-in-scheme (as #15); a manual slug is validated the same way but never
  re-derived. The `(scheme, slug)` `UniqueConstraint` from #15 remains the integrity backstop.
- **`uri`** (property): unchanged from #15 (`f"{self.scheme.uri}/{self.slug}"`).
- **Read helpers** (the language-filtered API — `contracts/python-api.md`):
  - `preferred_label(language=None)` → `self.label` when `language` is the scheme's effective
    default (or `None`), else the matching `ConceptLabel` pref row's text or `None`.
  - `alt_labels(language)` / `hidden_labels(language)` → lists of `ConceptLabel` texts.
  - `notes(language, kind=None)` / `definition(language)` → `ConceptNote` values.
- **Validation**: exactly one preferred value per language across (the `label` field for the default
  language) + (`ConceptLabel` pref rows for the others); a `ConceptLabel` pref row in the effective
  default language is rejected (the field owns that language). See `ConceptLabel` constraint below.

**FRs**: FR-002 (default-language label required, anchor), FR-003 (slug derivation preserved),
FR-010 (overridable slug pinned), FR-012 (slug uniqueness).

## ConceptLabel (new) — non-default-language preferred labels + all alternative/hidden labels

| Field | Type | Rules |
|---|---|---|
| `concept` | `ForeignKey(Concept, CASCADE, related_name="labels")` | required |
| `language` | `CharField` | choices bound to `settings.LANGUAGES`; required |
| `kind` | `CharField(choices=Kind)` | `PREFERRED` \| `ALTERNATIVE` \| `HIDDEN` |
| `text` | `CharField` | required; non-empty after strip |

- **Constraints**:
  - `UniqueConstraint(fields=["concept", "language"], condition=Q(kind=PREFERRED),
    name="one_preferred_label_per_language")` — enforces FR-001 for non-default languages.
  - Validation (model `clean`): a `PREFERRED` row whose `language` equals the concept's scheme
    effective default language is rejected — that language's preferred label is `Concept.label`.
- **Indexing**: `Index(fields=["language", "kind", "text"])` for label lookup/search (FR-015);
  FK auto-indexed.
- **`Meta.ordering`**: `("language", "kind", "text")` for stable reads.

**FRs**: FR-001 (one preferred per language), FR-005 (many alt/hidden per language), FR-007 (read by
language), FR-015 (label lookup indexed).

## ConceptNote (new) — definition + SKOS documentary notes, per language

| Field | Type | Rules |
|---|---|---|
| `concept` | `ForeignKey(Concept, CASCADE, related_name="concept_notes")` | required |
| `language` | `CharField` | choices bound to `settings.LANGUAGES`; required |
| `kind` | `CharField(choices=Kind)` | `DEFINITION` \| `SCOPE` \| `EXAMPLE` \| `EDITORIAL` \| `HISTORY` \| `CHANGE` \| `NOTE` (CURIE map lives with the model) |
| `value` | `TextField` | required; non-empty after strip |

- **No uniqueness constraint** — SKOS permits repeated notes of a kind per language (research R5).
- **Indexing**: FK auto-indexed; `value` deliberately **unindexed** (free prose, no lookup path this
  slice — recorded per Article XIII, FR-015). `(concept, language, kind)` needs no index beyond the FK
  for this slice's read pattern (fetch a concept's notes, filter in Python or a small `.filter`).
- **`Meta.ordering`**: `("language", "kind")`.

**FRs**: FR-006 (definition + documentary notes per language), FR-007 (read by language).

## Migration

One migration adds `ConceptScheme.default_language`, `Concept.slug_is_manual`, and the two new
models. `Concept.label` keeps its column (semantics clarified, not moved), so there is **no data
move** — and nothing is released, so the branch's migrations are squashed to one at convergence
(pipeline S5), regenerated from zero, verified green.

## Validation summary (for the test matrix)

- Missing default-language `label` → `ValidationError` (FR-002).
- Second preferred label in a language that already has one (field or row) → refused (FR-001).
- A `ConceptLabel` PREFERRED row in the effective default language → refused (belongs on the field).
- Language not in `settings.LANGUAGES` on any label/note → refused.
- Manual slug: pinned across `label` changes; auto slug: tracks `label`; collision within scheme →
  refused for both (FR-010, FR-012).
- Reading labels/notes for a language with none → empty list/`None`, not an error (FR-007).

## Explicitly not modelled here (sibling/later features)

Shared/translated JSON documents, the predicate registry, and django-parler (research R1 — deferred
to R2/R5); notation codes; `broader`/`narrower`/`related` relations (#17); collections (#18);
lifecycle/deprecation/`PROTECT`/upsert-by-URI (#19 + import); RDF import/export and frozen URIs;
SKOS pairwise label disjointness (`decisions.md` §10).
