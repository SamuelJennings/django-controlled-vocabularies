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
  Sam named them: static URI and local URL. Issue #49 gained `accepted` alongside the permanent
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
  module-level `validate_static_uri(value)` (absolute + scheme, refuses
  `javascript`/`data`/`vbscript` case-insensitively, 500-char cap, translatable named-placeholder
  messages) plus `_reject_static_uri_held_by_another_model`. T003 added `static_uri`
  (`CharField(max_length=500, null=True, blank=True)`, translatable `verbose_name`/`help_text`,
  `validators=[validate_static_uri]`) and a partial `UniqueConstraint` to `ConceptScheme`,
  `Concept`, and `Collection`. T004 generated migration `0005_collection_static_uri_concept_
  static_uri_and_more` — three `AddField` + three `AddConstraint`, no `RunPython`. T006 reworked
  `uri` on all three models to `self.static_uri or <R1 composition>` and added `has_static_uri`
  (`bool(self.static_uri)`); `local_url` does not exist yet (US-4/T017), so `uri` composes inline
  the R1 way for now, per the brief. T007 added the `save()`-path `validate_static_uri` call
  (wrapped as a `static_uri` field error) on all three models, protecting the path
  `full_clean()`-free `.objects.create()` takes. T008 added `clean()` overrides (new on all three
  models) and a `save()` call to the cross-model duplicate check.
