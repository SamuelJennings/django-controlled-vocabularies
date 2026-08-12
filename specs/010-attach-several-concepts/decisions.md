# Decisions — 010 Attach several concepts from a chosen vocabulary to a model

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.
The spec is the contract. This file is why the contract reads the way it does.

The single-value field ([#86](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/86),
`specs/009-attach-concept-to-model/`) settled naming by slug, the missing-vocabulary check, the
constraint's enforcement layer and the label readback, and those decisions are inherited here rather
than retaken. What follows is only what a *set* of concepts makes different.

## D1 — The set is unordered

The maintainer's decision at intake.

An order over a record's concepts is not free. It has to live somewhere, and the only place it can
live is on the membership itself, which means every consuming model in every project carries a
position column forever, written on every attachment and read on every access. That is a permanent
cost paid by every consumer.

Against it, the use the issue actually describes: a dataset tagged with several methods, a
publication covering several topics. Neither reads as a sequence. Nobody asks which method came
first.

The package already has an answer for concepts that genuinely belong in an order, and it is on the
other side of the relationship. A collection (FS-004) is a curator's deliberately grouped set of
concepts with an optional order, and it lives in the vocabulary, where the person who knows the
order owns it. A consumer that needs an ordered set of concepts is describing a collection, not a
tagging field.

If ordered tagging on the consumer side is ever wanted, it arrives then as its own feature, with a
use case to shape it. Adding it now would be speculation, which Article II rules out.

**ADR:** none — a feature-level decision about this field's shape, not a standing rule.

## D2 — The constraint must bite on the relation's own write path, not only at validation

This is the one place where copying the single-value field's answer would produce a field that does
not work.

FS-009 put the vocabulary constraint at model and form validation, and that was right there,
because a single-value field's value is an attribute of the record: assign it, validate the record,
and the check runs over what you assigned. `CONTEXT.md` records the resulting rule for the whole
package — model-level rules are enforced at validation, and a bulk queryset write goes around them.

A many-valued relation breaks the premise that argument rests on. Its contents are not an attribute
of the record. They live in a separate table, they are written through the relation's own manager
after the record is saved, and validating the record does not look at them at all. The ordinary,
documented, entirely non-exotic way to attach a concept is to write the relation — and that path
would carry no constraint whatsoever. A developer would follow the obvious usage, put a concept
from the wrong vocabulary into a record, get no complaint from anything, and the field's central
guarantee would be decorative.

That is a different situation from the bulk-write bypass `CONTEXT.md` describes. A bulk write is a
deliberate step around the model layer, taken by someone who knows they are taking it. Writing a
relation through its manager is not a step around anything; it is the interface.

So the refusal holds wherever a membership is created. A write carrying several concepts is refused
whole rather than partially applied, because a half-applied write leaves the record in a state
nobody asked for and the caller has no way to discover which members landed.

What stays bypassable is a write aimed straight at the join table, which is the true equivalent of
the bulk-write case and is left exactly as permissive as every other model-level rule in this
package.

**ADR:** none yet — this is a feature-level reading of an existing standing rule rather than a new
one. If a third feature needs the same distinction, the rule in `CONTEXT.md` should be amended to
state it, and that amendment is an ADR.

## D3 — Required means at least one concept, checked at validation

"Required" has an unambiguous meaning for an ordinary field: the column rejects null. A many-valued
relation has no column and therefore no empty state to reject, so the word has to be given a
meaning deliberately or every consumer will invent one.

The meaning chosen is the one Django's own forms already use for this shape: a required
many-valued field demands at least one selection. Taking it any further — enforcing it in the
database — is not possible without a trigger, because the record must exist before its memberships
can be written, so there is an instant in every single successful save where the set is empty and
correct.

That instant is also why this is a validation rule and not a save-time refusal. Refusing to save a
record whose set is empty would refuse the first half of every legitimate write.

A project that writes memberships without validating gets the same latitude it gets from every
other model-level rule here, which is the consistency `CONTEXT.md` already documents.

**ADR:** none — a feature-level decision about this field's declaration options.

## D4 — Attaching a concept twice is a set operation, not an error

A record either holds a concept or it does not. There is no reading of the feature under which a
record holds a concept twice, and no consumer has anything to do with the information that it was
attached again.

Refusing the second attachment would mean every caller checks membership before every write, which
is work for no benefit and a race in any concurrent path.

**ADR:** none.

## D5 — Deleting a consuming record removes its memberships and keeps the concepts

The protection Article IX requires runs one way: a curator must not be able to pull a concept out
from under a record. It says nothing about the record, and a record that could not be deleted
because it happened to be tagged would make the field a liability to declare.

This matches the single-value field exactly, where deleting the record leaves the concept alone,
and it is the only reading consistent with what the concepts are — shared reference data that
outlives any particular consumer of it.

**ADR:** none.

## D6 — Whether the two fields share an implementation is a design question, not a spec one

The obvious move on reading this feature is to factor the vocabulary constraint, the check and the
readback out of the single-value field and have both fields use the shared thing. It may well be
right. It is not the spec's decision, and this feature does not assume it.

Article III is explicit that an abstraction is earned by a present, concrete second use rather than
assumed, and this feature is exactly that second use — which is an argument for extracting, not a
licence to have already done so. The judgement belongs in `plan.md`, made against the two
implementations once both shapes are known, and the outcome has to hold up at design review either
way. What the spec fixes is that the two fields present the same idea to a developer, not that they
are built the same way.

**ADR:** none at spec time. If the plan does extract a shared base, that is a public extension point
and Article VIII makes it part of the Python API contract, so it wants an ADR then.

## D7 — The two fields do not share an implementation (resolves D6)

Taken at S3 with both shapes in view, which is what D6 said it would take.

The overlap is smaller than the two features' matching prose suggests. `research.md` R1 to R6
establish that every mechanism differs: `ForeignKey` against `ManyToManyField`, `validate()` against
an `m2m_changed` receiver, an inherited `on_delete=PROTECT` against a generated through model, a
column's `null=False` against a validation hook installed on the consuming class. What actually
repeats is storing and stripping the `vocabulary` kwarg — about six lines — and the shape of the
contributed accessors.

A base class holding six lines of kwarg handling would have to sit above two classes with different
parents, so it would be a mixin invented to avoid a small duplication rather than a shared concept.
Article III's own instruction covers the case: prefer duplication over the wrong abstraction. The
next reader of a declaration should find out what it does in one hop.

One thing is genuinely shared and is treated that way: the system check already walks every field of
every model, and gains a second type in its filter. A widened filter is not an abstraction.

**ADR:** none — declining to extract is the status quo, and nothing downstream inherits it. If a
third consumption field ever arrives, the question is properly reopened then, and by that point an
extraction would have three uses to shape it.

## D8 — The required-set rule is installed onto `full_clean`, guarded on the primary key

D3 fixed the meaning of required. This fixes where it runs, and the constraints are not stylistic.

Django gives a field no hook into model validation for a many-valued relation: `full_clean()` calls
`clean_fields()`, which iterates `_meta.fields`, which excludes many-to-many by an explicit filter
(`research.md` R2). Either the rule runs at the form layer only — which would leave FR-010's first
half unimplementable as approved — or the field installs the check itself. It installs it, once per
consuming class, delegating to the original.

**One installation, every field.** The wrapper is installed once per class, so it cannot be bound to
the field that triggered the installation — a second required `ConceptsField` on the same model would
then go unenforced with nothing raising. It resolves the class's required `ConceptsField`s at call
time and applies FR-010 to each.

Two further constraints came out of the probe rather than out of taste:

- **An unsaved record is skipped.** Touching the relation descriptor when the primary key is `None`
  raises `ValueError`, and `full_clean` catches only `ValidationError`, so an unguarded check turns
  an ordinary `ModelForm.is_valid()` on a new object into an uncaught crash. It is also the correct
  semantic: a record exists before its memberships can, so an empty set on an unsaved record is the
  right intermediate state of every legitimate creation.
- **Other errors survive.** The wrapped `full_clean` raises before the added check runs, so the check
  catches that `ValidationError`, merges its own message into the error dictionary under the field's
  name, and re-raises. A record with a bad character field and an empty required set reports both.

The cost is honest: this is the most invasive thing the feature does, because it modifies a class the
package does not own. It is bounded — one wrapper per class, delegating, merging — and it is the
price of `full_clean()` meaning what the spec says it means. A consuming model that overrides
`full_clean` after declaring the field would shadow it, which the README states.

**ADR:** none — a mechanism internal to this field, not a rule anything else inherits. It becomes
ADR-worthy only if a second feature needs the same installation trick, at which point the pattern is
the decision rather than this instance of it.

## D9 — A declaration names zero, one, or several vocabularies

Raised by the maintainer on 2026-08-12, after the design review and before any code existed. It
supersedes the part of D2's context that assumed exactly one vocabulary, and it replaces FR-002's
refusal of an unnamed one.

The original requirement was written from the single-value field's shape, where naming exactly one
vocabulary is the whole point, and it carried that assumption across without re-examining it. The
argument for refusing an unnamed vocabulary — that an unconstrained field is a plain many-to-many
and offers none of this field's guarantees — turns out to be wrong on its own terms. An
unconstrained `ConceptsField` still protects its references from deletion, still reads back labels
and identifiers, and still enforces the required-set rule. Those are three of the five guarantees,
and they are the three a plain many-to-many does not give you.

The use case is ordinary rather than exotic. Research metadata routinely carries keywords drawn
from whatever the project has imported, and more often from a named handful of published schemes
than from exactly one. A field that cannot express either shape sends those projects back to the
hand-rolled relation this package exists to remove.

**Three shapes, one parameter.** `vocabulary="rock-type"` restricts to one. `vocabulary=["gcmd",
"agu-index"]` restricts to the union. Omitting it restricts nothing. All three are the same `Q`
construction — `scheme__slug`, `scheme__slug__in`, or no filter at all — so the list form costs
almost nothing beyond the bare omission, and it is the form most research profiles actually want:
"keywords from GCMD or AGU" is a boundary, and without a list the only way to name two vocabularies
would be to accept every vocabulary.

**What is given up, stated rather than implied.** A field naming no vocabulary makes no promise
about which concepts land in it. The write-path refusal has nothing to enforce, the form offers
every concept, and the system check has no vocabulary that could be missing so it reports nothing.
The README says this in as many words. A field that quietly offers a weaker guarantee than its
siblings is worse than one that says what it does not do.

**ADR:** none — a decision about this field's declaration options, taken before release, with no
existing behaviour to supersede. Article VIII's data contract is untouched: nothing here changes a
concept's URI or its serialized form.
