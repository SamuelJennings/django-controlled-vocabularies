# ADR 0002 — A record's address is minted once and read back forever

**Status:** accepted

## Decision

A record's slug, and therefore its address on this site, is derived from its published identifier
at the moment the record is created, and is never derived again.

- The base comes from the identifier's own final segment: the fragment if the identifier has one,
  otherwise the last path segment. Nothing is derived from the record's name or label.
- A collision with a slug some other record already holds is resolved when the slug is minted, by
  appending a numeric suffix. The resolution is keyed on the identifiers involved, so reading the
  same file twice, in either order, produces the same slugs.
- A record the importer matches to one already in the database keeps the slug it already holds. It
  is read back from storage exactly as stored and handed to the write path unchanged. It is not
  recomputed, not re-collided, and not compared against what the current file would have produced.
- A record authored on this site, with no publisher identifier, keeps the older behaviour: its slug
  derives from its label and follows a relabel.

Because a stored slug now reaches the write path without being regenerated, it can no longer be
assumed valid. A value written around the model — `update()`, `loaddata`, `bulk_create`, a data
migration — is validated at the point of use and the record is set aside if it fails, rather than
letting the error escape the import.

## Why

An address that moves is a broken link, and the ways it can move are not obvious.

Deriving the slug from the name means a publisher who merely renames a concept moves its address
here. Deriving it from the identifier fixes that, but only for the first import. Recomputing on
every import reintroduces the problem from a different direction: collision suffixes are resolved
against whatever else currently occupies the vocabulary, and that set changes. Delete one of two
records whose identifiers end in the same segment, re-import the survivor's unchanged file, and its
address moves from `terms-2` to `terms` — a record's own address changing for a reason that has
nothing to do with that record.

Recomputing was *safe*, in that the base is a pure function of the identifier and never varies. It
was not *stable*, because the collision context around it does. The distinction cost four separate
defects across the import work before it was stated as a rule.

Two alternatives were weighed and rejected.

- **Recompute on every import and accept the movement.** Simpler, and defensible if addresses were
  private. They are not: they are URLs, they get bookmarked and cited, and a vocabulary is exactly
  the kind of resource other people link to.
- **Store the resolved collision order explicitly and replay it.** This keeps recomputation while
  making it deterministic, at the cost of a second stored thing that has to be migrated and kept
  honest. Reading back the slug that is already stored achieves the same result with nothing new to
  store.

## Revisit if

A curator needs to deliberately move a record's address — a rename tool, or a merge of two
vocabularies. That is a curatorial act and would need its own path, which this decision does not
provide and does not forbid.
