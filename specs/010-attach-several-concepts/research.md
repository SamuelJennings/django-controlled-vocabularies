# Research — 010 Attach several concepts from a chosen vocabulary to a model

Phase 0. Every unknown the plan depends on, resolved against Django's own source in the project's
virtualenv (Django 5.2.16) rather than against documentation or recollection. Line numbers are from
that installed copy. Where a reading was uncertain, it was confirmed by running a throwaway app
outside the repo tree, and the observed output is quoted.

The governing fact for this whole feature: **almost nothing FS-009 relied on carries over.** The
single-value field got its constraint, its validation and its delete protection from
`ForeignKey`'s own machinery. A many-valued relation supplies none of the three, and each has to be
built. R1 to R3 establish that; R4 to R6 settle how.

## R1 — `limit_choices_to` restricts a form and nothing else

**Question.** FS-009's R1 found that `limit_choices_to` gave both the form restriction (FR-006) and
model validation (FR-005) from one declaration. FR-005 and FR-006 here read almost identically, so
does the same single mechanism serve both?

**Finding.** No. On a many-valued relation `limit_choices_to` is a form-layer feature only.

`apply_limit_choices_to_to_formfield` (`forms/models.py:123-138`) rewrites the form field's queryset
with an `Exists` subquery, and `ModelMultipleChoiceField._check_values` (`forms/models.py:1621-1657`)
rejects a submitted primary key outside that queryset with `invalid_choice`. So FR-006 is met, and a
tampered form post is met with it.

Nothing else reads it. `related_descriptors.py`'s `_add_items` and `_get_target_ids`
(lines 1420-1450, 1505-1570) validate the model type, the database, and a non-null primary key —
never `limit_choices_to`. `full_clean()` never reaches it either, for the reason in R2.

Observed, with `limit_choices_to={"name__startswith": "ok"}`:

```
form queryset: ['ok-one', 'ok-four'] | all concepts: ['ok-one', 'nope-two', 'ok-four']
out-of-limit choice is_valid: False | errors: {'concepts': ['Select a valid choice. …']}
.add() of out-of-limit concept succeeded: True
full_clean() after out-of-limit add: PASSED
```

**Consequence for the plan.** `limit_choices_to` still earns its place — it satisfies FR-006 and
costs one line. It cannot satisfy FR-005, and a plan that assumed the FS-009 shape would ship a
field whose central guarantee holds only for form submissions. This is decision D2 in
`decisions.md`, and the empirical line above is its evidence.

## R2 — `full_clean()` does not see a many-valued relation at all

**Question.** FR-005 and FR-010 both say "when the record is validated". What does record validation
actually cover?

**Finding.** Not this. `Model.full_clean()` (`db/models/base.py:1634-1678`) calls `clean_fields()`,
`clean()`, `validate_unique()` and `validate_constraints()`. `clean_fields()` (lines 1681-1706)
iterates `self._meta.fields`, and `Options.fields` (`db/models/options.py:523-563`) is documented as
returning forward fields *excluding* `ManyToManyField`, enforced by an explicit
`is_not_an_m2m_field` filter. Many-valued fields live in the separate `Options.many_to_many`
property, which nothing in the validation path reads.

```
full_clean() with empty required m2m: PASSED (no error raised)
Item._meta.fields: ['id', 'title']
Item._meta.many_to_many: ['concepts']
```

**Consequence for the plan.** Two requirements lose their assumed home. FR-005's refusal has to be
attached to the write itself (R3), and FR-010's required-set rule has to be installed onto
validation deliberately (R5).

## R3 — `m2m_changed` is the write-path hook, and it survives an explicit `through`

**Question.** If validation cannot refuse a foreign concept, what can, and does it still work once
the relation carries an explicit through model (which R4 shows is needed for a different reason)?

**Finding.** `m2m_changed` fires on `pre_add` for `.add()` and `.set()`, and an explicit through
model does not suppress it. The only path that skips the signal is the `bulk_create` fast path, and
`_get_add_plan` (`related_descriptors.py:1470-1500`) disables that fast path whenever the through is
not auto-created or a listener is connected:

```python
can_ignore_conflicts = (
    self.through._meta.auto_created is not False
    and connections[db].features.supports_ignore_conflicts
)
must_send_signals = (...) and (signals.m2m_changed.has_listeners(self.through))
```

