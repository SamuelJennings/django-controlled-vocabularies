# Progress — 012 Concept selection inside the Django admin

Append-only. Each entry is written at the moment the event happens, not reconstructed afterwards.

| When (UTC) | Stage | Event |
|---|---|---|
| 2026-08-13 | S0 INTAKE | Issue #89 adopted. Grilled to one decision: the control is selection-only, no create or edit affordance on a consuming record's page. Statement confirmed by the maintainer. `accepted` label added. |
| 2026-08-13 | S1 SPECIFY | Branch `012-concept-selection-in-the-admin` created. `spec.md` written: 6 stories (2×P1, 3×P2, 1×P3), FR-001..FR-013, SC-001..SC-008. Coverage scan run: five ambiguities surfaced and self-resolved into `## Clarifications`; rationale in `decisions.md` D1–D8. Spec lint green. |
| 2026-08-13 | S2 SETUP | Branch pushed as forge-aeo. #89 promoted to epic `FS-012`, body grown with the original request preserved. Story sub-issues #125–#130 created and linked, no lifecycle labels. Draft PR #131 opened by the bot, milestone `v0.1.0`, `Closes` block covering the epic and all six stories. `stage-exit S2` green. |
| 2026-08-13 | Spec gate | **Approved** by SamuelJennings, in session, no changes requested. |
| 2026-08-13 | S3 PLAN | Research measured the admin path against Django 5.2.16 and django-tomselect 2026.6.2: the control already reaches admin pages intact, `RelatedFieldWidgetWrapper` is applied unconditionally at `options.py:193`, and the mechanism that declines it was prototyped before the plan was written. `plan.md`, `research.md`, `tasks.md` (18 tasks, 7 phases) and the ledger written. Decisions D9–D13 recorded. `stage-exit S3` green. |
| 2026-08-14 | S3R DESIGN_REVIEW | One reviewer, three lenses, no diff. Verdict `request_changes`: 7 findings (1 high, 3 medium, 3 low), all verified, all remedied in `spec.md`, `plan.md`, `research.md` and `tasks.md`; each remedy checked by the orchestrator against the finding's own evidence rather than a second review round. DR-001 amends FR-004 to the editable control (D14) and is raised with the maintainer in the plan notification. DR-002 dropped T016 (D15). One round, budget used. `stage-exit S3R` green. |

## 2026-08-14T06:01:02Z · Implementer US-1 · T002

Did: wrote `tests/test_admin.py` (new) — `TestConceptControlRendersOnAdminPages`, four
tests against the bare `ModelAdmin` registrations `tests/testapp/admin.py` already carries
(`Specimen.rock_type`, `Outcrop.minerals`). No production code — pins FR-001, FR-002, SC-001,
US-1 scenarios 1-3 and 6.

Verified: `poetry run pytest -q tests/test_admin.py::TestConceptControlRendersOnAdminPages` —
4 passed. All four passed on first run (expected: the context names this behaviour already
true by accident); sanity-checked the assertions are not vacuous by probing the rendered add
page directly outside pytest — the wrong field reference (`testapp.specimen.name`) is absent
while the right one (`testapp.specimen.rock_type`) is present, so the marker is genuinely
field-specific rather than always-on page furniture.

Next: T003 (vocabulary-size bound).

Watch: `tests/` is globally excluded from this repo's pre-commit hooks
(`.pre-commit-config.yaml` `exclude: "^docs/|/migrations/|^tests/"`), so `ruff check`/`ruff
format` on new test files must be run manually — pre-commit reported "no files to check" and
did not catch two lint findings (unused imports staged ahead of T004, one long test name) on
this task's first commit; fixed in two follow-up commits before moving on.

## 2026-08-14T06:01:44Z · Implementer US-1 · T003

Did: added `TestAdminPageRenderingIsBoundedByVocabularySize` to `tests/test_admin.py`,
mirroring `tests/test_forms.py::TestConceptFieldRenderingIsBoundedByVocabularySize` shape for
shape. No production code — pins FR-009, SC-006, US-1 scenario 4.

Verified: `poetry run pytest -q tests/test_admin.py::TestAdminPageRenderingIsBoundedByVocabularySize`
— 1 passed, on first run. `ruff check`/`ruff format --check` clean (run manually, per the T002
watch item).

Next: T004 (submission saves, foreign-vocabulary refusal, delete protection).

## 2026-08-14T06:04:28Z · Implementer US-1 · T004

