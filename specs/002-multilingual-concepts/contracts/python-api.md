# Public ORM contract — Multilingual names and descriptions

The programmatic surface a downstream developer uses. This is the contract acceptance tests exercise;
exact signatures are the Implementer's, but the behaviour below is fixed by the spec. Builds on #15's
contract (`ConceptScheme`, `Concept`, `Concept.objects.get_by_uri`), which is unchanged.

## ConceptScheme

- `default_language: str = ""` — an override; a language code from `settings.LANGUAGES`, or empty.
- `effective_default_language -> str` — `default_language or settings.LANGUAGE_CODE`.

## Concept

Identity anchor and slug behaviour:

- `label: str` — required; the preferred label in the scheme's effective default language. Drives
  the slug unless the slug is pinned.
- `slug: str` — derived from `label` on save when auto; a pinned slug is preserved across `label`
  changes. Unique within the scheme (from #15).
- Setting an explicit slug: a caller passes the slug and marks it manual (via a manager helper such
  as `Concept.objects.create(..., slug="x")` setting the manual flag, or `concept.set_slug("x")`).
  Exact spelling is the Implementer's; the guarantee is FR-010.

Read API (language-filtered; `language=None` means the scheme's effective default):

- `preferred_label(language=None) -> str | None`
- `alt_labels(language) -> list[str]`
- `hidden_labels(language) -> list[str]`
- `definition(language) -> str | None`  *(first definition value for that language, or None)*
- `notes(language, kind=None) -> list[str]`  *(all note values, optionally filtered to one kind)*

Write API (one language at a time; other languages untouched):

- `add_label(language, kind, text)` / equivalent — `kind ∈ {preferred, alternative, hidden}`; a
  second `preferred` for a language that already has one raises `ValidationError`; a `preferred` in
  the effective default language raises `ValidationError` (that lives on `label`).
- `add_note(language, kind, value)` — `kind ∈ {definition, scope, example, editorial, history,
  change, note}`; repeats allowed.

Errors (all translatable, named placeholders — Article XII):

- Missing default-language `label` → `ValidationError`.
- Duplicate preferred label in a language → `ValidationError`.
- Language outside `settings.LANGUAGES` → `ValidationError`.
- Slug collision within scheme (auto or manual) → `ValidationError` (from #15).

## Invariants the contract guarantees

- **Identity stability (FR-004/SC-003)**: `concept.uri` and `concept.slug` are unchanged by any
  `add/remove/change` of a label or note in a non-default language, and by any note change at all.
- **One preferred per language (FR-001)**: across the `label` field (default language) and
  `ConceptLabel` preferred rows (other languages), each language has at most one preferred label.
- **Slug provenance (FR-010)**: an auto slug tracks `label`; a manual slug never moves on relabel.
