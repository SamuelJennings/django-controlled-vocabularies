# ADR 0003 — A report reason names an outcome, and its message must be true on every path that reaches it

**Status:** accepted

## Decision

An import report draws every reason from a closed vocabulary, and each member obeys two rules.

- **A reason names an outcome, not a cause.** Two situations share a reason when they leave the
  curator in the same position, even if the code reached them differently. They get separate
  reasons when the remedy differs — a value lost from a record that still exists is not the same
  outcome as a record dropped in full, and a run that was refused is not the same outcome as either.
- **A reason's message must hold at every call site that raises it.** Adding a call site means
  re-reading the message against the new path. If the message would be false there, either the
  message changes to something true of both, or the new path gets its own reason.

A message that names a cause is the failure mode this exists to prevent, because a cause is what
goes stale when the code around it changes. Prefer wording that describes what happened to the
record.

## Why

Every one of these was found the same way: a message that had been correct when it was written,
read out loud on a path added later, and found to be false.

- A set-aside reason blamed the record's preferred label for an unusable address. That was true
  when addresses derived from labels. Once they derived from the published identifier, the message
  sent a curator to correct a value that was not at fault — and later, when the same reason was
  raised for a collision the importer could not resolve, nothing the publisher wrote was at fault
  at all.
- A refusal said a vocabulary published no name, on a path where a name was published and was
  merely unusable.
- A refusal said a name was longer than could be stored, on a path where nothing was published.
- A reason meaning "this value was not stored" was raised for a record that was never created, so
  the curator was told about a field when the whole record was missing.

Four instances, four separate review rounds, one shape. The pattern is that a message is written
against the single trigger in front of the author, and then inherits call sites that nobody
re-reads it against.

The alternative — one reason per code path, each with a narrowly accurate message — was considered
and rejected. It makes the vocabulary grow with the implementation rather than with what a curator
can actually do about the problem, and callers that group and count would then have to know which
paths are equivalent. The closed vocabulary exists so they do not.

## Revisit if

A caller genuinely needs to branch on *why* an outcome occurred rather than on what it was. At that
point the distinction has earned a place in the vocabulary and should be added as its own reason,
not smuggled into the message text of an existing one.