Did: added `TestAdminSubmissionSavesAndFieldRulesStillBite` to `tests/test_admin.py`, six
tests, both field kinds. No production code — pins FR-010, US-1 scenario 5.

Verified: `poetry run pytest -q tests/test_admin.py::TestAdminSubmissionSavesAndFieldRulesStillBite`
— 6 passed; `poetry run pytest -q tests/test_admin.py` (whole file) — 11 passed. `ruff
check`/`ruff format --check` clean (manual, per the T002 watch item).

First draft of the two refusal tests asserted the model-level custom message
("is not a valid concept...") and failed against the real response — the actual text is
Django's generic ModelChoiceField message, because the widget's own queryset restriction
refuses the foreign pk before the model-level message is ever reached. Recorded as D19 and
fixed to assert on the errored field instead, matching the restraint `tests/test_forms.py`'s
own refusal tests already use.

Next: T005+ is US-2's scope, out of this story.

Watch: none beyond D19 and the T002 pre-commit-exclusion note above.

## 2026-08-14T08:20:00Z · Implementer US-2 · T005

Did: added `TestConceptFieldOffersNoRelatedObjectAffordance` to `tests/test_admin.py`
(five tests) plus two module-level fixtures (`concept_registered_admin_site`,
`bare_admin_site`) and a small `_URLConf` helper that mounts a dedicated
`AdminSite` instance (registering `Specimen`, `Outcrop` and, in the first
fixture, `Concept`) at `admin/`, alongside this package's own route at
`vocabularies/` so the widget's autocomplete reverse still resolves. No
production code — pins FR-004, US-2 scenarios 1-5, SC-002.

Verified: `poetry run pytest -q tests/test_admin.py::TestConceptFieldOffersNoRelatedObjectAffordance`
— 4 failed, 1 passed. The four failures are the correct RED: with `Concept`
registered and a superuser, both field kinds' add and change pages carry
`related-widget-wrapper-link` and (bar the multi-value field's forced-off
three) `add-related`/`change-related`/`delete-related`/`view-related` —
matching research.md R1's measured table exactly. The one pass
(`test_the_same_absence_holds_with_concept_not_registered`) is correctly
green already: `options.py`'s `wrapper_kwargs = {}` on `NotRegistered` leaves
every affordance boolean `False` regardless of the mechanism this story adds,
which is scenario 4's own point — sanity-checked by temporarily deleting one
`not in` assertion and confirming it fails, so the passing test is not
vacuous.

Two false starts before the fixture worked: `types.SimpleNamespace` as the
`ROOT_URLCONF` override is unhashable (`_get_cached_resolver` is
`functools.cache`d) — replaced with a plain `_URLConf` class; and the first
version of `_URLConf` mounted only the admin, so every render raised
`ImproperlyConfigured` from `forms.py`'s route-mixin before reaching an
affordance assertion — fixed by mounting `controlled_vocabularies.urls` too,
matching `tests/urls.py`.

Next: T006 — the form field declines the wrapper.

Watch: none beyond the T002 pre-commit-exclusion note (ruff run manually on
this file; `ruff check --fix` on first run removed the now-unused `types`
import after the `_URLConf` rewrite).

## 2026-08-14T08:35:00Z · Implementer US-2 · T006

