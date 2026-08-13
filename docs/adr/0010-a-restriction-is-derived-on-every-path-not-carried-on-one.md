# ADR 0010 — A field's restriction is derived on every path, not carried on one

**Status:** accepted

## Decision

Which concepts a field allows is derived from the field's own declaration, separately, on each path
that needs it:

- **Searching.** The endpoint reads the declaration named by the request and applies that
  declaration's `limit_choices_to`.
- **Validating a submission.** The widget builds its queryset from the model field instance it was
  handed at construction, with no request consulted at all.
- **Displaying what a record already holds.** Neither restriction applies. An attached concept is
  rendered under its preferred label even when the declaration no longer names its vocabulary.

The request carries a *reference* to a declaration — `<app_label>.<model>.<field_name>` — and never
a restriction. The reference is a plain dotted path, not a signed token. Altering it can only name a
different declaration, whose own restriction is then applied, or fail to resolve, which returns an
empty page shaped exactly like a search that matched nothing.

## Why

The first design carried the restriction in one place: a parameter the control appends to its own
search requests. It covered searching, and it broke everything else.

The library's form field rebuilds its validation queryset during `clean()` from the widget, and the
stock widget walks back to the endpoint through whatever request is ambient. During a form
submission that request is the submission itself, whose query string carries no such parameter. The
fail-closed refusal written for a tampered reference would therefore have been the state on every
single save, and the form would have rejected legitimate concepts as invalid choices. Nobody could
have saved a record. It was found by reading the library's `clean()` before any code was written.

The general shape is what makes this an ADR rather than a bug fix. A restriction carried on one path
is invisible to every other path, and a fail-closed default turns that invisibility into a total
outage rather than a quiet hole — which is the better of the two failures, and still a feature that
does not work. Deriving from the declaration on each path costs one small method per path and cannot
develop a gap, because there is no shared carrier to be missing.

It is also what Django already does. An ordinary `ModelChoiceField` narrows itself from
`limit_choices_to` without anything travelling over the wire, so what this restores is the plain
behaviour rather than a rule of our own.

Signing the reference was considered and declined. There is nothing a signature would protect: the
value names a declaration and grants nothing, so tampering with it is already ineffective rather than
merely detectable. A signature would add key rotation, a longer address, and a second failure mode to
explain, in exchange for guarding a value whose alteration achieves nothing. This is recorded because
"the browser sends an identifier, so sign it" is a reasonable-sounding review comment, and the answer
is a property of the design rather than an oversight.

The display path is separated deliberately. Narrowing what a submission may contain is a rule about
new values. Refusing to show a value a record already holds is data loss on the next save.

## Revisit if

A field gains a restriction that cannot be expressed as `limit_choices_to` — one depending on the
requesting user, or on the object being edited. The declaration would no longer be a complete source
for every path, and this decision assumes it is.
