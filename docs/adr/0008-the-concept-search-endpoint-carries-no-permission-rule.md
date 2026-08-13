# ADR 0008 — The concept search endpoint carries no permission rule

**Status:** accepted

## Decision

The search endpoint this package ships at `controlled_vocabularies/urls.py` serves any request that
reaches it. It sets `allow_anonymous = True` and defines no permission check of its own.

A project that must not serve concept data to some audience restricts the URL include — wrapping it,
mounting it behind a login-required prefix, or not including it at all. That is the lever, and the
README says so rather than leaving it to be discovered.

The endpoint is still bounded in what it can be made to return. A result carries a concept's
identifier, its preferred label in the active language, and its vocabulary's name, and nothing else.
The set of concepts it will search is derived on the server from the field declaration named in the
request, never from the request's own values, and both of the library's request-controlled surfaces —
`filter_by` and the ordering field — are closed with empty allowlists.

## Why

This package exists to publish vocabulary data. Concepts are already committed to being served at
stable public addresses with content negotiation, and a concept's preferred label is the least
private thing it holds. A permission rule here would guard, at one address, data the package is being
built to hand out at another.

Worse than redundant, it would mislead. A permission check on the search endpoint reads as a security
boundary around concept data. It is not one, and anybody who took it for one would be reasoning about
their project's exposure from a control that never covered the paths that matter.

The alternative considered was a default of "authenticated users only", on the reasoning that a
tighter default is a safer one. It fails on the same ground: the default would be wrong for the
common case — a public form on a public page, which is the case this feature was asked for — so
projects would turn it off, and the ones that did would have learned nothing about their real
exposure while doing it.

What does need guarding is the shape of the query, not the identity of the caller. An autocomplete
endpoint that lets the request choose what to filter on is a query surface over the model, and a
filter that can be applied and observed reveals values the response never prints. That is where the
restriction went: fixed returned fields, a server-derived concept set, and no request-supplied filter
or ordering at all.

Naming this in the specification and putting it in front of the maintainer, rather than inventing a
permission model this package has no basis to define, is how the constitution's rule against
fast-lane authorisation work is met here.

## Revisit if

Concepts gain a field that is not public — an editorial note kept internal, a draft label, a
per-project annotation. The endpoint's returned-field list is fixed, so such a field would not leak
by default, but the reasoning above rests on "everything a concept holds is publishable", and that
premise would no longer hold.
