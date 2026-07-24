# Phase 0 Research: Multilingual names and descriptions for concepts

Decisions taken at planning, with the reasoning that makes each defensible. The load-bearing one is
the storage shape; the rest follow from it. Grilling-level decisions live in `decisions.md`; this
file is the technical layer.

## R1 — Storage: relational child models, not django-parler + JSON documents

**Decision.** Store per-language, multi-valued labels and notes as two concrete relational child
models — `ConceptLabel` and `ConceptNote` — each a row per (concept, language, kind, value). The
`brainstorm.md` lean toward django-parler plus a shared/translated JSON document and a predicate
registry is **not** adopted in this slice.

**Why.** The document-plus-registry apparatus earns its keep at two boundaries that do not exist
yet: *import escrow* for arbitrary unknown predicates (roadmap R2) and the *key-value predicate
editor* (roadmap R5). #16 has neither. What it has is a fixed, known set of SKOS lexical and
documentary predicates, each with a declared cardinality and translatability — which relational rows
model directly and index natively. Choosing rows now honours constitution Articles II (Simplicity)
and III (Anti-Abstraction): no new runtime dependency, no JSON-in-column query gymnastics, ordinary
Django constraints do the enforcing (one preferred label per language is a `UniqueConstraint`).

**Cost, named (Article VIII discipline — deliberate, not silent).** If R2/R5 later want the
document+registry model, a relational→document migration is required. That is a tracked, testable
step at the point its consumer arrives, and it does not touch the identity mechanism (URIs are
composed from slugs, not from label storage). Deferring is cheaper than carrying an unused
abstraction across every intervening feature. **Flagged at the Plan gate for Sam**, because it
overturns a `brainstorm.md` lean.

**Alternatives rejected:**

- *django-parler translated fields.* parler models one translated row per (object, language) with
  single-valued fields; SKOS's many-alt-labels-per-language do not fit without stuffing JSON lists
  into a parler field, which is the worst of both worlds (a heavy dependency AND JSON querying).
- *JSON document + projected columns now.* Real long-term design, but its value is escrow and a
  dynamic predicate set — both absent here. Building it now is the premature-generalisation the
  feature framework explicitly guards against.

## R2 — The identity anchor stays a field on `Concept`; translations are child rows

**Decision.** Keep the default-language preferred label as a concrete field on `Concept` (evolving
#15's `label`). Additional languages' preferred labels, and all alternative and hidden labels, live
in `ConceptLabel` child rows; the default-language preferred label is **not** duplicated as a row.

**Why.** A child row needs its concept's primary key to exist, but the slug derives from the
preferred label — a chicken-and-egg if every label is a child row (a concept would briefly exist
with no slug). Keeping the identity-bearing label on the model dissolves the ordering problem: the
slug derives from a field that is present at first `save()`, exactly as in #15. It also minimises the
supersession — #15's `label` field survives with a clarified meaning; only #15's *assumption* that a
concept has one label total is superseded.

**Trade-off, named.** The default language is asymmetric (a field) versus other languages (rows), so
"read the preferred label for language X" is a small helper: return `label` when X is the effective
default, else query the child rows. The asymmetry has a clear rationale — identity — and is recorded
so it reads as deliberate. Symmetric all-rows storage was rejected for the ordering cost above.

## R3 — Slug override provenance

**Decision.** Add a persisted boolean to `Concept` (working name `slug_is_manual`, default `False`).
`save()` re-derives `slug` from the default-language label **only when** the flag is `False`; an
explicitly set slug sets the flag and pins the value. Uniqueness-within-scheme (from #15) applies to
both derived and manual slugs.

**Why.** FR-010 needs to distinguish "auto slug that should track the label" from "curator's chosen
slug that must not move". A blank-triggered auto-populate cannot express "pinned to a value that
happens to equal the label", and re-deriving on every save (as #15 did) would clobber a manual slug.
An explicit flag is the honest, minimal signal. The public API sets it via a keyword/manager helper
so callers never poke the boolean directly.

## R4 — Language configuration

**Decision.** Available languages are `settings.LANGUAGES`; the application default is
`settings.LANGUAGE_CODE`. `ConceptScheme` gains `default_language` (a `CharField`, `blank=True`,
choices bound to `settings.LANGUAGES`); an `effective_default_language` property returns the override
or falls back to `settings.LANGUAGE_CODE`. Language values on labels/notes validate against
`settings.LANGUAGES`.

**Why.** Standard Django i18n configuration, no bespoke registry (Simplicity). Storing the override
as a plain code with a property fallback keeps the "app default unless overridden" rule in one place.

## R5 — Notes and definition as one `ConceptNote` model, typed by kind

**Decision.** One `ConceptNote(concept, language, kind, value)` model covers `definition` and the six
documentary notes (`scopeNote`, `example`, `editorialNote`, `historyNote`, `changeNote`, `note`),
`kind` a choices field over the SKOS predicate names. Multiple rows per (concept, language, kind) are
allowed (SKOS permits repeated notes); no uniqueness constraint on notes.

**Why.** They are handled identically (language-tagged text); a shared model with a `kind`
discriminator is simpler than seven fields or seven models (Anti-Abstraction) and makes the later RDF
mapping a single kind→predicate table. `definition` is not special-cased structurally; if a hot
index on the default-language definition is ever wanted, it is an additive projection decision, out
of scope here.

## R6 — Label search indexing

**Decision.** The identity/lookup value (`Concept.label`) and the `ConceptLabel(language, kind, text)`
lookup path are indexed for label search; `ConceptNote.value` (free prose, no lookup path this slice)
is deliberately unindexed, recorded per Article XIII. The `(concept, language)` uniqueness for
preferred rows is a `UniqueConstraint`.

**Why.** FR-015 + Article XIII: a field with a query path is indexed, and an unindexed queryable
field is a recorded decision. Label search (by pref/alt/hidden text) is the real query path this
feature introduces; note prose is not searched yet (that is browsing, R6).

## R7 — No new runtime dependency; test tooling unchanged

**Decision.** No runtime dependency is added (R1 avoids parler/rdflib). Tests use the existing
`pytest`/`pytest-django` + `factory_boy` from `mvp-shared[test]`; add `ConceptLabelFactory` and
`ConceptNoteFactory` and extend `ConceptFactory` for multilingual traits, mirroring the source tree
per the family testing standard.

**Why.** `deptry` fails a declared-but-unused dependency, and this slice imports neither parler nor
rdflib. Keeping the scaffold lean is the born-green standard.

## R8 — Supersession annotation of #15's artifacts

**Decision.** As part of this feature's PR, annotate the specific #15 statements this feature
overrides — its `spec.md` single-label assumption, the `data-model.md` `Concept.label` "one label"
note, and `decisions.md` §1 — with strikethrough plus a forward "Superseded by FS-002 (#16)" tag, and
add a line to #15's `decisions.md` recording the external supersession. The `label` field itself is
**not** struck (it survives, meaning clarified). Surgical and atomic with the change, per the
cross-spec supersession convention.

**Why.** Sam's rule that a later feature may supersede an earlier one needs a visible paper trail, or
a future reader trusts a stale decision. Strikethrough preserves the history; the forward tag makes
the current truth unambiguous. A dedicated task carries it so it lands in this PR.
