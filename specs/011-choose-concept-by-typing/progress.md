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
