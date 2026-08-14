# ADR 0012 — An explicit declaration wins, and nothing is reported

**Status:** accepted

## Decision

Where a project's `ModelAdmin` makes its own choice for a concept field — naming it in
`autocomplete_fields` or `raw_id_fields`, listing it in `readonly_fields`, or declaring a widget or
form of its own — that choice renders, and no check or warning is raised about it.

Every guarantee the field itself makes holds whichever control renders: the vocabulary constraint,
the delete protection, the required rule, and the label and identity readback. The refusal of the
related-object links in ADR 0011 also holds for whatever is rendered in place of the default.

## Why

A default that cannot be escaped is not a default. A project adopting this package should not have
to audit its existing `ModelAdmin` classes first, and the admin's own autocomplete is a legitimate
thing to want.

Treating the declaration as a mistake was the alternative, reported through `manage.py check`. That
channel already carries the three wiring entries a project genuinely is missing when they are
reported. A warning that fired on a correct configuration would dilute the one channel that has to
stay believable, which costs more than the warning could return.

## Revisit if

A future declaration form turns out to defeat one of the field's own guarantees rather than merely
changing what renders. That would be a correctness problem rather than a preference, and it belongs
in a check.
