# Progress — 010 Attach several concepts from a chosen vocabulary to a model

Append-only. One line per stage transition and per gate outcome, written at the moment it happens.

- **2026-08-12 — S0 INTAKE.** Issue #87 grilled. One question asked and answered: whether the set
  of attached concepts carries an order the consuming project can rely on. Answer: no, unordered,
  and ordered tagging becomes its own feature if it is ever wanted. Feature statement confirmed by
  the maintainer. `accepted` label added. Dependency #86 verified closed and merged before starting.
- **2026-08-12 — S1 SPECIFY.** Branch `010-attach-several-concepts` created,
  `specs/010-attach-several-concepts/spec.md` written (7 user stories, 13 FRs, 7 SCs), clarify run
  in full (1 intake clarification + 4 from the coverage scan, all self-resolved), `decisions.md`
  written (D1–D6). Spec lint green: every FR maps to a story, every story carries acceptance
  scenarios, G2 cited, no unresolved markers.
- **2026-08-12 — S2 SETUP.** Branch pushed as `forge-aeo` (bot). Issue #87 promoted to epic in
  place. Story sub-issues #102–#108 created and linked. Draft PR #109 opened bot-authored, title
  byte-identical to the epic, `Closes` block seeded for the epic and all seven stories, milestone
  `v0.1.0`. `check-issue-titles` green.
- **2026-08-12 — GATE_SPEC: APPROVED by Sam.** Approved in session against the epic, its seven
  story sub-issues, and `spec.md` on the branch. Gate brief posted as a bot comment on #87
  (`issuecomment-5264353690`), carrying the four self-resolved decisions and the two open risks
  (whether the two consumption fields share an implementation, left to the plan; and the delete
  guard having to be built rather than inherited, since Django drops a membership silently).
- **2026-08-12 — S3 PLAN.** `research.md` (R1–R7, all established empirically against the installed
  Django 5.2.16), `plan.md`, `tasks.md` (T001–T011 across eight stories), `decisions.md` extended
  with D7 (the two consumption fields do not share an implementation) and D8 (the required-set rule
  is installed onto `full_clean`). `stage-exit --stage S3` green.
- **2026-08-12 — S3R DESIGN_REVIEW.** One reviewer, three lenses, one round. Craft-skill receipts
  verified against the registry on all three findings files. Security: `approve`, no findings.
  Spec-compliance and architecture: `request_changes`, one verified `high` each, both accepted and
  applied as plan edits.
  - **SC-001** — D8's wrapper is installed once per consuming class, and nothing said it must
    resolve *every* required `ConceptsField` on that class rather than the one that triggered the
    install, so a second required field would go unenforced with nothing raising. Applied to
    `decisions.md` D8, `plan.md` Approach 5, `tasks.md` T009 (fourth constraint plus a three-part
    test case) and T001 (a two-required-field model to make the case declarable).
  - **ARC-001** — `tasks.md` T003 told the implementer to follow Django's own sequence,
    `super().contribute_to_class(...)` then generate. Read literally that double-registers the join
    model, because `ManyToManyField.contribute_to_class` generates and registers the CASCADE through
    model inside its own body. Confirmed against `django/db/models/fields/related.py:1957-2004` in
    the installed 5.2.16: there is no seam between attach and generate. `plan.md` Approach 3 and
    `tasks.md` T003 now specify the MRO skip, `super(ManyToManyField, self).contribute_to_class(...)`,
    require the hidden `related_name` branch that skip drops to be replicated (FR-011 accepts
    `related_name="+"`), and add a test asserting the registry warning is absent.
  No wording-drift notes returned. No finding fell on `spec.md`, so no delta brief and no re-gate.
- **2026-08-12 — SPEC AMENDMENT, re-gated and APPROVED by Sam.** Raised by the maintainer after the
  design review and before any code existed: requiring a non-empty `vocabulary` was too restrictive,
  because keywords drawn from several vocabularies — or from whatever a project has imported — are a
  standard shape in research metadata. The declaration now names one vocabulary, several, or none.
  Delta brief given in session and approved there. `spec.md` refined in place (FR-002, FR-004,
  FR-005, FR-006, FR-013, SC-002, User Story 2, new User Story 8, four new edge cases, one new
  assumption); `decisions.md` D9; propagated to `plan.md` (Summary, Approach 1, 4 and 7) and
  `tasks.md` (T001, T002, T005, T006, T010, T011, new T012). Story issue #110 created and linked,
  epic body and PR #109 `Closes` block re-synced, ledger carries US8/T012. Nothing was implemented
  against the superseded wording, so no code was reverted.

## 2026-08-12T12:20+02:00 · Implementer US0 · T002

