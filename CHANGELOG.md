# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