- **Verified with**: `poetry run pytest -q` → **190 passed** (175 baseline + 15 new in
  `TestStaticUri`). `poetry run ruff check .` → All checks passed. `poetry run ruff format
  --check .` → 12 files already formatted. `poetry run mypy controlled_vocabularies/` → Success, 4
  source files. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  --check --dry-run` → No changes detected. `python -m django migrate --run-syncdb` from an empty
  in-memory sqlite db → all 19 migrations including `0005_...` applied OK.
- **Deviation (logged as decisions.md D10)**: T006/T007/T008 were implemented in the same pass as
  the T002/T003 foundational work, ahead of T005's tests — inverting tasks.md's test-first order for
  this phase. Remediated by mutation-testing `TestStaticUri` against the already-written code
  (temporarily reverting the `uri` composition, separately the `save()` validation/cross-model
  calls) and confirming each targeted test failed for the right reason before trusting the final
  green run. No test was weakened or written to match a bug.
- **Commits**: `ba644d8` (T002+T003, foundational validator/field/cross-model-guard/uri-rework/save
  validation — bundled per the deviation above), `93556eb` (T004, migration), `a77290e` (T005, tests).
- **Next**: US-2 (T009–T011, `get_by_uri`/`StaticUriLookupMixin`) is out of this implementer's
  scope — not started.
- **Watch**: the concept/collection `uri` provisional-composition path still reads
  `self.scheme.uri`/`self.scheme.uri + "/collection/"` rather than a `local_url`, so a concept or
  collection added *locally* to a vocabulary whose own identifier is externally fixed would currently
  compose a provisional identifier under the *publisher's* domain rather than this site's. This
  matches the explicit brief for T006 (defer the `local_url` extraction to US-4/T017) but is a real
  edge case the spec calls out (spec.md "Edge Cases" §4); US-3/US-4's implementer should confirm
  T017's `local_url` extraction closes it, since the current `TestStaticUri` tests (US-1 scope)
  don't exercise that combination.

## 2026-08-03 — Phase 2b (T024–T025) and US-2 implementation (T009–T011)

- **Did**: T024 added `TestStaticUriIsFixed` to `tests/test_models.py` — parametrised over
  `ConceptScheme`/`Concept`/`Collection` — asserting a record loaded from the database refuses a save
  that rewrites or clears its stored `static_uri` (both via `save()` and via `full_clean()`), that
  the refusal is a translatable `ValidationError` on the `static_uri` key with a named `%(uri)s`
  placeholder, that re-saving with the identifier unchanged succeeds, that a record created with an
  identifier keeps it, that a record created without one may still have one set once, and that a
  record reloaded with `static_uri` deferred (`.only("label")`) is unconstrained. Confirmed red
  (9 failures — the three rewrite/clear/full_clean cases × 3 models; the other 10 already passed
  incidentally since nothing yet refused anything) before T025. T025 added `_snapshot_static_uri`
  and `_reject_static_uri_rewrite` as module-level helpers alongside
  `_reject_static_uri_held_by_another_model`, an `_loaded_static_uri: str | None = None` class
  attribute on all three models, a `from_db` classmethod on each that snapshots the loaded value only
  when `"static_uri"` is in `field_names` (left at its `None` default when deferred), and calls to
  the guard from each model's `clean()` and `save()` (unconditionally, so a clear-to-`None` is caught
  too, not just inside the existing `if self.static_uri:` block). `None` deliberately doubles as
  both "no snapshot" and "loaded provisional" — both are unconstrained, so no separate sentinel was
  needed once that was noticed (mypy caught the alternative: a `getattr` against an undeclared
  attribute failed `union-attr` on all three model types).
- **Then**: T009 added `TestGetByUri` to `tests/test_models.py` covering all three models — external
  identifier resolves, local composed identifier still resolves (the FR-014 compatibility case for
  `Concept.objects.get_by_uri`), an unheld identifier raises the model's `DoesNotExist`, and
  concept/scheme/collection identifiers don't cross-resolve into each other's manager. Confirmed red
  (10 of 14 failing — `ConceptScheme`/`Collection` had no `get_by_uri` at all, and `Concept`'s did not
  yet check `static_uri`) before T010/T011. T010 introduced `StaticUriLookupMixin`, a generic
  `models.Manager[_StaticUriModel]` subclass providing `get_by_uri`: exact match on `static_uri`
  first (caught via `django.core.exceptions.ObjectDoesNotExist`, not `self.model.DoesNotExist`,
  because mypy cannot resolve `DoesNotExist` off a bound `TypeVar` — a concrete `type[Concept]` on the
  old code could, a generic one could not), then delegating to a `_get_by_local_parse(uri)` hook each
  manager implements. `ConceptManager.get_by_uri`'s existing body moved verbatim into
  `ConceptManager._get_by_local_parse`, unchanged in behaviour. T011 added `ConceptSchemeManager`
  (`{base}/{slug}`, refusing a remainder containing `/` so a concept's or collection's identifier is
  never mistaken for a scheme's) and `CollectionManager` (`{base}/{scheme-slug}/collection/{slug}`,
  requiring the literal `collection` segment so a concept's two-segment identifier is never mistaken
  for a collection's), wired as `objects` on `ConceptScheme` and `Collection` respectively.
- **Verified with**: `poetry run pytest -q` → **223 passed** (190 baseline + 19 `TestStaticUriIsFixed`
  + 14 `TestGetByUri`). `poetry run ruff check .` → All checks passed. `poetry run ruff format
  --check .` → 12 files already formatted. `poetry run mypy controlled_vocabularies` → Success, 4
  source files. `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations
  --check --dry-run` → No changes detected (no field/constraint changes this phase, only methods and
  managers). `git status --short` → clean.
- **Commits**: `8eb13af` (T024, failing tests), `cbe277d` (T025, the rewrite guard),
  `9eb17c8` (T009, failing tests), `a541164` (T010+T011, `StaticUriLookupMixin` and the two new
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
  loaded with `static_uri` deferred, and asserted that exemption in a test
  (`test_deferred_static_uri_is_unconstrained`). Probing it directly showed the exemption is
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
  `_reject_static_uri_rewrite` reads the stored value back when the flag is set *and* the column
  has since been assigned; `_static_uri_still_deferred` short-circuits `save()` and `clean()` when
  it has not; and `_note_static_uri_saved` adopts the written value at the end of each `save()`.
  The three duplicated `save()` blocks collapsed into one `_validate_static_uri_on_save` helper.
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
  base-address-follow, and `has_static_uri is False`, for all three models), `TestPreExistingRecordsUpgrade`
  (3 tests: the FR-009/Article IX evidence — a record built the way a pre-005 database holds one reports
  the identifier R1's composition produced and still resolves by it), and `TestStaticUriDatabaseUniqueness`
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
  exactly as data-model.md specifies. `uri` on all three models became `self.static_uri or self.local_url`.
  This is the fix: previously `Concept.uri`/`Collection.uri` read `self.scheme.uri` directly, so when a
  scheme carried an external `static_uri` a locally authored concept or collection in it silently composed
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
  and `Collection` — so `static_uri`'s `verbose_name`/`help_text` were already covered by that walk
  with no change needed; confirmed by mutation (temporarily changing `static_uri`'s `help_text` on
  one model to a non-lazy value made that test fail for the right reason, then reverted — no diff left
  from that probe). What the generic walk cannot see is message translatability, so five new tests were
  added following the file's existing per-message pattern (Promise check + named-placeholder check +
  `params` check): `validate_static_uri`'s three refusals (not-absolute, unsafe-scheme, too-long) and
  the two save-path refusals (held-elsewhere, fixed-rewrite).
- **Verified with**: all five new tests passed green on first run, since the messages they check were
  already delivered translatable in earlier phases. Non-vacuousness proven by mutation: temporarily
  replaced all five messages with plain non-lazy strings with no placeholders, reran
  `pytest tests/test_standards.py -k static_uri`, confirmed all five failed for the stated reason
  (`isinstance(err.message, Promise)` false), then restored the original file from a pre-mutation copy
  and reran the full `test_standards.py` suite — 37 passed (32 baseline + 5 new), `git diff` on
  `controlled_vocabularies/models.py` empty.
- **Deviation**: none — T018 needed no production change, matching the fact that Phase 6 lands after
  every model change (Phase 1–5b) that could touch metadata or messages.
- **Commit**: see below.

## 2026-08-03 — Phase 6 (T019) implementation

- **Did**: T019. Added an opt-in `external` trait (`factory.Trait`, matching `ConceptFactory`'s existing
  `multilingual` trait idiom) to `ConceptSchemeFactory`, `ConceptFactory`, and `CollectionFactory` in
  `tests/factories.py`, each setting `static_uri` to a per-model `factory.Sequence` under
  `http://publisher.example.org/...` — a plausible externally assigned identifier, distinct per call.
  Six tests added to `tests/test_factories.py`: for each of the three factories, a plain call is
  provisional (`static_uri is None`, `has_static_uri is False`) and `Factory(external=True)`
  yields a record with `has_static_uri is True` and `uri == static_uri`.
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

