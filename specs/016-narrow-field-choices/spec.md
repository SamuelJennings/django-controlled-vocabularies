# Feature Specification: Narrow a field's choices to part of a vocabulary

**Feature Branch**: `016-narrow-field-choices`

**Created**: 2026-08-25

**Status**: Draft

**Input**: Issue [#164](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/164) — "Some vocabularies are large. A field on a consuming model rarely wants all of one, and offering every concept in a vocabulary of thousands makes the field harder to use and makes the wrong answer easier to pick. A consuming project should be able to point a field at the part of a vocabulary that suits it, in whichever of three ways fits the vocabulary it has: the members of a named collection, an explicit list of concepts, or a named concept together with everything below it in the broader/narrower hierarchy."

**Serves**: G2 (one-field consumption — a field that can only take a whole vocabulary is a field a large vocabulary cannot be consumed through) · **Roadmap**: R3 · **Issue**: #164

> Scope note: R3 delivered the consumption fields and their vocabulary restriction. This slice adds a **second, finer restriction inside a single named vocabulary**, in three forms, and the declaration rules that keep the three from meaning something ambiguous. **Out of scope:** any change to the existing vocabulary restriction or to declarations that do not use the new arguments; making a deep hierarchy traversal fast, which is deliberately deferred (see Assumptions); creating or editing collections and relations, which is curation (R5) and import (R2, delivered); publication and deprecation (R4).

## Clarifications

### Session 2026-08-25 (intake)

Four decisions were taken with the maintainer at intake. The first changed the feature's scope; the rest decide behaviour a consumer would otherwise discover by guessing.

- **Q: A large vocabulary can be narrowed by collection, by an explicit list, or by hierarchy. The request named the first two. Is the hierarchy in scope?** → A: In scope. It is the axis that works on an imported vocabulary as it arrives: a publisher almost always ships `broader`/`narrower` edges and almost never ships collections, because a collection is a curator's own grouping. Without it, a consumer restricting an imported vocabulary has only the explicit list, which cannot express a branch and goes stale the moment the publisher adds a term. Integrated into User Story 3 and FR-004.
- **Q: What does a consumer write to name a collection, a concept, or a branch root?** → A: A slug, for all three, the way a vocabulary is already named. The alternatives considered were the concept URI and its notation. Both were rejected: the slug is what the existing vocabulary restriction already uses, so one rule covers every argument, and the maintainer confirmed slugs cover the vocabularies this is intended for. The known weakness is the one FS-009 already recorded for vocabulary slugs — a locally authored record's slug is re-derived from its name on save, so renaming one breaks declarations naming it, and the reporting in User Story 5 is what catches that. Integrated into FR-001 and Edge Cases.
- **Q: Does the hierarchy restriction include the concept it names, or only what sits below it?** → A: Inclusive. A consumer naming a branch is naming a subject area, and the branch's own term is usually the right answer where no child is more specific; the exclusive reading leaves a field short by exactly one valid choice and nothing reports it. The argument is therefore named for a branch rather than for what is under one. Integrated into FR-004 and User Story 3.
- **Q: A curator can mark a collection as ordered, which states a deliberate sequence. Does that sequence reach a field restricted to it?** → A: Yes. A collection small enough to restrict a field to is exactly the case where the sequence is visible to whoever picks a value, and if it does not reach here it reaches nowhere a consumer ever looks. The maintainer qualified it — honour it if it does not complicate the selection control — so it is specified as its own P2 story rather than folded into User Story 1, and it can be dropped without the three restrictions losing their meaning. Integrated into FR-010 and User Story 6.

### Session 2026-08-25 (coverage scan)

Three further ambiguities surfaced by the structured coverage scan over the drafted spec, resolved against the intake decisions, FS-009's precedents, and the constitution.

- **Q: What happens when a declaration combines the new restriction with several vocabularies, or combines two of the three restrictions with each other?** → A: Both are refused when the declaration is read, the way the existing fields already refuse `on_delete`, `through` and `limit_choices_to`. A restriction inside one vocabulary has no meaning across several, and two restrictions applied at once have no obvious reading — an intersection and a union are equally defensible, which is the definition of an ambiguous declaration. Refusing at declaration time rather than at validation time means the failure lands on the developer who wrote it, in the process that imports the model, rather than on whoever first submits a form. Integrated into FR-005, FR-006 and User Story 4.
- **Q: Does a restriction naming something absent from the database stop the project?** → A: No, and for exactly the reason FS-009 recorded for a missing vocabulary: collections, concepts and relations arrive by import or curation, which only a running project can perform, so refusing to boot would make a fresh install unbootstrappable. The gap is reported by the same system check FS-009 established, as a warning carrying a stable identifier, silent when the database cannot be queried at all. Integrated into FR-009 and User Story 5.
- **Q: The hierarchy is stored as edges, and the restriction is a transitive read over them. What if the stored edges contain a cycle?** → A: The traversal terminates and yields each concept once. The relation model refuses a self-relation and a reversed duplicate of an existing edge, but nothing in it walks the graph, so a longer cycle is not currently prevented from being stored. A restriction that hangs or exhausts memory on data the database was willing to accept is a defect regardless of how the data got there. Integrated into FR-004 and Edge Cases.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A field is restricted to a collection's members (Priority: P1)

A developer whose project uses a vocabulary of several thousand concepts declares a field naming that vocabulary and one of its collections. The field then accepts and offers that collection's members and nothing else. When a curator adds a concept to the collection, the field picks it up with no code change and no restart.

**Why this priority**: This is the request's own leading case, and the simplest of the three restrictions. It also establishes everything the other two reuse — resolving a target within one named vocabulary, applying a second restriction on top of the vocabulary one, and carrying that through migrations.

**Independent Test**: With a vocabulary holding a collection and concepts outside it, declare both fields restricted to the collection, confirm a member is accepted and a non-member refused, confirm the offered choices are exactly the members, then add a concept to the collection and confirm the field offers it without the declaration changing.

**Acceptance Scenarios**:

1. **Given** a field restricted to a collection, **When** a member of that collection is assigned and the record validated, **Then** validation passes.
2. **Given** the same field, **When** a concept of the named vocabulary that is not a member is assigned and the record validated, **Then** validation fails with a message naming the collection.
3. **Given** a form built from the consuming model, **When** its choices are inspected, **Then** they are exactly the collection's members.
4. **Given** the same declaration on the multi-value field, **When** a set containing a non-member is attached, **Then** the whole write is refused and the record's existing set is untouched.
5. **Given** a concept added to the collection after the project started, **When** the field's choices are next read, **Then** the new member is among them.
6. **Given** the declaration, **When** `makemigrations` runs and then `makemigrations --check`, **Then** a migration is produced and the check reports no further changes.

---

### User Story 2 - A field is restricted to a named list of concepts (Priority: P1)

A developer needs a field to take one of a handful of terms from a large vocabulary, and no collection groups exactly those terms. They list the concepts in the declaration. The field accepts those and nothing else.

**Why this priority**: It is the only restriction that needs nothing of the vocabulary's curation — no collection, no hierarchy — so it is the one that always works, on any vocabulary, however it arrived. It is also the smallest increment on top of User Story 1.

**Independent Test**: Declare both fields restricted to a list of two concepts drawn from a vocabulary holding more, confirm each listed concept is accepted, confirm an unlisted concept of the same vocabulary is refused, and confirm the offered choices are exactly the two.

**Acceptance Scenarios**:

1. **Given** a field restricted to a list of concepts, **When** a listed concept is assigned and the record validated, **Then** validation passes.
2. **Given** the same field, **When** an unlisted concept of the named vocabulary is assigned and the record validated, **Then** validation fails with a message naming the permitted concepts.
3. **Given** a form built from the consuming model, **When** its choices are inspected, **Then** they are exactly the listed concepts.
4. **Given** a declaration listing the same concept twice, **When** the model is read, **Then** the duplicate is collapsed and the field offers that concept once.
5. **Given** a declaration whose list is empty, **When** the model is read, **Then** the declaration is refused, because a field offering nothing while reading as restricted is not what the writer meant.

---

### User Story 3 - A field is restricted to a branch of the hierarchy (Priority: P1)

A developer using an imported vocabulary that arrived with its broader/narrower hierarchy intact and no collections at all declares a field naming one concept as a branch root. The field accepts that concept and every concept below it, however deep. When the publisher's next import adds terms under that root, the field picks them up.

**Why this priority**: It is the axis that works on an imported vocabulary as published, which is the case the request was raised for. Without it, the same consumer's only option is the explicit list, which cannot express a branch and is wrong again on the next import.

**Independent Test**: Build a vocabulary three levels deep, declare both fields restricted to a mid-level concept, and confirm that concept, its children and its grandchildren are all accepted while a sibling branch and the root above are refused.

**Acceptance Scenarios**:

1. **Given** a field restricted to a branch, **When** the branch root itself is assigned and the record validated, **Then** validation passes.
2. **Given** the same field, **When** a concept two levels below the root is assigned, **Then** validation passes.
3. **Given** the same field, **When** a concept in a sibling branch is assigned, **Then** validation fails with a message naming the branch.
4. **Given** the same field, **When** the concept the root is itself below is assigned, **Then** validation fails, because the restriction runs downward only.
5. **Given** a branch root with nothing below it, **When** the field's choices are read, **Then** they are exactly that one concept.
6. **Given** a concept added below the root after the project started, **When** the field's choices are next read, **Then** the new concept is among them.
7. **Given** stored hierarchy edges that form a cycle, **When** the field's choices are read, **Then** the read returns each concept once and terminates.

---

### User Story 4 - A declaration that cannot mean anything is refused (Priority: P1)

A developer writes a declaration that restricts a field to a collection while naming two vocabularies, or one that names both a collection and a branch. The model does not import. The message says which rule was broken, so the mistake is fixed where it was made rather than found by whoever first uses the form.

**Why this priority**: The two rules this story enforces are the only thing keeping the three restrictions unambiguous, and both failures are otherwise silent — a restriction quietly ignored, or one of two restrictions quietly winning. Silence here produces a field that looks constrained and is not, which is worse than the unrestricted field the developer started from.

**Independent Test**: Attempt each invalid declaration — a restriction alongside several vocabularies, a restriction alongside no vocabulary, and two restrictions together — and confirm each is refused when the declaration is read, with a message identifying the rule.

**Acceptance Scenarios**:

1. **Given** a declaration naming several vocabularies and a collection, **When** the declaration is read, **Then** it is refused with a message stating that the restriction needs exactly one vocabulary.
2. **Given** a declaration naming no vocabulary and a branch, **When** the declaration is read, **Then** it is refused for the same reason.
3. **Given** a declaration naming one vocabulary, a collection and a list of concepts, **When** the declaration is read, **Then** it is refused with a message stating that at most one restriction may be given.
4. **Given** a declaration naming one vocabulary and exactly one restriction, **When** the declaration is read, **Then** it is accepted.
5. **Given** any declaration using none of the three restrictions, **When** the declaration is read, **Then** it behaves exactly as it did before this feature existed.
6. **Given** a restriction whose slug is an empty string, **When** the declaration is read, **Then** it is refused, on the same reasoning that already refuses an empty vocabulary slug.

---

### User Story 5 - A restriction naming something absent is reported, not silent (Priority: P2)

A developer mistypes a collection slug, or names a branch root that this project's import has not brought in yet. The project still imports its models, migrates and starts. Running `manage.py check` names the field and the target it expects, so the gap shows up in CI and on deploy instead of as a form that mysteriously offers nothing.

**Why this priority**: A restriction is the one kind of declaration whose failure mode is an empty field rather than an error, and an empty field looks identical whether the target is missing, misspelt or genuinely empty. It sits below the restrictions themselves because a project whose targets are all present never reaches this story.

**Independent Test**: Declare fields naming a collection, a branch root and a concept that are each absent from the database, confirm `makemigrations`, `migrate` and the test suite all succeed, then run `check` and confirm each is reported as a warning identifying the field and the missing target.

**Acceptance Scenarios**:

1. **Given** a field restricted to a collection absent from the named vocabulary, **When** `makemigrations` and `migrate` are run, **Then** both succeed.
2. **Given** the same project, **When** `manage.py check` is run, **Then** it reports a warning identifying the field and the collection it names.
3. **Given** a field restricted to concepts of which one is absent, **When** `check` is run, **Then** the warning names the absent concept specifically rather than reporting the whole list.
4. **Given** a field restricted to a branch root absent from the vocabulary, **When** `check` is run, **Then** it reports a warning identifying the field and that root.
5. **Given** a project that silences the check by its identifier, **When** `check` is run, **Then** it reports nothing for that field.
6. **Given** a database whose tables do not exist yet, **When** `check` is run, **Then** it reports nothing rather than failing.
7. **Given** a collection that exists and holds no members, **When** `check` is run, **Then** it reports nothing, because the collection is present and empty rather than missing.

---

### User Story 6 - An ordered collection's sequence reaches the choices (Priority: P2)

A curator marks a collection ordered and arranges its members deliberately. A field restricted to that collection offers them in that order, so the sequence the curator arranged is the sequence whoever fills the form sees.

**Why this priority**: It is the only place a consumer ever sees an ordered collection's order, so without it the ordering feature has no reader. It is second-tier because the three restrictions are correct and complete without it, and the maintainer qualified it as worth having only if it does not complicate the selection control.

**Independent Test**: Restrict a field to an ordered collection whose members' sequence differs from both alphabetical and creation order, and confirm the offered choices come back in the curator's sequence; repeat with the collection unordered and confirm no sequence is promised.

**Acceptance Scenarios**:

1. **Given** a field restricted to an ordered collection, **When** its choices are read, **Then** they are in the collection's member order.
2. **Given** the same collection with a member's position changed, **When** the choices are next read, **Then** they reflect the new sequence.
3. **Given** a field restricted to a collection that is not ordered, **When** its choices are read, **Then** the restriction still holds and no particular sequence is promised.
4. **Given** an ordered collection with a member removed, **When** the choices are read, **Then** the survivors keep their relative order.

---

### User Story 7 - Translatable messages, documentation, and vocabulary (Priority: P3)

Every message these restrictions put in front of a person is translatable, the README shows a developer how to narrow a field three ways and when to reach for each, and `CONTEXT.md` records what the package now means by a restricted field.

**Why this priority**: Constitutional obligations spanning the feature rather than any one journey through it. The README point carries more weight than usual here, because the whole feature is a public declaration surface a consumer writes by hand, and there is no way to discover the three forms other than being told.

**Independent Test**: Assert no user-visible string these restrictions add is a bare literal, that the README documents all three forms and the declaration rules, that `CONTEXT.md` carries the terms, and that the CHANGELOG records the addition.

**Acceptance Scenarios**:

1. **Given** the refusal messages and the fields' `help_text`, **When** the source is inspected, **Then** each is wrapped for translation with named placeholders, per Article XII.
2. **Given** the shipped documentation, **When** the README is read, **Then** it shows each of the three restrictions, states that they need exactly one vocabulary and exclude one another, and says what happens when a named target is absent.
3. **Given** a field carrying a restriction and no `help_text` of its own, **When** its `help_text` is read, **Then** it describes a field restricted within its vocabulary rather than one offering the whole of it.
4. **Given** `CONTEXT.md`, **When** it is read, **Then** it defines the restriction this feature adds and reconciles the existing `ConceptField`/`ConceptsField` entries with it.

---

### Edge Cases

- A collection slug is unique only within its vocabulary, and a concept slug only within its vocabulary. Every target is therefore resolved inside the one named vocabulary, so a name belonging to some other vocabulary is simply absent here and reported as absent.
- A locally authored collection or concept is renamed, which re-derives its slug, and declarations naming the old slug now name nothing. The check reports it. Setting the slug explicitly is what prevents it moving.
- The named collection exists and holds no members. The field offers nothing and the check stays quiet, because the collection is present and empty rather than missing — the same distinction FS-009 drew for an empty vocabulary.
- A concept is removed from the collection, or moved out of the branch, while a record points at it. The reference survives, and the record holds a concept outside its field's restriction until it is next validated — the same outcome FS-009 recorded for a concept moved between vocabularies.
- The stored hierarchy contains a cycle. The branch read terminates and returns each concept once.
- A branch root is named and the vocabulary's hierarchy is a forest with no single root. Nothing about the restriction assumes one; it reads downward from whatever concept is named.
- A concept appears twice in the explicit list. The duplicate is collapsed, as a duplicate vocabulary slug already is.
- A concept is assigned through a bulk queryset write. The restriction is bypassed, as every model-level rule in this package is by a bulk write.
- The restriction's target is imported after the project started. The field picks it up without a restart, because nothing about it is resolved at declaration time.
- A branch restriction is declared against a vocabulary whose hierarchy is many thousands of concepts deep or wide. It works and it may be slow; see Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Both concept fields MUST accept three optional restrictions that narrow choices inside the vocabulary a declaration names — a collection, an explicit set of concepts, and a branch of the hierarchy — each naming its target by slug, resolved within that vocabulary.
- **FR-002**: The collection restriction MUST limit the field to that collection's members, resolved live rather than fixed when the declaration is read, so a membership change reaches the field without a code change or a restart.
- **FR-003**: The explicit restriction MUST limit the field to exactly the concepts named, collapsing duplicates. An empty set MUST be refused, on the same reasoning that already refuses an empty vocabulary slug: it reads as a restriction and offers nothing.
- **FR-004**: The branch restriction MUST limit the field to the concept named **together with** every concept below it in the broader/narrower hierarchy, at any depth, resolved live. The traversal MUST terminate and yield each concept once even where the stored edges form a cycle.
- **FR-005**: A restriction MUST be refused when the declaration does not name exactly one vocabulary, at the point the declaration is read, with a message stating the rule.
- **FR-006**: A declaration carrying more than one of the three restrictions MUST be refused at the point the declaration is read, with a message stating the rule. Combining them has no single defensible reading, so no reading is chosen.
- **FR-007**: No database query MUST be issued while a declaration is being read, exactly as for the existing vocabulary restriction, so a project imports its models, generates migrations, migrates and starts with none of the named targets present.
- **FR-008**: A restriction MUST be enforced both in the choices a form offers and when a record is validated, for the single-value and the multi-value field alike, with a curator-facing message naming what the field is restricted to. For the multi-value field a write containing any concept outside the restriction MUST be refused whole, leaving the record's existing set untouched.
- **FR-009**: The package's existing system check MUST additionally report, as a warning with a stable identifier, every declared field whose named collection, branch root, or listed concept is absent from the named vocabulary, identifying the specific absent target. It MUST report nothing when the database cannot be queried, and nothing for a target that exists and is empty.
- **FR-010**: Where the restriction is a collection the curator marked ordered, the choices the field offers MUST follow the collection's member order.
- **FR-011**: A restriction MUST survive `deconstruct()` and rebuild from the emitted arguments, so migrations, `makemigrations --check` and the test-database build are unaffected, and the emitted arguments MUST record the restriction itself rather than any expression derived from it.
- **FR-012**: Every string these restrictions put in front of a person, including refusal messages and the `help_text` a restricted field falls back to, MUST be translatable per Article XII, with named placeholders so message identifiers stay static.
- **FR-013**: The README MUST document all three restrictions, the two declaration rules, and the behaviour when a named target is absent. `CONTEXT.md` MUST carry the vocabulary and reconcile the existing field entries. The CHANGELOG MUST record the addition.
- **FR-014**: A declaration using none of the three restrictions MUST behave exactly as it did before this feature, including one naming several vocabularies or none.

### Key Entities *(include if feature involves data)*

- **Restriction**: The second, narrower constraint a declaration may carry inside its one named vocabulary. Exactly one of three forms — `collection=<slug>`, `concepts=[<slug>, …]`, `branch=<slug>` — or none, which is every declaration that exists today.
- **Collection**: An existing curator-authored grouping of concepts within one vocabulary, optionally ordered. This feature reads it and never writes it.
- **Branch**: A concept together with its transitive `narrower` closure. Not a stored entity — a read over the existing relation edges, named by its root concept's slug.
- **Named target**: Whatever a restriction points at, identified by slug within the named vocabulary. It may be absent when the declaration is read, and it arrives by import or by curation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consuming project restricts a field to part of one vocabulary in each of the three ways, writing no query, no validator and no form-field override of its own.
- **SC-002**: No validated write path stores a concept outside a field's restriction, and no form offers one, for the single-value and multi-value field alike.
- **SC-003**: A restriction reflects a change to the underlying collection membership or hierarchy on the next read, with no code change, no migration and no restart.
- **SC-004**: Every declaration that combines a restriction with anything other than exactly one vocabulary, or that carries two restrictions, fails when the model is imported, and the message identifies the rule broken.
- **SC-005**: A project whose restriction targets are absent from the database generates migrations, migrates, starts and runs its tests without failure, and `manage.py check` names each field and the specific target it expects.
- **SC-006**: A branch restriction over a hierarchy containing a cycle returns each concept once and terminates.
- **SC-007**: Coverage floors hold (project ≥ 90%, patch ≥ 85%), lint, type-check and dependency checks pass, migrations are consolidated per Article XIII, and no user-visible string this feature adds is untranslatable.

## Assumptions

- **Making a deep branch read fast is not this feature's job.** The maintainer raised the performance of a transitive hierarchy read at intake and deferred it explicitly. This feature owes a correct and terminating read; the scale work belongs with R7, alongside the rest of the tens-of-thousands-of-concepts question. A branch restriction over a large hierarchy is expected to work and permitted to be slow.
- **Collections and hierarchy arrive by import or curation.** This feature creates neither. A project whose vocabulary has no collections is not a case this feature handles differently — it is a project for which the branch or the explicit restriction is the right one.
- **The restriction is a model-layer rule.** A bulk queryset write bypasses it, as it bypasses every model-level rule in this package. The delete protection the existing fields provide is unchanged and still holds against a bulk delete.
- **The three restrictions do not compose, by decision rather than by omission.** An intersection and a union are equally defensible readings of a combined declaration, so a combination is refused rather than assigned a meaning nobody can predict from reading it.
- **This is additive and pre-1.0.** Every declaration that exists today keeps its meaning. The package is at `0.0.x` with its first publish still ahead in the v0.1.0 milestone, so a new argument owes no upgrade path and no deprecation cycle.
- **Deprecation does not exist yet.** A concept is either present or absent, so a restriction cannot exclude a retired concept. Publication and deprecation arrive with R4.
