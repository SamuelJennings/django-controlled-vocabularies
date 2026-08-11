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
- **2026-08-11 — Implementer US-3 · T007.** Did: added `TestConceptFieldDeleteGuard` to
  `tests/test_fields.py` (no second file, per the plan's convention) — a proof task per `tasks.md`'s
  own framing ("No new code either — `PROTECT` was fixed in T001"), so `fields.py` is unmodified.
  Five tests: `concept.delete()` on a referenced concept raises `ProtectedError`, and both the
  concept and the referencing `Specimen` survive; `Concept.objects.filter(pk=...).delete()` (bulk
  queryset delete) is refused identically, confirming the guard lives in the relation rather than in
  model validation; `scheme.delete()` on the `ConceptScheme` holding a referenced concept also raises
  `ProtectedError` and removes nothing — `Concept.scheme` cascades (`on_delete=CASCADE`), so the
  collector tries to cascade-delete the concept and meets `ConceptField`'s `PROTECT` on the way down,
  confirmed by reading `controlled_vocabularies/models.py`'s `Concept.scheme` declaration before
  writing the test rather than assuming the cascade direction; a concept no record references deletes
  normally; deleting the referencing `Specimen` leaves the concept in place. No new `decisions.md`
  entry — no deviation from `tasks.md`. No RED step to observe against new behaviour, consistent with
  T005/T006: `on_delete=PROTECT` was fixed on the field in T001, so all 5 new tests passed on first
  run, proving Phase F's mechanism rather than driving new code. Verified: `poetry run pytest -q
  tests/test_fields.py::TestConceptFieldDeleteGuard` — 5 passed. `poetry run pytest -q
  tests/test_fields.py` — 41 passed (36 + 5). Full suite: `poetry run pytest -q` — 1047 passed (1042
  + 5). `poetry run pre-commit run --all-files` — all hooks green (trim-whitespace, end-of-file,
  check-yaml, poetry-check, ruff lint, ruff format, mypy, deptry). `DJANGO_SETTINGS_MODULE=tests.settings
  poetry run django-admin makemigrations --check --dry-run` — "No changes detected", exit 0. Diff
  scope: `tests/test_fields.py` only. Next: US-4 (T008) or US-5 (T010), per `tasks.md`'s sequencing
  (US-3, US-4, US-5 are independent of one another once Phase F lands).
- **2026-08-11 — Implementer US-4 · T008.** Did: new `controlled_vocabularies/checks.py` —
  `check_concept_field_vocabularies()`, registered **untagged** in `ControlledVocabulariesConfig.ready()`
  per `research.md` R3 (`Tags.database` is skipped unless `--database` is passed, which is exactly the
  bare `manage.py check` invocation FR-004 exists to make useful). Walks `apps.get_models()`, collects
  every field that `isinstance(field, ConceptField)`, resolves the distinct vocabulary slugs in one
  `ConceptScheme.objects.filter(slug__in=...)` query, and yields a `checks.Warning` (id
  `controlled_vocabularies.W001`) per field whose slug is absent, naming the model, the field and the
  slug via a `gettext_lazy`-wrapped, named-placeholder message. New `tests/test_checks.py`
  `TestCheckConceptFieldVocabularies`: a field naming an absent vocabulary is warned about (asserted by
  reading the warning's own `.msg`, not just its presence); once both vocabularies exist the check
  reports nothing; every reported object is `django.core.checks.Warning`, not `Error`; the whole check
  costs exactly one query however many `ConceptField`s are declared (`CaptureQueriesContext`, 3 fields
  across 2 distinct slugs in the test app). RED observed for the right reason: temporarily stubbed
  `check_concept_field_vocabularies()` to `return []` and confirmed all three behavioural assertions
  failed (empty warning dict, empty list, 0 captured queries) before restoring the real body. No
  `on_delete`/`vocabulary` refusal changes — `fields.py` untouched. Verified: `poetry run pytest -q
  tests/test_checks.py::TestCheckConceptFieldVocabularies` — 4 passed. `ruff check`/`ruff format`
  clean. Diff scope: `controlled_vocabularies/checks.py` (new), `controlled_vocabularies/apps.py`
  (+`ready()`), `tests/test_checks.py` (new). Next: T009.

  **Deviation, recorded rather than hidden:** `tests/test_checks.py` was authored in one pass covering
  both T008 and T009 before T008 was committed, so T009's `TestCheckSurvivesUnmigratedDatabase` class
  was present — and failing, since the `DatabaseError` guard didn't exist yet — at the moment T008's
  commit was made. `craft-increments`' "tree is green between slices" held for every test *run* (T008
  was verified narrow-scope green before committing), but not for the file as committed, since the
  T009 class rode along unexercised. Caught immediately by running the whole file straight after
  T008's commit, before starting T009's implementation; T009 landed within minutes closing the gap.
  Recorded as a process note for future tasks sharing a test module: write and commit one task's test
  class at a time, not the whole file up front.
- **2026-08-11 — Implementer US-4 · T009.** Did: added `except DatabaseError: return []` around the
  check's one query in `controlled_vocabularies/checks.py` — `ProgrammingError`, `OperationalError` and
  an unreachable database all subclass `django.db.DatabaseError` (`research.md` R3), so the one clause
  covers every case FR-004 names. New `TestCheckSurvivesUnmigratedDatabase` in `tests/test_checks.py`,
  five tests: three run `poetry run django-admin check|makemigrations --check --dry-run|migrate` in a
  **real subprocess** against a fresh, never-migrated `:memory:` sqlite database (`tests/settings.py`'s
  own `DATABASES`) — a genuinely unmigrated connection, not a mock of `DatabaseError`, per `plan.md`
  Risks' explicit call-out that this is "the single most likely defect in the feature"; two run
  in-process against the normal (migrated, but vocabulary-absent) test database — silencing
  `controlled_vocabularies.W001` via `SILENCED_SYSTEM_CHECKS` suppresses it from `manage.py check`'s
  stderr output (Django's check command writes issues to `stderr`, not `stdout` — caught on first run
  and corrected before this was reported green), and a `ModelForm` built from `Specimen` with the named
  vocabulary absent offers an empty queryset rather than raising. RED observed for the right reason:
  the three subprocess tests failed against T008's implementation with the actual, unmocked
  `django.db.utils.OperationalError: no such table: controlled_vocabularies_conceptscheme` propagating
  out of `django-admin migrate`/`check` (captured in the failure output) before the `except` clause was
  added. Verified: `poetry run pytest -q tests/test_checks.py` — 9 passed (4 + 5). Full suite: `poetry
  run pytest -q` — 1056 passed (1047 + 9). `poetry run pre-commit run --all-files` — all hooks green
  (trim-whitespace, end-of-file, check-yaml, poetry-check, ruff lint, ruff format, mypy, deptry).
  `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin makemigrations --check --dry-run` —
  "No changes detected", exit 0. No new `decisions.md` entry — no deviation from `tasks.md` beyond the
  one recorded under T008. Diff scope: `controlled_vocabularies/checks.py`, `tests/test_checks.py`.
  US-4 (T008, T009) complete. Next: US-5 (T010) or US-6 (T012), per `tasks.md`'s sequencing.
- **2026-08-11 — Implementer US-5 · T010.** Did: added `Concept.display_label()` to
  `controlled_vocabularies/models.py`, beside `preferred_label()` and composed from it —
  `self.preferred_label(get_language()) or self.label`. `preferred_label(None)` already returns
  `self.label` when the active language equals the scheme's effective default (or when
  `get_language()` returns `None`), so the fallback to the default-language label falls out of
  `preferred_label()`'s own behaviour rather than needing a second branch. `preferred_label()`
  itself is unmodified. New `TestConceptDisplayLabel` in `tests/test_models.py`, beside
  `TestConceptPreferredLabels`: the active language's label under `translation.override("de")`;
  the default-language fallback under `translation.override("fr")` for a concept with no French
  label; never empty across all three configured languages. No new test duplicating
  `test_preferred_label_absent_language_returns_none` — the existing `TestConceptPreferredLabels`
  class passing unmodified is itself tasks.md's named regression proof. RED observed for the right
  reason: all three new tests failed with `AttributeError: 'Concept' object has no attribute
  'display_label'` before the method existed. No deviation from `tasks.md`; no new `decisions.md`
  entry. Verified: `poetry run pytest -q tests/test_models.py::TestConceptDisplayLabel
  tests/test_models.py::TestConceptPreferredLabels` — 10 passed. `poetry run pytest -q
  tests/test_models.py` — 225 passed. `ruff check`/`ruff format` clean (ruff's own import-sort fix
  applied to the added `get_language` import, reviewed and correct). Diff scope:
  `controlled_vocabularies/models.py`, `tests/test_models.py`. Next: T011.
- **2026-08-11 — Implementer US-5 · T011.** Did: added `ConceptField.contribute_to_class()` to
  `controlled_vocabularies/fields.py` — after calling `super().contribute_to_class()`, sets
  `get_<name>_label()` and `get_<name>_uri()` on the consuming model, each a closure over the
  field's own `name` reading `getattr(instance, name)` for the attached concept (or `None`). The
  label closure delegates to T010's `display_label()`; the URI closure returns `concept.uri`
  unchanged. Each `setattr` is guarded by `hasattr(cls, attr_name)` first, so a model's own
  pre-existing definition survives — confirmed the guard is reachable before `contribute_to_class`
  runs for the field: `ModelBase.__new__` (`django/db/models/base.py`) sets every plain (non-field)
  class-body attribute directly via `new_attrs`/`super_new` *before* iterating `contributable_attrs`
  and calling each field's `add_to_class`/`contribute_to_class`, regardless of source-order within
  the class body — verified against the installed Django 5.2.16 source rather than assumed, since
  `Artifact.mineral` is declared before `Artifact.get_mineral_label()` in `tests/testapp/models.py`.
  New `TestConceptFieldLabelAndUriAccessors` in `tests/test_fields.py`, appended after
  `TestConceptFieldDeleteGuard`: the label accessor returns the active language's label
  (`translation.override("de")`) and falls back to the vocabulary default under a language the
  concept carries no label in (`translation.override("fr")`); the URI accessor matches the
  concept's own `uri`; both return `None` on `Sample` with nothing attached; `Artifact`'s own
  `get_mineral_label()` (T002's pre-built collision fixture) survives the guard untouched — this
  last test passed before any implementation, since it only exercises `Artifact`'s existing method,
  and served as the guard's specification rather than a RED step. RED observed for the right reason
  on the other four: `AttributeError: 'Specimen' object has no attribute 'get_rock_type_label'` /
  `'get_rock_type_uri'` / `'Sample' object has no attribute 'get_mineral_label'` before
  `contribute_to_class` existed. No model field added, no migration touched — `contribute_to_class`
  only sets plain methods. No deviation from `tasks.md`; no new `decisions.md` entry. Verified:
  `poetry run pytest -q tests/test_fields.py::TestConceptFieldLabelAndUriAccessors` — 5 passed.
  `poetry run pytest -q tests/test_fields.py` — 46 passed. `ruff check`/`ruff format` clean (ruff's
  own import-sort fix applied to the added `ConceptLabel`/`translation` imports, reviewed and
  correct). Diff scope: `controlled_vocabularies/fields.py`, `tests/test_fields.py`.

  US-5 (T010, T011) complete. Full suite: `poetry run pytest -q` — 1064 passed (1056 + 8: 3 T010 +
  5 T011). `poetry run pre-commit run --all-files` — all hooks green (trim-whitespace, end-of-file,
  check-yaml, poetry-check, ruff lint, ruff format, mypy, deptry). `DJANGO_SETTINGS_MODULE=tests.settings
  poetry run django-admin makemigrations --check --dry-run` — "No changes detected", exit 0. Next:
  US-6 (T012, T013), the only story left.
- **2026-08-11 — Implementer US-6 · T012.** Did: audited `fields.py` and `checks.py` string by
  string — every user-visible message in both (the `help_text` default, `default_error_messages`,
  the `checks.Warning` message and hint) was already wrapped with `gettext_lazy` and named
  placeholders by the tasks that wrote them (T001, T008), so no production code changed. The work
  was proving that, rather than assuming it: added `_FieldsChecksI18nVisitor` to
  `tests/test_standards.py`, an AST visitor with the sinks `tasks.md` names —
  `Field`/`ForeignKey`-style `help_text=`/`verbose_name=` keyword literals (and the
  `kwargs.setdefault("help_text", …)` form `ConceptField` actually uses),
  `error_messages`/`default_error_messages` dict values, and bare strings into
  `ValidationError(...)`, `checks.Warning(...)`, `checks.Error(...)` — deliberately not the
  existing `_ManagementI18nVisitor`, whose four sinks (`CommandError`, `.stdout`/`.stderr.write`,
  `add_argument(help=...)`, a class-level `help = "..."`) match nothing either module contains and
  would have reported a false-clean sweep. `TestFieldsChecksI18nVisitorCatchesAViolation` (8 tests)
  proves the visitor against synthetic snippets mirroring each sink, including one confirming a
  translated sink is *not* flagged. `TestFieldsChecksI18nSweep` runs it against the two real
  modules. Proved the gate is real per the ritual: reinstated a bare literal in `fields.py`
  (`kwargs.setdefault("help_text", "A concept from this field's configured vocabulary.")`), ran
  `poetry run pytest -q "tests/test_standards.py::TestFieldsChecksI18nSweep::test_module_carries_no_bare_user_visible_literal[controlled_vocabularies.fields]"`,
  observed the real failure (`AssertionError: ... passes a bare, untranslated literal ...
  ["A concept from this field's configured vocabulary."]`), then reverted and confirmed
  `git diff controlled_vocabularies/fields.py` was empty and the suite green again. Reconciled
  `CONTEXT.md`'s `ConceptField / ConceptsField` row: now states this feature delivers the
  single-value field, attributes `ConceptsField` to #87 and the autocomplete widget to #88, and
  defines the term as what a consuming project's own `models.py` writes into its code. Recorded
  the `on_delete`/`vocabulary` `TypeError` exemption as `decisions.md` D8 — both are developer-facing,
  import-time diagnostics outside every sink the visitor recognises, exempt by construction rather
  than by a special case. Verified: `poetry run pytest -q tests/test_standards.py` — 65 passed (55
  existing + 10 new: 8 `TestFieldsChecksI18nVisitorCatchesAViolation` + 2
  `TestFieldsChecksI18nSweep` parametrizations).
  `ruff check`/`ruff format` clean. Diff scope: `tests/test_standards.py`, `CONTEXT.md`,
  `specs/009-attach-concept-to-model/decisions.md`. No deviation from `tasks.md`. Next: T013.
- **2026-08-11 — Implementer US-6 · T013.** Did: added "Attaching a concept to your model" to
  `README.md`, between "Configuration" and "Importing a published vocabulary" — a `ConceptField`
  declaration on a `Specimen` model, reading `rock_type`/`get_rock_type_label()`/
  `get_rock_type_uri()` back, what happens when `"rock-type"` has not been imported yet (the
  `controlled_vocabularies.W001` check, not a startup failure), and the `research.md` R7 finding
  that `select_related("<field>__scheme")` + `prefetch_related("<field>__labels")` collapse the
  readback's per-row queries. Added a matching `CHANGELOG.md` entry at the top of `### Added`
  (newest-first, matching the file's own ordering), following the file's existing entry shape:
  what the field does, its guarantees, and the missing-vocabulary behaviour, with "See the
  README." No test required — a documentation-only task, and no test in the suite reads either
  file. Neither file passed through the humanizer, per prohibition — that runs once for the whole
  feature at S7. No production code touched; no deviation from `tasks.md`. No `decisions.md`
  entry. Diff scope: `README.md`, `CHANGELOG.md`.

  US-6 (T012, T013) complete. Full suite: `poetry run pytest -q` — 1074 passed (1064 + 10, all
  from T012; T013 added no tests). `poetry run pre-commit run --all-files` — all hooks green.
  `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin makemigrations --check --dry-run`
  — "No changes detected", exit 0. Story complete; no tasks remain in `tasks.md`.