## 2026-08-03 — Phase 6 (T020) implementation

- **Did**: T020. Added `test_static_uri_is_covered_only_by_its_partial_unique_constraint`
  (parametrised over `ConceptScheme`/`Concept`/`Collection`, so 3 test ids) to `tests/test_standards.py`,
  asserting
  each model's `static_uri` field carries `db_index=False`, appears in no explicit `Meta.indexes`
  entry, and is covered by exactly the partial `UniqueConstraint` (`<model>_static_uri_unique`,
  fields `("static_uri",)`, non-null `condition`) the earlier phases already wired. Added
  `test_local_url_and_has_static_uri_are_properties_not_indexable_columns`, asserting `local_url`
  and `has_static_uri` are plain Python `property` objects on all three models, not entries in
  `_meta.get_fields()` — so neither could carry an index even by mistake.
  Checked `data-model.md`'s "Indexing decision" section (Article XIII) against the delivered code:
  it already states exactly this — `static_uri` indexed only via its partial unique constraint,
  `local_url`/`uri`/`has_static_uri` uncounted because they are properties, not columns — so no
  doc correction was needed.
- **Verified with**: both new tests passed green on first run (the indexing decision was already
  correctly implemented in Phase 1–5b). Non-vacuousness proven by mutation: temporarily added
  `db_index=True` to `ConceptScheme.static_uri`'s field definition, reran
  `pytest tests/test_standards.py -k static_uri_is_covered`, confirmed
  `test_static_uri_is_covered_only_by_its_partial_unique_constraint[ConceptScheme]` failed for the
  stated reason (`field.db_index is False` → `AssertionError`), then restored the original file from a
  pre-mutation copy and reran the full `test_standards.py` suite — 41 passed, `git diff` on
  `controlled_vocabularies/models.py` empty. `poetry run pytest -q` → 281 passed (277 + 3 parametrized
  + 1 new). `ruff format` reflowed two lines in the new tests to the project's line-length rule
  (auto-fixed, no logic change); `poetry run ruff check .` / `ruff format --check .` → clean after.
- **Deviation**: none — no production or doc change was needed; the decision was already correctly
  implemented and documented.
- **Commit**: see below.

## 2026-08-03 — Phase 7 (T021) docs

