# Progress — 004-collections-group-concepts

Append-only narrative log. The ledger (`feature-state.json`) is the source of truth for state; this is
the human-readable trail.

## 2026-07-25 — S0→S3

- **S0 grill.** Confirmed with Sam: no nested collections (members are concepts only); ordered is a
  property of the collection. Caught and corrected a scope divergence — the intake framing named the
  Django admin, but the three sibling R1 slices are all programmatic-only (admin deferred to R5); Sam
  chose to align Collections with them. Issue #18 swapped `feature-request` → `feature`.
- **S1 specify.** `spec.md` written (5 user stories, FR-001..012, SC-001..011), spec-lint green.
  Self-resolutions logged in `decisions.md` (D1–D6).
- **S2 setup.** Branch `004-collections-group-concepts` pushed; #18 promoted to epic `FS-004`; story
  sub-issues #42–#46 created and linked; draft PR #47 opened (bot-authored, milestone v0.1.0, `Closes`
  block for the epic + all five stories); title lint green. **Spec gate approved by Sam.**
- **S3 plan.** Two-model design (`Collection` + `CollectionMember` through model), hand-rolled
  `position` ordering. **Evaluated Sam's suggested `django-ordered-model` and rejected it** — last
  release March 2023, no Django 5.2/6.0 support, which CI requires (research R5, plan Complexity
  Tracking, decisions D7). `plan.md`, `research.md`, `data-model.md`, `contracts/python-api.md`,
  `quickstart.md`, `tasks.md` (T001–T015) written; analyze prerequisites green; `feature-state.json`
  created (all tasks `todo`, Spec gate recorded). **Awaiting the Plan gate.**
