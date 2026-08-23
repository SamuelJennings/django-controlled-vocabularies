# Progress — 014-look-inside-a-vocabulary

Append-only. Each entry is written at the moment the thing happened, not reconstructed afterwards.

---

## 2026-08-20 — Spec gate: APPROVED

Approved by SamuelJennings, in session, on the revised specification (the one with hierarchy
navigation removed).

The gate ran twice. The first request went out with four stories, the second of which navigated the
broader/narrower hierarchy one level at a time. The maintainer asked what "following a concept goes
to this page scoped under it" meant, and on reading the explanation removed hierarchy navigation from
the feature altogether: one flat, searchable list of every concept, and how concepts relate moves to
a concept's own page (#142). The specification, the four stories, the epic body and the pull request
description were re-synced before approval; `decisions.md` D2 and D3 are struck through in place
rather than deleted.

Approved scope, in one line: the page a vocabulary's address leads to — what it says about the
vocabulary, one flat list of every concept it holds, a search over that list, and the collections it
holds, with nothing on the page linking to an individual record.

Open at approval, and carried forward rather than resolved:

- A concept's notation cannot be searched, though the maintainer agreed at intake that it should be.
  Nothing stores one. Raised at the gate and approved with the gap.
- Rendering a vocabulary's identifier as a link is provisional and expected to be revisited once it
  has been seen working.

Surfaces: epic #141 · stories #150, #151, #152, #153 · pull request #154 · branch
`014-look-inside-a-vocabulary`.

---

## 2026-08-20 — Plan written (S3)

`plan.md`, `research.md` and `tasks.md` on the branch. 21 tasks across the four stories, run in
sequence: US-1, US-2 and US-4 all write the same page template, and US-2 and US-3 both write the
view's queryset behaviour, so parallel worktrees would collide at every convergence.

The two findings that shaped the plan and were not visible from the specification:

- **A vocabulary's address and the browsing app's mount have never been made to agree.** The address
  is composed from a setting; the mount is the project's choice; nothing compared them, because until
  now nothing served a page there. The demonstration is itself misconfigured today. The plan adds the
  route, a system check that reports the disagreement as a warning, and a corrected demonstration.
- **The search control still does not submit** on a page carrying search and no filter
  (django-mvp/django-mvp#282, open). The search itself works through the address. ADR 0015 governs:
  the defect is waited on, the affected tests are skipped naming the issue, and nothing is built
  around it — the same state #140 already ships.

No model change, no migration, and nothing in the `exchange` package is touched.

## Design review

Two findings, both verified against the code before being acted on, both applied to the plan and
the task graph:

- The queryset annotation naming a concept in the reading language was called `display_label`, which
  is already a public method on `Concept`. An annotation is set as a plain attribute, so a concept
  fetched through this view would carry a string where the rest of the package calls a method. The
  annotation is now `resolved_label` (D11).
- The new view was to be tested in a module of its own beside the existing one for the same source
  file. Its tests now join `tests/test_ui/test_views.py` as new classes (D12).

No task's scope changed. No change to the specification.