- **Did**: T021. `CONTEXT.md`'s single **URI** glossary entry ("the globally stable identifier of a
  scheme or concept") is replaced by **static URI**, extended to cover collections as well as
  schemes and concepts and to state both fixedness paths (externally assigned and held verbatim, or
  composed here and fixed at publication). **Local URL** joins it as a distinct entry: this site's own
  address, always composed from the configured address and the record's slugs, distinct from the
  static URI for an imported record. The one other in-file mention of the old term ("URI identity"
  in the Architectural decisions closing line) was updated to "static URI identity" for consistency.
  No code change — documentation only.
- **Deviation**: none.
- **Commit**: see below.

## 2026-08-03 — Phase 7 (T022) docs

- **Did**: T022. `README.md`'s Configuration section stated "Concept and scheme URIs are composed from
  a base address" and "A concept's URI is then `{base}/{scheme-slug}/{concept-slug}`" without
  qualification — exactly the claim this task was written to catch, now stale since an externally
  assigned `static_uri` is held verbatim instead. Reworded: the section now leads with the
  static-URI/local-URL split (identity is stored and fixed; an imported record keeps its
  publisher's identifier; a record authored here composes one from the base address until published),
  then gives the same configuration steps and the same `{base}/{scheme-slug}/{concept-slug}` formula
  for this site's own address, explicit that it holds "even when that record's static URI points
  elsewhere." No other README section made the same claim (checked every remaining `URI` mention —
  the rest describe stable/consumption-facing properties, not the composition rule). No code change.
- **Deviation**: none.
- **Commit**: see below.

## 2026-08-03 — Phase 7 (T023) gate run — Phase 6/7 complete

- **Did**: T023, the closing gate for Phase 6 and Phase 7. Ran the full verification matrix from a
  clean working tree on `005-impl`:
  - `poetry run pytest -q` → **281 passed**, 0 failed.
  - `poetry run ruff check .` → All checks passed.
  - `poetry run ruff format --check .` → 12 files already formatted.
  - `poetry run mypy controlled_vocabularies` → Success, 4 source files.
  - `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`
    → No changes detected.
  - Migrate-from-zero: `tests/settings.py` points at an in-memory sqlite database
    (`NAME=":memory:"`), so every fresh process invocation starts from an empty database.
    `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django migrate --run-syncdb` applied
    all five `controlled_vocabularies` migrations (`0001_initial` through
    `0005_collection_static_uri_concept_static_uri_and_more`) cleanly, each reporting `OK`;
    inspecting the resulting `conceptscheme` table's schema directly (`PRAGMA table_info`) confirmed
    `static_uri` landed as a nullable `varchar(500)`, matching data-model.md.
  - `git status --short` → clean except this task's own doc edits.
- **Deviation**: none.
- **Phase 6/7 complete**: T018–T023 all done. This closes out FS-005's implementation task list
  (Phases 1 through 7, including 2b and 5b).

## 2026-08-03 — Phase 8 (T028) refactor: StaticUriModel abstract base

- **Did**: T028. Introduced `class StaticUriModel(models.Model)` (`Meta.abstract = True`) carrying
  the `static_uri` field, `uri`, `has_static_uri`, the static-URI half of `clean()`, and a
  `save()` that brackets `super().save()` with the validation hook — byte-identical across
  `ConceptScheme`/`Concept`/`Collection` before this task. Each concrete model now keeps only its own
  `local_url` property, its `Meta.constraints` entry name, and its `static_uri` field redeclaration
  (an ordinary Django abstract-field override, changing only `help_text` wording). Replaced the
  hardcoded `(ConceptScheme, Concept, Collection)` tuple in `_reject_static_uri_held_by_another_model`
  with `_static_uri_models()`, derived from `StaticUriModel.__subclasses__()`. Added
  `test_every_concrete_static_uri_model_is_registered_for_the_cross_model_check` to
  `tests/test_standards.py`, asserting the registry against Django's own `apps.get_models()` — a source
  independent of the registry helper's own implementation, so a regression to a hardcoded, incomplete
  list is still caught.
