# ADR 0014 — Database collation differences are disclosed, not repaired

**Status:** accepted

## Decision

Where a search this package ships behaves differently on one supported database than on another,
and the difference comes from the database's own collation rather than from the query, the package
states the difference and does not attempt to level it.

Concretely, for the vocabulary search added with the browsing page: case-insensitive matching covers
ASCII letters on every database, and letters outside ASCII on PostgreSQL only. SQLite's `LIKE` folds
ASCII and nothing else, so a vocabulary named *Ökologie* is found by *ÖKOLOGIE* and not by
*ökologie*. The README says so where it describes the search, the requirement is written against it,
and a test pins each half so a change in either direction fails rather than passing quietly.

## Why

There is no repair available above the database. `icontains` compiles to `LIKE` on both backends,
and `Lower()` compiles to SQLite's own `LOWER()`, which folds ASCII for the same reason. What is
left costs more than the problem: registering a Python case-folding function on every SQLite
connection means a library reaching into a project's database configuration, and a stored normalised
column means a migration, a signal and a second source of truth for every searchable field.

Django itself takes this position for the same limitation, and documents it rather than working
around it.

The tidier-looking alternative is to narrow the requirement to whatever SQLite does and say nothing,
and it is worse than the difference it hides. A reader searching the lowercase form of a German
vocabulary's own name gets the no-match empty state, which looks exactly like a correct answer. A
limitation someone can read about costs them one surprise. A limitation they cannot read about
costs them the search.

Every search surface that follows this one inherits both halves, the behaviour and the duty to
state it. That covers searching concepts inside a vocabulary, and any later search across them.

## Revisit if

The package stops supporting SQLite for anything but its own tests, or PostgreSQL becomes a
requirement rather than one supported option. Either would remove the difference rather than repair
it, and the disclosure goes with it.
