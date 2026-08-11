# Research — 009 Attach a concept from a chosen vocabulary to a model

Phase 0. Every unknown the plan depends on, resolved against Django's own source in the project's
virtualenv (Django 5.2, `django/db/models/fields/related.py` and `django/core/checks/`) rather than
against documentation or recollection. Line numbers are from that installed copy.

## R1 — `limit_choices_to` gives both the form restriction and model validation, lazily

**Question.** FR-005 wants a concept from another vocabulary refused at validation, and FR-006 wants
a form to offer only the named vocabulary's concepts. Are those two mechanisms or one? And does
either of them query the database when the field is declared, which FR-003 forbids?

**Finding.** One mechanism, and it queries nothing at declaration time.

`ForeignKey.validate()` (related.py:1122) filters the target queryset by the value and then applies
`qs.complex_filter(self.get_limit_choices_to())` before checking `.exists()`. A value outside
`limit_choices_to` therefore raises `ValidationError` from `full_clean()` with code `invalid`.

`ForeignKey.formfield()` passes `limit_choices_to` through to the form field
(related.py:940–945), and `apply_limit_choices_to_to_formfield` narrows the queryset. So the choices
a `ModelForm` offers are restricted by the same declaration.

`limit_choices_to` accepts a `Q` object, which is a lazily-evaluated expression tree and issues no
query when constructed. `Q(scheme__slug=<slug>)` therefore satisfies FR-003: the declaration holds a
string and a `Q`, and the database is first touched when something validates or renders.

**Consequence for the plan.** The field sets `limit_choices_to=Q(scheme__slug=vocabulary)` in
`__init__`. No custom queryset, no custom form field, no descriptor. Two functional requirements are
met by one line, which is the Article II and Article III answer.

**What still needs writing.** The default `invalid` message reads "concept instance with id 4 does
not exist", which is wrong twice over — the concept does exist, and the message does not name the
vocabulary FR-005 requires. So `error_messages["invalid"]` is overridden with a translatable message
carrying a named placeholder. That is a message override, not a validation override.

## R2 — `deconstruct()` must strip three inherited kwargs

**Question.** What does a `ForeignKey` subclass have to do to migrate cleanly?

**Finding.** `ForeignKey.deconstruct()` emits `to` (related.py:725–729), `on_delete`
(related.py:716), and — from `ForeignObject.deconstruct()` — `limit_choices_to` whenever it is truthy
(related.py:386–387).

All three are fixed by this field rather than supplied by the consumer, and `limit_choices_to` is
derived from `vocabulary`. Left alone, every generated migration would carry a redundant `to`, a
redundant `on_delete`, and a `Q` object literal that duplicates the `vocabulary` string and would
drift from it the moment either changed.

**Consequence for the plan.** `ConceptField.deconstruct()` deletes `to`, `on_delete` and
`limit_choices_to` from the returned kwargs and adds `vocabulary`. The migration then records the
one thing the consumer actually wrote. A round-trip test — deconstruct, reconstruct from the emitted
kwargs, compare — is the cheapest guard against this rotting, and `makemigrations --check` after
`migrate` catches the rest.

## R3 — A system check runs before `migrate`, so it has to be a warning

**Question.** The spec asserts that an `Error` would block the migration that creates the tables the
vocabulary is imported into. Is that true?

**Finding.** Yes. `BaseCommand.requires_system_checks` defaults to `"__all__"`
(`core/management/base.py:270`), and neither `migrate` nor `makemigrations` overrides it. Both
therefore run every registered check before doing any work, and a check returning an `Error` raises
`SystemCheckError` and aborts the command.

Tag choice matters and cuts against the obvious answer. `Tags.database` looks right, but
database-tagged checks are filtered out unless `--database` is passed to `manage.py check`
(`core/checks/registry.py:85–86` plus `commands/check.py:48`), which is exactly backwards for a check
whose whole purpose is to surface in an ordinary CI `manage.py check`. So the check is registered
untagged.

`SILENCED_SYSTEM_CHECKS` filters by check ID, so a stable ID is all FR-004's silencing clause needs.

**Consequence for the plan.** One app-level check function, registered untagged in the app config's
`ready()`, returning `Warning` objects with a stable ID. It walks `apps.get_models()`, collects every
declared `ConceptField`, and resolves the distinct vocabulary slugs in **one** query rather than one
per field.

