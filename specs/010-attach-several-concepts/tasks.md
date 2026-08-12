# Tasks — 010 Attach several concepts from a chosen vocabulary to a model

Every task is test-first (Article I): the failing test comes before the code that satisfies it, in
the same task. Task ids are stable and never reused.

**No pre-existing test is modified.** This feature adds a class to `fields.py`, widens one filter in
`checks.py`, and otherwise adds new material. A task that needs to edit an existing test has got the
change wrong — with one declared exception, T010, which widens an existing check and may extend (not
rewrite) its tests.

**Tasks have no issues** — this file and `feature-state.json` are the whole task record.

**The research is not optional reading.** `research.md` R1 to R6 were established empirically
against the installed Django, and three of them contradict what the equivalent FS-009 code does.
Anything below that cites an R-number is citing a verified finding, not a hypothesis.

**Sequencing.** Phase F blocks everything, and its three tasks are strictly ordered. After it, US-1,
US-2 and US-5 all work on `fields.py` and are sequenced together. US-3, US-4 and US-6 are independent
of one another once Phase F lands. US-7 is last, because it documents what the others built.

## Phase F — Foundational (blocks every story)

- **T001** — Consuming models in the test app (FR-001, US-1 through US-6).

  Extend `tests/testapp/models.py` — do not replace it; `Specimen`, `Sample` and `Artifact` are
  FS-009's and stay exactly as they are. Add:

  - a model carrying a **required** `ConceptsField` (no `blank=True`), for US-5's refusal;
  - a model carrying an **optional** `ConceptsField` (`blank=True`) with a `related_name`, for US-1's
    reverse accessor and US-5's permissive half;
  - a model carrying **two required** `ConceptsField`s against the same vocabulary, for T009's
    enumeration case — one required field enforced and the other silently skipped is the failure that
    case exists to catch, and it needs a model with two of them to be visible at all;
  - a model carrying **both** a `ConceptField` and a `ConceptsField` against the same vocabulary,
    which is the collision case the plan's Risks section refuses to assume away — two declarations on
    one model must generate distinct membership tables and non-clashing reverse accessors.

  Every field gets `verbose_name` and `help_text` wrapped in `gettext_lazy` (Article XII makes
  `help_text` mandatory). Generate the migration for the test app in the same task and confirm
  `makemigrations --check` is clean afterwards.

  This task lands *after* T002 and T003 in wall-clock terms — the models cannot import a field that
  does not exist — so implement it as the last step of the phase, or write the models against the
  field's intended signature and let T002/T003 make them importable. Either way the phase is one
  sequential unit and exits green as a whole.

- **T002** — `ConceptsField` construction and deconstruction (FR-001, FR-002, FR-011, R6).

  `ConceptsField(ManyToManyField)` in `controlled_vocabularies/fields.py`, alongside `ConceptField`.
  Article VIII already names this class, so the name is fixed by the constitution.

  `__init__` takes `vocabulary` (the `ConceptScheme` slug) and fixes what the consumer may not
  supply:

  - `to = "controlled_vocabularies.Concept"` — **the string form, always, never the imported class.**
    The reasoning is `ConceptField`'s and is written out in its docstring: migration state cannot
    hold a resolved model class. Read it before deviating.
  - `limit_choices_to = Q(scheme__slug=vocabulary)` — constructed, never evaluated, so nothing
    queries the database while the declaration is read (FR-003). Assert that with
    `django.test.utils.CaptureQueriesContext` around the field's construction rather than assuming it.
  - `help_text` defaults to a translatable string the consumer can override. Do **not** interpolate
    `vocabulary` into it: `%` on a `gettext_lazy()` proxy evaluates it immediately and defeats the
    laziness the default exists to keep. `ConceptField` carries a comment saying so.

  Rejections, all at construction time, all `TypeError` naming the reason:

  - `vocabulary` absent or empty — an unconstrained field is a plain `ManyToManyField` and offers
    none of this field's guarantees (FR-002).
  - `limit_choices_to` passed by the consumer — it is what constrains the field.
  - `through` passed by the consumer — a consumer-supplied membership model silently drops the
    delete guarantee T003 exists to provide. Refusing loudly keeps FR-011's "never silently
    override" true.

  `deconstruct()` strips `to` and `limit_choices_to` and records `vocabulary` instead. Both are
  emitted by Django (`ManyToManyField.deconstruct` always emits `to`; `RelatedField.deconstruct`
  emits `limit_choices_to` whenever truthy, which here is always), and `Field.clone()` feeds exactly
  those kwargs back into `__init__` on every `makemigrations`, `makemigrations --check`, `migrate`
  and pytest-django test-database build. Left alone, the field cannot be cloned at all. **A kwarg
  stripped without a recorded replacement is worse than one left in** — migration state and field
  definition then diverge silently — so `vocabulary` has to carry the whole declaration. `through` is
  never emitted, for the reason in T003.

  Tests: construction with and without each rejected kwarg; the no-query assertion; a
  deconstruct/reconstruct round trip that rebuilds the field from its own output.

