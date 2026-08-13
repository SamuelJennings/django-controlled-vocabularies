# Tasks — 011 Choose a concept by typing instead of scrolling

Every task is test-first (Article I): the failing test comes before the code that satisfies it, in
the same task. Task ids are stable and never reused.

**Tasks have no issues** — this file and `feature-state.json` are the whole task record.

**`research.md` and the wheel verification are not optional reading.** Every line number this file
cites in `django_tomselect` was read from the published wheel `2026.6.2`, not from the project's
default branch. Where the two differ the wheel wins, because the wheel is what a project installs.

**One pre-existing test module is modified**, `tests/test_checks.py`, and only extended (T008). Any
other task that finds itself editing an existing test has got the change wrong: this feature adds
`views.py`, `forms.py` and `urls.py`, adds one method to `fields.py`'s mixin, and adds two warnings
to `checks.py`.

**No migration.** This feature touches no model. A task that produces one has got the change wrong;
`makemigrations --check` is in every task's commands for that reason.

**Sequencing.** Phase F blocks everything and its two tasks are ordered. After it, T003–T005 all
work on `views.py`/`forms.py` and are sequenced together. T006 and T007 are the security pair and
follow T003. T008, T009 and T010 are independent of one another once T004 lands. T011 is last,
because it documents what the others built.

## Phase F — Foundational (blocks every story)

- **T001** — The dependency, declared and justified (FR-015, Article VII).

  Add `django-tomselect = "^2026.6.2"` to `[tool.poetry.dependencies]` with the comment naming
  `views.py`/`forms.py` as the code that imports it, matching how `rdflib` and `defusedxml` are
  declared. Add `django_tomselect` to `tests/settings.py`'s `INSTALLED_APPS`.

  Test first: a test asserting the package imports and that `AutocompleteModelView`,
  `TomSelectModelChoiceField` and `TomSelectModelMultipleChoiceField` are importable from
  `django_tomselect` — this is the compatibility contract of Article VIII pinned to names rather
  than to a version, so a later release that renames one fails here rather than at a form render.

  Commands: `poetry lock`, `poetry install`, `poetry run pytest tests/ -q`,
  `poetry run deptry .`, `poetry run pre-commit run --all-files`.

- **T002** — The endpoint and its route, answering nothing yet (FR-002).

  Create `controlled_vocabularies/views.py` with `ConceptAutocompleteView(AutocompleteModelView)`
  carrying only `model = Concept`, `page_size = 20`, `ordering = ("label", "pk")`,
  `allow_anonymous = True`, `allowed_filter_fields = []`, `allowed_ordering_fields = []`,
  `value_fields = ["id"]`. Create `controlled_vocabularies/urls.py` with `app_name` and the single
  `concept-autocomplete` path. Include it in `tests/urls.py` under a **non-empty prefix of the test
  project's choosing**, because a test project mounting it at the root would never catch a
  hard-coded path.

  Test first, in `tests/test_urls.py`: reversing `controlled_vocabularies:concept-autocomplete`
  returns the prefixed address, and an anonymous GET returns 200 with a JSON body carrying
  `results`, `page` and `has_more`.

  Commands: `poetry run pytest tests/test_urls.py -q`, `poetry run pytest -q`,
  `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`,
  `poetry run pre-commit run --all-files`.

## US-1 — A concept is chosen by typing (#116)

- **T003** — Results carry the concept, its preferred label and its vocabulary (FR-005, FR-012).

  `virtual_fields = ["display_label", "vocabulary"]` and a `prepare_results()` override reading
  `Concept.display_label()` and the scheme's label. `get_queryset()` gains
  `select_related("scheme")` and `prefetch_related("labels")`.

  Test first, in `tests/test_views.py`: a result carries exactly the identifier, the preferred label
  and the vocabulary, and **carries none of** the editorial notes, definitions or hidden labels the
  concept holds — assert on the exact key set, not on the presence of the three, or FR-012 passes
  while the payload grows. A second test asserts a full page of twenty concepts, each carrying
  labels and notes, costs a bounded number of queries under `assertNumQueries` (R5).

- **T004** — Both fields render as the control, with nothing declared (FR-001, FR-003, FR-009).

  Create `controlled_vocabularies/forms.py` with `ConceptChoiceField`, `ConceptsChoiceField` and
  their two widgets (the widgets are empty subclasses at this task; T006 gives them their override).
  Add `formfield()` to `ConceptFieldMixin` in `fields.py`, returning them with `css_framework` pinned
  to the framework-free default and every kwarg Django supplies passed through.

  Test first, in `tests/test_forms.py`: build an ordinary `ModelForm` from the test app's existing
  consuming models — no widget declared, no form field declared — and assert the bound widget is this
  package's. Then **FR-003 properly**: render the form against a vocabulary of five concepts and
  again against one of several thousand, and assert the rendered length is identical and that no
  concept's label appears in the output. Then assert a submitted form still saves the record with the
  concept attached, for both the single- and multiple-value field, and that a foreign concept is
  still refused — FR-009 is a promise that nothing was taken away, so it needs the assertion.

## US-2 — Found by any of its names, shown by one (#117)

