# Progress — 005-concepts-keep-identifier

Append-only narrative log. The ledger (`feature-state.json`) is the source of truth for state; this is
the human-readable trail.

## 2026-08-03 — S0→S2

- **S0 grill.** Grounded on issue #49, its three siblings (#50 import, #51 languages, #52 command
  line), `GOALS.md`, and the R1 code before asking anything. Three questions, each answered by Sam.
  The feature covers vocabularies, concepts, and collections, not concepts alone. A published record's
  identifier is stored and fixed, an unpublished local one is composed and provisional. The identity
  and the address a record is viewed at are two different things and both are needed, because an
  imported record's identifier points at its publisher's site while it still has to be viewable here.
  Sam named them: permanent URI and local URL. Issue #49 gained `accepted` alongside the permanent
  `feature-request` label.
- **S1 specify.** `spec.md` written (5 user stories, FR-001..014, SC-001..013). Clarify's taxonomy scan
  run in full: Functional Scope, Interaction, Integration, Constraints, and Completion Signals clear;
  Domain & Data Model, Non-Functional, and Terminology partial. Four questions raised and self-answered
  from grilling context, landed under `## Clarifications` and integrated into FR-002, FR-004, FR-013,
  FR-014. The scan caught a real defect drafting had missed — FR-002 carried an "other than an explicit
  re-import" escape hatch, which is wrong because upsert matches a record *by* its identifier and so
  never has occasion to rewrite it. Self-resolutions logged in `decisions.md` (D1–D9). Spec lint green:
  all 14 FRs map to a story, every story has acceptance scenarios and an independent test, both goal ids
  cited, no unresolved markers.
- **S2 setup.** Branch `005-concepts-keep-identifier` pushed as the bot (author and committer both
  `forge-aeo[bot]`, verified through the API — the repo's history carries three different numeric ids
  for that account and only one is real). #49 promoted to epic `FS-005` in place; story sub-issues
  #53–#57 created unlabelled and linked; draft PR #58 opened bot-authored, milestone v0.1.0, with a
  `Closes` line for the epic and each story; title lint green.
- **Spec gate: APPROVED by Sam, 2026-08-03.** Brief posted in-session and mirrored as a bot comment on
  #49. No changes requested.

## 2026-08-03 — US-1 implementation (T001–T008)

- **Did**: T001 confirmed `tests/settings.py` carries `CONTROLLED_VOCABULARIES_BASE_URI` and needs no
  new dependency (`urllib.parse` is stdlib) — no code change, as specified. T002 added the
  module-level `validate_permanent_uri(value)` (absolute + scheme, refuses
  `javascript`/`data`/`vbscript` case-insensitively, 500-char cap, translatable named-placeholder
  messages) plus `_reject_permanent_uri_held_by_another_model`. T003 added `permanent_uri`
  (`CharField(max_length=500, null=True, blank=True)`, translatable `verbose_name`/`help_text`,
  `validators=[validate_permanent_uri]`) and a partial `UniqueConstraint` to `ConceptScheme`,
  `Concept`, and `Collection`. T004 generated migration `0005_collection_permanent_uri_concept_
  permanent_uri_and_more` — three `AddField` + three `AddConstraint`, no `RunPython`. T006 reworked
  `uri` on all three models to `self.permanent_uri or <R1 composition>` and added `has_permanent_uri`
  (`bool(self.permanent_uri)`); `local_url` does not exist yet (US-4/T017), so `uri` composes inline
  the R1 way for now, per the brief. T007 added the `save()`-path `validate_permanent_uri` call
  (wrapped as a `permanent_uri` field error) on all three models, protecting the path
  `full_clean()`-free `.objects.create()` takes. T008 added `clean()` overrides (new on all three
  models) and a `save()` call to the cross-model duplicate check.