- **T003** — The membership model, generated with `PROTECT` (FR-007, US-3, R4, R6).

  `contribute_to_class` skips `ManyToManyField`'s own through generation and substitutes one whose
  foreign key to `Concept` is `on_delete=PROTECT` rather than `CASCADE`. Django's auto-created join
  model cascades, which means deleting a concept silently removes every membership pointing at it —
  the exact failure US-3 exists to prevent, and one that leaves no trace.

  Follow `django/db/models/fields/related.py:1308-1361`
  (`create_many_to_many_intermediary_model`) closely: same `<Owner>_<fieldname>` naming, same
  `unique_together`, same hidden `related_name="…+"` accessors, same `Meta.apps`, same `db_table`
  from `field._get_m2m_db_table(klass._meta)`. **Keep `Meta.auto_created` set to the owning model
  class**, exactly as Django sets it — that one attribute is what keeps the model out of migration
  state (`ProjectState.from_apps` calls `apps.get_models()`, which excludes auto-created models) and
  out of `deconstruct()` (which emits `through` only when `not …auto_created`), while still having
  its table created and dropped with the owner by the schema editor. Setting it to a bare `True`
  happens to behave the same way; matching Django's own value costs nothing and keeps the model
  indistinguishable from a stock one.

  Ordering inside `contribute_to_class` matters: the generation helper reads
  `field.model._meta.apps` and `field._get_m2m_db_table(...)`, both of which need the field already
  attached to the model. So the field must be attached first, then the model generated, then the
  `ManyToManyDescriptor` installed and `m2m_db_table` curried — the same order Django uses.

  **Attach with `super(ManyToManyField, self).contribute_to_class(cls, name, **kwargs)`, not a plain
  `super()` call.** `ManyToManyField.contribute_to_class` generates and registers the CASCADE through
  model inside its own body, after its `super()` call and before it returns, so a plain `super()`
  leaves no seam between "attached" and "generated". Generating the `PROTECT` replacement after it
  registers a second model under the same name and Django warns `Model … was already registered` on
  every consuming declaration — not an edge case, and a warning rather than an error, so it will not
  fail a test that is not looking for it. Assert its absence: wrap the model declarations in
  `warnings.catch_warnings(record=True)` and require no `RuntimeWarning` naming the through model.

  The MRO skip drops the `related_name` rewriting at the top of
  `ManyToManyField.contribute_to_class`, so **replicate the hidden branch before the `super()`
  call**: when `self.remote_field.hidden`, rewrite `related_name` to
  `"_%s_%s_%s_+" % (cls._meta.app_label, cls.__name__.lower(), name)`, exactly as Django does. FR-011
  accepts `related_name="+"`, and two such fields on one model clash without it. Do not replicate the
  symmetrical branch — the target is always `Concept` and never the owner, so the condition cannot
  hold. Test with two `ConceptsField`s declared `related_name="+"` on one model: both declare cleanly
  and the reverse accessors do not collide.

  Tests, all against a real model from T001, none against the helper in isolation: `makemigrations`
  produces a migration and `makemigrations --check` is clean afterwards; the field's `deconstruct()`
  emits no `through`; the generated model's foreign key to `Concept` is `PROTECT` and the one to the
  owner is `CASCADE`; two declarations on one model produce two distinct tables.

## US-1 — A project attaches several concepts with one declaration (#102, P1)

