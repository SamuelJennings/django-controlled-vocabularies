# Decisions — 012 Concept selection inside the Django admin

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry records what was unclear, what was chosen, and why the choice is defensible.
Decisions taken *with* the maintainer live in `spec.md` under `## Clarifications`.

## D1 — The related-object affordances are refused, not merely absent

**Ambiguous**: Django's admin wraps a foreign-key or many-to-many field in a wrapper that offers to
add, change, delete and view the related record. It renders those buttons only when the related
model is registered in the admin and the person holds the matching permission, so today the
question is invisible: this package registers nothing, and the buttons never appear. It would have
been possible to write the specification to describe today's behaviour and say nothing.

**Chosen**: the specification requires the affordances to be absent *whatever* is registered, and
tests must prove it with the concept model registered and a superuser signed in.

**Why defensible**: the curator interface (R5) is an Essential goal in the same milestone. When it
registers the concept model, every consuming project's data-entry page would grow a "create a
concept" button, with no code changed anywhere and nobody looking. A requirement that only holds
because a precondition happens to be false is not a requirement, and the failure would arrive
inside an unrelated feature. This is the FR-004 / User Story 2 pair.

## D2 — The scope of "selection-only" covers all four affordances

**Ambiguous**: the maintainer's decision named creating a concept. The wrapper offers four things.

**Chosen**: none of the four render.

**Why defensible**: delete is strictly worse than add — removing a shared concept from the page of
a record that merely references it damages every other record using it, and the package's own
delete protection exists precisely because that must not be easy. Change has the same shape one
step down: editing a shared label from a data-entry form is authoring. View is the only benign one,
and it is refused for a different reason rather than a safety one: it opens the admin's own change
form for the concept, which is R5's to design and does not exist, and reading a concept's
definition is what the browsing interface in R6 is for. Shipping three of four and leaving one
pointing at a page that does not exist yet would be worse than a clean rule.

## D3 — An explicit `ModelAdmin` declaration wins silently

**Ambiguous**: a project naming the field in `autocomplete_fields` gets the admin's own autocomplete
instead of this package's control. That could be treated as a mistake worth reporting — the project
is passing up the feature — or as an instruction.

**Chosen**: an instruction. It wins, and nothing is reported.

**Why defensible**: Article II. A default that cannot be escaped is not a default, and a project
adopting the package should never have to audit its existing `ModelAdmin` classes first. The admin's
own autocomplete is a legitimate thing to want, and a warning that fired on a correct configuration
would be noise in `manage.py check` — the same channel the package uses for the three wiring
entries that genuinely are missing when it reports them. Diluting that channel costs more than the
warning could return.

## D4 — Inline rows added in the browser are in scope

**Ambiguous**: the issue says "admin add and change pages". An inline row created by clicking "Add
another" is neither, strictly — it is a copy of a hidden template row, made in the browser after
the page was delivered.

**Chosen**: in scope, and called out as a requirement of its own (FR-003).

**Why defensible**: excluding it produces a feature that demonstrates correctly and fails in use.
The rows rendered with the page are the records that already exist; the row someone adds is the one
they are entering. A control that initialises only at page load leaves an inert box in exactly the
place the person is working, and this is the single most common way a search-as-you-type control
integrated into the admin goes wrong. Naming it in the specification makes it a tested behaviour
rather than a discovered defect.

## D5 — The admin remains an optional dependency

**Ambiguous**: whether the package may now assume `django.contrib.admin` is installed.

**Chosen**: it may not. Nothing added by this feature may be imported at startup in a way that
requires the admin, no check may report on it in a project that does not have it, and the behaviour
must equally reach a project running its own `AdminSite`.

**Why defensible**: the consumption fields are for any Django project, and the admin is an optional
application in Django's own layering. A package that made it mandatory would break projects that
never asked for the feature, at startup rather than on a page. The custom-site half is the same
argument in the other direction: a feature wired only to `django.contrib.admin.site` would appear
to work in the test project and silently do nothing in a project that runs its own site, which is
common in exactly the research-infrastructure projects this package targets.

## D6 — Read-only presentation renders no control

**Ambiguous**: what a field in the admin's read-only list, or a page a person may view but not
change, should show.

**Chosen**: the concept's preferred label, no control.

**Why defensible**: it is what read-only means, and the alternative — a disabled control — invites
a person to type into something that cannot accept a change. The label is also the correct value to
show, because the field's readback is already part of the delivered contract.

## D7 — The changelist is excluded

**Ambiguous**: whether searching or filtering a consuming model's admin list page by concept
belongs here.

**Chosen**: no. The specification says so explicitly rather than leaving it unstated.

**Why defensible**: the issue names the add and change pages. A filter sidebar over a vocabulary of
tens of thousands of concepts is the same problem this feature exists to solve, one page along, and
it would need its own decisions about what a filter offers before anything is typed. Leaving it
unstated would have invited it into the implementation as an obvious extra.

## D8 — No admin-specific endpoint, and no second copy of the search rules

**Ambiguous**: the admin could plausibly have justified its own search view, closer to the admin's
own autocomplete conventions.

**Chosen**: it reuses the delivered endpoint unchanged.

**Why defensible**: Article III. Every rule about what a typed string matches, what a result shows,
how results are bounded and where the restriction comes from was settled in #88 and is enforced in
one place. A second endpoint would be a second copy of the security-relevant rule that the
restriction is derived from the field declaration rather than taken from the request, which is the
rule Article V cares about most here. One endpoint, one place to get that right.
