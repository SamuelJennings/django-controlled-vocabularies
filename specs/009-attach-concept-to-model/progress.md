# Progress — 009 Attach a concept from a chosen vocabulary to a model

Append-only. One line per stage transition and per gate outcome, written at the moment it happens.

- **2026-08-11 — S0 INTAKE.** Issue #86 grilled. One question asked and answered: what happens when
  a field names a vocabulary that has not been imported yet. Feature statement confirmed by the
  maintainer. `accepted` label added.
- **2026-08-11 — S1 SPECIFY.** Branch `009-attach-concept-to-model` created,
  `specs/009-attach-concept-to-model/spec.md` written (6 user stories, 12 FRs, 6 SCs), clarify run
  in full (1 intake clarification + 4 from the coverage scan, all self-resolved), `decisions.md`
  written (D1–D6). Spec lint green: every FR maps to a story, every story carries acceptance
  scenarios, G2 cited, no unresolved markers.
- **2026-08-11 — S2 SETUP.** Branch pushed as `forge-aeo` (bot). Issue #86 promoted to epic in
  place. Story sub-issues #90–#95 created and linked. Draft PR #96 opened bot-authored, title
  byte-identical to the epic, `Closes` block seeded for the epic and all six stories, milestone
  `v0.1.0`. `check-issue-titles` green. `stage-exit --stage S2` green.
- **2026-08-11 — GATE_SPEC: APPROVED by Sam.** Approved in session against the epic, its six story
  sub-issues, and `spec.md` on the branch. Gate brief posted as a bot comment on #86
  (`issuecomment-5253525466`), carrying the five self-resolved ambiguities and the one open risk
  (Article IX still describing a per-concept lifecycle that #19's ruling superseded — R4's to
  reconcile). No conditions attached. Proceeding to S3 PLAN.
- **2026-08-11 — S3 PLAN.** `research.md` R1–R7 (every finding verified against Django's own source
  in the project virtualenv, not documentation), `plan.md` with the Constitution Check clean and no
  Complexity Tracking entries, `tasks.md` T001–T013 across a foundational phase and the six stories,
  `feature-state.json` generated. Cross-artifact analyze: all 12 FRs and all 6 SCs map to at least
  one task, every story maps to its issue, no unresolved markers. No spec amendment needed — the
  research confirmed the spec rather than contradicting it. Next: S3R design review.
- **2026-08-11 — S3R DESIGN REVIEW.** One reviewer, three lenses, one round. Security `approve`
  (0 findings), architecture `approve` (0 findings), spec-compliance `request_changes` (1 high,
  2 medium, all `verified`). All three spec-compliance findings independently re-verified against
  the installed Django 5.2.16 source and `tests/test_standards.py` before being accepted, and all
  three applied as plan edits:
  - **SPEC-001 (high).** `ForeignKey.validate()` builds its own `params` (`model`, `pk`, `field`,
    `value`), and `ValidationError` interpolates at iteration time, so T001's planned
    `%(vocabulary)s` message would raise `KeyError` the moment T005's own test read it. T001 now
    carries a `validate()` override that re-raises with `params={"vocabulary": ...}`; T005 reworded
    — the constraint needs no new code, the message does.
  - **SPEC-002 (medium).** `plan.md` called US-3/US-4/US-5 independent while four stories write
    `tests/test_fields.py` and three write `fields.py`, which collides across worktrees. Approach
    section now states the real dispatch order: US-1/US-2 → US-3 → US-5 in sequence, US-4 the only
    parallel story.
  - **SPEC-003 (medium).** T012 reused `tests/test_standards.py`'s visitor, whose four sinks match
    nothing a field or check contains — it would have reported zero regardless. T012 now names the
    sinks (`help_text`/`verbose_name` kwargs, `error_messages` values, bare strings into
    `ValidationError`/`checks.Warning`/`checks.Error`) and requires the gate be proven against a
    reinstated bare literal.
  - Two citation drifts in `research.md` corrected in passing (R1's `formfield` line reference,
    R3's `Tags.database` skip mechanism — a per-check `if databases is None: return []` convention,
    not registry filtering). Neither changed a conclusion.
  Reviewer ran on Sonnet rather than Opus (dispatch omitted the model override). Findings judged on
  merit and all three verified true at source, so no re-run. Next: plan veto notification, then S4.