- **Verified with**: `poetry run pytest -q` → 282 passed (281 baseline + 1 new registry test), no
  behavioural change. `poetry run ruff check .` / `ruff format --check .` → clean.
  `poetry run mypy controlled_vocabularies` → one error (`candidate.objects.filter` on a
  `type[StaticUriModel]` the stubs can't resolve `.objects` off) fixed by switching to
  `candidate._default_manager.filter(...)`, which the stubs do type; then clean.
  `DJANGO_SETTINGS_MODULE=tests.settings python -m django makemigrations --check --dry-run` → No
  changes detected — migration 0005 unchanged, confirming the field's deconstructed form is identical
  whether declared directly or inherited-then-overridden. Mutation-tested the new registry test by
  temporarily hardcoding `_static_uri_models()` to return `(ConceptScheme, Concept)` (forgetting
  `Collection`) — the test failed for exactly that reason — then restored from a pre-mutation copy and
  reran the full suite green.
- **Deviation**: none — implemented as prescribed.
- **Commit**: `refactor(FS-005): T028 collapse static_uri duplication into StaticUriModel`.

## 2026-08-03 — Phase 8 (T029) headline fix: database read-back replaces the rewrite-guard snapshot

- **Did**: T029. Wrote the four repro cases as tests first, in
  `TestStaticUriRewriteGuardReadsTheDatabase`: (a) a stale second instance of the same row rewriting
  a concurrently stored identifier; (b) a refreshed stale instance clearing one, plus a stale
  provisional instance's plain `.save()` nulling one stored meanwhile; (c) explicit-`pk` construction
  rewriting or clearing one outright; (d) is the same underlying gap as (b)'s `refresh_from_db()` case.
  Confirmed all 11 parametrised cases red against the pre-fix code (3 sanity-check cases already
  green). Deleted `_loaded_static_uri`, `_static_uri_deferred`, the `from_db` override, and
  `_note_static_uri_saved` (~60 lines) from `StaticUriModel`. Replaced
  `_validate_static_uri_on_save`/`_reject_static_uri_rewrite` with a single `_check_static_uri`
  that reads `_stored_static_uri(instance)` back from the database (short-circuiting on
  `instance.pk is None`) and refuses when the in-memory value differs from what is stored — no state to
  go stale. Folded in, while already holding `stored`: skip `_reject_static_uri_held_by_another_model`
  when the in-memory value equals `stored`, removing two wasted queries from every unchanged re-save.
- **Verified with**: all 11 previously-red cases green; `poetry run pytest -q` → 296 passed (282 + 14
  new). `ruff check`/`format --check` clean after one auto-reformat. `mypy` clean.
  `makemigrations --check --dry-run` → No changes detected.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T029 replace the rewrite-guard snapshot with a database read-back`.

## 2026-08-03 — Phase 8 (T030) skip validation on a save that excludes static_uri

- **Did**: T030. Wrote the literal repro from the review write-up first
  (`test_assigning_and_saving_excluding_the_column_leaves_the_record_provisional_and_still_storable`)
  and it was already green — T029's read-back redesign incidentally closed that specific narrative,
  since fixedness is no longer adopted from an unwritten in-memory value. Probed further and found the
  underlying defect the review was pointing at was still live: `_check_static_uri` ran full format
  validation and the fixedness/cross-model checks against `static_uri` even on a
  `save(update_fields=[...])` that never writes that column, so an invalid or would-be-conflicting
  in-memory value blocked an unrelated, valid save (e.g. a label-only update). Wrote two more repro
  tests for that (malformed value; would-be rewrite conflict), confirmed red. Fixed by making
  `StaticUriModel.save()` skip `_check_static_uri` entirely when `update_fields` is given and
  excludes `"static_uri"`.
- **Verified with**: all 4 tests in `TestStaticUriUpdateFieldsExclusion` green (2 confirmed red
  beforehand). `poetry run pytest -q` → 300 passed. `ruff`/`mypy`/`makemigrations --check` clean.
- **Deviation (logged, not silent)**: the review's literal repro turned out to already be fixed by
  T029; implemented the prescribed fix anyway, against the real underlying defect the repro was
  gesturing at, per the task brief's instruction not to silently substitute a different design.
- **Commit**: `fix(FS-005): T030 skip static_uri validation on a save that excludes it`.

## 2026-08-03 — Phase 8 (T031) catch urlsplit's ValueError

- **Did**: T031. Confirmed both verified repros raise a bare `ValueError` from
  `urllib.parse.urlsplit` in a plain Python REPL check first (`http://exa℀mple.com/x` → NFKC
  normalization error; `http://[fe80::1` → invalid IPv6 URL), then wrote them as tests at the
  validator, `save()`, and `full_clean()` layers and confirmed all four red. Wrapped the `urlsplit`
  call in `try/except ValueError`, re-raising as `ValidationError` with a new code
  `static_uri_unparseable`, lazily translated with a named `%(uri)s` placeholder matching its
  siblings. Added a sixth Article XII translatability test to `test_standards.py` alongside the
  existing five.
