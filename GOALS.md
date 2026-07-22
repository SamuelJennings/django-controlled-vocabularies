# GOALS — django-controlled-vocabularies

Enduring goals this project pursues. Identity lives in the README; when work happens and which
release delivers it lives in the roadmap — this file names no versions. A goal is a capability
or quality you steer toward, not a task you complete: its id is stable, its importance is a tag
that can change, and whether it has been addressed enough is judged through the roadmap, specs,
and review rather than the goal itself.

**Importance** — `Essential`: not worth adopting without it · `Expected`: a complete,
dependable version is expected to have it · `Aspirational`: a genuine want whose absence never
makes the package incomplete.

**Status** — unmarked means accepted and live · `draft`: captured, not yet refined ·
`rejected`: decided against, kept with a reason and an ADR link when it's a design stance.

| ID | Goal | Importance | Status | Notes |
|----|------|------------|--------|-------|
| G1 | **Code-free vocabulary management** — create, edit, and deprecate SKOS vocabularies and concepts through a web interface, without hand-editing RDF or writing code. | Essential | | |
| G2 | **One-field consumption** — attach concepts to any Django model through a single field, so a vocabulary evolves as data rather than a code release of every consumer. | Essential | | |
| G3 | **Standards-compliant publishing** — serve valid SKOS/RDF at stable, permanent concept URIs, with content negotiation. | Essential | | |
| G4 | **Lossless interoperability** — import an external vocabulary and export it again without dropping predicates the model does not natively represent. | Essential | | |
| G5 | **Safe re-import** — updating a vocabulary never breaks existing references: identity is the concept URI, and concepts are deprecated rather than deleted. | Essential | | |
| G6 | **Scale to large vocabularies** — tens of thousands of concepts (e.g. NASA GCMD) stay responsive to search, browse, and autocomplete. | Expected | | |
| G7 | **Multilingual concepts** — labels and definitions carry per-language values, editable one language at a time. | Expected | | |
| G8 | **Embeddable and standalone** — usable both installed into an existing Django project and run as a standalone system. | Expected | | |
| G9 | **Real adoption** — the FairDM ecosystem and its heat-flow vocabularies rely on it instead of bespoke vocabulary code. | Expected | | |
| G10 | **Collaborative curation** — multiple curators work with object-level permissions and an editorial workflow. | Aspirational | draft | Permissions model (per-object vs per-scheme) not yet pinned. |

_Written 2026-07-22. Revise as the goals change._
