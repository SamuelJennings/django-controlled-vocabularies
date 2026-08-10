# Progress — 008 Run an import from the command line

Append-only. Each stage transition and gate outcome is written at the moment it happens, so a
crashed run resumes from fact rather than from inference.

## 2026-08-10 — S0 INTAKE

Issue [#52](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/52) claimed.
Dependency #50 checked: closed and merged, so nothing blocked. Sibling issues citing R2 read
(#49, #50, #51, all closed) to fix this feature's boundary against them.

Grilling agreed with the maintainer. Two decisions widened the issue as written:

- the source may be an `http`/`https` URL as well as a local file path, which #50 had put out of
  scope;
- the command exposes no target-vocabulary argument, and a source declaring no concept scheme is
  refused.

The second came with a wider instruction: the implementation so far has put too much weight on
guarding against what an operator might do, and that posture should be dropped across R2's
surface rather than only here.

Issue labelled `accepted`.

## 2026-08-10 — S1 SPECIFY

`specify` created branch `008-run-skos-vocabulary`, renamed to `008-import-from-command-line` to
match the family's spec-slug style. `spec.md` written: 6 user stories, 16 functional requirements,
6 success criteria. `clarify` taxonomy scan run over the draft and self-answered — 5 further
ambiguities resolved, recorded under `## Clarifications` and integrated into the requirements they
affect. Rationale too long to inline sits in `decisions.md` (D1–D9).

Spec lint green: every FR maps to a story, every story carries acceptance scenarios, the spec
cites G4 and G8, no unresolved markers.

## 2026-08-10 — S2 SETUP

Spec artifacts committed and pushed as `forge-aeo` (push actor = bot). #52 promoted to epic in
place, intake body preserved. Six story sub-issues created and linked: #78–#83, no lifecycle
labels, milestone v0.1.0. Draft PR [#84](https://github.com/SamuelJennings/django-controlled-vocabularies/pull/84)
opened bot-authored, title byte-identical to the epic, `Closes` block covering the epic and all six
stories, milestone v0.1.0.

`forge check-issue-titles` green.

Spec gate brief posted to #52 as a bot comment and sent to the maintainer.

## 2026-08-10 — Spec gate APPROVED

Approved by the maintainer in session, without changes to the spec or the story set. Recorded here
at the moment of approval, ahead of the ledger, so a crash between the gate and S3 cannot lose it.

## 2026-08-10 — S3R DESIGN REVIEW

One reviewer, three lenses, one round. Verdict `request_changes`, risk medium, seven findings, all
`verified`. Every one accepted and remedied in the artefacts before the plan notification; each was
re-checked against the code it cites first.

- **ARCH-001 (high) and SPEC-003** — `ReportRenderer` was US-4's, but US-3's rehearsal line is a
  flag on it and US-1 printed its own output for US-4 to replace, which would have meant editing
  another story's tests. T015 moved to Foundational, T003 renders through it from its first line,
  T019 deleted.
- **SPEC-002 (medium)** — US-2, US-3, US-4 and US-5 were declared independent while four of them
  edited `handle()`. US-4 no longer touches the command; the other three are now sequenced.
- **SPEC-001 (medium)** — verified in `skos.py:216-248` and `:1923`: every refusal names
  `str(path)`, so a fetched document's failures would have named a dead temporary file. Two lines
  added to T001, recorded in D10.
- **SEC-001 (medium)** — the redirect check ran on the response, i.e. after an `ftp://` redirect had
  already been connected and transferred. Replaced with an opener carrying no other handler.
- **SEC-002 (low)** — `urlopen`'s timeout is per read, not per transfer, and nothing bounded the
  fetch size. Byte ceiling added to T008.
- **SPEC-004 (medium)** — FR-003 and SC-002 name no serialization but only Turtle was to be proved.
  T001 now carries a relative-identifier fixture per serialization.
- **ARCH-002 (low)** — the temporary file's serialization-carrying suffix was never consulted.
  Dropped.

## Gates

- **Spec gate:** approved 2026-08-10 by SamuelJennings. No conditions.