`set()` (lines 1325-1352) is implemented as `remove()` + `add()`, so it passes through the same
hook. The signal's `sender` is the through model, so a receiver connects with `sender=<through>`.

Two details the plan depends on:

- `pk_set` on `pre_add` is `missing_target_ids` (line 1531) — concepts already attached are excluded.
  Re-attaching a concept a record already holds fires nothing and writes nothing, which is decision
  D4 satisfied by Django itself rather than by code of ours.
- Raising from a `pre_add` receiver aborts the write before any row is inserted, which is what FR-005
  means by a mixed write being refused whole.

```
through: Link | _meta.auto_created: False
.add() signals: [('pre_add', [1]), ('post_add', [1])]
.set() signals: [('pre_add', [2]), ('post_add', [2])]
```

**Consequence for the plan.** FR-005's refusal is a `pre_add` receiver that checks the incoming
primary keys against the named vocabulary in one query and raises `ValidationError` naming it. A
write straight at the through table's own manager bypasses this, which is exactly the bypass the
spec's Assumptions already declare.

## R4 — Delete protection needs an explicit through model, because the auto-created one cascades

**Question.** FS-009 got FR-007 free from `on_delete=PROTECT` on the foreign key. Where does a
many-valued relation put that?

**Finding.** Django's auto-created join model gives both of its foreign keys `on_delete=CASCADE`, so
deleting a concept silently removes every membership pointing at it — the exact failure US-3 exists
to prevent, and one that leaves no trace.

`PROTECT` (`db/models/deletion.py:34-44`) raises unconditionally once the collector reaches it, and
both delete paths reach it. `Collector.collect()` (lines 308-357) walks the candidate relations,
calls the handler at line 345 and re-raises an aggregated `ProtectedError` at 349-357;
`can_fast_delete` (lines 185-227) returns `False` whenever a related foreign key's `on_delete` is not
`DO_NOTHING`, so the fast path cannot skip it. `Model.delete` (`base.py:1272-1281`) and
`QuerySet.delete` (`query.py:1177-1201`) both build that same collector.

```
instance.delete():  ProtectedError -> Cannot delete some instances of model 'Concept' …
queryset.delete():  ProtectedError -> Cannot delete some instances of model 'Concept' …
unrelated queryset.delete(): (1, {'probeapp.Concept': 1})
```

That covers both halves of US-3's first two scenarios, and the third — deleting the vocabulary —
follows without extra work, because collecting a `ConceptScheme` cascades to its concepts and the
collector then meets the protected membership.

**Consequence for the plan.** The relation carries a through model whose foreign key to `Concept` is
`PROTECT`. Since the source model belongs to the consuming project and is unknown here, that through
model is generated per declaration, the way Django generates its own. R6 settles whether that
survives migrations and deconstruction.

## R5 — `blank=False` covers the form half of "required" and nothing else

**Question.** FR-010 wants required to mean at least one concept, at validation and in a form.

**Finding.** The form half is free. `Field.formfield` (`db/models/fields/__init__.py:1101-1105`)
derives `required` from `not self.blank`, `ManyToManyField.formfield`
(`related.py:2041-2054`) passes it to `ModelMultipleChoiceField`, and that field's `clean`
(`forms/models.py:1605-1611`) raises `required` on an empty selection.

```
formfield class: ModelMultipleChoiceField | required: True
empty selection is_valid: False | errors: {'concepts': ['This field is required.']}
```

The model half is absent, per R2, and the ordering constraint underneath it is real rather than
incidental: `ModelForm._post_clean` (`forms/models.py:474-500`) calls `full_clean()` on the instance
*before* `_save_m2m` writes the selection, so a required-set check that ran on an unsaved instance
would refuse every legitimate creation. This is decision D3 restated as a mechanism.

**Consequence for the plan.** The required rule is installed onto `full_clean` by the field itself,
and it applies only to a record that already has a primary key. An unsaved record is skipped,
because its memberships cannot exist yet. The two halves then compose: the form catches an empty
submission, and the model catches a record left empty afterwards.

## R6 — The through model is generated per declaration, and stays invisible

**Question.** R4 says the relation needs a through model whose foreign key to `Concept` is
`PROTECT`. The source model belongs to the consuming project, so no through model can be written by
hand in this package. Can one be generated, and does the rest of Django accept it?

