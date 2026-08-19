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

## 2026-08-19 — Design review: CHANGES REQUESTED, then applied

Three lenses over the design artefacts, no code. Six findings, all verified against django-mvp
v0.19.1 source before acting on them. All six applied to `plan.md` and `tasks.md`:

- **FR-009 was unreachable through the mechanism the plan chose** (high). django-mvp's empty-state
  component renders heading and message as autoescaped strings with no slot, so the required "back
  to the full list" link could not live in the message — and the shortest repair, `mark_safe` over
  a string that also echoes the search term, would have emitted an unescaped attacker-supplied
  term. The link now renders in the actions block T011 already owns; both empty-state methods
  return plain text, and T013 asserts on the escaped form.
- **`django_tables2` in the test settings** would have broken collection of the whole suite —
  it is not a django-mvp dependency, `--extras ui` does not install it, and `tests/settings.py` is
  the repo-wide settings module. Dropped, along with the inert `SITE_ID`.
- **The `[tool.forge.conformance] non-mirror-paths` declaration the plan promised** had no task
  creating it. T001 now writes it, naming the four files rather than the directory.
- **django-mvp's search submit button ships a hard-coded English label** its component exposes no
  variable for, which made SC-006 false. T011 renders our own translated button.
- **US-1 and US-2 are not independent** — same view module, same page template, same test module,
  and T011 rewrites the block T006 writes. They now run in sequence, and T011's dependency points
  at T009 rather than through a documentation task.
- **Ordering moved from `get_queryset()` to the `ordering` class attribute**, so it applies ahead
  of the search mixin's `.distinct()` rather than after it — the operand order upstream's own
  docstring says its mixin order exists to avoid, and one this SQLite-only suite could not catch.

Three editorial notes also applied: `paginate_by = 24` restated an inherited default and is gone;
search is multi-word OR, so a second word widens the list, which T014 now documents; and the
`tests/test_ui/conftest.py` in the plan's tree was unwanted, since the root conftest already
exposes the `scheme` fixture.
