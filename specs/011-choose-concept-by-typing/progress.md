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
