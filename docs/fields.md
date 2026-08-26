# Attaching concepts to your models

Two model fields attach concepts to your own records: `ConceptField` for one concept, and
`ConceptsField` for several. Both can be restricted to the vocabularies you name, and narrowed
further to part of a vocabulary.

## Attaching a concept to your model

`ConceptField` is a `ForeignKey` to `Concept`, optionally restricted to the vocabularies you name.
`vocabulary` takes three shapes:

```python
from django.db import models

from controlled_vocabularies.fields import ConceptField


class Specimen(models.Model):
    name = models.CharField(max_length=200)
    rock_type = ConceptField(vocabulary="rock-type")                     # one vocabulary
    dominant_material = ConceptField(vocabulary=["igneous", "mineral"])  # several
    keyword = ConceptField(null=True, blank=True)                        # no vocabulary named
```

`vocabulary` names the owning `ConceptScheme` by its slug rather than by a database relation. A
field declaration is read when Python imports the module, and a vocabulary is rows in a table that
may not exist yet, so the slug is all the field can carry.

`vocabulary="rock-type"` restricts to one vocabulary. A list restricts to the union of the named
vocabularies, and the refusal names every vocabulary the field accepts. Leaving `vocabulary` out
entirely restricts nothing: any concept in the database is a valid choice. That last shape is for a
field drawing on whatever a project has imported rather than one fixed list.

When the field names at least one vocabulary, only a concept whose `scheme.slug` matches is offered
as a form choice or accepted by `full_clean()`. A concept from any other vocabulary is refused.
Deleting a concept a record still references is refused whichever shape you declare
(`on_delete=PROTECT`), whether the delete reaches it directly or cascades down from its scheme.

Reading a concept back:

```python
specimen.rock_type              # the attached Concept, or None
specimen.get_rock_type_label()  # its preferred label in the active language, falling
                                # back to the vocabulary's default language
specimen.get_rock_type_uri()    # its URI
```

If `"rock-type"` has not been imported yet, which is the state of a fresh install before the
vocabulary's own import step has run, nothing about the field declaration fails. `manage.py check`
reports a warning (`controlled_vocabularies.W001`) naming the model, the field, and the missing
slug. If the vocabulary genuinely arrives in a later deployment step, silence the warning with
`SILENCED_SYSTEM_CHECKS`.

Reading `get_<field>_label()` on every row of a list costs a query for the concept and one for its
scheme, plus one for its labels when the active language is not the vocabulary's default, per row.
`select_related("rock_type__scheme")` and `prefetch_related("rock_type__labels")` collapse that
back to a fixed number of queries for the whole list.

## Attaching several concepts to your model

`ConceptsField` is the many-to-many counterpart: several concepts on one record instead of one.
`vocabulary` takes the same three shapes it takes on `ConceptField`, and means the same thing by
each:

```python
from django.db import models

from controlled_vocabularies.fields import ConceptsField


class Sample(models.Model):
    name = models.CharField(max_length=200)
    rock_types = ConceptsField(vocabulary=["igneous", "sedimentary"])  # several vocabularies
    keywords = ConceptsField(blank=True)  # no vocabulary named
```

One slug restricts to that vocabulary, a list restricts to the union of the named vocabularies, and
leaving `vocabulary` out — as `keywords` does above — restricts nothing. A concept outside the
named vocabularies is refused, and the refusal names every vocabulary the field accepts.

Reading concepts back:

```python
sample.rock_types                    # the many-to-many manager
sample.get_rock_types_labels()       # a list of preferred labels, active language with fallback
sample.get_rock_types_uris()         # a list of URIs, same order
```

Both accessors return an empty list for a record holding nothing, including one that has not been
saved yet, rather than raising.

**Required and optional.** `blank=True`, as on `keywords` above, makes the field optional: a record
can hold zero concepts. Without it, as on `rock_types`, the field is required, and required means at
least one concept attached. Django gives a many-to-many field no hook into ordinary field
validation, so this is enforced when `full_clean()` runs rather than by the database — a
`ModelForm` or an explicit `full_clean()` call catches an empty required field, a plain `.save()`
does not. A record cannot hold any concepts before it has a primary key, so the check is skipped on
an unsaved instance. If your own model overrides `full_clean()` after declaring the field, your
override shadows this check, and you'll need to call it yourself or reproduce it.

