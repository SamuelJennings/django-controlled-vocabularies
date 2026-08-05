# CONTEXT.md — Ubiquitous language

The shared vocabulary for this project. Every core concept is named once here so specs, issues,
and code speak the same language. Where a term has a tempting synonym, the synonym is called out.
This is a seed — it grows as the code does.

## RDF / SKOS foundations

| Term | Definition | Notes / synonyms to avoid |
|---|---|---|
| **SKOS** | W3C [Simple Knowledge Organization System](https://www.w3.org/TR/skos-reference/) — the RDF vocabulary this package targets exclusively. | Not "ontology" (that implies OWL). |
| **Triple** | The atom of RDF: **subject** (the thing described), **predicate** (a property), **object** (the value). | In this package: subject = a Concept/Scheme, predicate = a JSON key, object = a JSON value. |
| **URI** (`uri`) | The globally stable identifier of a scheme, concept, or collection — always present, never `None`. Static once fixed (see **Static URI**), otherwise dynamic: composed from the site's configured address and follows the record until it is fixed. **Identity lives here, never in the database PK.** | Every record has one; it is never "missing," only dynamic or static. |
| **Static URI** (`static_uri`) | The identifier once it is fixed: assigned by an external publisher and held exactly as given, or frozen when this site publishes the vocabulary (R4). Empty (`None`) means the record's `uri` is still dynamic. Held fixed by `save()`/`full_clean()` — a bulk queryset write bypasses that, as it bypasses every model-level rule. | Was called "Permanent URI". Fixed once externally assigned or once published; never rewritten before then, either. Not the same as **URI** — it is one of the two states `uri` can be in. |
| **Local URL** | This site's own address for a record, always composed from the site's configured address and the record's slugs, regardless of what its `static_uri` is. For a locally authored, unpublished record the two are the same string; for an imported record they differ, because the record is viewable here even though its identity belongs to its publisher. | The address a record is viewed at, not necessarily its identity. |
| **CURIE** | Compact URI, `prefix:name` (e.g. `skos:prefLabel`), expanded against known namespaces. | The shorthand form, not a full URI. |
| **Turtle / TTL / RDF-XML / JSON-LD** | Serialization formats produced on export and accepted on import (via rdflib). | Formats, not the data model. |

## Domain model

> **Storage status (as of R1, #16).** The JSON-**document** + **projection** storage described in
> this and the next table is the *intended* direction for the import and editor features (R2/R5),
> per `docs/brainstorm.md`. The shipped R1 slice stores labels and notes as **relational models**
> (`ConceptLabel`, `ConceptNote`) with the default-language preferred label held on `Concept.label`.
> The document/predicate-registry design is deferred to the features that consume it
> (`specs/002-multilingual-concepts/research.md` R1). Read the JSON rows below as design intent, not
> current implementation.

| Term | Definition | Notes / synonyms to avoid |
|---|---|---|
| **ConceptScheme** | A vocabulary: the `skos:ConceptScheme` container. A Django model. | The formal container. Don't call it a "namespace". |
| **Concept** | A term within a scheme — `skos:Concept`. A Django model whose editable state is a JSON **document**; core fields are projected into indexed columns. | Avoid "term"/"entry"; the type is **Concept**. |
| **Collection** | A `skos:Collection` — a grouping of concepts within a scheme, optionally ordered. | Distinct from a scheme; a grouping *inside* it. |
| **Label** | A language-tagged name for a concept: `prefLabel` (one per language), `altLabel` / `hiddenLabel` (many per language). Stored as translated JSON, indexed via a projected `pref_label` column. | Multi-valued per language — the reason plain per-object translation frameworks don't fit. |
| **Definition / Note** | Descriptive predicates: `definition`, `scopeNote`, `editorialNote`, `example`, etc. Language-tagged. | `definition` is the primary; treat foreign `dcterms:description` as an import alias for it. |
| **Notation** | A `skos:notation` — a typed, language-*independent* code for a concept. | Language-independent → shared document, not translated. |
| **Relation** | An intra-vocabulary link between two concepts: `broader` / `narrower` (inverse pair), `related` (symmetric). Stored as a self-referencing M2M with a `relationship_type` through-model. | Only one canonical direction is stored; the inverse is derived (`docs/brainstorm.md`). |
| **Mapping** | A cross-vocabulary link: `exactMatch`, `closeMatch`, `broadMatch`, … usually pointing at concepts in *other* vocabularies (URIs with no local row). | Lives in the JSON document, **not** the relation M2M. |

## This package's mechanisms

| Term | Definition | Notes |
|---|---|---|
| **Document** | The JSON representation of a concept's predicate→object pairs — the **sole source of truth** for its literal-valued and unknown predicates. | Split into a **shared** document (language-independent) and a **translated** document (language-tagged), per `docs/brainstorm.md`. |
| **Projection / index column** | A concrete, read-only DB column (`uri`, `pref_label`, `definition`) synced from the document on save, existing purely to be indexed and queried. | Materialised index, not a second source of truth. |
| **Escrow** | The role the JSON document plays for predicates the schema doesn't model — stored verbatim, re-emitted on export, so round-tripping is lossless. | Nothing imported is ever silently dropped. |
| **Predicate registry** | A curated map: CURIE → `{value_type: literal\|uri\|typed, cardinality: one\|many, translatable: bool}`. Drives the editor dropdown, per-row widget, validation, shared-vs-translated routing, and import aliases. | `docs/brainstorm.md`. Unregistered predicates still work as free-text escrow. |
| **ConceptField / ConceptsField** | The consumption API: a model field wrapping a `ForeignKey` / `ManyToMany` to `Concept`, constrained to a scheme, with an autocomplete widget. | Replaces choice-iterable style entirely (`docs/brainstorm.md`). |
| **Lifecycle** | A concept's `status`: `draft` → `published` → `deprecated` (`owl:deprecated` on export). Referenced concepts are `PROTECT`ed, not deleted. | `docs/brainstorm.md`. |

## Importing published vocabularies

| Term | Definition | Notes / synonyms to avoid |
|---|---|---|
| **Base language** | The first subtag of a language tag — `en` in `en-GB`, `zh` in `zh-Hans`. Matching a published tag against the site's configured languages runs on this, never on the whole tag. | Not the tag itself; two tags can share a base language and still differ. |
| **Variant** | A published language tag that shares a base language with a configured one without matching it exactly, such as a file's `en-gb` against a site configured for `en`. Where a value's kind holds only one per language, as a preferred label does, one variant is kept and the rest are set aside and reported under their own published tag. Where it holds many, as alternative labels, hidden labels and notes do, every variant offered is stored. | Distinct from an exact match, which always wins over a variant and is never displaced by one. |
| **Substitution** | A value stored under a configured language other than the tag it was published under, because only a variant match reached it. Reported alongside what was created and updated, distinguishable from a value that was not stored at all. | The value *was* kept — not the same as a value set aside. |

## Architectural decisions

Design reasoning lives in [`docs/brainstorm.md`](docs/brainstorm.md). Start there for the "why" behind
models-as-truth, document-plus-projection storage, canonical-direction relations, the
shared/translated split, static URI identity, and the consumption field.
