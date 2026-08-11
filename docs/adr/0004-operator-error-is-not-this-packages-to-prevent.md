# ADR 0004 — Operator error is not this package's to prevent

**Status:** accepted

## Decision

Where an operator or a developer has already been trusted with an action, this package does not
add a mechanism whose only purpose is to stop them performing it incorrectly.

Concretely, in the surfaces reached so far:

- The import command takes a source and imports it. It offers no way to declare which vocabulary
  the operator expects, and therefore no way to refuse a run because the source turned out to
  contain a different one. Pointing a deployment script at the wrong address is the operator's
  mistake, and the result — a second vocabulary — is visible, inspectable and reversible.
- A source that declares no concept scheme is refused because it is not SKOS, not because the
  operator might have meant something else. The refusal states a fact about the document.
- The programmatic entry point keeps its target-vocabulary parameter, because a library caller has
  reasons to use it that a terminal operator does not.

This does not extend to input the operator did not author. A published document fetched from a
remote address is untrusted content, and everything protecting the process from it — the safety
scan, the scheme restriction on the fetch, the response size ceiling — stays. The distinction is
between guarding against the person driving the tool and guarding against what a third party sends
them.

## Why

The import surface had accumulated a habit of anticipating misuse. Two mechanisms existed solely
so that a caller who named the wrong target would be stopped, and the natural reading at the time
was to expose both at the command line, where operators would meet them most.

The maintainer's ruling was the opposite, and the reasoning generalises past the one command: the
implementation had put far too much weight on controlling what someone *might* do. A developer who
points the tool at the wrong file has made a mistake in their own deployment, and it is not this
package's responsibility to catch it.

Three things follow, and they are why this is worth an ADR rather than a note in one feature's
decisions file.

- **Every guard is permanent surface.** A flag exists forever, gets documented, gets tested, gets
  a translation, and constrains every later change to the thing it guards. It is not free because
  it is small.
- **A guard against a hypothetical caller cannot be validated.** There is no report of the failure
  it prevents, so nothing tells anyone whether the trade was worth it, and it never gets removed.
- **Defensive surface reads as required surface.** An operator meeting a `--vocabulary` flag
  reasonably concludes they are expected to use it, which makes the simple case look harder than
  it is.

The alternative position — that a published package should protect its consumers from themselves —
is defensible in general and is the one the code drifted into. It was rejected here on the specific
ground that these are mistakes with visible, reversible consequences inside a deployment the
operator controls, made by someone who already holds shell and database access. That is a
different risk class from untrusted input, which is why the boundary above is drawn where it is
rather than everywhere.

## Revisit if

The package grows a surface reachable by someone who is not the deployment's operator — a web
view, an API endpoint, or an editing interface used by a curator without shell access. Nobody on
the far side of such a surface is trusted by this decision, and the reasoning above does not
transfer to them.