**Finding.** Yes, and Django already does exactly this for every ordinary many-valued relation.
`create_many_to_many_intermediary_model()` (`related.py:1308-1361`) builds the join model at
`contribute_to_class` time, and the only change this feature needs is `on_delete=PROTECT` instead of
`CASCADE` on the foreign key to the target. The generated model's `Meta.auto_created` is set to the
*owning model class* — a truthy value, not the boolean it looks like — and that one attribute is
what keeps it invisible:

- `deconstruct()` (`related.py:1822-1826`) emits `through` only when `not …auto_created` is true, so
  an auto-created through is never written into a migration's field kwargs.
- The schema editor creates and drops the table as a side effect of the owning model
  (`backends/base/schema.py:535-537`), gated on the same attribute.
- Migration state never holds it, because `ProjectState.from_apps` (`migrations/state.py:592-597`)
  calls `apps.get_models()`, which defaults `include_auto_created=False`
  (`apps/registry.py:169-179`).

The whole approach was run end to end in a throwaway app. The migration carries one `CreateModel`
for the owning model with the field on it and no operation for the join model, the table is created
anyway, `makemigrations --check` is clean afterwards, `deconstruct()` emits no `through`, `.add()`
and `.set()` still fire `m2m_changed`, deleting a referenced concept raises `ProtectedError` from
both `instance.delete()` and `queryset.delete()`, and deleting the consuming record removes only the
join rows:

```
Item.delete() -> (3, {'probe4.Item_concepts': 2, 'probe4.Item': 1})
concepts still present: ['c1', 'c2']
join table DDL: CREATE TABLE "probe4_item_concepts" (… "concept_id" integer NOT NULL REFERENCES …)
makemigrations --check: CLEAN (exit 0, no changes)
```

Historical models rendered from a migration get the protection too, because the migration names the
field subclass by import path and state rendering re-runs its `contribute_to_class`.

**Two consequences the plan has to carry.**

First, `on_delete` never reaches the DDL — Django emits no `ON DELETE` clause for any relation, and
`PROTECT` is enforced entirely by the Python collector. The join table is byte-identical to a stock
one. So the guarantee holds for the ORM, including a queryset delete, and does not hold against SQL
issued outside Django. That is the same boundary the rest of the package already has, and the README
should not overstate it.

Second, and easier to get wrong: because `auto_created` is truthy, `_get_add_plan`'s
`can_ignore_conflicts` becomes true again, so Django will take the `bulk_create(ignore_conflicts)`
fast path — which skips `m2m_changed` entirely — **whenever no receiver is connected for that
through model**. The vocabulary check of R3 therefore depends on its receiver being connected before
any write can happen. Connecting it inside `contribute_to_class`, against the through model just
generated for that declaration, is what makes that unconditional: the field cannot exist on a model
without its own guard attached. A receiver connected later, from `AppConfig.ready()` or a module
imported on demand, would leave a window in which writes are silently unchecked.

**Deconstruction of the field itself** follows FS-009's pattern. `RelatedField.deconstruct`
(`related.py:384-392`) emits `limit_choices_to` whenever it is truthy and `ManyToManyField.deconstruct`
always emits `to`, while `Field.clone()` (`fields/__init__.py:666-673`) rebuilds the field by calling
`__init__` with exactly those kwargs. Both must be stripped and `vocabulary` recorded instead, or
`makemigrations`, `makemigrations --check`, `migrate` and pytest-django's test-database build all
fail at clone time. The research agent confirmed the failure mode directly: a subclass that rejects
an emitted kwarg raises `TypeError` from `clone()`, and one that silently pops it without recording a
replacement loses it from the deconstruction altogether, so migration state and field definition
diverge without an error.

## R7 — Indexing

Article XIII requires the indexing choice to be deliberate and recorded. The membership table's two
foreign keys each carry Django's automatic index, and the pair carries the uniqueness constraint the
join needs. The queries this feature issues are "which concepts does this record hold" (source
side), "does any record hold this concept" (the delete guard, served by the collector's own reverse
lookup), and the `pre_add` check's lookup of incoming concepts by primary key and vocabulary. Each
is served by an existing index, so the plan adds none.
