# ADR 0009 — The search control is a dependency; the vocabulary logic is not

**Status:** accepted

## Decision

The search-as-you-type control is `django-tomselect`, added as a runtime dependency. This package
writes no selection widget, no browser code, and no pagination protocol.

What this package does write is the part that is about vocabularies: which concepts a declaration
allows, how a typed string is matched across a concept's preferred, alternative and hidden labels,
which single label is displayed, and what a result may contain. That is four method overrides on the
dependency's view, two widget mixins, and a `formfield()`.

A project wires three things once: include this package's URL configuration, add `django_tomselect`
to `INSTALLED_APPS`, and add its middleware to `MIDDLEWARE`. Each missing step is reported by a
system check.

## Why

The alternatives were `django-autocomplete-light`, and vendoring Tom Select's browser code behind a
view written here.

Three things decided it, none of them popularity:

- **Nothing transitive.** Its own requirement is Django. There is one thing to justify, and it drags
  in no second ecosystem.
- **Closed by default where it matters.** Its view fixes the model, the searched fields and the
  returned fields on the class, where no request can reach them. `django-autocomplete-light`'s base
  view gates nothing on a GET and leaves both the filtering and the access decision to whoever writes
  the subclass — which is to say, to this package, every time.
- **A pagination contract that already survives abuse.** Page size is clamped on the server whatever
  the request asks for.

There is also a standing preference against jQuery, which rules out `django-select2` outright. Tom
Select is a plain-JavaScript rewrite of Selectize and carries none.
`django-autocomplete-light` can satisfy that constraint, but only by committing to its newer backend
and never touching the select2 one it also ships, and a constraint honoured by remembering to avoid
something is not honoured.

The cost is real and worth naming: effectively one maintainer, and a fraction of
`django-autocomplete-light`'s users. What bounds that cost is the split above. The vocabulary logic
depends on nothing the dependency provides, so leaving would mean replacing a widget layer, not
rewriting the feature.

One process point belongs here, because it changed three decisions in this feature. The evaluation
was first run against the project's default branch on GitHub and then re-run against the published
wheel, and the two disagreed: documented extension points that do not run, a configuration enum that
fails its own validation, and a method that warns it ignores an argument and then passes it through.
A plan built on a default branch is a plan built on code nobody will install.

## Revisit if

The dependency stops releasing against a Django version this package supports, or acquires a runtime
dependency of its own that a consuming project would not otherwise carry. The replacement work is
the widget layer and the four view overrides, not the vocabulary logic — which is the shape this
decision was chosen to preserve.
