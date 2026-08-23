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
