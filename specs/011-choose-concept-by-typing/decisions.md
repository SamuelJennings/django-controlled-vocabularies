# Decisions — 011 Choose a concept by typing instead of scrolling

Rationale too long to inline in `spec.md`, plus every ambiguity resolved without the maintainer.
Each entry names what was unclear, what was chosen, and why the choice is defensible.

## D1 — Search-as-you-type comes from an established third-party integration, not from custom code

**Status:** maintainer's direction, recorded at intake 2026-08-13. Binding on the plan.

The maintainer stated the shape of the solution before specification began and asked that it be
carried into planning rather than discussed at intake:

- the feature calls for a select2-style custom form field, which he supports;
- he does not want custom selection logic written for it;
- he prefers an established third-party integration over anything hand-rolled;
- **`django-select2` is preferred against**, because it depends on select2, which depends on
  jQuery, and he avoids jQuery where he can;
- **`django-tomselect` is the candidate to evaluate first** as a newer alternative offering
  similar functionality.

This is a direction, not a decision already taken. The plan stage owes it a real evaluation
against this specification's requirements — in particular FR-006 (the restriction is derived from
the declaration, never taken from the request), FR-007 (bounded, stable paging) and FR-002 (the
package carries the endpoint and the control resolves the project's chosen address) — plus
Article VII's dependency justification and the dual compatibility contract of Article VIII, which
constrains what Django and Python versions a dependency may drop. If the candidate cannot meet
those, the finding goes back to the maintainer with the evidence rather than being worked around
quietly.

## D2 — Matching does not cover notation, though intake agreed it would

**Status:** self-resolved, corrects an intake answer.

At intake the maintainer confirmed that a typed string should match a concept's notation, so
someone who knows a code can type it. That was proposed on the strength of `CONTEXT.md`, which
defines **Notation** as a term of the domain. The model does not implement it: `Concept` has no
notation field, and the importer's own report enumerates a published `skos:notation` as a value
the models "have no place for" and did not store.

A requirement to match on a value no record holds is untestable and would be quietly vacuous. The
specification therefore covers the three kinds of label, and the correction is recorded in
`spec.md`'s clarifications rather than left as a silent narrowing of what was agreed. Notation
joins the search when a concept can carry one, which is the feature that adds it.

## D3 — The search endpoint carries no permission rule by default

**Status:** self-resolved.

The endpoint returns a concept's preferred label, its identifier and its vocabulary. G3 and R4
commit this package to serving concept data at stable public URIs with content negotiation, so a
default permission rule here would guard data the package is being built to publish, and would
mislead anyone who took it for a security boundary.

What the endpoint must not do is return more than the identified field would offer, which is
FR-006, and it must not become a general query surface over the project's models, which is why the
field reference resolves to one of this package's declarations or to nothing at all. A project
holding vocabularies it does not want read has one lever — the include — and the README documents
it rather than leaving it to be discovered.

Article V's "auth/authz is never fast-lane work" is honoured by naming the decision here and
putting it in front of the maintainer at the spec gate, rather than by inventing a permission
model this package has no basis to define.

## D4 — Accent folding is not promised

**Status:** self-resolved.

Whether a search for `e` matches `é` depends on the database's collation. The package supports more
than one database, so a promise of accent-insensitivity either holds on one and not another, or
forces a portable implementation nobody has asked for. Case-insensitivity is portable and is
promised. The specification says which is which rather than staying silent and letting a consumer
infer either.

## D5 — Ordering of results is stable, not relevance-ranked

**Status:** self-resolved.

FR-007 requires successive pages to neither repeat nor skip a concept, which needs a total order.
Relevance ranking — preferred-label matches before alternative ones, prefix before substring — is a
plausible improvement and is not required here: nothing in the issue asks for it, and it would make
the paging guarantee harder to state and to test. A stable order that a person can page through is
the guarantee this feature makes. If ranking is wanted, it arrives with R6 or R7, where searching
across vocabularies is the subject rather than a means.

## D6 — The missing route is reported by the existing system check

**Status:** self-resolved.

The package already contributes a system check that reports vocabularies a declaration names and
the database does not hold. Adding the missing-route report to it rather than inventing a second
mechanism keeps one place a developer looks, and matches how the absent-vocabulary case was handled
for the delivered fields. It stays a warning for the same reason that one is: a project mid-setup,
or one whose forms are not yet wired, is not broken.
