# Roadmap: django-controlled-vocabularies

**Date:** 2026-07-22

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md) for
domain terminology and [memory/constitution.md](../memory/constitution.md) for project standards.

## Versioning

Releases are gated on goal importance, not on a fixed count of features.

| Version | Gate | Meaning |
|---|---|---|
| `0.0.x` | building toward the Essential goals | pre-viable; expect churn; git-pin only, nothing on PyPI |
| `0.1.0` | all Essential goals delivered | the minimum usable release; first PyPI publish |
| `0.1.x` to `0.x` | Expected goals, at whatever granularity the work takes | each advances one or more Expected goals; patches are fixes |
| `1.0.0` | all Expected goals delivered | the complete, dependable release |
| `1.x` | stable line | non-breaking fixes and additive features only |
| `2.0` | next major | breaking changes |

Aspirational goals may be developed against v2 or v1 as required.

Two rules this table encodes. A goal does not equal a minor release: some goals take several
minors, and one minor can move two goals. And once `1.0` ships, a breaking change cannot go out as
`1.x`; it waits for the next major, because a consumer pinned to `>=1,<2` is trusting that it will
not break.

The repo is at `0.0.x` today. Nothing is built yet, so the first published release is still some
way off.

## Essential goals: v0.1.0

Everything needed to reach a minimum usable release.

### 1. Core domain foundation

*Large, expect several stories · advances the foundation, and G6 directly.*

Nothing else can be built until the system can represent a vocabulary and everything inside it, so
this goes first.

**Deliverables:**

- models for concept schemes, concepts, collections, labels, and concept relationships;
- creation and querying through the ORM and the Django admin;
- stable identity for concepts, and a concept lifecycle;
- tests covering the identity and safety behaviour.

Serves the foundation and G6. Out of scope: RDF import and export, the consumption field, the
served URLs, and the editing interface.

### 2. RDF import

*Full feature · advances G4, and G8, G6.*

Import is the only way to get real vocabularies into the system: the heat-flow vocabularies already
published as Turtle, large external sets, and whatever a curator starts from. Until it exists,
nothing downstream can be tested against real data.

**Deliverables:**

- reading vocabularies from Turtle, RDF/XML, and JSON-LD into the models;
- a re-runnable, safe import that upserts rather than delete-and-recreates;
- external vocabularies normalised to the app's configured languages, with what was set aside
  reported to the user, and an additive re-import that fills in newly added languages;
- both a management command and a programmatic entry point.

Serves G4, G8, and G6. Out of scope: export and serving, the consumption field, the editing
interface.

### 3. Concept consumption field

*Full feature · advances G2.*

This is what the whole package was built for: letting a Django project attach controlled-vocabulary
concepts to its own models as first-class data. It depends on item 1.

**Deliverables:**

- a field (single and multiple) that attaches concepts from a chosen vocabulary to a consumer's
  model;
- autocomplete-backed selection in forms and the Django admin;
- referential integrity, so a referenced concept cannot silently disappear;
- the concept's label and identity reachable from the consuming record.

Serves G2. Out of scope: import, export and serving, the editing interface.

### 4. RDF publishing and stable URIs

*Full feature · advances G3, and G4.*

This closes the consume loop and makes the stable-URI promise real: a published concept URI has to
resolve to standards-compliant RDF. The details belong in this feature's own spec.

**Deliverables:**

- concept and scheme URLs that resolve to valid SKOS in Turtle and at least one other
  serialization, chosen by content negotiation;
- a human-readable response alongside the machine ones;
- a vocabulary exported this way that re-imports cleanly.

Serves G3 and G4. Out of scope: the editing interface, browsing external sources.

### 5. Vocabulary management interface

*Large, multi-feature · advances G1.*

The graphical, code-free way for curators to create, edit, and deprecate vocabularies and concepts.
It is the last Essential goal, so `0.1.0` cannot ship without it, but it comes after the consume
items because it needs the domain and the publish path in place.

**Deliverables:**

- create, edit, and deprecate schemes, concepts, and collections through the UI;
- edit labels and notes per language;
- manage hierarchy and relationships between concepts.

A fuller brief gets written when it reaches the front of the queue.

## Expected goals: v1.0.0

Anything that advances toward the v1.0.0 release.

### 6. Vocabulary browsing

*Full feature · advances G7.* A read-only way for people to search and move around concepts, across
both local vocabularies and imported external ones, so a stable URI leads somewhere a person can
use.

### 7. Scale hardening

*Full feature · advances G5.* Keep search, browse, and autocomplete responsive at tens of thousands
of concepts, and support navigation over deep hierarchies.

### 8. Embeddable and standalone modes

*Full feature · advances G9.* Make the app a good guest inside a host Django project, and, with a
thin wrapper, a system that runs on its own.

### 9. Adopt the heat-flow vocabularies as first real content

*Small to medium · advances G10.* Move the existing heat-flow vocabularies onto this app as the
first production content, exercising the manage, consume, and publish loop on a real dataset.

## Aspirational goals: v2.0

Bigger bets, taken on once the 1.x line is stable.

### 10. Collaborative curation

*Draft · large · advances G11.* Several curators working the same vocabularies under object-level
permissions.

### 11. Vocabulary versioning

*Draft · large · advances G12.* Track versions of a vocabulary as it changes so a consumer can cite
the version it used.
