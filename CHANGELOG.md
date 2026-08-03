# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Static, externally assigned identifiers: `ConceptScheme`, `Concept`, and `Collection` each gain a
  `static_uri` field holding an identifier assigned by an external publisher, held exactly as given
  and never recomputed by the app. Set it and it stays put — the app will not overwrite it, though
  nothing stops you from editing it, so make the field non-editable wherever you expose it once a
  record is published. A locally authored, unpublished record's `uri` instead stays dynamic,
  composed and reported live and following a rename, until one is assigned. `local_url` is a new,
  separate accessor for this site's own address for a record, always composed from the configured
  base address and the record's slugs regardless of what `static_uri` holds. `has_static_uri`
  reports whether the identifier is static rather than dynamic.
  `get_by_uri()` — already on `Concept.objects` — is now shared by `ConceptScheme.objects` and
  `Collection.objects` too, resolving a stored identifier first and falling back to the site's own
  composition. `validate_static_uri` is exported for reuse: it requires an absolute identifier with
  an accepted scheme and caps length at 500 characters.
- `CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES` setting: the schemes an externally assigned
  `static_uri` may use — `http`, `https`, `urn`, `doi`, `info`, `ark`, `tag`, `hdl`, and `oai` by
  default (see the README).
- Collections: a vocabulary's concepts can be gathered into named collections, optionally ordered,
  held on the new `Collection` and `CollectionMember` models and reached through `Collection.add()`,
  `remove()`, `members()`, `set_member_order()`, and `Concept.collections()`. Membership is
  many-to-many, held once per collection, and confined to the collection's own vocabulary. It asserts
  no relation between members, so a collection stays clear of the broader/narrower hierarchy. An
  ordered collection reads its members back in a deliberate sequence. Authored through the ORM. The
  editing interface comes later.

- Concept relationships: concepts within a vocabulary can be linked through a broader/narrower
  hierarchy and a symmetric related association, held on the new `ConceptRelation` model and reached
  through `Concept.broader()`, `narrower()`, `related()`, and the `add_`/`remove_` helpers. Only the
  broader direction is stored; narrower is derived, so the pair can never disagree. A concept may sit
  under several broader concepts. The model refuses a self-relation, a duplicate, a broader/related
  overlap on the same pair, and a link across vocabularies; a cycle in the hierarchy is not prevented
  (a deliberate non-guarantee for now). Authored through the ORM; the editing interface comes later.
- Multilingual concepts: each concept carries per-language labels (one preferred label per language,
  plus any number of alternative and hidden labels) and the full SKOS documentary note family:
  `definition`, `scopeNote`, `example`, `editorialNote`, `historyNote`, `changeNote`, and a generic
  note. All are language-tagged and held on the new `ConceptLabel` and `ConceptNote` models. Authored
  through the ORM. The editing interface comes later.
- Per-vocabulary default language: a `ConceptScheme` defaults to the app's `LANGUAGE_CODE` but can
  set its own default language, which is the one that anchors its concepts' slugs. A German
  vocabulary anchors its identifiers in German inside an English-default app.
- Overridable concept slugs: a slug still derives from the default-language preferred label, but a
  curator can set an explicit slug that survives later relabels.
- `multilingual` factory trait building a fully populated multi-language concept for downstream tests.
- `ConceptScheme` and `Concept` models: a vocabulary is a named container of concepts, each concept
  a term within it. Slugs derive from the scheme name and the concept label and track them while a
  vocabulary is unpublished.
- Stable concept identity: a locally authored concept's URI composes from
  `CONTROLLED_VOCABULARIES_BASE_URI`, the scheme slug, and the concept slug, and stays resolvable when
  a label is reworded. (An externally assigned identifier instead holds verbatim — see static,
  externally assigned identifiers, above.) `Concept.objects.get_by_uri()` resolves a URI back to its
  concept.
- `CONTROLLED_VOCABULARIES_BASE_URI` setting for the URI base address (see the README).
- Test factories (`ConceptSchemeFactory`, `ConceptFactory`) for use in downstream tests.
- Initial project scaffold: package metadata, CI, and early design notes (see `docs/brainstorm.md`).