- **Verified with**: all 4 repro tests green; `poetry run pytest -q` → 305 passed. `ruff`/`mypy`/
  `makemigrations --check` clean.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T031 catch urlsplit's ValueError and re-raise as ValidationError`.

## 2026-08-03 — Phase 8 (T032) length check first, echoed value bounded

- **Did**: T032. Wrote two repro tests first: a 2028-character well-formed-but-overlong value
  producing a 2085-character message (raw value echoed untruncated), and a value that is both
  malformed (no scheme) and overlong being refused with code `static_uri_not_absolute` rather than
  `static_uri_too_long` (proving the order defect directly). Confirmed both red. Moved the length
  check to the top of `validate_static_uri`, before `urlsplit` runs at all, and added an
  `_echoed_uri()` helper (`django.utils.text.Truncator(value).chars(80)`) used in every message's
  `%(uri)s` slot; the too-long message's `%(length)s`/`%(max_length)s` params still report the true,
  untruncated length. Adjusted the pre-existing `test_static_uri_too_long_message_uses_named_placeholders`
  in `test_standards.py`, which had asserted `err.params["uri"] == overlong` (the full raw value).
- **Verified with**: both repros green; `poetry run pytest -q` → 307 passed. `ruff`/`mypy`/
  `makemigrations --check` clean.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T032 check length first and bound every echoed value`.

## 2026-08-03 — Phase 8 (T033) guard get_by_uri against a falsy or non-str identifier

- **Did**: T033. Wrote repro tests first for all three managers (`None` and `""`, plus the
  two-provisional-records `MultipleObjectsReturned` case for `Concept`) and confirmed the `None` cases
  red — `Concept.objects.get_by_uri(None)` returned an unrelated provisional concept with one in the
  table, and raised `MultipleObjectsReturned` with two; the `""` cases were already green (an empty
  string does not compile to `IS NULL`). Added a guard at the top of
  `StaticUriLookupMixin.get_by_uri`: a falsy or non-`str` `uri` raises `self.model.DoesNotExist`
  immediately, before the ORM query runs.
- **Verified with**: all 7 tests in `TestGetByUriRejectsAbsentIdentifiers` green (4 confirmed red
  beforehand). `poetry run pytest -q` → 314 passed. `ruff`/`makemigrations --check` clean. `mypy`
  needed `# type: ignore[attr-defined]` on `self.model.DoesNotExist` — the same generic-vs-concrete gap
  decisions.md D11 already documents (django-stubs' plugin only re-attaches `.DoesNotExist` to a
  *concrete* model class, not a still-generic `type[_ModelT]`) — annotated with a comment pointing at
  D11 rather than left bare.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T033 guard get_by_uri against a falsy or non-str identifier`.

## 2026-08-03 — Phase 8 (T034) refuse an identifier that shadows a local record's own address

- **Did**: T034. Wrote six tests first in `TestStaticUriDoesNotShadowALocalRecordsAddress`: same-
  model shadowing (a new concept's `static_uri` set to a different concept's `local_url`), the same
  against an existing provisional record's later single set, cross-model shadowing (a collection
  against a concept's address, a concept against a scheme's address), and the two accepted cases
  (resolves to nothing under the base address; resolves to the record's own address). Confirmed the
  four refusal cases red, the two acceptance cases already green. Added `_resolve_as_local_url(uri)`,
  trying each of the three models' `_get_by_local_parse` in turn (their local address spaces are
  structurally disjoint per research R4, so at most one can ever match), and
  `_reject_static_uri_shadowing_local_url`, called from `_check_static_uri` alongside the
  cross-model probe and skipped under the same unchanged-value condition. Recorded the reverse-
  direction residual limitation (a rename later displacing an already-stored identifier) in
  decisions.md D14, per the task brief's explicit instruction not to fix it here.
- **Verified with**: all 6 tests green (4 confirmed red beforehand). `poetry run pytest -q` → 320
  passed. `ruff`/`makemigrations --check` clean. `mypy` needed
  `# type: ignore[attr-defined,no-any-return]` on the dynamic `manager._get_by_local_parse(uri)` call
  inside `_resolve_as_local_url` — the same generic-vs-concrete stub gap as T033/D11, annotated
  accordingly.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T034 refuse an externally assigned identifier that shadows a local record's own address`.

