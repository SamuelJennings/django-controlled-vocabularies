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
- **2026-08-11T00:40:00Z · Implementer Phase F · T003.** Forge moved T003 (`deconstruct()`) into
  Phase F ahead of T002 (`tasks.md`/`plan.md` commits `565724b`, `06d4776`) after verifying the
  T002 blocked report at both cited source lines. Did: `ConceptField.deconstruct()` strips `to`,
  `on_delete`, `limit_choices_to` and adds `vocabulary`. First attempt paired it with a `clone()`
  override that stringified `to` only for that call site; this fixed `makemigrations`
  (`ModelState.from_model()`'s autodetector path) but not `migrate` — reproduced with the same
  probe app, this time via `django-admin migrate` against a scratch sqlite DB, which failed at
  `CreateModel.state_forwards()` building `ModelState` from the migration operation's own,
  freshly-`__init__`-constructed field (not a `clone()`), hitting the identical
  `ModelState.fields cannot refer to a model class` `ValueError`. Reported as a new finding per
  instruction rather than patched further. Directed fix: `to` is the string
  `"controlled_vocabularies.Concept"`, set unconditionally in `__init__`, `clone()` override
  removed (the default `Field.clone()` now works unmodified), and the `Concept` import dropped
  from `fields.py` entirely. Accepted consequence: an unbound field cannot run `validate()`
  (`remote_field.model` only resolves once `contribute_to_class` binds the field to a real model),
  so T001's `TestConceptFieldValidate` class (3 tests reading `.messages`/`str()`/`.code` on an
  unbound field) no longer has anything to construct against and was deleted; `test_fixes_to_concept`
  now asserts the string form. That behavioural proof is T005's, against a real test-app model —
  not this task's. `tasks.md` already carries this as the design record (commit `06d4776`).
  Verified: `poetry run pytest -q tests/test_fields.py` — 14 passed (11 construction/deconstruct +
  3 removed from validate). End-to-end reproduction against the probe app (never committed, removed
  after): `django-admin makemigrations` produces a clean migration
  (`ConceptField(help_text=..., vocabulary='rock-type')`, none of the three stripped kwargs, no
  `to`); `django-admin migrate` against a scratch sqlite DB applies cleanly; `makemigrations
  --check --dry-run` reports "No changes detected", exit 0; and a bound `Specimen.full_clean()`
  against a concept from the wrong vocabulary raises `ValidationError` whose `.messages` reads
  `"2 is not a valid concept in the 'rock-type' vocabulary."` — the `validate()` override works
  correctly once bound, exactly as T005 will prove. `ruff check`/`ruff format` clean. Next: T002.
  Watch: `feature-state.json`'s `US1.tasks` still lists `T003` (not moved to `US0` alongside T001/
  T002) — the ledger wasn't restructured when the plan moved the task; flagged in `concerns` rather
  than restructured, since moving a task between story blocks is outside "flip your own tasks'
  status/attempts/evidence."
- **2026-08-11T01:00:00Z · Implementer Phase F · T002.** Unblocked by T003's corrected fix. Did:
  new `tests/testapp/` (`apps.py`, `models.py`, `migrations/0001_initial.py`), added to
  `INSTALLED_APPS` in `tests/settings.py`. Three models: `Specimen` (required `ConceptField`,
  vocabulary `"rock-type"`), `Sample` (optional, `related_name="samples"`, vocabulary
  `"mineral"`), `Artifact` (optional, vocabulary `"mineral"`, and already defines
  `get_mineral_label()` — the exact name T011's `contribute_to_class()` would generate for a field
  named `mineral` — so that story's collision guard has a real pre-existing definition to test
  against). Factories (`SpecimenFactory`, `SampleFactory`, `ArtifactFactory`) added to
  `tests/factories.py`. Two vocabulary fixtures (`multilingual_scheme`, `single_language_scheme`)
  added to `tests/conftest.py` for #87/#88/#89 to reach without redefining, named for what they
  are rather than for this feature. Verified: `poetry run pytest -q tests/test_testapp.py` — 9
  passed (`TestMigrations` — tables queryable after migrating from zero, `makemigrations --check
  --dry-run` exits normally rather than raising `SystemExit(1)`; `TestFactories` — the three
  factories build valid saved records; `TestVocabularyFixtures` — the two scheme fixtures build
  the shape their docstrings promise). Full suite: `poetry run pytest -q` — 1029 passed (1020 +
  9). `poetry run pre-commit run --all-files` — all hooks green (trim-whitespace, end-of-file,
  check-yaml, poetry-check, ruff lint, ruff format, mypy, deptry). Deliberately not tested here:
  declaring/saving/reading back a concept through the field, the reverse accessor, `null`/`blank`
  behaviour — that is T004's (US-1) acceptance, against a real model, not T002's. Phase F (T001,
  T003, T002) complete; worktree clean, all three tasks committed.
