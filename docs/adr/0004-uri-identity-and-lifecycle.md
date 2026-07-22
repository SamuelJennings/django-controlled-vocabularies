# 4. The URI is identity; import upserts by URI; concepts have a lifecycle

Date: 2026-07-22

## Status

Accepted

## Context

Once downstream user data holds references (foreign keys) to concepts, those concepts stop being
disposable rows. Two failure modes follow: a re-import that deletes and recreates concepts breaks
or silently repoints every referencing row; and a curator deleting a concept that thousands of
records reference destroys data.

## Decision

- **Identity is the concept URI, never the database primary key.** The URI is immutable after a
  concept is first published; enforce it at the model layer. Labels may be renamed freely — the
  URI never moves.
- **Import upserts by URI.** Re-importing a vocabulary matches existing concepts on their URI and
  updates them in place. Never delete-and-recreate.
- **Concepts have a status lifecycle:** `draft` → `published` → `deprecated` (emitted as
  `owl:deprecated` on export). Referenced concepts are removed via deprecation, not deletion.
- **Referential integrity is enforced:** references to concepts use `on_delete=PROTECT`.

## Consequences

- User data survives vocabulary updates; FK references remain valid across re-imports.
- The database defends curators from destructive edits — but the editor must surface
  **deprecation** prominently, or curators will experience `PROTECT` as an obstacle.
- URI-immutability and upsert-by-URI are the load-bearing invariants of the whole design; they are
  tested first and violated never.
