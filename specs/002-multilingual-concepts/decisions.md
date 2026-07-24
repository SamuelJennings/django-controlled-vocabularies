# Decision record — 002-multilingual-concepts

Ambiguities resolved without escalation while specifying, with the reasoning that makes each
defensible. Gate-level decisions (the ones Sam ruled on during grilling) are summarised first;
the fine grain follows. This file is the durable record of why the spec reads as it does.

## Settled with Sam during grilling (S0)

1. **Identity anchors to the default-language preferred label (evolve #15, do not rebuild).**
   Multilingual labels force the question "which label drives the slug". Chosen: a required
   preferred label in the vocabulary's default language is the anchor; the slug derives from it and
   the URI composes exactly as in #15. Other languages are additive and never touch identity. The
   alternative — decoupling identity into a language-neutral opaque/notation code — was weighed and
   rejected for this slice: it pulls the feature into publishing/identity-freezing territory (R4)
   that #16 does not own.

2. **This supersedes #15's single-`label` decision.** #15 recorded its single label as a deliberate
   deferral to this feature (its `decisions.md` §1, R8). #16 is the legitimate owner and overrides
   it. Nothing is released (repo at 0.0.x, models branch-local, no shared DB), so the change is a
   clean evolution with no data migration.

3. **Default language: app-wide with a per-vocabulary override.** The effective default language is
   the application's configured default (`LANGUAGE_CODE`), overridable per `ConceptScheme`. Reason:
   the package explicitly hosts several independently-authored vocabularies in one instance, which
   will not share one primary language; without the override a German vocabulary in an English
   instance would anchor its identifiers in English. App-wide-only was the considered alternative;
   rejected because the need is already visible in the package's purpose. (US-4, FR-009/FR-011.)

4. **The concept slug is overridable.** It auto-derives from the default-language preferred label
   unless explicitly set; an explicit slug is preserved across later relabels. This removes the
   sharp edge of anchoring identity to a label and, with one mechanism, leaves room for later import
   (R2) to carry an external vocabulary's own slugs unchanged. The live "type label → slug fills in,
   override if you want" UX is roadmap R5; #16 owns only the model-layer rule. (US-5, FR-010.)

5. **Descriptions: the full SKOS documentary note family.** `definition` (primary) plus `scopeNote`,
   `example`, `editorialNote`, `historyNote`, `changeNote`, and a generic `note`, all language-tagged.
   Reason: they are handled identically to labels once the per-language mechanism exists, so the
   marginal cost is near zero, and carrying them all makes the later faithful round-trip (G4) real
   from the start. The minimal alternative (definition + scope note only) was rejected as a false
   economy. (US-3, FR-006.)

6. **Scope of the slug/identity discussion is locally-authored vocabularies only.** Imported
   external pre-published vocabularies keep their source URI slugs — the package never re-derives or
   edits them (they are the published identity). That is import behaviour (R2), out of scope here;
   FR-010's explicit-slug mechanism is what will accommodate it later.

## Self-resolved at specify (S1)

7. **Labels and notes are language-tagged, multi-valued values; preferred label is one-per-language.**
   The issue fixes the cardinalities on the name side ("one preferred name per language, plus any
   number of alternative and hidden names"). Extended the same shape to notes: each documentary note
   type (and the definition) is a language-tagged value that may occur more than once per language,
   because SKOS permits repeated notes and uniform handling is simpler than special-casing single vs
   multi. The spec states cardinality as WHAT (one preferred per language; many for the rest); the
   storage shape is left to planning.

8. **Available languages = the application's configured languages; default = its configured default.**
   No bespoke language registry. `settings.LANGUAGES` is the value set a concept may carry; the
   effective default is `settings.LANGUAGE_CODE` unless a vocabulary overrides it. Standard Django,
   so recorded as an assumption rather than re-specified.

9. **Changing a vocabulary's default language does not retroactively re-slug existing concepts.**
   A slug moves only when its own source label changes (and no explicit slug is set). Reason:
   retroactive re-slugging would silently rewrite identifiers of concepts a curator may already
   depend on — the opposite of the stability the identity model promises. Documented as an edge case
   with a test so it is explicit, not accidental.

10. **SKOS pairwise label disjointness (S13) is not enforced this slice.** The condition that a
    concept's preferred/alternative/hidden labels within one language be pairwise distinct is a
    validation nicety that adds cross-list checking over three multi-valued sets per language, with
    no consumer yet (no editor, no import). Deferred to a later validation/editor feature and
    recorded as a deliberate omission, not an oversight.

11. **Definition projection/indexing left to planning.** Whether the definition (or which value) is
    projected into an indexed column is a data-model/plan decision. The spec fixes only that the
    value used for preferred-label lookup is indexed (FR-015), inheriting #15's rule that a field
    with a query path is indexed and any queryable-but-unindexed field is a recorded decision.

## Deferred by design (recorded so later constitution checks read them as deliberate)

- **Storage mechanism** for per-language, multi-valued labels/notes (the shared/translated document
  split and any predicate registry the brainstorm leans toward): a planning (S3) and Implementer
  decision, not fixed by this spec.
- **Publishing / URI freezing** (Article VIII data contract): unchanged from #15 — all identifiers
  here are computed and dynamic while unpublished.
- **Notation codes**: language-independent, no consumer here; first feature that needs it models it.
- **Relations (#17), collections (#18), lifecycle (#19), RDF import/export (R2/R4)**: sibling/later.

## Implementation (US-1, T002–T004)

12. **`add_label` validates through `Model.full_clean()`.** `Concept.add_label` builds an unsaved
    `ConceptLabel`, calls `full_clean()`, then `save()`. **Why**: one call routes both US-1 refusals to
    `ValidationError` — the second-preferred-per-language case via `validate_constraints()` (the partial
    `UniqueConstraint`), and the preferred-in-default-language case via the model's `clean()`. No
    hand-rolled duplicate check that could drift from the DB constraint. **Revisit if**: bulk label
    authoring needs to skip per-row validation for performance (then batch-validate explicitly).

13. **Partial `UniqueConstraint` condition uses the literal `"preferred"`, not `Kind.PREFERRED`.**
    In `ConceptLabel.Meta` the condition is `Q(kind="preferred")`. **Why**: a nested `Meta` class body
    cannot reference its sibling nested `Kind` enum (Python class-scoping), and `ConceptLabel` is not
    yet bound during its own body. The literal equals `Kind.PREFERRED`'s value and is documented inline.
    **Revisit if**: the `Kind` values are ever renamed — the literal must move with them.

14. **`Kind` carries PREFERRED/ALTERNATIVE/HIDDEN now; only PREFERRED is exercised in US-1.**
    **Why**: `ConceptLabel` is the shared label model US-2 builds alt/hidden labels on (data-model.md);
    fixing its full lexical vocabulary once avoids a churn migration. US-1 adds no alt/hidden *helpers*
    (those are US-2). **Revisit if**: US-2 changes the label taxonomy.

## Implementation (US-2, T005–T007)

15. **`add_label` was left unchanged in US-2; only the two readers were added.**
    T006 asked to "extend `add_label` for alt/hidden kinds". Inspecting §12's implementation, no code
    change was needed: `add_label` already builds any-`Kind` row and validates via `full_clean()`, and
    since the only uniqueness is the *partial* `PREFERRED` constraint, alt/hidden rows validate and save
    with no special-casing. Only the docstring was widened to state this. **Why record it**: so the "no
    diff to `add_label`" reads as deliberate, not a skipped task. **Revisit if**: a kind ever needs its
    own uniqueness or normalisation.

16. **A wrong expected value in the T005 hidden-labels test was corrected within T006.**
    T005 asserted `sorted(hidden_labels("en")) == ["heet flow", "heatflow"]`; Python sorts `"heatflow"`
    first (`'a'` < `'e'` at index 1). The list order was the test author's slip, not implementation
    behaviour, so the expectation was fixed in the T006 commit rather than bending the reader. **Why**:
    the correction touches only a test this same Implementer authored in T005 (no *pre-existing* test was
    modified); folding it into T006 keeps the red→green story of the fixture honest.

17. **No US-2 migration.** T007 generated none: §14 already baked all three `Kind` values in US-1's
    `0002`, and US-2 added no model fields, so `makemigrations --check` is clean. Per the task's "only
    add a migration if Django reports drift", the step is a verification, not an artifact. **Revisit if**:
    a later story adds a `ConceptLabel`/`Concept` field on this branch before the S5 squash.

## Implementation (US-3, T008–T010)

18. **T008 tests pass note kinds as plain choice-value strings, not the `ConceptNote.Kind` enum.**
    US-1/US-2 tests reference `ConceptLabel.Kind.PREFERRED`; the US-3 tests instead pass `"definition"`,
    `"scope"`, … as literals. **Why**: `ConceptNote` does not exist at T008, so importing its `Kind`
    would fail at module import and turn every test in the file red at *collection* — erasing the signal
    that only the new US-3 tests are red and the 65 prior tests still pass. Passing the choice values
    keeps the module importable, so the red is a precise `AttributeError` on the missing `Concept`
    methods (`add_note`/`definition`). The literals equal the `Kind` member values chosen in T009.
    **Revisit if**: the `Kind` values are renamed — the literals must move with them.
