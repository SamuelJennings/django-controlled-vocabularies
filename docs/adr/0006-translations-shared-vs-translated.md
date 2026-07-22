# 6. Translations: django-parler with a shared/translated split

Date: 2026-07-22

## Status

Accepted

## Context

SKOS labels and notes are language-tagged and often multi-valued per language (many `altLabel`s per
language). Per-object translation frameworks assume single-valued fields per language, which fights
SKOS. But some predicates (`notation`, mappings, URI-valued and typed literals) are
language-*independent* and must not be duplicated per language.

## Decision

Use **django-parler**, with the concept split into two JSON documents:

- a **shared document** on the base model — language-independent predicates; and
- a **translated document** inside parler's `TranslatableFields` — the language-tagged predicates,
  one document per language.

Routing is mechanical and applied automatically on import: **a literal with a language tag → the
translated document; everything else → the shared document.** Multi-valued labels are lists inside
the translated document, so SKOS's many-per-language labels fit without straining parler.

For the hot path, a `pref_label` column (the default-language prefLabel) is projected per `0005`
for autocomplete, ordering, and `__str__`.

## Consequences

- parler's shared-model/translated-model split reinforces RDF semantics instead of fighting them.
- UI language (Django i18n) and data language (parler) stay separate — a German-UI curator can edit
  English concepts.
- Residual cost: parler's editable language set is deploy-time config (`PARLER_LANGUAGES`).
  Importing a 24-language thesaurus into a 2-language deployment stores all languages, but *editing*
  the extra ones needs a settings change. Acceptable friction for FairDM deployments.
