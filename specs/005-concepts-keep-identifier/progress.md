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

## T026 — closing two holes in the fixedness guard (review, 2026-08-03)

- **Why**: reviewing the T024/T025 delivery rather than accepting its report. T025 exempted a record
  loaded with `permanent_uri` deferred, and asserted that exemption in a test
  (`test_deferred_permanent_uri_is_unconstrained`). Probing it directly showed the exemption is
  reachable from ordinary code: `Model.objects.only("id").get(pk=...)`, assign, save — the stored
  identifier was rewritten, and the same route cleared it to `None`, returning an imported record to
  a provisional identity. A second probe found a hole with no deferral involved: a provisional record
  given an identifier and saved could be given a different one and saved again from the same
  in-memory instance, because its snapshot was still `None`. Both contradict FR-002 and FR-013.
- **Tests first**: the exemption test was replaced by four parametrized tests across all three models
  — a deferred load refuses a rewrite, refuses a clear, leaves the column deferred when it never
  touches it (the evidence the read-back is not paid for on every deferred save), and a provisional
  record may be given an identifier only once. Confirmed red, 12 failing, before any change.
- **Implementation**: `from_db` now flags a deferred load instead of silently leaving no snapshot;
  `_reject_permanent_uri_rewrite` reads the stored value back when the flag is set *and* the column
  has since been assigned; `_permanent_uri_still_deferred` short-circuits `save()` and `clean()` when
  it has not; and `_note_permanent_uri_saved` adopts the written value at the end of each `save()`.
  The three duplicated `save()` blocks collapsed into one `_validate_permanent_uri_on_save` helper.
  Recorded as `decisions.md` D12.
- **Verified with**: `poetry run pytest -q` → **234 passed** (223 + 12 new − 1 replaced).
  `ruff check` → All checks passed. `ruff format --check` → 12 files already formatted.
  `mypy controlled_vocabularies` → Success, 4 source files. `makemigrations --check --dry-run` → No
  changes detected. Each of the three parts of the fix was removed in turn and the suite re-run: the
  read-back fails 6 tests, the post-save snapshot fails 3, the deferred short-circuit fails 3, all
  for the right reason. The original probes now raise instead of silently rewriting.
- **Not covered, deliberately**: `QuerySet.update()` and raw SQL, which bypass every `save()`-based
  rule this app already has. Noted in D12.

## 2026-08-03 — Phase 4 (T012–T015) and Phase 5 (T016–T017) implementation