## 2026-08-03 — Phase 8 (T035) allowlist accepted URI schemes

- **Did**: T035. Wrote 12 tests first in `TestStaticUriSchemeAllowlist` (the six default schemes
  accepted; four denylisted-by-example values — `file:`, `about:`, `blob:`, `jar:` — refused; the
  setting override honoured; the original denylist still firing inside an overridden allowlist).
  Confirmed the refusal and override cases red (5 of 12; the denylist-inside-override case was already
  green by construction of the test). Added `conf.DEFAULT_ALLOWED_URI_SCHEMES` and
  `conf.get_allowed_uri_schemes()` (same style as `get_base_uri()`), and a new
  `CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES` setting. `validate_static_uri` now checks scheme
  membership in the allowlist before the original three-scheme denylist, which stays as a second gate
  reachable even inside an overridden allowlist (new code `static_uri_scheme_not_allowed`). Adjusted
  the pre-existing `test_static_uri_unsafe_scheme_message_uses_named_placeholders` in
  `test_standards.py` to override the allowlist to include `javascript`, so it exercises the denylist's
  own message rather than the allowlist's (which now fires first for a scheme outside the default six);
  added a matching translatability test for the new code. Updated README's Configuration section and
  logged decisions.md D15, explicit that this supersedes D5's *shape* (denylist → allowlist) but not
  its *content* — D5's own reasoning for including `urn:` is why the allowlist carries `urn`/`doi`/
  `info`/`ark`, not just `http`/`https`.
- **Verified with**: all 12 new tests green; full suite `poetry run pytest -q` → 333 passed, no
  regressions from tightening the default scheme set. `ruff`/`mypy`/`makemigrations --check` clean.
- **Deviation**: none.
- **Commit**: `fix(FS-005): T035 allowlist accepted static_uri schemes instead of denylisting three`.

## 2026-08-03 — Phase 8 (T036) case-preservation coverage

- **Did**: T036. Confirmed this is a coverage gap, not a defect — nothing in `validate_static_uri`,
  `_check_static_uri`, or the field itself touches case. Added
  `test_static_uri_case_round_trips_byte_identical_through_save_and_reload`, parametrised over all
  three models, asserting a mixed-case identifier survives `.create()`, `refresh_from_db()`, and `.uri`
  byte-identical.
- **Verified with**: green on first run (as expected — no code change). `poetry run pytest -q` → 336
  passed.
- **Deviation**: none.
- **Commit**: `test(FS-005): T036 lock in static_uri case preservation`.

## 2026-08-03 — Phase 8 (T037) documentation honesty

- **Did**: T037. `CHANGELOG.md`: added an `[Unreleased]` entry covering the three `static_uri`
  fields, `local_url`, `has_static_uri`, `get_by_uri` gaining `ConceptScheme`/`Collection` managers,
  the exported `validate_static_uri`, and the new `CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES`
  setting; amended the surviving R1 "Stable concept identity" entry to scope its unconditional URI-
  composition claim to a locally authored record. `decisions.md` D2 corrected: the original wording
  ("every record always has one... the difference... is fixedness, never presence") conflated the
  always-answering `uri` *accessor* with the `static_uri` *column*, which is genuinely absent for an
  unpublished record — contradicted both the shipped `has_static_uri` and Sam's own words at the
  spec gate. Rewrote D2 to state presence as the distinction, with a correction note; fixed the same
  drift in `data-model.md`'s `has_static_uri` row. `decisions.md` D12's "not covered, deliberately"
  list extended with `bulk_create` and the fixture/raw-deserializer path — verified empirically (not
  merely inferred) with a probe script: `bulk_create` accepted an unsafe scheme, a raw blank string
  (not normalised to `None`), and a cross-model duplicate. `research.md` R4 now states plainly that its
  cross-model validation check is exactly the "application checks only" alternative R4 itself rejects
  two paragraphs below, for the same concurrent-write race, adopted anyway because closing it needs the
  shared-identity-table alternative R4 already found premature. `data-model.md`'s cross-model-probe
  cost description corrected: it previously said nothing is paid for a locally authored record (true
  but silent that every record *with* an identifier paid two queries on *every* save before T029); now
  records the real pre-T029 cost and that T029's skip-when-unchanged optimisation (extended to the
  shadow check by T034) closes it. `tasks.md` updated with a new Phase 8 (T028–T037) marked done; this
  entry is the corresponding `progress.md` log.