Did: added `ConceptsField(ManyToManyField)` to `controlled_vocabularies/fields.py`, alongside
`ConceptField`. `vocabulary` is optional and normalised once in `__init__` (`_normalise_vocabulary`)
to a tuple of slugs — single slug, list (duplicates collapsed), or omitted → `()`. `limit_choices_to`
is set only when the tuple is non-empty; `to` is fixed to the string
`"controlled_vocabularies.Concept"`; `limit_choices_to` and `through` are refused with `TypeError`
naming the reason. `deconstruct()` strips `to`/`limit_choices_to` and records `vocabulary`.
`contribute_to_class` is not yet overridden — T003's task — so at this stage the field's through
model is still Django's stock CASCADE-on-both-sides one; no consuming model declares the field yet,
so nothing observes that.

Verified: `poetry run pytest tests/test_fields.py -k "TestConceptsFieldConstruction or
TestConceptsFieldDeconstruct"` — 16 passed. Full file `poetry run pytest tests/test_fields.py` — 65
passed (49 pre-existing + 16 new). `poetry run ruff check` and `poetry run ruff format --check` on
both touched files — clean.

Next: T003 — `contribute_to_class` generating the `PROTECT` membership model, against a real
test-app model (some of T001's models land alongside it, since T003's own acceptance needs a real
model to attach the field to — tasks.md sanctions either ordering).

Watch: none.

## 2026-08-12T12:45+02:00 · Implementer US0 · T003

Did: added `ConceptsField.contribute_to_class`, entering the MRO one class higher
(`super(ManyToManyField, self).contribute_to_class(...)`) so `ManyToManyField`'s own through
generation is skipped rather than run and then overridden — the ARC-001 correction. Replicated the
hidden `related_name` rewrite before that call. Added `_create_membership_model`, following
`django.db.models.fields.related.create_many_to_many_intermediary_model` (installed 5.2.16,
`related.py:1308-1361`) with one change: `PROTECT` on the foreign key to `Concept`, `CASCADE` on
the one to the owner, `Meta.auto_created` set to the owning class. Added the two test-app models
T003's own acceptance needs a real declaration to test against — `Deposit` (one required
`ConceptsField`) and `Survey` (two, both `related_name="+"`, for T009's enumeration case and for
the hidden-related-name-rewrite proof) — plus `DepositFactory`/`SurveyFactory`, and generated
`tests/testapp/migrations/0002_concepts_field_deposit_survey.py`. See `decisions.md` D10 for why
these two models land in this task rather than waiting for T001.

Verified: `poetry run pytest tests/test_fields.py -k "TestConceptsFieldMembershipModel or
TestConceptsFieldMigrations"` — 10 passed (including the PROTECT/CASCADE FK check, the two-distinct-
tables check, the hidden-related-name-rewrite check via `Survey.check()` returning no `E304`/`E305`,
and the `warnings.catch_warnings` proof that no `Model ... was already registered` warning fires).
Full file `poetry run pytest tests/test_fields.py` — 75 passed. `poetry run pytest tests/test_checks.py`
— 9 passed (System check untouched by this task still passes with the new models present).
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations testapp --check
--dry-run` — clean. `poetry run ruff check` / `ruff format --check` on all touched files — clean
after converting the `%`-formatted strings copied from Django's own factory to f-strings (`UP031`).

Next: T001 — the remaining four consuming models (optional-with-related_name, both field types on
one model, two-vocabulary, no-vocabulary), their factories, and the final migration for the phase.

Watch: none.

## 2026-08-12T13:05+02:00 · Implementer US0 · T001

Did: added the four remaining consuming models `tasks.md` T001 lists — `Outcrop` (optional
`ConceptsField` with `related_name="outcrops"`), `RockSample` (a `ConceptField` and a
`ConceptsField` against the same "mineral" vocabulary on one model, the collision case), `FieldNote`
(`ConceptsField` naming two vocabularies, `["rock-type", "mineral"]`), `Photograph` (`ConceptsField`
naming none) — plus their factories, and generated
`tests/testapp/migrations/0003_concepts_field_remaining_consumers.py`. All six T001 models (the two
from T003 plus these four) now exist. Every `ConceptsField` on the extended test app carries an
explicit `verbose_name` and a `gettext_lazy`-wrapped `help_text` (Article XII).

Verified: `poetry run pytest tests/test_fields.py -k TestConceptsFieldConsumingModels` — 15 passed
(all-six-queryable, makemigrations --check clean, all-six-factories-build, the optional
related_name reverse accessor, the collision case reading/writing both field types independently,
the two-vocabulary union restriction, the no-vocabulary field still attaching a concept from any
scheme, and the parametrized help_text/verbose_name check across all seven `ConceptsField`
declarations). Full file `poetry run pytest tests/test_fields.py` — 90 passed (75 prior + 15 new).
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`
— "No changes detected". `poetry run ruff check` / `ruff format --check` on all touched files —
clean (one migration file needed `ruff format`, applied).