**Query cost.** `get_<field>_labels()` and `get_<field>_uris()` issue a query for the field's
concepts, and a further query per concept for its scheme and its labels — the same per-concept cost
`ConceptField`'s singular accessors carry, multiplied by however many concepts a record holds. Over
a list of records that's at least one query per record. `prefetch_related("rock_types__scheme",
"rock_types__labels")` collapses that back to a fixed number of queries for the whole list.

**What every shape guarantees, and what the unrestricted one gives up.** Naming one vocabulary,
several, or none all give a record the same three things: a concept it already holds cannot be
deleted out from under it, its attached concepts read back by label and by URI, and required still
means at least one. Naming one or several vocabularies adds a fourth guarantee on top — a concept
outside those vocabularies is refused, both by a form built from the model and by the relation
itself, in either direction, at the moment the membership is written.

A field naming no vocabulary gives up only that fourth guarantee, and nothing else. Said plainly, so
it needn't be inferred:

- It places **no restriction** on which concepts a record can hold — any concept in the database is
  accepted.
- A form built from the model offers **every concept in the database** as a choice, not a filtered
  subset. On an installation with several vocabularies imported, that can be a genuinely long list
  of choices in an ordinary select widget — sooner than a restricted field would ever reach.
- `manage.py check` has no named vocabulary that could be missing, so it reports **nothing** for
  this field.

It still deletes-protects, reads back, and enforces "required" exactly as a restricted field does.

**The delete guarantee's real boundary.** "Cannot be deleted out from under it" holds for anything
that goes through the Django ORM — a single instance, and a bulk queryset `.delete()` alike, since
Django applies `on_delete=PROTECT` to both the same way. It does not hold for a `DELETE` issued
directly against the database outside Django — raw SQL, a database console, a migration that drops
rows without going through the ORM — because Django never writes an `ON DELETE` clause into the
schema for any relation. The protection lives in application code, not in a database constraint.

## Restricting a field to part of a vocabulary

Naming a vocabulary offers every concept it holds. Large vocabularies are often too much to put in
front of someone filling in one field. `ConceptField` and `ConceptsField` both take one more
argument on top of `vocabulary` for this: `collection`, `concepts` or `branch`. Both fields accept
the same shapes with the same effect.

```python
from django.db import models

from controlled_vocabularies.fields import ConceptField


class CoreSample(models.Model):
    name = models.CharField(max_length=200)

    # Only concepts in the "core-samples" collection of "rock-type".
    rock_type = ConceptField(vocabulary="rock-type", collection="core-samples")

    # Only "granite" and "basalt" themselves, named directly.
    # rock_type = ConceptField(vocabulary="rock-type", concepts=["granite", "basalt"])

    # "igneous" itself and everything narrower than it, at any depth.
    # rock_type = ConceptField(vocabulary="rock-type", branch="igneous")
```

Use `collection` where a curator has already grouped the concepts the field should offer. The group
is then maintained in the vocabulary editor rather than in your code, which is usually what you
want if it changes at all. `concepts` suits a short list that will not change often and does not
earn a collection of its own. `branch` suits a field whose subject is a whole part of the
hierarchy, such as everything under "igneous", where naming each member by hand would go stale the
moment the publisher adds a term.

A restriction narrows one vocabulary and never several, so declaring one alongside more than one
`vocabulary` slug is refused when the module is imported, before the app starts. The three
arguments also exclude each other, and for the same reason: a field naming two of them has no
single meaning a reader could recover from the code. A field carries at most one restriction.

The target a restriction names does not have to exist when the field is declared, any more than an
unrestricted field's own `vocabulary` does. If it never arrives, or arrives misspelled, the field
offers nothing at all rather than raising. Every choice and every search comes back empty, which
looks the same from outside as a vocabulary that has not been imported. `manage.py check` catches
it: `controlled_vocabularies.W005` names the model, the field and the missing target, the way
`controlled_vocabularies.W001` already does for an absent vocabulary.

A branch restriction reads the hierarchy fresh on each request rather than caching it, so every
search against a deeply nested branch walks it again from the root down. On a form the public can
reach, a deep branch is worth choosing deliberately.

Marking a collection `ordered` in the vocabulary editor buys a field restricted to it one more
thing. The concept search offers the collection in the curator's own sequence while the search box
is still empty, then falls back to relevance order as soon as someone types. No order is promised
anywhere else, including a `ModelForm`'s rendered choices and any unordered collection.

---

Next: [choosing a concept](search.md).