- **Verified with**: `poetry run pytest -q` → 336 passed (no code touched by this task).
  `ruff check .` / `ruff format --check .` clean (docs excluded from ruff's scope; no `.py` files
  touched). `mypy controlled_vocabularies` clean (unchanged). `makemigrations --check --dry-run` → No
  changes detected.
- **Deviation**: none.
- **Commit**: see below.

## 2026-08-03 — Phase 8 complete

T028–T037 all done: the three-lens review's prescribed fixes are landed, each with red-then-green
regression-test evidence where a repro was given, and the documentation drift the review found is
corrected. One disagreement logged (T030's literal repro was already closed by T029; the prescribed
fix was implemented anyway against the real underlying defect, per instruction not to silently
substitute a different design). No other deviations across T028–T037.

## 2026-08-03 — T038 orchestrator correction: `permanent_uri` → `static_uri`

- **Did**: T038. Renamed the field, `validate_permanent_uri`, `has_permanent_uri`, every private
  helper (`_check_permanent_uri`, `_stored_permanent_uri`, `_permanent_uri_models`,
  `_reject_permanent_uri_held_by_another_model`, `_reject_permanent_uri_shadowing_local_url`,
  `_normalise_blank_permanent_uri`, `_permanent_uri_still_deferred`), `PermanentUriModel` →
  `StaticUriModel`, `PermanentUriLookupMixin` → `StaticUriLookupMixin`, every error `code=`, and the
  three `*_permanent_uri_unique` constraint names, to `static_uri` throughout `models.py`, `conf.py`,
  the four test files, and this spec set. Deleted migration 0005 and regenerated it from the renamed
  models rather than hand-editing the historical file or layering a second rename migration — the
  feature is unreleased, so there is no shipped state to preserve a migration path for (mirrors how
  T004's original migration was itself just regenerated, not patched, whenever the field definition
  changed pre-release).

  Beyond the mechanical rename, reworded every `help_text`, `verbose_name`, docstring, and validation
  message the orchestrator's correction touched, per the corrected semantics: `uri` is the record's
  identity and always answers; it is *static* once fixed (externally assigned, or later frozen at
  publication) and *dynamic* otherwise, never "absent." Fixed three places that had drifted into the
  wrong framing before the correction landed — `spec.md`'s "'Permanent' is earned at publication"
  assumption (now "'Static' is earned..."), `decisions.md` D2's "an unpublished vocabulary has no
  static URI" (now "holds no *stored* `static_uri`"), and `quickstart.md`'s upgrade note ("hold no
  permanent identifier" → "hold no static identifier yet — their `uri` is still dynamically
  composed"). Logged the rename itself as `decisions.md` D16.
- **Verified with**: `poetry run pytest -q` → 336 passed (same count as before the rename — nothing
  about behaviour changed). `poetry run ruff check .` and `poetry run ruff format --check .` clean.
  `poetry run mypy controlled_vocabularies` clean. `DJANGO_SETTINGS_MODULE=tests.settings poetry run
  python -m django makemigrations --check --dry-run` → No changes detected. Migrate-from-zero on an
  empty in-memory sqlite reached the same state. `git status --short` clean after commit.
- **Deviation**: none — this is the correction itself, not a deviation from it. Files touched beyond
  the original US-1 brief's `controlled_vocabularies/`/`tests/`/`progress.md`/`decisions.md` scope
  (`conf.py`, `README.md`, `CHANGELOG.md`, `CONTEXT.md`, and the rest of `specs/005-concepts-keep-
  identifier/`) were already part of the shipped feature surface by T021/T022/T037, and the
  orchestrator's correction explicitly asked for "every test and docstring you have written so far,"
  which by T038 spans the whole feature, not just US-1.
- **Commit**: `T038: rename permanent_uri to static_uri`.