Did: added `controlled_vocabularies/admin.py` (new) — one function,
`related_field_widget_wrapper_class()`, returning `RelatedFieldWidgetWrapper`
or `None` when `django.contrib.admin` is not installed (`apps.is_installed()`,
matching `checks.py`'s existing idiom), importing the admin only inside the
function. Registers nothing. Added `_DeclinesAdminRelatedWrapper` to
`forms.py`: `widget` becomes a property whose setter unwraps a
`RelatedFieldWidgetWrapper` to the widget it holds via that lookup, and
stores everything else unchanged; the getter tolerates being read before
anything is stored (`getattr(self, "_widget", None)`). Applied to
`ConceptChoiceField` and `ConceptsChoiceField` as the first base, before the
django-tomselect field class, per the mechanic both the brief and the design
review named.

Verified: `poetry run pytest -q tests/test_admin.py::TestConceptFieldOffersNoRelatedObjectAffordance`
— 5 passed (T005 green). `poetry run pytest -q tests/test_forms.py` — 22
passed, unchanged (the non-admin path untouched). `poetry run pytest -q
tests/test_admin.py` (whole file) — 16 passed. `poetry run mypy
controlled_vocabularies/admin.py controlled_vocabularies/forms.py` — 4 errors
on first run (`queryset`/`to_field_name` MRO conflict between
`BaseTomSelectModelMixin` and `ModelChoiceField`, surfaced by the mixin
becoming a second explicit base — third-party, unrelated to this change,
confirmed by reverting and re-checking clean on the base branch); fixed with
a targeted `# type: ignore[misc]` on each field class line, recorded as D20.
`ruff check`/`ruff format --check` clean (manual, both files touched are
non-test).

Next: T007 — the declining behaviour asserted at form-field level.

Watch: none.

## 2026-08-14T08:45:00Z · Implementer US-2 · T007

Did: added `TestConceptFieldDeclinesTheAdminWrapper` to `tests/test_forms.py`,
four tests, both field classes. Each mirrors `options.py:215` exactly: wrap
the field's own already-built widget in a `RelatedFieldWidgetWrapper`, assign
it back onto `widget`, and assert the field holds the original widget
instance (so its `model_field` binding is intact by construction, not
re-checked separately) rather than the wrapper. A second pair per field class
assigns an ordinary widget and asserts it is held as given. No production
code — proves the seam T006 built, at the form-field level, complementing
T005's page-level proof.

Verified: `poetry run pytest -q tests/test_forms.py::TestConceptFieldDeclinesTheAdminWrapper`
— 4 passed, on first run (expected: T006 already implements the mixin).
Sanity-checked not vacuous: reconstructed the pre-T006 field shape (a plain
`TomSelectModelChoiceField` subclass with no mixin) in an interactive shell
against the same wrapper-assignment steps — `field.widget is original` came
back `False` and the type stayed `RelatedFieldWidgetWrapper`, confirming the
assertions genuinely exercise `_DeclinesAdminRelatedWrapper` rather than
something already true without it. `poetry run pytest -q tests/test_forms.py`
(whole file) — 26 passed. `ruff check`/`ruff format --check` clean (manual).

Next: T007 was US-2's last task — the story's full-suite verify and report
are next, not another task.

Watch: none.

## 2026-08-14T09:00:00Z · Implementer US-3 · T008

Did: added `Locality` to `tests/testapp/models.py` — a new parent model with
its own required-vocabulary-free but declared `ConceptField` (`primary_mineral`,
vocabulary `"mineral"`), and a `locality` foreign key on the existing
`Specimen` (`related_name="specimens"`, nullable so every pre-existing
`SpecimenFactory()` call stays valid). `Specimen.rock_type` (vocabulary
`"rock-type"`) and `Locality.primary_mineral` (vocabulary `"mineral"`) are
deliberately different vocabularies — US-3 scenario 4 needs the parent form's
own field and the inline row's field to be distinguishable. Added
`LocalityFactory` to `tests/factories.py`, mirroring the existing one-factory-
per-model convention (Article X); not in the brief's `test_project_ownership`
file list, called out in deviations. Generated
`tests/testapp/migrations/0004_locality_specimen_locality.py`.

Departure from `tasks.md`: no inline `ModelAdmin` registrations were added to
`tests/testapp/admin.py`. Its own docstring states the convention — bare
registrations only, anything that declares something (an inline is a
declaration) lives on its own site in `tests/test_admin.py` — and the brief's
context names this explicitly. T009–T011 register `Locality` with its
`Specimen` inline on dedicated sites there instead.

Verified: `DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin
makemigrations --check --dry-run` — before the migration: `Migrations for
'testapp': tests/testapp/migrations/0004_locality_specimen_locality.py`
(exit 1, as expected); after generating it, `No changes detected` (exit 0).
`DJANGO_SETTINGS_MODULE=tests.settings poetry run django-admin check` —
`System check identified no issues (0 silenced).` `poetry run pytest -q
tests/test_admin.py` — 16 passed, unchanged (T008 adds no admin-facing
behaviour of its own). `poetry run ruff check`/`ruff format --check` on
`tests/testapp/models.py`, `tests/factories.py` and the new migration — clean
(the migration needed one `ruff format` pass, applied).

Next: T009 — saved inline rows carry the control.

Watch: none.

## 2026-08-14T09:25:00Z · Implementer US-3 · T009

Did: added `tests/test_admin.py::TestInlineRowsCarryTheControl` (2 tests) —
`Locality` registered with a `Specimen` `TabularInline` (`extra = 1`) on a
dedicated site (`locality_tabular_site` fixture; also added
`locality_stacked_site` for T010/T011). First test: two saved `Specimen`
rows under one `Locality`, each carrying its own control showing its own
concept (`id="id_specimens-<index>-rock_type"`, its own
`autocompleteParams`), plus a third concept created but never attached,
asserted absent — the vocabulary isn't dumped onto the page regardless of
row count. Second test: `Locality.primary_mineral` (vocabulary `"mineral"`)
and the inline row's `Specimen.rock_type` (vocabulary `"rock-type"`) each
carry their own distinct `field=...` autocomplete reference and their own
held concept's label (US-3 scenario 4). No production code — both tests pin
behaviour Django's own per-field `formfield()` binding already provides
correctly for formset rows, the same shape as T002-T004.

Verified: `poetry run pytest -q tests/test_admin.py::TestInlineRowsCarryTheControl`
— 2 passed, on first run. Not vacuous — confirmed by breaking the mechanism
under test rather than assuming: a throwaway interactive script (mirroring
T007's method) monkeypatched `ConceptChoiceField.__init__` to always pass
`model_field=None`, the pre-`_ConceptWidgetReferenceMixin`-binding shape, and
re-rendered the same `Locality` change page — both the parent's own
`field=testapp.locality.primary_mineral` reference and the inline row's
`field=testapp.specimen.rock_type` reference disappeared from the response
(`get_autocomplete_params()` returns `""` when `model_field is None`),
confirming the tests would have caught a regression in the per-field
binding, for both the top-level and the inline case. `poetry run pytest -q
tests/test_admin.py` (whole file) — 18 passed. `ruff check`/`ruff format
--check tests/test_admin.py` — clean (one `ruff format` pass applied).

Found, not fixed (out of scope — no production file this story may touch
carries the cause, and it predates T008): a `Concept.label` containing an
apostrophe never appears in a `ConceptField`'s already-selected-option
render, reproduced identically on the pre-existing `Sample.mineral` with no
`Locality`/US-3 code involved at all — `escapejs`-escaping the label
(`'` for `'`) is also absent from the rendered output, so it isn't only
a raw-apostrophe-vs-escaped mismatch; the selected option appears to be
dropped from `_get_selected_options()`'s result entirely. Both test labels
in this story avoid apostrophes to sidestep it. Recorded in this story's
`concerns` for Forge to triage as a separate issue.

Next: T010 — the empty-form row and the shipped script.

Watch: the apostrophe-label finding above.

## 2026-08-14T09:50:00Z · Implementer US-3 · T010

Did: added `controlled_vocabularies/static/controlled_vocabularies/js/concept-inline.js`
(new) — an IIFE listening for `formset:added`, recovering the configuration
registered against the empty-form template row by substituting the added
row's own `-<digits>-` segment back to `-__prefix__-` (mirroring
`findSimilarConfig`'s own normalisation direction, reversed), then calling
`window.djangoTomSelect.initialize(select, config)` — the same call the
library's own per-widget script makes. Additive only: no existing
django-tomselect path is read, wrapped or replaced, and it does nothing on a
page that never dispatches the event. Added `class Media: js = [...]` to
both `ConceptWidget` and `ConceptsWidget` in `forms.py` — the only
`forms.py` change this story makes; `media_property`'s own MRO-walking
merge keeps the base widget's own tomselect JS/CSS.

Verified (TDD, both red first): `tests/test_forms.py::TestConceptWidgetsShipTheInlineInitialisationScript`
— asset discoverable via `django.contrib.staticfiles.finders.find()` (green
immediately, the asset already existed); both widgets' `Media.js` containing
it — red before the `Media` classes were added (`AssertionError:
'controlled_vocabularies/js/concept-inline.js' in
['django_tomselect/js/django-tomselect.min.js']`), green after.
`tests/test_admin.py::TestEmptyFormRowIsInitialisable` (2 tests, against
`locality_stacked_site`/`locality_tabular_site`, `extra = 0`/`extra = 1`) —
the empty-form row's select carries `id="id_specimens-__prefix__-rock_type"`,
`data-tomselect`, and its own registered `autocompleteParams`; and the
script's own id-substitution (mirrored in Python:
`re.sub(r"-\d+-", "-__prefix__-", ...)`) applied to the real numbered row id
on the same page equals the real template row id on that same page — both
passed on first run (server-side rendering the script depends on, not the
script's own execution, which decisions.md D12 keeps a documented manual
check). `poetry run pytest -q tests/test_forms.py tests/test_admin.py` — 49
passed. `poetry run ruff check`/`ruff format --check` on `forms.py`,
`test_forms.py`, `test_admin.py` — clean. `poetry run mypy
controlled_vocabularies/forms.py` — clean.

decisions.md D12 gained the manual browser check steps (five steps: the
"Add another" control initialises rather than staying bare, results arrive
scoped to the row's own vocabulary, a browser-added row's save persists,
the `extra = 0`/no-saved-rows shape from research.md R4 behaves the same,
and no console error on repeated adds).

Next: T011 — a parent saved with a new inline row keeps its concept.

Watch: none.

## 2026-08-14T10:10:00Z · Implementer US-3 · T011

Did: added `tests/test_admin.py::TestNewInlineRowSavesItsConcept` — POSTs
the change form of an existing `Locality` (`locality_stacked_site`,
`extra = 0`, no saved children — the exact shape research.md R4 measured
the library's own fallback failing on) with `specimens-TOTAL_FORMS` raised
to `1` and one new, unsaved row (`specimens-0-id=""`) carrying a concept.
No production code — the server-side "Add another" save path is Django's
inline formset machinery, unrelated to `concept-inline.js`, which only
initialises the widget in the browser (decisions.md D12).

Verified: `poetry run pytest -q
tests/test_admin.py::TestNewInlineRowSavesItsConcept` — 1 passed, on first
run. Non-vacuous, checked directly: the same POST with `specimens-0-name`
left blank (a required field) returned `200` with the form re-rendered
(validation failure), not `302` — confirming the test's `302` + `Specimen
.objects.get(...)` assertions discriminate a genuine save from a rejected
one, not a POST that always redirects. `poetry run pytest -q
tests/test_admin.py` (whole file) — 21 passed. `ruff check`/`ruff format
--check tests/test_admin.py` — clean.

Next: US-3's last task — the story's full-suite verify and completion
report, not another task.

Watch: the apostrophe-label finding recorded at T009 remains open, for
Forge to triage as a separate issue.

## 2026-08-14T09:00:00Z · Implementer US-4 · T012

Did: added `tests/test_admin.py::TestExplicitDeclarationWins` — three dedicated admin sites, each
giving `Specimen.rock_type` one of the three declarations FR-005 names
(`autocomplete_fields`, `raw_id_fields`, a `Meta.widgets`-declared widget), plus a shared
`_ConceptSearchAdmin` for the two sites that also register `Concept`. No production code —
`controlled_vocabularies/` untouched. `tests/testapp/admin.py` also untouched, per its own
bare-registrations-only docstring convention; departure from `tasks.md`'s file list recorded as
`decisions.md` D22, the same pattern D21 already established for T008.

Verified non-vacuous, four ways, each by temporarily sabotaging the fixture or test data and
watching the specific assertion fail for the right reason, then restoring: (1) each of the three
"renders what it declared, not data-tomselect" tests — temporarily emptied the corresponding
declaration (`autocomplete_fields = []`, `raw_id_fields = []`, `widgets = {}`) and reran; all
three failed on `data-tomselect` being present. (2) the "no related-object link" assertion on
`autocomplete_site`/`declared_widget_site` — a scratch probe registering `Specimen.locality` (a
plain `ForeignKey`, no `_DeclinesAdminRelatedWrapper`) under `autocomplete_fields` on an
otherwise-identical site showed the same markers `_assert_no_related_object_affordance` checks
for; a plain FK does carry them, so the committed test's D9-declining ConceptField genuinely has
something to prove. (3) the save/refuse pair — swapped each test's scheme so the "legitimate"
concept came from the wrong vocabulary and the "ineligible" one from the right one; both flipped
to red (302↔200) as expected. (4) `test_no_declaration_reports_a_check_error` — emptied
`_ConceptSearchAdmin.search_fields`; `admin.E040` appeared. `poetry run pytest -q
tests/test_admin.py::TestExplicitDeclarationWins` — 10 passed on restore. `poetry run pytest -q
tests/test_admin.py` (whole file) — 31 passed. `ruff check`/`ruff format --check
tests/test_admin.py` — clean.

Next: T013 — read-only presentation renders no control.

Watch: none.

## 2026-08-14T09:45:00Z · Implementer US-4 · T013

Did: added `tests/test_admin.py::TestReadOnlyPresentationRendersNoControl` — two independent
triggers for the same Django read-only presentation, kept deliberately separate rather than
combined into one configuration: an explicit `readonly_fields` declaration exercised by
`admin_client` (a superuser with full change permission, so the declaration alone is what is
under test — `readonly_concept_site`), and a person holding view but not change permission on a
bare registration that declares no `readonly_fields` at all (`concept_registered_admin_site`,
T005's fixture — `ModelAdmin.get_form()` excluding every field once `has_change_permission()` is
`False` is the only thing making it read-only). Both cases cover the single-valued relation
(`Specimen.rock_type`, asserted against the exact `<a href="...">label</a>` `AdminReadonlyField`
renders once `Concept` is registered) and the many-to-many (`Outcrop.minerals`, asserted as plain
comma-joined text with no concept-change URL present). No production code —
`controlled_vocabularies/` and `tests/testapp/admin.py` both untouched, per `decisions.md` D22.

Verified non-vacuous, three ways, each by temporarily sabotaging the fixture and watching the
right assertion fail for the right reason, then restoring: (1) both `readonly_fields`-declared
tests — emptied `readonly_fields` on both `ModelAdmin`s; both failed on `data-tomselect` being
present (the field became editable again). (2) both view-only-permission tests — granted the
viewer `change_specimen`/`change_outcrop` alongside `view_*`; both failed the same way (one on my
own `has_perm` guard, both eventually on `data-tomselect`), confirming the read-only rendering
genuinely depends on the missing change permission and not on anything else in the fixture.
(3) the link assertions specifically — commented out `site.register(Concept)` on
`readonly_concept_site`; both single- and multi-valued tests failed with `NoReverseMatch` on the
concept change URL, since that route only exists once `Concept` is registered. A separate scratch
probe (not committed) confirmed the positive side of the same claim: with `Concept` unregistered,
the label renders as plain text with no `<a href=` wrapper, matching `decisions.md` D14 exactly.
`poetry run pytest -q tests/test_admin.py::TestReadOnlyPresentationRendersNoControl` — 4 passed on
restore. `poetry run pytest -q tests/test_admin.py` (whole file) — 35 passed. `ruff check`/`ruff
format --check tests/test_admin.py` — clean (one `# noqa: S106` on the throwaway view-only user's
unused password, matching `tests/test_checks.py`'s existing `# noqa: S603` convention).

Next: US-4's full-suite verify and completion report — this story's last task.

Watch: none.

## 2026-08-14T09:40:00Z · Implementer US-5 · T014

Did: added `tests/settings_no_admin.py` (new) — mirrors `tests/settings.py` minus
`django.contrib.admin` and the middleware/apps that exist only for its own system checks.
Added `tests/urls_no_admin.py` (new) — `tests/urls.py` mounts `admin.site.urls`
unconditionally, and resolving any route through it walks that pattern too, which imports
`django.contrib.admin` regardless of which route is being reversed; a urlconf carrying only
the package's own route is what a no-admin project actually mounts. Gave
`tests/test_checks.py:_run_django_admin()` a `settings: str = "tests.settings"` parameter,
threaded into `DJANGO_SETTINGS_MODULE` — every existing call site unaffected. Added
`TestProjectWithoutTheAdminIsUnaffected` (three tests): `check` is as clean under
`settings_no_admin` as under `settings.py`; `django.contrib.admin` is absent from
`sys.modules` in a fresh subprocess after a `ModelForm` over `Specimen` renders (via
`django-admin shell -c`, `--no-startup --no-imports`); and, back under `tests.settings`
(admin installed), `controlled_vocabularies.admin` registers nothing with the default site's
`_registry`. Both new file-list departures recorded in `decisions.md` D23, per the task
brief's own instruction. Covers FR-006, US-5 scenarios 1-2, SC-005.

Verified non-vacuous, three ways: (1) the `check`-is-clean test — temporarily dropped
`django_tomselect` from `settings_no_admin.py`'s `INSTALLED_APPS`; failed correctly
(`CHECK_ID_MISSING_INSTALLED_APP` in stderr, no "no issues" line), restored. (2) the
`sys.modules` test — ran the same subprocess script by hand with an explicit
`import django.contrib.admin` spliced in before the assertion (a scratch probe, not
committed); the `AssertionError` fired and the process exited non-zero, proving the
mechanism genuinely catches a leak rather than always reporting clean. (3) the
registers-nothing test — ran the same assertion by hand under `tests.settings` with
`django_admin.site.register(Concept)` added first (also a scratch probe); the assertion
failed as expected.

`poetry run pytest -q tests/test_checks.py::TestProjectWithoutTheAdminIsUnaffected` — 3
passed, on restore. `poetry run pytest -q tests/test_checks.py` (whole file) — 39 passed
(35 pre-existing + 4: the three new tests plus one existing call site re-verified against
the parameterised helper). `ruff check`/`ruff format --check` clean on
`tests/settings_no_admin.py`, `tests/urls_no_admin.py`, `tests/test_checks.py`.

Next: T015 (custom `AdminSite`).

Watch: none.

## 2026-08-14T09:55:00Z · Implementer US-5 · T015

Did: added `custom_admin_site` fixture and `TestCustomAdminSiteGetsTheSameBehaviour` (four
tests) to `tests/test_admin.py` — a dedicated, non-default `AdminSite` registering `Specimen`
and `Concept`. Asserts the control renders with no related-object affordance, a legitimate
concept saves through its add page, a foreign one is refused, and a model registered on both
the default site and this custom one carries the control on both. No production code — the
declining mechanism (`decisions.md` D9) is field-level, not site-level, so this pins
behaviour that already holds, the same shape as T002. Covers FR-007, US-5 scenarios 3-4.

All four passed on first run, as the story's own context predicts. Sanity-checked non-
vacuousness with a scratch probe (added to `tests/test_admin.py`, run once, then fully
removed — never committed, confirmed by `git diff` showing a clean end state): the same
custom site, with `Locality` additionally registered under a bare `ModelAdmin`, was
requested for `Specimen`'s add page. `rock_type` carried `data-tomselect` and its own field
reference; `related-widget-wrapper-link` — the ordinary `locality` foreign key's wrapper
marker — was present on the same page; and the wrong field reference
(`testapp.specimen.name`) was absent. That confirms `_assert_control_rendered` and
`_assert_no_related_object_affordance` are discriminating within this exact custom-site
request, not vacuously true because the markers never appear on any page from this app.

`poetry run pytest -q tests/test_admin.py::TestCustomAdminSiteGetsTheSameBehaviour` — 4
passed. `poetry run pytest -q tests/test_admin.py` (whole file) — 39 passed (35 + 4).
`ruff check`/`ruff format --check tests/test_admin.py` — clean.

Next: US-5's full-suite verify and completion report — this story's last task.

Watch: none.

## 2026-08-14T08:10:00Z · Implementer US-6 · T017

Did: added a "Choosing a concept in the admin" section to `README.md`, directly after "Choosing a
concept by typing" and before "Importing a published vocabulary" — registering a consuming model is
the whole requirement (the wiring is the same three steps already documented), concepts are chosen
there and never created or edited (no add, change, delete or view affordance), the read-only
presentation (Django's own, not this package's), and the four ways a project asks for a different
control (`autocomplete_fields`, `raw_id_fields`, a form's own declared widget via `Meta.widgets`,
`readonly_fields`). `CONTEXT.md`'s "Concept search control" row gains a sentence naming the admin
and a `#89` cross-reference, matching the row's existing `#86`/`#87`/`#88` convention. `CHANGELOG.md`
gains an `[Unreleased] → Added` entry directly below the existing "Choosing a concept by typing"
entry, same register. Test-first per `craft-tdd`: added `TestReadmeDocumentsTheAdminSection` to
`tests/test_standards.py` (mirroring `TestReadmeDocumentsTheConceptSearchControlsWiring`'s
technique for the sibling documentation story), ran it red against the unmodified README, then wrote
the section and reran green — `decisions.md` D24 records the file-list departure. `CONTEXT.md` and
`CHANGELOG.md` are not covered by an assertion; no established precedent tests either, and they are
short, targeted edits checked by re-reading them against the acceptance text.

Verified: `poetry run pytest -q tests/test_standards.py::TestReadmeDocumentsTheAdminSection
tests/test_standards.py::TestReadmeDocumentsTheConceptSearchControlsWiring` — 12 passed (the new
class did not disturb the sibling one it sits beside). `poetry run pytest -q tests/test_standards.py`
(whole file, narrowest scope covering a README change nothing else in the repo imports) — 87 passed.
`ruff check`/`ruff format --check tests/test_standards.py` — clean.

Next: T018 (translation status + test-structure conformance).

Watch: none.
