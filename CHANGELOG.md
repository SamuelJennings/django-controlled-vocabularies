# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ConceptScheme` and `Concept` models: a vocabulary is a named container of concepts, each concept
  a term within it. Slugs derive from the scheme name and the concept label and track them while a
  vocabulary is unpublished.
- Stable concept identity: a concept's URI composes from `CONTROLLED_VOCABULARIES_BASE_URI`, the
  scheme slug, and the concept slug, and stays resolvable when a label is reworded.
  `Concept.objects.get_by_uri()` resolves a URI back to its concept.
- `CONTROLLED_VOCABULARIES_BASE_URI` setting for the URI base address (see the README).
- Test factories (`ConceptSchemeFactory`, `ConceptFactory`) for use in downstream tests.
- Initial project scaffold: package metadata, CI, and early design notes (see `docs/brainstorm.md`).