- **T004** — Attaching, reading back, and the ordinary relation options (FR-001, D1, D4).

  With T002 and T003 in place, most of this is assertion rather than construction. Tests:

  - two concepts attached and the record reloaded returns both, and no third;
  - attaching a concept the record already holds leaves it held exactly once and raises nothing —
    Django gives this for free, because `pre_add`'s `pk_set` is `missing_target_ids` and an
    already-attached concept is excluded (R3), so assert the behaviour rather than writing code for
    it;
  - removing one of two leaves the other attached and the removed concept still in the database;
  - the reverse accessor named by `related_name` works from the concept side;
  - no order is asserted anywhere. D1 makes the set unordered, so a test that depends on the order two
    concepts come back in is testing something the feature does not promise. Compare as sets.

## US-2 — Every selection stays inside the named vocabulary (#103, P1)

- **T005** — The `pre_add` receiver (FR-005, D2, R1, R3, R6).

  Connect an `m2m_changed` receiver to the through model **inside `contribute_to_class`, at the
  moment that model is generated** — not in `AppConfig.ready()`, not at module import of anything
  else. This is load-bearing and R6 is the reason: a truthy `auto_created` re-enables Django's
  `bulk_create(ignore_conflicts)` fast path, and that path skips `m2m_changed` entirely **when no
  receiver is connected for that through model**. Binding the receiver to the model it guards, at
  creation, means a declaration cannot exist without its guard. Connect with `sender=<the generated
  through model>`; there is no module-level model to name.

  On `action="pre_add"`, resolve the incoming primary keys in **one** query and raise
  `ValidationError` if any concept falls outside the named vocabulary. The message is translatable
  with named placeholders (Article XII) and names the expected vocabulary — `ConceptField`'s
  `invalid` message is the wording to follow. Raising from `pre_add` aborts before any row is
  inserted, which is what FR-005 means by a mixed write being refused whole.

  Ignore every other action. `post_add`, `pre_remove`, `post_remove`, `pre_clear` and `post_clear`
  all reach the same receiver.

  Tests, all through a real model's relation manager, never by calling the receiver directly — a test
  that calls the receiver would pass even if the fast path were skipping it, which is precisely the
  failure this task guards against:

  - `.add()` of a concept from another vocabulary is refused and the record's set is unchanged;
  - `.set()` carrying a mix is refused whole, and the record's set is unchanged — assert the set
    *after* the failed write, not just that it raised;
  - `.add()` of several valid concepts succeeds;
  - the refusal message names the expected vocabulary.

- **T006** — Form choices (FR-006, R1).

  `limit_choices_to` from T002 already restricts a `ModelForm`'s `ModelMultipleChoiceField` queryset,
  and `ModelMultipleChoiceField._check_values` rejects a submitted primary key outside it. So this
  task is tests, not code, unless they show otherwise:

  - a form generated from the consuming model offers only the named vocabulary's concepts;
  - a submission carrying a concept from another vocabulary is rejected rather than saved;
  - a valid submission saves and the memberships appear.

## US-3 — A concept anyone holds cannot vanish (#104, P1)

- **T007** — Delete protection, both directions (FR-007, D5, R4).

  Tests only, against real models and real deletes. T003 supplies the mechanism; this task proves it
  at the boundary the spec states. Never assert on a mocked collector.

  - deleting a held concept raises `ProtectedError` and the concept, the record and the membership
    all survive;
  - the same deletion through `Concept.objects.filter(...).delete()` raises too — the queryset path
    builds the same collector and `can_fast_delete` returns `False` whenever a related `on_delete` is
    not `DO_NOTHING`, so this is a real guarantee rather than an accident of the single-object path;
  - deleting the `ConceptScheme` holding a held concept is refused, and nothing in the vocabulary is
    removed;
  - a concept no record holds deletes cleanly;
  - deleting the consuming record succeeds, removes only its membership rows, and leaves every
    concept (D5);
  - a concept detached from every record it was on can then be deleted.

## US-4 — The record reads back the labels and the identifiers (#105, P2)

- **T008** — `get_<name>_labels()` and `get_<name>_uris()` (FR-008, FR-009).

  Contributed in `contribute_to_class` alongside the through generation, named the way Django's own
  `get_FOO_display()` is and the way `ConceptField`'s singular accessors already are. Plural names,
  one entry per attached concept. Labels come from `Concept.display_label()`, which already resolves
  the active language and falls back to the vocabulary's default — do not reimplement that here.
  URIs are `Concept.uri`, unchanged.

  Keep `ConceptField`'s collision guard: a model that already defines either name keeps its own
  definition. A record holding nothing returns an empty result rather than raising.

  Tests use the existing `multilingual_scheme` and `single_language_scheme` fixtures rather than new
  ones: labels under an active language the concepts carry, labels under one they do not (the
  fallback), the URIs, the empty case, and the collision guard against a model that defines the name
  itself.

