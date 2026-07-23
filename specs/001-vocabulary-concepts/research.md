# Phase 0 Research: Represent a vocabulary and its concepts

Decisions that resolve the plan's open technical points. Format: decision · rationale · alternatives.

## R1 — URI is a computed property, not a stored column

**Decision**: `Concept.uri` and `ConceptScheme.uri` are computed on read from the configured base
address and the slugs; nothing is stored.

**Rationale**: in this slice every vocabulary is unpublished and slugs track their source text, so a
stored URI would need re-syncing on every rename — and a scheme rename would cascade a rewrite across
every concept it holds. That machinery has no consumer until publishing (freeze) and import
(upsert-by-URI) exist. Composition is cheap and deterministic. Uniqueness is still guaranteed
structurally by the slug constraints, so "no two concepts share a URI" holds without a stored column.

**Alternatives**: a stored, indexed `uri` with cascade re-sync — rejected for this slice as premature
(it belongs with the publishing feature that first freezes it); revisited then, not now.

## R2 — Base address is a single Django setting with a default

**Decision**: a thin `controlled_vocabularies/conf.py` reads `settings.CONTROLLED_VOCABULARIES_BASE_URI`
(a full base, e.g. `https://example.org/vocabularies`) with a sensible default, and strips a trailing
slash. Scheme URI = `{base}/{scheme.slug}`; concept URI = `{scheme.uri}/{concept.slug}`.

**Rationale**: the spec fixes the composition rule but leaves the mechanism to planning. One setting is
the simplest thing that works for both installed-in-a-host and standalone modes, and it avoids building
a settings framework (Anti-Abstraction). Reading it in one place keeps the rule from scattering.

**Alternatives**: Django `Sites` framework — rejected as heavier than needed and coupling identity to a
DB row; a per-scheme `base_uri` field — deferred, it only matters for imported external vocabularies
(import feature), not for locally-authored ones.

## R3 — Slugs via `slugify(..., allow_unicode=True)`, empty result rejected

**Decision**: derive slugs with Django's `django.utils.text.slugify(value, allow_unicode=True)`.
`SlugField(allow_unicode=True)`. If the slugified value is empty (e.g. a label of only punctuation),
raise a `ValidationError` rather than mint an empty identifier.

**Rationale**: the spec requires non-Latin labels ("Wärmefluss", Cyrillic) to yield usable slugs. With
`allow_unicode=False`, "Wärmefluss" degrades to "warmefluss" and pure-Cyrillic collapses to empty.
`allow_unicode=True` preserves Unicode letters, giving usable, percent-encodable slugs, and matches
SKOS's international content. Empty-after-slug is a genuine error the curator must fix.

**Alternatives**: ASCII-only slugs — rejected, they mangle or empty non-Latin labels; auto-suffixing an
empty slug to something synthetic — rejected, it mints an identifier the curator never chose.

## R4 — Slug collisions are refused, not auto-disambiguated

**Decision**: uniqueness is `ConceptScheme.slug` unique app-wide and `UniqueConstraint(scheme, slug)`
for concepts. A colliding slug surfaces as a validation error; the model does not silently append
`-2`.

**Rationale**: recorded spec decision — identifiers are this feature's whole point, and a silent suffix
mints one the curator never chose. The curator resolves the wording. (This mirrors the "reject, don't
invent" stance in the identity design.)

**Alternatives**: auto-suffix on collision — rejected as above; per-scheme non-unique slugs — rejected,
it would let two concepts in a vocabulary resolve to the same URI.

## R5 — Slug regenerates from source text on every save (this slice)

**Decision**: `save()` recomputes the slug from the name/label each time. There is no "freeze" and no
manual slug override in this slice.

**Rationale**: the spec requires renames to flow through to slugs and URIs while unpublished. Freezing
at publish is a later feature; until it exists, dynamic is correct and simplest.

**Alternatives**: set-once slugs — rejected, they contradict the approved "dynamic until published"
behaviour; a `slug` the curator edits by hand — deferred to the publishing/editing features.

## R6 — Lookup by URI via a manager method that parses the path

**Decision**: `Concept.objects.get_by_uri(uri)` strips the configured base and splits the remainder into
`scheme-slug/concept-slug`, then queries `get(scheme__slug=…, slug=…)`. No stored URI needed.

**Rationale**: with a fixed base and structural uniqueness, the URI ↔ (scheme-slug, concept-slug) map is
bijective, so parsing is exact. Keeps identity as the URI (Article IX) while the storage stays computed.

**Alternatives**: a stored indexed `uri` for direct lookup — rejected with R1; full-text/like matching —
unnecessary and wrong for an exact-identity lookup.

## R7 — Factories with `factory_boy`; confirm it ships in the test bundle

**Decision**: `tests/factories.py` provides `ConceptSchemeFactory` and `ConceptFactory` (the latter
sub-factories a scheme when none is given), built on `factory_boy` + `factory.django.DjangoModelFactory`.

**Rationale**: `factory_boy` is the standard Django factory library and gives US-4's "vocabulary in a few
lines" directly. Factories live in `tests/` because US-4 scopes them to this repo's later-feature tests.

**Open item (Constitution VII)**: confirm `factory_boy` is provided by `mvp-shared[test]`. If it is not,
add it as a **test-only** dependency, justified by US-4 (a shipped requirement, not speculation). Either
way `deptry` must stay green. The Implementer verifies this before writing the factories.

## R8 — Concept's preferred label is a single field this slice; #16 grows it

**Decision**: `Concept.label` is a plain `CharField` holding the default-language preferred label. It
seeds the slug and makes the object meaningful.

**Rationale**: multilingual labels/definitions/notes are sibling #16, which extends label storage (into
the language-keyed shared/translated shape from the design notes) **without disturbing the identity
mechanism** — the slug-from-label and computed-URI paths are what must stay stable, and they will. This
seam was accepted at the Spec gate (`decisions.md` item 1). Keeping the label a single field now is the
simplest thing that satisfies this slice.

**Alternatives**: introduce the JSON shared/translated document now — rejected for this slice: it is
#16's charter and has no other consumer here; building it now is exactly the speculation Article II/III
warn against. The identity seam, not the label storage, is the load-bearing part, and it is preserved.