- **2026-08-11 — S4 Phase F accepted.** T001, T003, T002 on `009-phase-f`, merged to the feature
  branch at `f36510e`. `forge verify` green (lint, typecheck, 1029 tests, build, conformance),
  `check-receipts` green, tamper-check's three flags all confirmed additive-only edits to
  `tests/conftest.py`, `tests/factories.py` and `tests/settings.py` that T002 requires.

  **Two plan corrections landed mid-phase, both raised by the Implementer reporting blocked rather
  than routing around a boundary, and both verified at source before being accepted:**
  - `deconstruct()` (T003) moved from US-1 into Phase F. `ModelState.from_model()` clones every
    local field through `deconstruct()`, so nothing carrying `ConceptField` could migrate — or build
    a test database — without it. US-1 is now T004 alone.
  - `to` is the string `"controlled_vocabularies.Concept"`, set unconditionally in `__init__`. A
    resolved model class is refused by migration state. The first attempt stringified it in a
    `clone()` override, which fixed the autodetector and left `migrate` broken; the override is
    gone. Consequence accepted rather than worked around: an unbound field cannot resolve
    `remote_field.model`, so T001's bound `validate()` tests were deleted and the message assertion
    sits in T005, which is where the design review put it.

  At convergence: `tests/test_testapp.py` folded into `tests/test_fields.py` (it mirrored no source
  module, which conformance rejects — a test app is scaffolding, not a package), and the ledger's
  US0/US1 task lists reconciled with `tasks.md`. Next: US-1 (T004), then US-2.
- **2026-08-11 — Implementer US-1 · T004.** Did: added `TestConceptFieldRoundTrip` and
  `TestConceptFieldOrdinaryOptions` to `tests/test_fields.py` (no second file, per the plan's
  convention). Round trip: `SpecimenFactory(rock_type=concept)` against a concept built in a scheme
  named "Rock Type" (slugifies to `"rock-type"`, `Specimen`'s declared vocabulary) survives a reload
  via `Specimen.objects.get(pk=...)`; `Sample(name=...)` with `mineral` unset passes `full_clean()`
  and saves; declaring and saving through the field stays `makemigrations --check --dry-run` clean
  (the regression guard against T003's `deconstruct()` rotting, restated here per `tasks.md`'s T004
  scope rather than relying solely on T002's identical assertion). Ordinary options asserted directly
  on the bound field rather than only through save/reload: `Sample.mineral`'s
  `remote_field.get_accessor_name()` is `"samples"`; `Specimen.rock_type` is `null=False`/
  `blank=False`, `Sample.mineral` is `null=True`/`blank=True`; `verbose_name`/`help_text` read back
  exactly as declared; `db_index is True` on the FK, matching a plain `ForeignKey`'s default
  (confirmed against the installed Django 5.2.16 field, not assumed). No production code touched —
  `fields.py` is unmodified, per T004's nature ("T001 implements `validate()`; T004 proves" the
  construction mechanism is already complete) — so there was no RED step to observe against new
  behaviour; all 8 new tests passed on first run, proving Phase F's mechanism rather than driving new
  code. No deviation from `tasks.md`; no new `decisions.md` entry. Verified: `poetry run pytest -q
  tests/test_fields.py` — 31 passed. Full suite: `poetry run pytest -q` — 1037 passed (1029 + 8).
  `poetry run pre-commit run --all-files` — all hooks green (trim-whitespace, end-of-file, check-yaml,
  poetry-check, ruff lint, ruff format, mypy, deptry). `DJANGO_SETTINGS_MODULE=tests.settings poetry
  run django-admin makemigrations --check --dry-run` — "No changes detected", exit 0. Diff scope:
  `tests/test_fields.py` only. Next: US-2 (T005).
- **2026-08-11 — Implementer US-2 · T005.** Did: added `TestConceptFieldValidation` to
  `tests/test_fields.py` (no second file, per the plan's convention) — a proof task per `tasks.md`'s
  own framing ("No new constraint code"), so `fields.py` is unmodified. `Specimen(rock_type=<concept
  from a "Mineral" scheme>).full_clean()` raises `ValidationError`; reading `.messages` (not merely
  catching the error, per the task's own emphasis) finds `"rock-type"` named — the assertion T001's
  `validate()` override exists for, only reachable against a real bound model per Phase F's design
  record. A concept from the correct vocabulary (`ConceptSchemeFactory(name="Rock Type")`, slugifying
  to `"rock-type"`) passes `full_clean()`; `Sample(name=...)` with the optional `mineral` field unset
  also passes, restated here per `tasks.md`'s T005 scope alongside T004's identical coverage of the
  same case. Confirmed the `ForeignKey.validate()` mechanism this proves by reading the installed
  Django 5.2.16 source directly (`db/models/fields/related.py`) before writing the tests, rather than
  assuming it from `fields.py`'s docstring. No new `decisions.md` entry — no deviation from
  `tasks.md`. Verified: `poetry run pytest -q tests/test_fields.py::TestConceptFieldValidation` — 3
  passed. Next: T006.
- **2026-08-11 — Implementer US-2 · T006.** Did: added `TestConceptFieldFormChoices` (plus a
  test-only `SpecimenForm(forms.ModelForm)`, `fields = ["name", "rock_type"]` — the plain form Django
  would auto-generate) to `tests/test_fields.py` — also a proof task ("Also no new code"), so
  `fields.py` stays unmodified. `form.fields["rock_type"].queryset` contains a concept from the
  "Rock Type" scheme and excludes one from a "Mineral" scheme; a submission carrying the "Mineral"
  concept's pk fails `is_valid()`, reports on `"rock_type"`, and leaves `Specimen.objects.count()` at
  0 — rejected rather than saved. No new `decisions.md` entry — no deviation from `tasks.md`.
  Verified: `poetry run pytest -q tests/test_fields.py` — 36 passed (31 + 5 across T005/T006). Full
  suite: `poetry run pytest -q` — 1042 passed (1037 + 5). `poetry run pre-commit run --all-files` —
  all hooks green (trim-whitespace, end-of-file, check-yaml, poetry-check, ruff lint, ruff format,
  mypy, deptry). `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin makemigrations
  --check --dry-run` — "No changes detected", exit 0. Diff scope across both tasks: `tests/test_fields.py`
  only. Next: US-3 (T007).
