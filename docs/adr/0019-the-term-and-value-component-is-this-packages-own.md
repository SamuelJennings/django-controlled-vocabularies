# 19. The term-and-value component is this package's own

Date: 2026-08-25

## Status

Accepted

## Context

This package builds its pages on a shared user-interface package for layout and
controls. That package already ships a label-and-value component, which was the first
thing checked when a definition list needed a term-and-value display for a record's
properties. What it renders is a heading followed by a paragraph, not a definition list,
so there is nothing in it a definition list could reuse.

The choice this leaves is where a component like this one belongs: build it locally now,
or propose it to the shared package first and depend on a new release of it. This is a
package-boundary decision, and one this package will face again — the shared package
will not always already carry the piece a given feature needs.

## Decision

The term-and-value component belongs to this package. It is not proposed to the shared
package before it lands here.

## Consequences

The feature ships without waiting on another package's release cycle, and without
coupling this feature's timeline to the review and acceptance of a user-interface change
maintained elsewhere.

The component's shape gets to prove itself in real use before anyone commits to it as a
piece the shared package carries for every consumer. Promoting a proven component later,
once its API and rendering have been exercised by a real feature rather than designed in
the abstract, is the cheap direction: the alternative — proposing a component upstream
and then discovering in use that it needs to change — costs a second release cycle
instead of one.

This decision is expected to recur. Any future component this package needs, that the
shared package does not yet carry, follows the same path: build it here first, and
propose it upstream only once its shape has proved itself in a real feature, rather than
coupling this package's delivery to another package's release for every new piece of
interface.