## US-5 — Required means at least one (#106, P2)

- **T009** — The required-set rule (FR-010, D3, D8, R2, R5).

  `blank=False` already gives the form half — `ModelMultipleChoiceField` raises `required` on an
  empty selection — so that half is a test. The model half has no hook, because `full_clean()` never
  looks at a many-valued relation (R2), so the field installs one on the consuming model class.

  Four constraints, all of them from D8 and none of them stylistic:

  - **Install once per class and delegate.** Guard on the class's own `__dict__`, not `getattr` — a
    subclass would otherwise inherit the flag and lose the check.
  - **Check every required `ConceptsField` on the class, not the one that installed the wrapper.**
    Because the install is once per class, a wrapper closing over the triggering field instance
    leaves a second required `ConceptsField` on the same model unenforced, with nothing raising and
    no test failing. Resolve the class's required `ConceptsField`s from `cls._meta.get_fields()` at
    call time and apply FR-010 to each.
  - **Skip an unsaved record.** Touching the relation descriptor when the primary key is `None`
    raises `ValueError`, and `full_clean` catches only `ValidationError`, so an unguarded check turns
    an ordinary `ModelForm.is_valid()` on a new object into an uncaught crash. It is also the correct
    semantic: a record exists before its memberships can.
  - **Merge, never replace, the error dictionary.** The original `full_clean` raises before the added
    check runs, so catch that `ValidationError`, add the field's message, and re-raise the whole
    thing.

  Tests:

  - an optional field with an empty set validates;
  - a required field with an empty set is refused with a message naming the field;
  - a model carrying **two** required `ConceptsField`s refuses on each of them independently — one
    empty and the other populated, then the reverse, then both empty reporting both. This is the case
    the once-per-class install would silently skip, and it fails against a closed-over wrapper;
  - an unsaved instance passes `full_clean()` without raising `ValueError`;
  - a record with both a bad character field and an empty required set reports **both** errors;
  - the form halves, required and optional, through a real `ModelForm`.

## US-6 — A vocabulary that has not been imported yet (#107, P2)

- **T010** — Widen the system check (FR-003, FR-004).

  `checks.py` filters `isinstance(field, ConceptField)` over `model._meta.get_fields()`. Widen it to
  cover both field types and change nothing else: same warning id, same single query for the distinct
  slugs, same silence on `DatabaseError`, same hint.

  This is the one task permitted to touch existing tests, and only to **extend** them —
  `tests/test_checks.py` keeps every assertion it has, and gains the multiple-value cases: a
  `ConceptsField` naming an absent vocabulary is reported; one naming a present vocabulary is not;
  a model carrying both field types against one absent vocabulary reports both fields; the
  unmigrated-database path stays silent. Assert the real condition, not a mock — the existing tests
  show how.

  Also assert here that `makemigrations`, `migrate` and the suite all succeed against a model naming
  a vocabulary no fixture creates, which is US-6's first scenario and the whole reason the check is a
  warning rather than an error.

## US-7 — Translatable messages, documentation, and reusable test material (#108, P3)

- **T011** — i18n audit and documentation (FR-012, FR-013, Articles VI and XII).

  Audit every string the new code puts in front of a person: `help_text` and validation messages are
  wrapped with `gettext_lazy` and use named placeholders so the message identifiers stay static. The
  `TypeError`s refusing fixed kwargs are developer diagnostics and are exempt, as they are on
  `ConceptField`.

  README gains the multiple-value declaration, the readback of labels and identifiers, what required
  and optional mean for it, and a query-cost note pointing at `prefetch_related` — the plural
  accessors will issue a query per record without it. **State the delete guarantee's real boundary
  rather than overstating it:** it holds for anything going through the ORM, including a bulk
  queryset delete, and not for SQL issued outside Django, because Django emits no `ON DELETE` clause
  for any relation (R6). Add the sentence about a consuming model that overrides `full_clean` after
  declaring the field (D8).

  `CONTEXT.md` gains the term this feature puts into a consuming project's code, reconciled with the
  entry FS-009 added. CHANGELOG records the addition.

  Public markdown is humanized before it lands, per the repo's documentation standard, and carries no
  internal process vocabulary.