Next: full-suite verify (`poetry run pytest -q`, expect 1080 + 30 new = 1110), `poetry run
pre-commit run --all-files`, completion report. Phase F (T001–T003) is then complete and every
later US0 story can build on it.

Watch: none.

## 2026-08-12T13:20+02:00 · Implementer US0 · Phase F (T001, T002, T003)

Did: Phase F complete — `ConceptsField` (T002), its generated `PROTECT` membership model (T003),
and the six consuming test-app models (T003 + T001) all committed, three commits, task ID in each
subject. Worktree clean.

Verified (story-level, run once per `craft-tdd`): `poetry run pytest -q` — **1121 passed** (1080
baseline + 41 new: 16 in T002, 10 in T003, 15 in T001). `poetry run pre-commit run --all-files` —
all eight hooks passed (trailing-whitespace, end-of-file-fixer, check-yaml, poetry-check, ruff
lint, ruff format, mypy, deptry). `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m
django makemigrations --check --dry-run` — "No changes detected". `git status --short` — clean.

Next: Forge re-verifies independently and gates. US-1 through US-8 (T004–T012) can now build on a
real `ConceptsField`.

Watch: `decisions.md` D10 records that `Deposit`/`Survey` (T003) and the remaining four models
(T001) landed across two migrations rather than one — Forge squashes at convergence, so this is not
expected to need attention, but naming it in case a reviewer diffs the two migration files
separately and wonders why.

## 2026-08-12T12:40:12+02:00 · Implementer US-1 · T004

Did: attaching, reading back and the reverse accessor — one new class,
`TestConceptsFieldAttachAndReadBack` in `tests/test_fields.py`, four tests. Assertion only, per the
brief and plan.md: T002/T003 already provide `.add()`/`.remove()`, the generated through model and
the `related_name` reverse accessor, so no code was written in `controlled_vocabularies/`. Covers:
two concepts attached and the record reloaded returns exactly those two, compared as a set, and not
a third; attaching an already-held concept is a no-op held exactly once (Django's own `pre_add`
`pk_set` exclusion, R3 — asserted, not built); removing one of two leaves the other attached and the
removed concept still in the database; the `related_name` reverse accessor from the concept side
returns the record and not an unrelated one. No ordering asserted anywhere (D1). One commit, task ID
in the subject.

Verified: `poetry run pytest tests/test_fields.py -q` — 94 passed (90 baseline + 4 new).
`poetry run ruff check tests/test_fields.py` — all checks passed. Story-level full verify
(`poetry run pytest -q`) not yet run — single-task story, deferred to the completion report per
`craft-tdd`.

Next: full-suite verify, completion report. T004 is the whole of US-1's brief scope for this run.

Watch: none.

## 2026-08-12T14:05:00+02:00 · Implementer US-2 · T005

Did: the `pre_add` receiver (FR-005, D2, R1, R3, R6) — `_refuse_concepts_outside_vocabulary` in
`controlled_vocabularies/fields.py`, connected in `ConceptsField.contribute_to_class` against the
generated through model, `weak=False`, only when the declaration named at least one vocabulary.
Refuses on `pre_add` when any incoming concept falls outside the named vocabularies, in one query;
ignores `reverse` writes (owner pks in `pk_set`, not `Concept`'s) and every action but `pre_add`.
One new class in `tests/test_fields.py`, `TestConceptsFieldWritePathVocabularyCheck`, five tests,
all against `Deposit`'s real relation manager: `.add()` of a foreign concept is refused and the set
stays empty; the refusal message names `rock-type`; a `.set()` mixing a held concept with a foreign
one is refused whole, asserted by re-reading the set afterwards; several valid concepts attach
together; and `Photograph` (no vocabulary) has no `m2m_changed` listener for its through model at
all — proved with `m2m_changed.has_listeners()`, not by calling the receiver. One commit, task ID
in the subject.

Deviation from `craft-tdd`'s worked example, recorded here rather than in `decisions.md` since it
is mechanical rather than a design choice: `.add()`/`.set()` run inside
`transaction.atomic(using=db, savepoint=False)`, so a `ValidationError` propagating out of the two
tests that read the set back afterwards poisoned pytest-django's own enclosing transaction
(`TransactionManagementError` on the next query) until the raising call was given its own
`transaction.atomic()` savepoint to roll back to — the documented Django pattern for asserting a
raise from inside an atomic block.

Verified: `poetry run pytest tests/test_fields.py -q` — 99 passed (94 baseline + 5 new).
`poetry run ruff check controlled_vocabularies/fields.py tests/test_fields.py` and
`poetry run ruff format --check` on the same two files — clean.
`DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check
--dry-run` — "No changes detected" (no model/field-structure change, so expected). Story-level full
verify deferred to the completion report per `craft-tdd`.

Next: T006 (form choices) — tests only, per the brief, unless they show `limit_choices_to` does not
already carry through for a `ConceptsField`.

Watch: none.
