# Progress — 013 Find a vocabulary

Append-only. Each entry: what happened, when, and the evidence for it.

## 2026-08-19 — Spec gate: APPROVED

Approved by Sam in session, on the epic (#140) plus story sub-issues #143 (US-1, P1) and #144
(US-2, P2), with `spec.md` and `decisions.md` on the branch. Gate brief posted as a comment on
#140 (comment 5345920852). Draft PR #145 open, bot-authored, milestone v1.0.0.

Two items raised and not folded into the feature: the goal G7 corner nobody fills (searching
concepts across vocabularies), and that "imported" is inferred from the identifier being fixed by
a publisher, which R4's publishing will complicate.

## 2026-08-19 — S3 PLAN

`research.md` read django-mvp v0.19.1 and django-literature's inner `ui` app against source.
`plan.md` and `tasks.md` authored: one new inner app behind a packaging extra, 14 tasks in three
phases (5 foundational, 5 for US-1, 4 for US-2). Ledger created and schema-valid.

Two findings from research that shape the plan: django-mvp's pagination preserves the query string
at 0.19.1 (so FR-010 needs a test, not a workaround), and its search action renders an input whose
form is defined by the *filter* action, so search alone cannot submit — worked around in our own
page template, to be filed upstream.
