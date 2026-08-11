# ADR 0005 — A preview is the real operation rolled back, never a prediction of it

**Status:** accepted

## Decision

Any facility that shows what an operation would do, without keeping it, performs that operation in
full inside a transaction it then abandons. It never computes an answer by a separate path that
predicts the outcome.

The mechanism is an outer `transaction.atomic()` exited by raising a private sentinel that carries
the result out with it, caught immediately outside the block. The operation itself is not modified,
takes no flag, and learns nothing about being previewed.

The import command's `--dry-run` is the first instance.

## Why

The obvious alternative is to read the input, work out what would happen, report that, and never
touch the database. It looks cheaper, and it is wrong here for a reason specific to this codebase.

A large share of the outcomes a curator runs a dry run to discover are refusals raised by the
models themselves, at the moment of writing: a record whose address cannot be derived, a value the
field rejects on length, a stored address that no longer passes validation. A prediction that never
writes encounters none of them. It would report a clean run for a document that will not import,
which is the precise failure a dry run exists to prevent.

The general form of that argument is what makes this an ADR rather than one command's
implementation note. A prediction is a second implementation of the operation, and the two drift
apart the moment either changes — the classic decay of a preview that stops matching what it
previews. Running the real thing and discarding it means the report a dry run produces is
produced by the same code that produces a live one, so "the dry run matches the live run" is true
by construction rather than by two implementations agreeing on the day they were written.

It also makes the guarantee testable as an equality: a dry run and a live run against the same
starting state produce equal reports. Against a predictive implementation that assertion would be
comparing two things that are supposed to agree, which is a much weaker statement than comparing
one thing to itself.

The cost is real and was accepted: a dry run takes as long as the import and does the same
database work before throwing it away. For a vocabulary of any realistic size that is seconds, and
an operator who asked for a dry run has already accepted waiting.

One consequence has to be handled deliberately: because the two renderings are identical by
construction, a dry run's output must say so in its own text, or a reader scrolling back cannot
tell which kind of run produced the numbers in front of them.

## Revisit if

An operation appears whose execution has effects outside the database — a file written, a message
sent, a remote system called. A transaction does not roll those back, and a preview of such an
operation needs a different mechanism rather than this one applied hopefully.
