# GOALS.md — django-controlled-vocabularies

The enduring goals this package pursues, and the boundaries it holds. Directions, not a backlog;
maturity tiers map to versions per the repo docs model.

## The problem

Research data infrastructure depends on controlled vocabularies and ontologies (SKOS, RDF) to
describe data and metadata consistently. Django has no native support for consuming or managing
them, and no widely adopted third-party package fills the gap. The existing editors are either
foreign stacks (Java/PHP/Ruby), unmaintained, deployment-heavy, or commercial — none installs
into a Django project. So there is a persistent gap between published research vocabularies and
the Django applications that need to use them.

## Who it is for

- **Curators and domain experts** (researchers, institutional librarians) who need to create,
  edit, version, and publish controlled vocabularies through a graphical interface — without
  editing RDF by hand, writing Python, or using git.
- **Django developers** building research portals (notably on FairDM) who need to *consume*
  vocabularies as first-class model relationships and serve standards-compliant RDF.

## What success looks like

- A curator creates and edits a vocabulary in a web UI, with per-language labels, hierarchy, and
  relationships, and publishes standards-compliant RDF served at stable URIs — all from Django.
- A developer installs the app, imports an existing vocabulary (including large ones like NASA
  GCMD, tens of thousands of concepts), and attaches concepts to their own models via a field —
  with the vocabulary evolving as *data*, not requiring a code release per term.
- Round-tripping an external vocabulary through import → edit → export loses nothing.

## Deliberately out of scope

- **General RDF/OWL modelling.** SKOS only. (Same narrowing that shaped its predecessors — see
  `docs/adr/0001`.) Arbitrary RDF stays rdflib's job.
- **A triplestore or SPARQL endpoint.** The relational DB is the store; RDF is a projection.
- **Replacing rdflib.** It is used at the import/export boundary and nowhere else.
- **Reasoning / inference.** No OWL reasoner, no transitive-closure materialisation beyond what
  hierarchy queries need.

## Relationship to predecessors

Supersedes and retires **`skos-builder`** (declarative vocab authoring in code) and
**`django-research-vocabs`** (the first Django integration attempt). Their lessons carry forward;
their code does not. `ihfc-iugg/ihfc-vocabularies` (heat-flow SKOS) is the first real content and
migrates in via its existing Turtle exports.

## Development appetite

A substantial, multi-release package — the largest in the FairDM portfolio. The django-mvp shell
collapses the CRUD/forms/permissions cost that would otherwise make this a multi-year platform;
`acdh-oeaw/vocabseditor` (MIT, Django) proves a small team can build the equivalent. Built
incrementally, consumption-first.

## Maturity tiers → versions

- **v0.1 — consume.** Core models (scheme / concept / label / relation / extra-JSON), RDF
  **import** (rdflib), a `ConceptField` (FK) and `ConceptsField` (M2M) for downstream models,
  and RDF **export/serve** at stable URIs. No editing UI yet. This delivers the FairDM-blocking
  need — SKOS concepts as model relationships — before a single edit form exists.
- **v0.x — curate.** The graphical editor: create/edit schemes and concepts, the registry-driven
  key/value editor, per-language editing, hierarchy and relationship management, object-level
  permissions, the draft→published→deprecated lifecycle.
- **v1.0 — publish.** Hardened publishing workflow, content negotiation, versioning of
  vocabularies, and a documented standalone-deployment mode.

## Genuinely open questions (not yet decided)

- **Vocabulary versioning.** How scheme versions are represented and whether concept history uses
  `django-reversion` or a bespoke audit trail. Direction only.
- **Permissions model.** Per-object (`django-guardian`) vs per-scheme role assignment — needed,
  shape unpinned.
- **Publishing/serving specifics.** Content-negotiation implementation, w3id.org indirection for
  institution-independent URIs, and where canonical published artifacts live. Direction set in
  `docs/adr/0002`; details open.
- **Standalone vs installable packaging.** The app must run both embedded and standalone; whether
  the standalone mode ships as a demo project in-repo or separately is undecided.
