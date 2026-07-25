# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Collections: a vocabulary's concepts can be gathered into named collections, optionally ordered,
  held on the new `Collection` and `CollectionMember` models and reached through `Collection.add()`,
  `remove()`, `members()`, `set_member_order()`, and `Concept.collections()`. Membership is
  many-to-many, held once per collection, and confined to the collection's own vocabulary; it asserts
  no relation between members, so a collection stays clear of the broader/narrower hierarchy. An
  ordered collection reads its members back in a deliberate sequence. Authored through the ORM; the
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
- Stable concept identity: a concept's URI composes from `CONTROLLED_VOCABULARIES_BASE_URI`, the
  scheme slug, and the concept slug, and stays resolvable when a label is reworded.
  `Concept.objects.get_by_uri()` resolves a URI back to its concept.
- `CONTROLLED_VOCABULARIES_BASE_URI` setting for the URI base address (see the README).
- Test factories (`ConceptSchemeFactory`, `ConceptFactory`) for use in downstream tests.
- Initial project scaffold: package metadata, CI, and early design notes (see `docs/brainstorm.md`).