- **2026-08-11T00:00:00Z · Implementer Phase F · T001.** Did: added `controlled_vocabularies/fields.py`
  with `ConceptField(ForeignKey)` — fixes `to=Concept`, `on_delete=PROTECT`,
  `limit_choices_to=Q(scheme__slug=vocabulary)`; rejects a consumer-supplied `on_delete` and a
  missing/empty `vocabulary`, both `TypeError`; overrides `validate()` per the design review's
  SPEC-001 finding so `.messages`/`str()` interpolate `vocabulary` instead of raising
  `KeyError: 'vocabulary'`. Verified: `poetry run pytest -q tests/test_fields.py` — 13 passed,
  including a test that reads `.messages` and one that reads `str()` on the raised
  `ValidationError`, and a `CaptureQueriesContext`-wrapped construction asserting zero queries.
  Independently reproduced the pre-fix `KeyError` against a copy of the field with the `validate()`
  override removed, to confirm the test actually exercises SPEC-001 rather than merely asserting
  `ValidationError` was raised. `ruff check`/`ruff format` clean. Next: T002. Watch: none.
- **2026-08-11T00:20:00Z · Implementer Phase F · T002.** Blocked before writing any test-app code.
  T001's construction-time rejections (`on_delete` in kwargs → `TypeError`; empty/missing
  `vocabulary` → `TypeError`) make `ConceptField` impossible to round-trip through Django's own
  field-state machinery without `deconstruct()` (T003, US-1, explicitly out of scope for this
  phase — "Phase F builds the field's construction and the test app; those stories build on it").
  `Field.clone()` — `self.__class__(*args, **kwargs)` from `self.deconstruct()` — is called by
  `ModelState.from_model()` on *every* command that builds Django's migration state
  (`makemigrations`, `makemigrations --check`, `migrate`, and pytest-django's own migration
  application to build the test database), not only when writing a new migration file. Verified by
  reproduction: built a throwaway app (`tests/_probe_testapp`, never committed, removed after)
  with one model carrying `ConceptField(vocabulary="rock-type")`, added it to a scratch settings
  module, and ran `django-admin makemigrations _probe_testapp` against this worktree's installed
  Django 5.2.16 —
  ```
  TypeError: Couldn't reconstruct field rock_type on _probe_testapp.Specimen: ConceptField()
  requires a non-empty 'vocabulary' naming the ConceptScheme slug to constrain choices to.
  ```
  raised from `field.clone()` inside `ModelState.from_model()`, before a migration file is even
  written — `ForeignKey.deconstruct()`/`RelatedField.deconstruct()` emit `to`, `on_delete` and
  `limit_choices_to` (confirmed against the installed source, matching `research.md` R2) but never
  `vocabulary`, since T001 does not override `deconstruct()`. So any model carrying `ConceptField`
  cannot pass through `makemigrations --check` or `migrate` — including the migration T002 itself
  requires — until `vocabulary` survives that round trip. Adding `tests/testapp` to
  `INSTALLED_APPS` in this state would turn pytest-django's own migration application red for the
  whole suite (1006 tests), which the story's baseline-verify and "leave the tree green" rules both
  forbid building on top of. No workaround attempted — implementing any form of round-trip
  survival (a `deconstruct()` override or an equivalent `clone()` override) is T003's named scope,
  dispatched to a separate worktree; doing it here would be exactly the prohibition this protocol
  says to report blocked against rather than route around. Nothing committed for T002; worktree
  left clean. Next: Forge to resolve the phase's task ordering (T003's `deconstruct()` — or an
  equivalent minimal fix — needs to land before or inside Phase F, not after it). Watch: this also
  blocks every one of US-1 through US-6, since Phase F is a hard dependency for all six.
