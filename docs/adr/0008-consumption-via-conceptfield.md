# 8. Consumption via a relationship field, not choice iterables

Date: 2026-07-22

## Status

Accepted

## Context

The original motivation was integrating controlled vocabularies into Django as choice fields. But
Django's `choices=` iterable bakes vocabulary content into schema and code: adding a concept means
a code release of every consuming application, there is no referential integrity, and a choice
tuple cannot carry a concept's definition or URI.

## Decision

Consumption is a **relationship**, not a choice list. Provide a **`ConceptField`** (wrapping a
`ForeignKey` to `Concept`) and a **`ConceptsField`** (wrapping a `ManyToMany`), each constrained to
a scheme (via `limit_choices_to` / a validator) and rendered with an autocomplete widget from the
django-mvp stack. The plain choice-iterable style is deliberately dropped.

## Consequences

- Vocabulary evolution is a **data** operation: a curator adds a concept and every consuming form
  picks it up instantly — no deploy.
- Referential integrity, `PROTECT` on delete (`0004`), and access to the concept's definition/URI
  in forms and detail views all come for free.
- The trade-off — no simple choice-field style — is accepted: choices were always the wrong
  representation for an evolving, shared, richly-described vocabulary.
- Large vocabularies work as autocomplete-backed lookups against indexed rows, not in-memory lists.
