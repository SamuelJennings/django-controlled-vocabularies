# 18. A short form's prefix comes from the vocabulary's slug

Date: 2026-08-25

## Status

Accepted

## Context

A record's full identifier is always available, but a short form — a prefix and a local
part — is easier to read and write by hand. Nothing in the data model records a short
prefix for a vocabulary today. A vocabulary has a name, a slug, a description, a default
language, and an identifier, and none of those fields is a prefix a publishing community
would recognize.

Two ways to get a prefix were open. Store one explicitly per vocabulary, curated by
whoever manages it. Or derive one from a field the vocabulary already has. Slugs are
already unique across every vocabulary on the site, which is the property a prefix needs
in order to avoid two vocabularies' short forms colliding with one another.

## Decision

A record's short-form prefix is derived from the slug of the vocabulary holding it. It
is not stored as a field of its own.

## Consequences

No new field, no migration, and no curator responsibility to keep a prefix filled in and
correct as vocabularies are added. Deriving from a slug that already has to be unique
and already has to exist gets a working prefix at no additional cost.

The cost, accepted plainly: a vocabulary published elsewhere usually already has a
prefix its own community writes and recognizes, and this site shows its own slug
instead. Nothing is misidentified by this — the record's full canonical identifier is
disclosed on the page, and the short form's link still leads to the record — but the
short form printed here is not the one that community would write by hand.

This decision is superseded the day a vocabulary is given a real prefix field of its
own. A feature that adds one, and lets an imported vocabulary carry the prefix its
publisher actually uses, replaces the derivation this decision describes rather than
sitting alongside it.