- **Why**: US-3 (a locally authored record shows the identifier it will publish under) and US-4
  (every record has a place on this site) — the two remaining stories the T009–T011 report flagged as
  out of scope, and specifically the "Watch" note it left open: whether T017's `local_url` extraction
  closes the spec.md Edge Cases §4 hole (a concept or collection added locally to a vocabulary whose
  own identifier is externally fixed composing under the *publisher's* domain).
- **Tests first — Phase 4 (T012–T014)**: `TestProvisionalUri` (9 tests: composition, rename-follow,
  base-address-follow, and `has_permanent_uri is False`, for all three models), `TestPreExistingRecordsUpgrade`
  (3 tests: the FR-009/Article IX evidence — a record built the way a pre-005 database holds one reports
  the identifier R1's composition produced and still resolves by it), and `TestPermanentUriDatabaseUniqueness`
  (4 tests: `bulk_create` — which bypasses `save()`/`clean()` — hits the per-model partial `UniqueConstraint`
  directly and raises `IntegrityError`, plus many-`NULL`-coexist-freely). All 16 passed immediately, run and
  confirmed before anything else in this phase. This is not a test-first violation: tasks.md's own T015 text
  anticipated it ("Expected to be no production change beyond Phase 2 and 3 — if any is needed, it belongs
  here"), because Phase 2's `uri` composition (T006) and Phase 2/3's constraints and migration (T003/T004)
  already deliver every guarantee these three stories describe. A mutation check (temporarily corrupting
  `Concept.uri`'s composition) confirmed the `TestProvisionalUri` concept cases are non-vacuous rather than
  incidentally passing on a tautology.
- **T015**: confirmed — no production change was needed for Phase 4. Marked complete alongside T014.
- **Tests first — Phase 5 (T016)**: `TestLocalUrl` (10 tests) written and run before any implementation.
  All 10 failed with `AttributeError: '<Model>' object has no attribute 'local_url'` (exit 1) — including
  the two Edge Cases §4 regression tests (`test_local_concept_of_an_externally_fixed_scheme_composes_under_this_sites_address`
  and its collection counterpart), which assert a locally authored concept/collection inside an externally
  fixed vocabulary does *not* start with the publisher's domain. Confirmed red for the right reason (the
  attribute genuinely does not exist yet, not a typo or fixture problem) before T017.
- **Implementation (T017)**: added `local_url` to `ConceptScheme` (`{base}/{slug}`, moved verbatim from
  what `uri`'s provisional branch used to inline), `Concept` (`{scheme.local_url}/{slug}`), and `Collection`
  (`{scheme.local_url}/collection/{slug}`) — composing from the *parent's* `local_url`, never from its `uri`,
  exactly as data-model.md specifies. `uri` on all three models became `self.permanent_uri or self.local_url`.
  This is the fix: previously `Concept.uri`/`Collection.uri` read `self.scheme.uri` directly, so when a
  scheme carried an external `permanent_uri` a locally authored concept or collection in it silently composed
  its own provisional identifier under the *publisher's* domain. All 10 `TestLocalUrl` tests flipped from red
  to green with no other change.
- **Verified with**: `poetry run pytest -q` → **260 passed** (250 after Phase 4 + 10 `TestLocalUrl`).
  `poetry run ruff check .` → All checks passed (fixed 3 auto-fixable `SIM117` findings in the T014 tests
  along the way, committed separately as style, not folded into T014's or T017's commit). `poetry run ruff
  format --check .` → 12 files already formatted. `poetry run mypy controlled_vocabularies` → Success, 4
  source files. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check
  --dry-run` → No changes detected (T017 added no field). `git status --short` → clean.
- **Commits**: `27705ff` (T012), `2a15930` (T013), `578a5c4` (T014+T015), `6bad5fc` (T016, failing),
  `bbfc3d9` + `8249000` (style: ruff `SIM117`/format fixes surfaced while verifying, scoped to the T014
  tests, not model code), `b299a3b` (T017, `local_url` + Edge Cases §4 fix).
- **Deviation**: none from the task text for T016/T017 (strict red-then-green, as prescribed). Phase 4's
  tests-pass-immediately outcome is not a deviation — it is what T015 itself predicted — but is called out
  explicitly here rather than silently claimed as "test-first" in the strict red-before-green sense.
- **No new decision**: data-model.md's `local_url` composition (`{base}/{slug}`, `{scheme.local_url}/{slug}`,
  `{scheme.local_url}/collection/{slug}`) was already fully specified; nothing here needed a judgment call
  beyond what tasks.md and data-model.md already state, so no new `decisions.md` entry was added.
- **Out of scope, untouched as briefed**: T018–T023 (factories, `CONTEXT.md`, `README.md`, `forge verify`,
  migration squashing).
- **Next**: Phase 6 (T018–T020, US-5 metadata/indexing/factories) and Phase 7 (T021–T023, docs/polish) are
  out of this implementer's scope — not started.

## 2026-08-03 — Phase 6 (T018) implementation

- **Did**: T018. `test_every_editable_field_has_metadata` in `tests/test_standards.py` already walks
  `_meta.get_fields()` generically over `ALL_MODELS`, which already includes `ConceptScheme`, `Concept`,
  and `Collection` — so `permanent_uri`'s `verbose_name`/`help_text` were already covered by that walk
  with no change needed; confirmed by mutation (temporarily changing `permanent_uri`'s `help_text` on
  one model to a non-lazy value made that test fail for the right reason, then reverted — no diff left
  from that probe). What the generic walk cannot see is message translatability, so five new tests were
  added following the file's existing per-message pattern (Promise check + named-placeholder check +
  `params` check): `validate_permanent_uri`'s three refusals (not-absolute, unsafe-scheme, too-long) and
  the two save-path refusals (held-elsewhere, fixed-rewrite).
- **Verified with**: all five new tests passed green on first run, since the messages they check were
  already delivered translatable in earlier phases. Non-vacuousness proven by mutation: temporarily
  replaced all five messages with plain non-lazy strings with no placeholders, reran
  `pytest tests/test_standards.py -k permanent_uri`, confirmed all five failed for the stated reason
  (`isinstance(err.message, Promise)` false), then restored the original file from a pre-mutation copy
  and reran the full `test_standards.py` suite — 37 passed (32 baseline + 5 new), `git diff` on
  `controlled_vocabularies/models.py` empty.
- **Deviation**: none — T018 needed no production change, matching the fact that Phase 6 lands after
  every model change (Phase 1–5b) that could touch metadata or messages.
- **Commit**: see below.

## 2026-08-03 — Phase 6 (T019) implementation

- **Did**: T019. Added an opt-in `external` trait (`factory.Trait`, matching `ConceptFactory`'s existing
  `multilingual` trait idiom) to `ConceptSchemeFactory`, `ConceptFactory`, and `CollectionFactory` in
  `tests/factories.py`, each setting `permanent_uri` to a per-model `factory.Sequence` under
  `http://publisher.example.org/...` — a plausible externally assigned identifier, distinct per call.
  Six tests added to `tests/test_factories.py`: for each of the three factories, a plain call is
  provisional (`permanent_uri is None`, `has_permanent_uri is False`) and `Factory(external=True)`
  yields a record with `has_permanent_uri is True` and `uri == permanent_uri`.
- **Tests first**: ran the three `external=True` tests before the trait existed — all three failed with
  `TypeError: <Model>() got unexpected keyword arguments: 'external'` (exit 1), confirming `factory_boy`
  rejects an unrecognised parameter rather than silently ignoring it. Added the traits; all 6 new tests
  passed, 25/25 in `tests/test_factories.py`, 277/277 for the full suite.
- **Verified with**: `poetry run pytest -q` → 277 passed (266 baseline + 5 new in T018's
  `test_standards.py` + 6 new in T019's `test_factories.py`). `poetry run ruff check
  tests/factories.py tests/test_factories.py` → All checks passed. `poetry run ruff format --check`
  on the same two files → already formatted.
- **Deviation**: none.
- **Commit**: see below.