- **T005** — Matching across three kinds of label, in the active language (FR-004).

  Override `search()` per plan A4. Leave `search_lookups` empty.

  Test first, in `tests/test_views.py`, one case per acceptance scenario: alternative label, hidden
  label, active-language preferred label differing from the default-language one, a concept with no
  labels at all in the active language found by its default-language label, a concept matching on
  two of its labels appearing **once**, and a search differing only in case. Each asserts the
  returned label is the preferred one for the active language, whichever label matched. Run the
  language-sensitive cases under a real `translation.override`, not by passing a language argument —
  the requirement is about the *active* language.

## US-3 — The results honour what the field allows (#118)

- **T006** — The restriction is derived from the declaration (FR-006).

  The widget override sending `field=<app_label>.<model>.<field_name>`, and `get_queryset()`
  resolving it and applying `complex_filter(field.get_limit_choices_to())`.

  Test first, in `tests/test_views.py`, with three vocabularies in the database and a search string
  matching concepts in all three:

  1. a field declared against one vocabulary returns only that vocabulary's concepts;
  2. **the request altered to name a different vocabulary returns the same results** — the case the
     whole requirement exists for;
  3. a field declared against several returns exactly those;
  4. a field declared against none returns every concept, bounded the same way;
  5. the rendered widget actually carries the reference — assert the attribute is in the rendered
     output, because a reference the browser never sends makes every other case in this task pass
     against a default rather than against a declaration.

- **T007** — Refusal discloses nothing, and the two request-controlled surfaces are closed (FR-006).

  Test first, in `tests/test_views.py`: a reference naming a model that does not exist, one naming a
  real model whose field is not one of this package's, one naming a field that does not exist, and an
  absent reference — each returns HTTP 200 with an empty page, and the four responses are **byte-identical
  to one another and to a search that simply matched nothing**. Asserting "returns no results" would
  pass while a 404 disclosed which model exists.

  Then the two allowlists (D8): a request carrying `f=` filtering on a `Concept` field outside
  `value_fields`, and one carrying an `ordering` parameter, each returns results unchanged from the
  same request without them. Reinstate the open default (`allowed_filter_fields = None`) locally and
  confirm the test fails before closing it again — a guard that has never been seen to fail is not
  known to guard anything.

## US-4 — One route, and nothing else to wire (#119)

- **T008** — Both wiring steps reported at check time (FR-010).

  Two warnings in `checks.py`, neither touching the database: the package's URL configuration is not
  included, and `django_tomselect` is not in `INSTALLED_APPS`. Each names what to add.

  Test first, extending `tests/test_checks.py` (the one pre-existing module this feature modifies):
  each warning appears when its condition holds and is absent when it does not, each is a warning
  rather than an error, and the check runs without a database — assert with `django_assert_num_queries(0)`
  rather than by reading the code.

## US-6 — An existing record shows what it holds (#121)

- **T009** — Attached concepts render, including one the declaration no longer allows (FR-008).

  Inherited behaviour, verified first and overridden only if it fails (plan A8, R1).

  Test first, in `tests/test_forms.py`: a record holding one concept through the single-value field
  and another holding three through the multiple-value field, each reopened, showing the attached
  concepts under their **active-language preferred labels**; submitting an untouched form leaving the
  record unchanged; removing one and saving removing exactly that one; and **a record holding a
  concept from a vocabulary its field no longer names still showing that concept**. If the last fails,
  add a `get_context()` override on this package's widget — the budget for it is in this task, not a
  replan.

## US-5 — A real vocabulary stays usable (#120)

- **T010** — Bounded, stable, and correct past the end (FR-007).

  The `paginate_queryset()` override for the empty-page branch (plan A7).

  Test first, in `tests/test_views.py`: a search matching more concepts than one page holds returns
  one page and says more exist; the following page returns the next concepts with **none repeated and
  none skipped** — assert by collecting both pages' identifiers and comparing them against the full
  ordered match set, not by comparing lengths; opening the control with nothing typed offers a first
  page in a stable order; a page past the last returns nothing and says no more exist (this fails
  against the inherited behaviour, which re-serves page 1 — that is the point of the task); a request
  asking for more than `MAX_PAGE_SIZE` is clamped; and a field naming no vocabulary is bounded the
  same way.

## US-7 — Strings, documentation, and test material (#122)

- **T011** — Translatable strings, README, `CONTEXT.md`, CHANGELOG (FR-011, FR-013, FR-014, FR-015).

  README gains **both** wiring steps in the order a developer does them, what the endpoint exposes,
  that it carries no permission rule and that a project needing to restrict concept data restricts
  the include, and the JavaScript requirement. `CONTEXT.md` defines the terms this feature makes
  public. CHANGELOG records the addition and the new dependency.

  Test first, extending `tests/test_standards.py`'s existing sweep to cover `views.py`, `forms.py`
  and the new check messages: no user-visible string is a bare literal, and every placeholder is
  named. Assert the README documents both steps by name — the second one is the one a reader is most
  likely to be missing.

  The README is public markdown and goes through the humanizer pass before it lands.

  Commands: `poetry run pytest -q`, `poetry run deptry .`,
  `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -m django makemigrations --check --dry-run`,
  `poetry run pre-commit run --all-files`, `forge verify`.
