# Decisions — 011 Choose a concept by typing instead of scrolling

Rationale too long to inline in `spec.md`, plus every ambiguity resolved without the maintainer.
Each entry names what was unclear, what was chosen, and why the choice is defensible.

## D1 — Search-as-you-type comes from an established third-party integration, not from custom code

**Status:** maintainer's recommendation, recorded at intake 2026-08-13 and qualified at the spec gate the same day. **Not binding — the research step decides.**

The maintainer stated the shape of the solution before specification began and asked that it be
carried into planning rather than discussed at intake:

- the feature calls for a select2-style custom form field, which he supports;
- he does not want custom selection logic written for it;
- he prefers an established third-party integration over anything hand-rolled;
- **`django-select2` is preferred against**, because it depends on select2, which depends on
  jQuery, and he avoids jQuery where he can;
- **`django-tomselect` is the candidate to evaluate first** as a newer alternative offering
  similar functionality.

The maintainer confirmed at the spec gate that this is a recommendation rather than an
instruction, and that research settles it. So the plan stage owes the candidate a real evaluation
against this specification's requirements, alongside the alternatives it is being preferred over — in particular FR-006 (the restriction is derived from
the declaration, never taken from the request), FR-007 (bounded, stable paging) and FR-002 (the
package carries the endpoint and the control resolves the project's chosen address) — plus
Article VII's dependency justification and the dual compatibility contract of Article VIII, which
constrains what Django and Python versions a dependency may drop. The jQuery objection stands whatever the evaluation concludes: it is a
constraint on the answer, not a preference to be traded away.

The research step names the choice with its evidence. If it lands anywhere other than the
recommended candidate, that goes to the maintainer with the reasoning rather than being decided
quietly, because he named a starting point and is owed the result.

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

## D7 — django-tomselect is adopted, and the evaluation was run against the wheel

**Status:** self-resolved at the plan stage, settling D1.

`research.md` evaluated django-tomselect, django-autocomplete-light and vendoring Tom Select behind
a view written here. It lands on django-tomselect, which is also what the maintainer recommended.
The reasons that decided it are not the recommendation:

- **One runtime dependency and nothing transitive.** Its own requirement is `django>=4.2.29`; the
  published metadata declares no other runtime package. Article VII has one thing to justify.
- **No jQuery anywhere.** Tom Select is a vanilla-JavaScript rewrite of Selectize, which is the
  reason it exists. DAL satisfies the constraint only by committing to its newer `dal_alight`
  backend and never touching `dal_select2`, which wraps select2 and therefore jQuery. A constraint
  honoured by remembering to avoid something is not honoured.
- **Closed by default where it matters.** Its view refuses anonymous requests unless told otherwise,
  and fixes the model, the searched fields and the returned fields on the view class where no
  request can reach them. DAL's base view gates nothing on GET and leaves both the filtering and the
  access decision to whoever writes the subclass.
- **A pagination contract that already survives abuse.** Page size is clamped server-side to 200
  regardless of what the request asks for.

**Against it:** effectively one maintainer, three years old, 87 stars against DAL's 1,870. That is
the real cost and it is worth naming plainly. What limits it is that this package's own code is four
method overrides and a `formfield()`. The vocabulary logic — which concepts a declaration allows,
how a concept is matched across three kinds of label, how it is displayed — is written here and
depends on nothing the dependency provides. Leaving would mean replacing the widget layer, not the
feature.

**The evaluation was re-run against the artefact.** `research.md` read the project's default branch
on GitHub. Every API fact the plan depends on was re-checked against the published wheel
`django_tomselect-2026.6.2-py3-none-any.whl`, because a plan built on a default branch is a plan
built on code nobody will install. D8, D9 and D10 are what that re-check changed.

## D8 — Both request-controlled surfaces are closed explicitly, against the library's default

**Status:** self-resolved.

The view accepts `filter_by` and an ordering field from the request. Both are validated against an
allowlist — `allowed_filter_fields` and `allowed_ordering_fields` — and both allowlists default to
`None`, which the library treats as "check that the named field exists on the model" rather than
"refuse". A hand-edited request can therefore filter or order by any field on `Concept`, including
ones outside what the endpoint returns. No value leaks, because the response is built strictly from
the declared fields, but a filter that can be applied and observed is a boolean oracle over the
model.

Both are set to the empty list here. The library checks them with `is not None`, so `[]` genuinely
refuses rather than falling back to the open default — verified in the wheel at
`autocompletes.py:500` and `:696`, not inferred from the documentation. FR-006 says the restriction
comes from the declaration and not from the request, and leaving a second request-supplied filter
open would satisfy that requirement in the letter while breaking it in fact.

**Amended after design review:** the two refuse differently, and the test has to say so. A rejected
`f=` discards the whole result set — `_apply_filter_list()` returns `None`, `apply_filters()` turns
that into `queryset.none()` (`autocompletes.py:597-603`), and it runs before `search()` (`:392-396`),
so the empty set survives the rest of the pipeline. A rejected `ordering` leaves the results in the
view's own order. The original wording asked for both to be "unchanged from the same request without
them", which is true of the second and false of the first, and a test written to it would have failed
on a guard that was working correctly.

## D9 — The endpoint-ownership requirement is met, and the research flag is resolved rather than carried

**Status:** self-resolved, closes a flag `research.md` raised.

`research.md` reported FR-002 as unmet by every candidate, on the grounds that neither ships an
includable `urls.py` and the consuming project must write the `path()` entry itself. That reads the
requirement one layer out from where it sits. The consumer of django-tomselect here is **this
package**, which is the party FR-002 requires to own the endpoint. The wheel shipping no URL
configuration of its own is precisely what leaves this package free to ship one.

So this package carries `controlled_vocabularies/urls.py`, a project includes it once under a prefix
of its own choosing, and the control resolves the URL *name* rather than a path. The requirement is
met as written. The flag was a real thing to check and the answer is that it does not bind.

## D10 — A project wires two things, not one, and the spec is amended to say so

**Status:** self-resolved, amends a requirement the maintainer approved. **Raised at the plan gate.**

`spec.md` promised that a project's only obligation outside the admin is including one route. That
promise cannot be kept. The dependency's templates and static assets live inside its own app
directory, and Django's app-directories template loader and static-files finder only look inside
installed apps, so `django_tomselect` has to be in the project's `INSTALLED_APPS` for the control to
render at all. No amount of work in this package moves that: an installed app is the mechanism by
which Django finds another package's templates.

Two honest options existed. Ship copies of the dependency's assets from this package, which trades
one line of a project's settings for a permanent obligation to track someone else's build. Or state
the second step. The second is taken.

What softens it is that the step is discoverable rather than remembered: the system check reports a
missing `INSTALLED_APPS` entry the same way it reports a missing route, so a project that has done
one and not the other is told, at check time, before a page is ever rendered. FR-002, FR-014 and
User Story 4 are amended to describe two steps. This is recorded here rather than absorbed quietly
because the maintainer read and approved the one-step promise.

## D15 — A project wires three things, and the third one fails silently

**Status:** self-resolved during implementation, amends the requirement D10 already amended.
**Raised at US-6.**

D10 corrected one wiring step to two. It is three. The third is
`django_tomselect.middleware.TomSelectMiddleware` in the project's `MIDDLEWARE`.

The dependency's widget builds the context that carries the control — the script that turns the
`<select>` into a search-as-you-type box — only when its own thread-local request is set, and
`TomSelectMiddleware` is the only thing in the package that ever sets it (`middleware.py` holds the
sole assignment to `_request_local`). Without it, `TomSelectModelWidget.get_context()` takes the
early return at `widgets.py:626-629` and hands back its base context.

Measured on this package's own `SampleForm`, against the installed wheel: 36,232 characters
rendered without the middleware against 67,519 with it, and the string `new TomSelect(` — the
instantiation itself — absent from the first and present in the second. A project that wires the
two steps D10 names gets an empty `<select>` and no error of any kind.

This one was found because T009 could not test its own subject without it, not because anything
failed. Nothing fails: no exception, no warning, no log line above debug level. That is what makes
it worth a decision record rather than a line in a commit message. It also means every render
assertion this feature had written until now was made against the degraded context, so none of them
would have noticed the control missing — `tests/test_forms.py` now asserts the instantiation is
present under an ambient request and absent without one, so the two states are distinguished rather
than assumed.

The remedy matches D10's: a third system check (`controlled_vocabularies.W004`) naming the exact
entry to add, so the step is discoverable at check time rather than remembered. `tests/settings.py`
now wires the middleware, so the test project matches a correctly wired real one. FR-002, FR-010,
FR-014 and User Story 4 are amended to describe three steps.

## D11 — The field reference is a plain dotted path, not a signed token

**Status:** self-resolved.

The control tells the endpoint which declaration it is searching for, as
`<app_label>.<model>.<field_name>`. Signing it would make tampering pointless rather than merely
ineffective, and the temptation is real because the parameter is the obvious place for a trusted-input
mistake.

It is not taken. The reference carries no restriction — it names a declaration, and the restriction
is read from that declaration on the server. Altering it can only name a different declaration,
whose own restriction is then applied, or fail to resolve, which returns an empty page identical to
every other failure. There is nothing a signature would protect. It would add key rotation, a longer
address and a second failure mode to explain, in exchange for guarding a value whose alteration
already achieves nothing.

The reason to record this rather than simply not do it is that "the browser sends an identifier, so
sign it" is a reasonable-sounding review comment, and the answer is a property of FR-006's design
rather than an oversight.

## D12 — The form's validation queryset comes from the widget, not from the endpoint

**Status:** correction, found in design review.

The first draft of A6 carried the field's restriction in one place: a `field=` parameter the control
appends to its own search requests, resolved server-side into `limit_choices_to`. That covers
searching and nothing else, and the gap is not cosmetic — it would have made the feature unusable.

The library's field replaces its own queryset during `clean()` from `self.widget.get_queryset()`
(`forms.py:210-215`). The stock widget walks back to the endpoint through `LazyView`, which builds
its request from `get_current_request()` — the ambient request in thread-local storage
(`lazy_utils.py:117`, `middleware.py:38`) — or, with no middleware installed, from a synthetic proxy
request carrying no parameters at all. During a form POST the ambient request is the page's own
submission, whose `GET` is empty under either branch. A6's fail-closed refusal, written for a
tampered reference, would therefore have been the state on *every* submission, and
`ModelChoiceField.to_python()` raises `invalid_choice` against an empty queryset. Nobody could have
saved a form.

The fix separates the two paths rather than making the reference reach further. This package's widget
overrides `get_queryset()` to build the restriction directly from the model field instance
`formfield()` already holds. Nothing is read from the request on that path, so FR-006 holds there by
construction, and it now holds on the write path as well — which the search-only design never did.
This is also what Django's unmodified `formfield()` does with `limit_choices_to`, so the behaviour
restored is the ordinary one rather than a new rule.

Two consequences are carried, not absorbed. Narrowing the widget's `get_queryset()` also narrows how
already-attached concepts are resolved for display (`widgets.py:965`), so FR-008 now needs an
explicit `_get_selected_options()` override — moved from a contingency in T009 to required work.
And T004 gains the assertion that would have caught this: submit a legitimate concept and confirm
the form saves.

The general shape is worth keeping. A restriction carried on the request path is invisible to every
other path, and a fail-closed default turns that invisibility into a total outage rather than a
quiet hole. The reviewer found it by reading the library's `clean()` rather than its documentation.

## D13 — `Concept.label` is not indexed for this feature

**Status:** self-resolved, recorded under Article XIII.

A7 puts `ordering = ("label", "pk")` on the endpoint, the first ordering path anything has placed on
`Concept.label`. Article XIII requires the indexing choice to be recorded either way, so: **no index
is added.**

The reasons. Every request that reaches this ordering has already been narrowed by a declaration's
`limit_choices_to` and, in the typing case, by an `icontains` match over a joined label table — the
sort runs over a small remainder, not over the table. US-5's "tens of thousands" is a whole-database
figure, not a per-request one. And an index on `label` alone would not serve the ordering tuple
anyway; matching it needs a composite `(label, pk)`, which is a migration in a package that ships
none in this feature.

What would change it: a measured page-fetch cost on a real vocabulary, or a request path that orders
by `label` without narrowing first. R7 owns the scale work and is where a benchmark belongs. The
composite index is the answer if one is ever needed, not `db_index=True`.

## D14 — A missing route reads the same at render time as at check time

**Status:** self-resolved.

FR-010 reports both wiring steps through the system check. US-4's independent test asks for something
slightly wider: a missing route should fail with a message naming what is missing rather than an
internal error. A project that ignores a check warning still reaches a render, and the library
re-raises `NoReverseMatch` verbatim there (`widgets.py:239-241`), which names a URL pattern and not
the thing to do about it.

This package's widget catches it and raises `ImproperlyConfigured` naming both steps. The alternative
was to narrow the spec's wording to the check path only, which would have been honest and left a
developer reading a traceback about a reverse match they never wrote. One `try`/`except` is cheaper
than that.
