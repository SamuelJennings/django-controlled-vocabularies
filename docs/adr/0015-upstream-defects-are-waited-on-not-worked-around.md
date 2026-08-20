# 15. Upstream defects are waited on, not worked around

Date: 2026-08-20

## Status

Accepted

## Context

This package's browsing interface renders through django-mvp, which supplies the page shell, the
list layout, the search control and the pagination. The contract is that a consuming package
supplies its own row and nothing else.

Building the vocabulary list surfaced a fault in the shipped search control: its input and its
submit button carry a `form` attribute naming an element that only the filter control defines, so a
page rendering search without a filter has a search box associated with no form. Two smaller faults
sit beside it — the submit button's label cannot be translated, and the box prefills from the raw
query value rather than the stripped one.

Each has an obvious local repair: override the page template and supply the missing pieces. The
first version of this feature did exactly that, and every requirement passed.

## Decision

We do not override an interface package's templates to route around a defect in it. We report the
defect upstream, and we disable the tests that depend on the fix — each naming the upstream issue
and the condition that re-enables it.

Where the shortfall is visible to someone using the package, we say so in the documentation rather
than leaving them to discover it.

## Consequences

A released version of this package may be missing something its specification asks for, with the
gap named in its documentation. That is the cost, and it is deliberate.

What it buys is that the fix, when it arrives, is adopted by upgrading — not by finding and
deleting a workaround nobody remembers. An override is invisible once it works: no test fails when
the upstream fix lands, nothing reports that a local copy of someone else's markup is now stale,
and the copy quietly diverges from the thing it was copied from. A skipped test is the opposite. It
appears in every test run, it carries its own reason, and it turns back into coverage the moment the
dependency ships.

The wider point is about what an interface package is for. django-mvp exists so that the projects
built on it do not each maintain their own version of its markup. A consumer that overrides a
template to fix a bug has taken on a piece of django-mvp's job permanently, and has made its own
next upgrade harder. If enough consumers do it, the shared interface has stopped being shared —
and the defect stays unfixed upstream, because everyone downstream has already worked around it.