**The failure mode this must survive.** The check runs on a database with no tables — the first
`migrate` on an empty database is precisely that state, and it is also the state every CI run starts
in. A query against `ConceptScheme` there raises `ProgrammingError` (Postgres) or `OperationalError`
(SQLite), and an unreached database raises `OperationalError` too. All are subclasses of
`django.db.DatabaseError`, so one `except DatabaseError: return []` covers every case FR-004 names.
This needs a test that runs the check against an unmigrated connection, not a mocked one.

## R4 — The label fallback belongs on `Concept`, not on the field

**Question.** Where does FR-008's active-language-then-default resolution live?

**Finding.** `Concept.preferred_label(language=None)` (models.py:731) returns `self.label` when
`language` is `None` or matches the scheme's effective default, and otherwise the matching
`ConceptLabel` row's text, or `None`. It reads `self.labels.all()` deliberately so a caller's
`prefetch_related("labels")` collapses the read path to one query.

The resolution FR-008 asks for is a composition of two calls to that method, and it is a property of
a **concept**, not of the field pointing at one. #87 will need the identical resolution for each
concept in a set, and a serializer or an export rendering a concept reached any other way needs it
too.

**Consequence for the plan.** Add `Concept.display_label()` — active language via
`django.utils.translation.get_language()`, falling back to the scheme's default. `preferred_label()`
is not touched, which keeps the "did this language have a label?" question answerable for import
reporting and the future editor. The consuming model then gets `get_<field>_label()` and
`get_<field>_uri()`, which delegate.

**Why `get_FOO_…` rather than properties.** Django's own precedent for a derived read named after a
field is `get_FOO_display()`, contributed by `Field.contribute_to_class`. Following it means the
generated names sit in a namespace consumers already recognise as framework-generated, and cannot
collide with an ordinary attribute the way a bare `topic_label` property could. `setattr` is guarded
so a model that already defines the name is left alone rather than silently overwritten.

## R5 — `on_delete` is fixed, and the consumer may not override it

**Question.** FR-010 says ordinary field options pass through and are not silently overridden.
FR-007 requires `PROTECT`. A consumer passing `on_delete=CASCADE` would satisfy the first and break
the second.

**Finding.** These do not actually conflict, because FR-010 forbids *silent* overriding.

**Consequence for the plan.** `__init__` refuses an `on_delete` argument with a `TypeError` naming
the reason. That is a developer-facing diagnostic at import time, not a user-facing string, so
Article XII exempts it from translation. Everything else a relation takes — `null`, `blank`,
`related_name`, `related_query_name`, `verbose_name`, `help_text`, `db_index`, `db_constraint` —
passes straight through.

`PROTECT` lives in the relation, so it holds against `queryset.delete()` and against a cascade
arriving from `ConceptScheme`. Django raises `ProtectedError` in both. Deleting the vocabulary is
refused as a consequence of protecting its concepts rather than by a separate rule, which is worth
asserting in a test precisely because nothing in the code says so.

## R6 — Indexing

Article XIII requires the indexing decision to be deliberate and recorded. A `ForeignKey` creates an
index on its column by default (`db_index=True`, stripped from `deconstruct` at related.py:143–146).

Kept. The whole point of the field is that consumers filter their own records by concept, and a
consumer cannot add an index to a column this package defines the semantics of. The write cost is
one index on one integer column.

## R7 — Query cost, and what the README has to say about it

`get_<field>_label()` on a freshly-loaded record costs a query for the concept, then a query for its
labels, then a query for the scheme when the active language is not the default. Rendering a list of
records that way is the N+1 every Django project meets eventually.

Nothing in the spec requires solving it, and solving it inside the field would mean a custom manager
or descriptor caching, which is the abstraction Article III exists to refuse. What it does require
is that the README says `select_related("<field>__scheme")` and `prefetch_related("<field>__labels")`
collapse it, because a consumer who does not know the storage layout — which is the whole premise of
FR-008 — cannot work that out.

## Rejected alternatives

- **A custom descriptor exposing `record.topic_label` as a property.** Rejected: it can silently
  shadow an attribute the consuming model already defines, and it buys nothing over the
  `get_FOO_…()` naming Django already established.
- **A database `CheckConstraint` enforcing vocabulary membership.** Rejected in the spec (D4) and
  confirmed here: it needs the concept's scheme denormalised onto the consuming table, which this
  package cannot keep in step because it does not own that table's writes.
- **A `database`-tagged system check.** Rejected: those are skipped by a bare `manage.py check`,
  which is the command FR-004 exists to make useful.
- **A callable `limit_choices_to`.** Unnecessary. A `Q` is already lazy, and a callable would be
  re-evaluated per form render for no gain.
