# Progress — 011 Choose a concept by typing instead of scrolling

Append-only record of stage transitions, gate outcomes and anything a resumed run must know.

## S0 INTAKE — 2026-08-13

Grilled from issue #88 against R3, its siblings (#86 and #87 delivered, #89 owns the admin,
#111 landed the shared vocabulary contract), `GOALS.md` and `CONTEXT.md`. Two decisions taken
with the maintainer: what a typed string matches, and what a consuming project must do to get
the behaviour. Both are in `spec.md`'s clarifications. Accepted; `accepted` label added to #88.

## S1 SPECIFY — 2026-08-13

`spec.md` written (7 user stories, FR-001..015, SC-001..007) and `decisions.md` started with six
entries. The clarify coverage scan raised five further ambiguities, all self-resolved, one of
which corrects an intake answer: matching cannot cover a concept's notation, because the model
has nowhere to hold one.

## S2 SETUP — 2026-08-13

Branch `011-choose-concept-by-typing` pushed as the bot. Issue #88 promoted in place to
`FS-011: Choose a concept by typing instead of scrolling`, seven story sub-issues created
(#116–#122) and linked, draft PR #123 opened bot-authored with the `Closes` block and the
`v0.1.0` milestone. `forge check-issue-titles` green.

## Spec gate — APPROVED 2026-08-13 by Sam (SamuelJennings)

Approved in session, with one amendment to the run's direction: **django-tomselect is a
recommendation, not a binding choice, and the research step decides.** `decisions.md` D1 updated
accordingly. No changes requested to the specification itself.

## Plan gate — restored to a real gate, 2026-08-13

The maintainer asked to inspect the plan before implementation begins. For this run the plan
notification is a **stop**, not a veto window: the run halts after the design review and waits for
an explicit go-ahead before any story is implemented. Silence is not consent here.

## S3 PLAN — 2026-08-13

`research.md` landed: three candidates evaluated (django-tomselect, django-autocomplete-light,
vendoring Tom Select behind a view written here), recommending **django-tomselect**, which is also
what the maintainer suggested. `django-select2` stays excluded — it wraps select2, which is a jQuery
plugin, and no configuration removes that.

**Every load-bearing API fact was re-verified against the published wheel `2026.6.2`** rather than
the project's default branch, which is what the research read. Three things changed as a result and
are recorded as D8, D9 and D10.

`plan.md` (A1–A10, five risks, three complexity entries) and `tasks.md` (T001–T011, mapped to the
seven story issues) written. `decisions.md` gained D7–D11.

**One amendment to the approved specification.** D10: a project wires two entries, not one. The
dependency's templates and static assets live inside its own app directory, and Django finds another
package's templates only in an installed app, so `django_tomselect` must be in `INSTALLED_APPS`
alongside the route include. FR-002, FR-010, FR-014, User Story 4 and the intake clarification are
amended in place rather than stretched, and the system check reports either step when it is missing.
This is on the plan gate because the maintainer read and approved the one-step promise.

## S3R DESIGN REVIEW — 2026-08-13

Dispatched: one reviewer, three lenses (spec compliance, security, architecture), one round.
`forge check-skills --role design_reviewer,design_reviewer_security,design_reviewer_architecture`
green before dispatch — craft-review, craft-security and craft-simplify all present, receipted and
on the allowlist.

**Verdict: request-changes, five findings, all five confirmed.** Receipts returned and matched
(`forge check-receipts` green): craft-review/2026-08-05/57b2f2f3, craft-security/2026-08-04/ea3d6742,
craft-simplify/2026-08-04/69038ce1.

Every finding was checked against the wheel's own source before it became work, rather than accepted
on the reviewer's severity. One piece of the critical finding's reasoning was wrong and the finding
still held: `BaseTomSelectModelMixin.__init__` does *not* discard a `queryset` kwarg — it warns and
then passes it to `super().__init__()` (`forms.py:156-188`), so the library's own warning text is
untrue. The defect binds one line later, at `clean()`, which overwrites `self.queryset` from the
widget regardless of what was passed. That is why the remedy is the widget override and not a
constructor argument.

| # | Lens | Severity | Confirmed | Disposition |
|---|---|---|---|---|
| F1 | security | critical | yes, and the remedy narrowed | D12 — validation queryset comes from the widget; A6 split into two paths; T004 and T009 rewritten |
| F2 | spec compliance | high | yes — `Concept.label` carries no index and no record of the choice | D13 — recorded as "not indexed", with the reason and what would change it |
| F3 | security | medium | yes — a rejected `f=` empties the queryset before `search()` runs | D8 amended; T007's assertion rewritten per surface |
| F4 | architecture | medium | yes — `hook_queryset()` is the documented pre-pipeline hook | A5, A6, T003 and T006 moved off `get_queryset()` |
| F5 | spec compliance | low | yes — `get_autocomplete_url()` re-raises `NoReverseMatch` verbatim | D14 — widget reframes it as `ImproperlyConfigured`; folded into T008 |

No finding was declined. F1 would have shipped a feature in which no form could be saved, and the
test that catches it (T004, `form.is_valid()` on a legitimate concept) did not exist in the first
draft of the task list.

**Waiting at the plan gate.** Nothing is implemented and nothing will be until the maintainer says go.

## Plan gate — APPROVED 2026-08-13 by Sam (SamuelJennings)

Approved after inspection at the hard stop, with no changes requested. The approval covers D10,
the one decision raised for him: a consuming project wires two entries rather than the one the
specification promised at the spec gate — the route, and the supporting package among its
installed applications. `spec.md`'s intake clarification carries the correction in place.

Implementation begins. Stories are implemented by dispatched subagents on the Sonnet tier, one at
a time, each in its own worktree, each verified here against evidence rather than assertion.

## S4 IMPLEMENT — US-0 (Phase F), 2026-08-13

T001 and T002 accepted. `django-tomselect` declared as a runtime dependency, the autocomplete
view and its route in place, answering nothing yet. The implementer's own checks read green while
`forge verify` did not: the dependency contract had been written to `tests/test_dependencies.py`,
which mirrors no source module and so fails the Article X conformance rule, and pre-commit does
not run conformance. Moved here to `tests/test_smoke.py`, the standing exception for a
package-level check (`4e2c0c3`). All five verify steps green afterwards.

## S4 IMPLEMENT — US-1 (#116), 2026-08-13

T003 and T004 accepted (`81a0fb4`, `6f1fbd5`). Results carry the identifier, the preferred label
and the vocabulary and nothing else, built on `hook_queryset()` and `prepare_results()` with no
`get_queryset()` override on the view (A5, A6). Both model fields bind this package's form field
and widget from the declaration alone, and the widget derives its validation queryset from the
model field instance rather than an ambient request — D12, the design review's critical finding.
The implementer reproduced that defect on the way through: with `formfield()` landed but before
the widget override, a legitimate concept failed with `invalid_choice`, exactly as predicted.

Verified here rather than accepted: full suite re-run at 1230 passed, `forge verify` green on all
five steps against `origin/main`, both craft receipts confirmed against the registry.

Two items came back with the report, and one of them was overstated.

- **The wheel's `TomSelectConfig.validate()` rejects its own enum.** `css_framework` is annotated
  `AllowedCSSFrameworks` and validated against `{f.value for f in AllowedCSSFrameworks}`, and the
  enum does not subclass `str`, so passing the member raises `ValidationError` while satisfying
  the type checker. Confirmed in the installed wheel (`app_settings.py:151`, `:585`). The member's
  `.value` is passed with a narrow `type: ignore` and the wheel line named in the docstring. This
  is a fourth documentation-versus-behaviour error in `django-tomselect`, on top of the three the
  plan already records.
- **A required `ConceptsField` has a pre-existing submission defect — narrower than reported.**
  The report claimed every submission fails, valid or not. Probed directly: creating a record
  works, because `_install_required_set_check` skips an instance with no primary key, and editing
  a record whose relation already has members works. The one failing path is editing a saved
  record whose relation is still empty, where `_post_clean()` runs `full_clean()` before
  `save_m2m()` and the check reads the database rather than the submission. That path matters —
  it is the one that would populate a record imported without concepts — so it is filed as #124
  against FS-010, with the measured behaviour per path. Nothing in this feature depends on it and
  the T004 tests use an optional `ConceptsField`, whose class docstring was corrected here to the
  measured behaviour rather than the reported one.

## S4 IMPLEMENT — US-3 (#118), 2026-08-13

T006 and T007 accepted (`9af5076`, `791b696`, plus the test repair below). The endpoint now derives what a
search may return from the field declaration a `field=<app_label>.<model>.<field_name>` reference
names, resolved through Django's app registry at `hook_queryset()`, and never from anything else
the request carries. The four refusal shapes — an unresolvable model, a field that is not one of
this package's, a field that does not exist, and no reference at all — return byte-identical
HTTP 200 empty pages, indistinguishable from a search that matched nothing. Both request-controlled
surfaces stay closed: a blocked `f=` filter empties the page, a blocked ordering parameter leaves
the view's own order in place.

The implementer ran a mutation probe per covered mechanism, as the US-3 brief required after US-2,
and one of its own probes caught a vacuous test on the way through: the allowlist test sent no
`field=`, so T006's own restriction emptied the queryset regardless of the allowlist. Repaired
before the report by sending an unrestricted reference first.

Verified here rather than accepted: full suite 1245 green, `forge verify` green on all five steps,
all three craft receipts confirmed against the registry.

**The report came back red, correctly.** Making a `field=` reference mandatory broke eight
pre-existing T003/T005 tests that call the endpoint bare. The behaviour is what the plan specifies
(A6 point 3, R3) and the browser always sends the reference, so the tests were stale rather than
the code wrong: they are about result shaping and label matching, and each now searches through
`Sketch.subject`, the declaration that names no vocabulary and so leaves every concept eligible.
The restriction is present but neutral, which keeps each assertion about its own subject.

**A seventh mutation probe found a gap US-2 left open.** Removing the active-language constraint
from the search filter altogether left all sixteen tests green: every case asserted that a label
in the active language *matches*, and none that a label in another language does *not*. A concept
whose German alternative label must not be found under English — and must be found under German —
now covers it. All six clauses of the filter (three label kinds, the default-language column, the
deduplication, the language constraint) fail at least one test when removed.

## S4 IMPLEMENT — US-4 (#119), 2026-08-13

T008 accepted (`d85085b`, plus the test repair below). A project missing either wiring step D10
requires now hears about it twice: `manage.py check` reports the absent route include
(`controlled_vocabularies.W002`) and the absent `INSTALLED_APPS` entry (`W003`), and a render that
gets past both warnings raises `ImproperlyConfigured` naming both steps rather than the library's
own `NoReverseMatch` against a URL pattern the developer never wrote. Neither check touches the
database, proven with `django_assert_num_queries(0)` rather than by reading the code.

**D14 named the wrong hook, and the implementer measured its way to the right one.** Against the
installed `django_tomselect` 2026.6.2 wheel, `TomSelectModelWidget.get_autocomplete_context()`
resolves the route twice while building one widget's context — once inside `get_search_lookups()`
(`widgets.py:1209-1216`, via `LazyView.get_url()`) before `get_autocomplete_url()`
(`widgets.py:225-241`) ever runs. Both re-raise `NoReverseMatch` verbatim and the earlier one wins,
so an override on `get_autocomplete_url()` alone never executes on a missing route. The mixin wraps
`get_autocomplete_context()` instead, the one seam both roads pass through, shared by both concept
widgets through the same MRO. The fifth documentation-versus-behaviour discrepancy this feature has
found in the library.

Verified here rather than accepted: full suite 1259 green after the repair below, `forge verify`
green on all five steps, both craft receipts confirmed against the registry.

**Two mutation probes of my own found gaps the implementer's nine left open**, both in the same
shape: a mechanism covered only where it is reached one way.

- **Neither check was registered in any test.** Deleting both `register()` calls from
  `apps.ready()` left all 1254 tests green — every check test called the function directly, so the
  functions were covered and the thing FR-010 actually promises, that a project is *told*, was not.
  `W001` had this covered all along through `test_silencing_the_check_id_suppresses_it`. Four tests
  now assert both ids through `call_command("check")`, present when the wiring is missing and
  absent when it is not.
- **The many-valued widget's render path was uncovered.** Removing `_ConceptWidgetRouteMixin` from
  `ConceptsWidget` alone left all 1254 green, because the render test used `SampleForm`
  (a `ConceptField`). It is now parametrised across `SampleForm` and `DepositForm`, so each widget
  class fails on its own.

Both mutations now fail at least one test. Five tests added, 1254 → 1259.
