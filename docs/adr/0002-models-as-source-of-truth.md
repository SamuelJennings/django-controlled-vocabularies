# 2. Relational models are the source of truth; RDF is a projection

Date: 2026-07-22

## Status

Accepted

## Context

A vocabulary manager can hold its data as serialized RDF files, in a triplestore, or in relational
models. Predecessors kept vocabularies as RDF (in git, or in memory via rdflib) and repeatedly hit
the same walls: querying required deep RDF knowledge, large vocabularies (tens of thousands of
concepts, e.g. NASA GCMD) were awkward to load and search, and there was no natural home for
editing, permissions, or referential integrity.

## Decision

Store vocabularies as **Django models in a relational database**, which are the single source of
truth. RDF is a **projection** generated from the models by rdflib, only at the import/export
boundary. rdflib is not used for querying or in-memory representation.

## Consequences

- Everything Django is good at — forms, admin, CRUD, object permissions, indexed search,
  autocomplete, FK integrity, migrations — applies directly, via the django-mvp shell.
- Large vocabularies become ordinary indexed rows; performance is a database concern, solved
  structurally rather than with caching tricks.
- rdflib retreats to a thin serialization/parsing layer where its low-level nature is appropriate.
- Published RDF is **served by Django** at stable URIs via content negotiation. The serving
  mechanism (content negotiation details, w3id.org indirection, where canonical artifacts live) is
  a direction here; specifics remain open (see `GOALS.md`).
- The system is not a triplestore and exposes no SPARQL endpoint.