- **Verified with**: `poetry run pytest -q` → **190 passed** (175 baseline + 15 new in
  `TestPermanentUri`). `poetry run ruff check .` → All checks passed. `poetry run ruff format
  --check .` → 12 files already formatted. `poetry run mypy controlled_vocabularies/` → Success, 4
  source files. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  --check --dry-run` → No changes detected. `python -m django migrate --run-syncdb` from an empty
  in-memory sqlite db → all 19 migrations including `0005_...` applied OK.
- **Deviation (logged as decisions.md D10)**: T006/T007/T008 were implemented in the same pass as
  the T002/T003 foundational work, ahead of T005's tests — inverting tasks.md's test-first order for
  this phase. Remediated by mutation-testing `TestPermanentUri` against the already-written code
  (temporarily reverting the `uri` composition, separately the `save()` validation/cross-model
  calls) and confirming each targeted test failed for the right reason before trusting the final
  green run. No test was weakened or written to match a bug.
- **Commits**: `ba644d8` (T002+T003, foundational validator/field/cross-model-guard/uri-rework/save
  validation — bundled per the deviation above), `93556eb` (T004, migration), `a77290e` (T005, tests).
- **Next**: US-2 (T009–T011, `get_by_uri`/`PermanentUriLookupMixin`) is out of this implementer's
  scope — not started.
- **Watch**: the concept/collection `uri` provisional-composition path still reads
  `self.scheme.uri`/`self.scheme.uri + "/collection/"` rather than a `local_url`, so a concept or
  collection added *locally* to a vocabulary whose own identifier is externally fixed would currently
  compose a provisional identifier under the *publisher's* domain rather than this site's. This
  matches the explicit brief for T006 (defer the `local_url` extraction to US-4/T017) but is a real
  edge case the spec calls out (spec.md "Edge Cases" §4); US-3/US-4's implementer should confirm
  T017's `local_url` extraction closes it, since the current `TestPermanentUri` tests (US-1 scope)
  don't exercise that combination.

## 2026-08-03 — Phase 2b (T024–T025) and US-2 implementation (T009–T011)

- **Did**: T024 added `TestPermanentUriIsFixed` to `tests/test_models.py` — parametrised over
  `ConceptScheme`/`Concept`/`Collection` — asserting a record loaded from the database refuses a save
  that rewrites or clears its stored `permanent_uri` (both via `save()` and via `full_clean()`), that
  the refusal is a translatable `ValidationError` on the `permanent_uri` key with a named `%(uri)s`
  placeholder, that re-saving with the identifier unchanged succeeds, that a record created with an
  identifier keeps it, that a record created without one may still have one set once, and that a
  record reloaded with `permanent_uri` deferred (`.only("label")`) is unconstrained. Confirmed red
  (9 failures — the three rewrite/clear/full_clean cases × 3 models; the other 10 already passed
  incidentally since nothing yet refused anything) before T025. T025 added `_snapshot_permanent_uri`
  and `_reject_permanent_uri_rewrite` as module-level helpers alongside
  `_reject_permanent_uri_held_by_another_model`, an `_loaded_permanent_uri: str | None = None` class
  attribute on all three models, a `from_db` classmethod on each that snapshots the loaded value only
  when `"permanent_uri"` is in `field_names` (left at its `None` default when deferred), and calls to
  the guard from each model's `clean()` and `save()` (unconditionally, so a clear-to-`None` is caught
  too, not just inside the existing `if self.permanent_uri:` block). `None` deliberately doubles as
  both "no snapshot" and "loaded provisional" — both are unconstrained, so no separate sentinel was
  needed once that was noticed (mypy caught the alternative: a `getattr` against an undeclared
  attribute failed `union-attr` on all three model types).
- **Then**: T009 added `TestGetByUri` to `tests/test_models.py` covering all three models — external
  identifier resolves, local composed identifier still resolves (the FR-014 compatibility case for
  `Concept.objects.get_by_uri`), an unheld identifier raises the model's `DoesNotExist`, and
  concept/scheme/collection identifiers don't cross-resolve into each other's manager. Confirmed red
  (10 of 14 failing — `ConceptScheme`/`Collection` had no `get_by_uri` at all, and `Concept`'s did not
  yet check `permanent_uri`) before T010/T011. T010 introduced `PermanentUriLookupMixin`, a generic
  `models.Manager[_PermanentUriModel]` subclass providing `get_by_uri`: exact match on `permanent_uri`
  first (caught via `django.core.exceptions.ObjectDoesNotExist`, not `self.model.DoesNotExist`,
  because mypy cannot resolve `DoesNotExist` off a bound `TypeVar` — a concrete `type[Concept]` on the
  old code could, a generic one could not), then delegating to a `_get_by_local_parse(uri)` hook each
  manager implements. `ConceptManager.get_by_uri`'s existing body moved verbatim into
  `ConceptManager._get_by_local_parse`, unchanged in behaviour. T011 added `ConceptSchemeManager`
  (`{base}/{slug}`, refusing a remainder containing `/` so a concept's or collection's identifier is
  never mistaken for a scheme's) and `CollectionManager` (`{base}/{scheme-slug}/collection/{slug}`,
  requiring the literal `collection` segment so a concept's two-segment identifier is never mistaken
  for a collection's), wired as `objects` on `ConceptScheme` and `Collection` respectively.
- **Verified with**: `poetry run pytest -q` → **223 passed** (190 baseline + 19 `TestPermanentUriIsFixed`
  + 14 `TestGetByUri`). `poetry run ruff check .` → All checks passed. `poetry run ruff format
  --check .` → 12 files already formatted. `poetry run mypy controlled_vocabularies` → Success, 4
  source files. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  --check --dry-run` → No changes detected (no field/constraint changes this phase, only methods and
  managers). `git status --short` → clean.
- **Commits**: `8eb13af` (T024, failing tests), `cbe277d` (T025, the rewrite guard),
  `9eb17c8` (T009, failing tests), `a541164` (T010+T011, `PermanentUriLookupMixin` and the two new
  managers).
- **Deviation**: none from the task text. One implementation choice not spelled out in tasks.md is
  logged as `decisions.md` D11 — using `ObjectDoesNotExist` instead of `self.model.DoesNotExist` in
  the mixin, forced by mypy's inability to resolve `DoesNotExist` off a generic `TypeVar` bound to
  `models.Model`.
- **Out of scope, untouched as briefed**: `local_url` (US-4/T017), factories (T019), `CONTEXT.md`/
  `README.md` (T021/T022), migration squashing. The US-1 report's "Watch" note above is still open —
  T017 is what closes it, not this pass.
- **Next**: US-3 (T012–T015, provisional-URI and uniqueness tests) and US-4 (T016–T017, `local_url`)
  are out of this implementer's scope — not started.
