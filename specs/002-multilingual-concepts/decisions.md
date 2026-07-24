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

9. ~~**Changing a vocabulary's default language does not retroactively re-slug existing concepts.**
   A slug moves only when its own source label changes (and no explicit slug is set).~~
   **⟶ Superseded by §35 (review fix, 2026-07-24).** The freeze makes the stronger guarantee — the
   default language cannot change at all once concepts exist, so the "changed default language"
   scenario no longer arises. The reasoning below is exactly what the freeze now enforces. Reason:
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

19. **`ConceptNote.kind` values are the logical names; each carries its SKOS CURIE via a side map.**
    `Kind` values are `definition/scope/example/editorial/history/change/note` (matching the public
    contract's documented `kind ∈ {…}` set), and a module-level `SKOS_CURIE` dict maps each to its
    SKOS predicate CURIE (`skos:definition`, `skos:scopeNote`, `skos:example`, `skos:editorialNote`,
    `skos:historyNote`, `skos:changeNote`, `skos:note`). **Why**: the write contract passes the logical
    kind, not a CURIE, so the stored value is the logical name; carrying the CURIE alongside makes the
    later RDF export a straight kind→predicate lookup (tasks.md US-3 checkpoint) without coupling the
    stored value to RDF syntax. **Revisit if**: a kind needs more than one predicate, or the CURIE
    prefix is made configurable.

20. **`ConceptNote.value` is deliberately UNINDEXED (Article XIII recorded decision).**
    `value` is free documentary prose (`TextField`) with no lookup path in this slice — notes are read
    by fetching a concept's related `concept_notes` and filtering on the auto-indexed FK plus
    `language`/`kind`, never by searching `value`. Indexing free text would cost write/storage for a
    query nobody issues here. FR-015 requires only the *label*-lookup value indexed (that is
    `ConceptLabel`), and #15's rule is "a queryable-but-unindexed field is a recorded decision" — this
    is that record. **Revisit if**: full-text search over note bodies is added (then a dedicated search
    index / `GinIndex` chosen for the search engine, not a plain b-tree).

21. **`add_note` validates through `Model.full_clean()`, mirroring `add_label` (§12).** It builds an
    unsaved `ConceptNote`, calls `full_clean()`, then `save()`. **Why**: one path validates the
    `language`/`kind` choices and the non-empty `value` (and any future note constraint) consistently
    with the label writer, with no hand-rolled checks. Notes carry no uniqueness, so nothing beyond
    field validation trips. **Revisit if**: bulk note authoring needs to skip per-row validation.

## Implementation (US-4, T011–T013)

22. **`effective_default_language` reads `self.default_language or settings.LANGUAGE_CODE` — no
    explicit blank check.** `default_language` is `CharField(blank=True)` whose unset value is the
    empty string, which is falsy, so the `or` short-circuits to the app default without a separate
    `if not self.default_language` guard. **Why**: it matches the exact contract in `data-model.md`
    and keeps the property a one-liner. The US-1 `TestConceptSchemeDefaultLanguage` test (an *unsaved*
    `ConceptScheme()`, no override) still passes because the field default is `""`. **Revisit if**:
    the field ever becomes nullable (`null=True`) — then `None or ...` still works, but the intent
    would be clearer as `self.default_language or settings.LANGUAGE_CODE` unchanged.

23. **US-4 is a genuine field-add migration (`0004`), unlike US-2's no-migration.** Adding
    `ConceptScheme.default_language` is a real schema change, so `makemigrations` produced
    `0004_conceptscheme_default_language.py` (contrast §17, where US-2 added no field and drifted
    nothing). No data move: the override only *decides* which language `Concept.label` already holds,
    so overriding a scheme to `de` means its concepts' `label` field carries the German preferred
    label and the slug derives from it — the identity mechanism from #15 is reused, not rebuilt
    (spec Assumption "identity mechanism preserved"). The branch's migrations are squashed to one at
    convergence (S5). **Revisit if**: a later story on this branch adds a `ConceptScheme` field before
    the squash.

24. **The US-4 red (T011) fails on the missing field, not a blanked module.** The three tests read or
    pass `default_language`, which does not exist pre-T012, so they fail precisely — an
    `AttributeError` reading `scheme.default_language`, a `TypeError` passing it to `create()` — while
    the module still imports and the prior 71 tests stay green. The no-override test asserts
    `scheme.default_language == ""` first so its red is the missing field, not an accidental pass on
    the already-correct app-default behaviour. **Why record it**: mirrors §18's discipline — the red
    signal must isolate the new story, never collapse the file at collection.

## Implementation (US-5, T014–T016)

25. **`slug_is_manual` is a boolean flag on `Concept`, not a "slug came from import" enum or a
    nullable override slug.** `save()` re-derives the slug from `label` only when the flag is `False`;
    a `True` flag means the slug is the curator's and is left exactly as stored. **Why**: FR-010 needs
    a single bit — "does the label drive the slug or not" — and a boolean expresses precisely that with
    the least surface. A separate override-slug column would duplicate `slug` and force every reader to
    decide which one wins; encoding provenance as an enum (auto/manual/imported) would pre-build R2
    import semantics this slice does not own. The flag defaults `False`, so every existing and
    factory-built concept keeps #15's derive-on-save behaviour untouched. **Revisit if**: R2 import
    needs to distinguish "manual" from "imported" for audit — then widen to an enum, keeping `False`/
    auto as the default.

26. **`set_slug(value)` stores the value verbatim — it does not re-slugify.** The entry point sets
    `slug = value`, flags it manual, and saves; the non-empty and within-scheme uniqueness checks still
    run (FR-012), but the value is not passed through `slugify`. **Why**: FR-010 acceptance 1 requires
    the slug to be *exactly* what was set, and the same mechanism must later carry an imported
    vocabulary's own URI-path slugs unchanged (spec Assumption "imported vocabularies keep their own
    slugs", R2). Re-slugifying would silently rewrite a curator's or a source's chosen identifier.
    Callers own the responsibility of passing a URL-safe value; the model only guarantees non-empty and
    unique. **Revisit if**: a UI layer (R5) wants to offer "tidy this into a slug" — that belongs in the
    UI, not in `set_slug`.

27. **The empty-slug guard splits by provenance: an auto slug errors on `label`, a manual one on
    `slug`.** In `save()`, when not manual an empty derived slug raises `ValidationError({"label": …})`
    (unchanged from #15 — a bad *label* is the cause); when manual an empty explicit slug raises
    `ValidationError({"slug": …})` (the *slug* the caller set is the cause). **Why**: the error points
    at the field the curator can actually fix, and it keeps the existing US-2 `test_empty_label_is_rejected`
    / message tests (which read `error_dict["label"]`) green — the manual branch is additive and never
    reached by label-derived saves. **Revisit if**: `full_clean`-based validation replaces the hand-rolled
    save checks — then both would surface through the normal field-cleaning path.

28. **The US-5 red (T014) fails on the missing entry point and field, not a blanked module.** The four
    tests call `concept.set_slug(...)` and read `concept.slug_is_manual`, neither of which exists
    pre-T015, so they fail with a precise `AttributeError` while the module imports and the prior 74
    tests stay green. The migration `0005` is generated during T015 so the DB-backed tests can run, but
    committed separately in T016 (mirrors US-4's §23 split). **Why record it**: continues §18/§24's
    discipline — the red must isolate US-5, never collapse collection.

## Implementation (US-6, T017)

29. **The `multilingual` trait carries the en anchor as `Concept.label` and only the *de* preferred
    label as a `ConceptLabel` row — it never mints a `PREFERRED` row in the default language.** The
    trait adds one `ConceptLabel(language="de", kind=PREFERRED)` plus en+de definition notes; the en
    preferred label is the anchor `label` the base factory already sets. **Why**: `Concept.label` *is*
    the default-language preferred label (§9, data-model), and `ConceptLabel.clean()` rejects a
    `PREFERRED` row in the effective default language — a factory that added an en `PREFERRED` row would
    build an object the model forbids. Sourcing the second language from `de` (the fixed non-default in
    `tests.settings.LANGUAGES`) makes "preferred labels in more than one language" true through the two
    legitimate channels — the field for the default, a row for the rest. **Revisit if**: a scheme with a
    non-`en` `default_language` needs fixtures — then parameterise the trait's languages off
    `scheme.effective_default_language` rather than hard-coding `de`.

30. **The trait uses `RelatedFactory` (post-generation children), and the standalone factories default
    to the languages that are valid *without* `full_clean`.** `ConceptLabelFactory` defaults
    `language="de", kind=PREFERRED`; `ConceptNoteFactory` defaults `language="en", kind=DEFINITION`.
    factory_boy calls `Model.save()`, not `full_clean()`, so the DB partial-unique constraint
    (`one_preferred_label_per_language`) is the only guard that fires — one `de` preferred per concept
    is fine. **Why the de default for labels**: a `PREFERRED` label needs a non-default language to be a
    legitimate standalone row; `de` is that language in the test settings, so `ConceptLabelFactory()`
    with no args yields a valid, saveable row rather than one that only the absent `full_clean` would
    reject. **Revisit if**: the factories gain a `full_clean` step (e.g. to exercise `clean()` paths) —
    then the default (language, kind) must stay `clean()`-valid or move behind an explicit trait.

31. **The US-6 red (T017) fails at import — the new factories and trait do not exist — while the other
    72 tests stay green.** The six new tests import `ConceptLabelFactory`/`ConceptNoteFactory` and call
    `ConceptFactory(multilingual=True)`; pre-GREEN the import raises `ImportError`, collapsing only
    `tests/test_factories.py` (its six prior tests included), and the remaining 72 pass. **Why record
    it**: unlike §18/§24/§28 (an `AttributeError`/blank-module signal that keeps the module importing),
    a factories story's red is necessarily an *import* failure isolated to the one test module — the
    signal still isolates US-6 and never touches the other modules' collection.

## Implementation (US-7, T018–T019)

32. **The duplicate-preferred-per-language refusal gained a `clean()`-level check — the exact
    hand-rolled check §12 avoided — but the partial `UniqueConstraint` stays the integrity backstop.**
    §12 routed the second-preferred-per-language refusal through `validate_constraints()` and warned
    off "a hand-rolled duplicate check that could drift from the DB constraint". US-7 (Article XII,
    FR-010) requires that refusal to carry a *translatable* message with a named placeholder, and a
    constraint's `violation_error_message` is interpolated eagerly (`% {"name": …}`), so it cannot
    yield the lazy `ValidationError(msgid, params={…})` form the standard demands. So `ConceptLabel.clean()`
    now queries for an existing `PREFERRED` row in the same `(concept, language)` and raises the
    named-placeholder error. **Why this is not the drift §12 feared**: the `clean()` query and the
    partial constraint test the *identical* condition (`kind="preferred"`, same `(concept, language)`);
    the constraint is unchanged and still fires on any `save()` that bypasses `full_clean` (e.g.
    factory_boy, §30) — the `clean()` check is a message layer in front of it, not a replacement.
    **Revisit if**: the constraint's condition and the `clean()` query ever diverge — they must move
    together, so keep them adjacent in the model.

33. **The missing-default-language-label message (FR-002) was reworded to name the language, and stays
    keyed to `"label"`; the manual empty-slug message keeps its bare form.** The auto-slug empty guard
    in `Concept.save()` — which fires exactly when the default-language `label` is empty (§27) — now
    raises `ValidationError(_("A preferred label in the default language '%(language)s' is required."),
    params={"language": effective_default_language})` instead of the old slug-worded string. It is still
    keyed to `"label"`, so #15's `test_empty_label_message_is_translatable` and US-2's empty-label test
    (which read `error_dict["label"]`) stay green. The *manual*-branch empty-slug error
    (`"An explicit slug must not be empty."`, keyed to `"slug"`, §27) is left a bare `_()` string with no
    placeholder — it is a slug-provenance error, not the FR-002 anchor requirement, and #15 §9 rules that
    placeholder-free messages need no `params`. **Revisit if**: FR-002 ever needs enforcing on a
    non-empty label that still slugifies to empty (e.g. punctuation-only) as a distinct message.

34. **The `(language, kind, text)` index on `ConceptLabel` was the story's one schema change (migration
    `0006`); everything else is Python-only.** data-model.md fixes this index for the label lookup/search
    path (FR-015); it was absent (the model carried only the ordering tuple and the partial constraint),
    so it was the sole `makemigrations` output. `ConceptNote.value` is confirmed **unindexed** (§20) and
    the reinstated `test_standards.py` now asserts it, alongside walking all four models' `_meta` so any
    future field inherits the metadata + indexing standard automatically. **The US-7 red (T018)** is
    assertion/`KeyError` failures on the message and index gaps (the module imports and 12 metadata
    assertions are already green) — the §18/§24/§28 discipline, isolating US-7 without collapsing
    collection. **Revisit if**: note bodies gain a search path — then a search-engine-specific index
    (not a plain b-tree) is chosen and §20 revisited.

## Convergence — tamper-check triage (Forge, S5)

**tamper-check flagged 6 items — reviewed, all benign (no test weakening).**
`verify.sh` at convergence passed (lint/typecheck/test/build). `tamper-check` (base `main`) flagged
`deleted_test` on `test_concept.py`, `test_identity.py`, `test_scheme.py`, `test_smoke.py` and
`modified_preexisting_test` on `conftest.py`, plus `deleted_test` on `test_standards.py`. Triage:
- The four `test_*` deletions are the `chore/align-tests` consolidation into `test_models.py` that
  already merged to `main` (PR #27) — they exist on neither `main` nor this branch, so this feature
  deleted nothing (stale-base artifact of the tamper run).
- `test_standards.py` was **reinstated** (added) by US-7 (T018, commit e812bfd), not deleted — the
  flag is inverted/stale.
- `conftest.py` is a fixtures module, not an assertion-bearing test; T001 added the multi-language
  settings fixture. Same name-based false-positive class recorded for #15 (its decisions §8).
Independent re-verification on the converged branch: **99 tests collected, 99 passed**, no assertion
removed or weakened. Approved; no fix cycle warranted.

## Review fix (S6) — freeze the default language once concepts exist

35. **A `ConceptScheme`'s `default_language` is frozen once the vocabulary has concepts.**
    Raised as a **high-severity** review finding and approved by Sam. `Concept.label` holds the
    preferred label in the scheme's *effective default language*; if the default language could be
    changed after concepts exist, every concept's identity anchor would be silently reinterpreted
    (its `label` would no longer be the default-language preferred label) and a `ConceptLabel`
    PREFERRED row could collide with the new default language, breaking the
    one-preferred-per-language invariant. **Fix**: `ConceptScheme.save()` compares the incoming
    `default_language` against the stored value and, when it differs and `self.concepts.exists()`,
    raises a translatable `ValidationError`. Before any concept exists the change is free (nothing
    anchors to it yet); a no-op re-save (same value) never trips the guard. Logic-only — no schema
    change, no migration. Tests: three cases in `TestConceptSchemePerVocabularyDefaultLanguage`
    (free before concepts, frozen after, same-value allowed). Strengthens FR-009 and supersedes §9.
    **Revisit if**: a supported "re-anchor this vocabulary to another language" operation is ever
    wanted — it would need an explicit, deliberate re-slug/migration path, not a silent field edit.

## Review fixes (S6) — hardening batch

Applied after the three-lens review panel (all findings addressed to a clean PR; only the note-size
cap is deferred, with a reason). Test coverage lives in `TestReviewHardening` + the freeze tests.

36. **Manual slug is validated, not just stored (security, medium).** `Concept.save()` now runs
    `validate_unicode_slug` on an explicit slug before persisting, so `set_slug("foo/bar")` or a
    slug with spaces/control chars is refused. It is still stored verbatim (not re-slugified) — but
    a malformed slug would corrupt the composed URI and break `get_by_uri` (Article IX). Since
    `save()` never calls `full_clean()`, the validator is applied explicitly.

37. **The default-language-preferred rule is backstopped at `save()` (correctness/security, medium).**
    The rule "no separate PREFERRED `ConceptLabel` in the effective default language" lived only in
    `clean()`; `.objects.create()`/factories bypass `full_clean`, so a second identity anchor could
    be planted. Extracted to `_reject_default_language_preferred()` and called from both `clean()`
    and `save()`. A cross-table DB constraint against `Concept.label` is not expressible, so this is
    the honest backstop; the one-preferred-per-language rule keeps its partial `UniqueConstraint`.

38. **`choices=settings.LANGUAGES` dropped from the model fields (correctness, low → real packaging
    bug).** Binding the setting as field `choices` froze the maintainer's `LANGUAGES` into shipped
    migration `0002`, so a downstream project with different `LANGUAGES` saw spurious
    `makemigrations --check` drift. The `language`/`default_language` fields now carry no choices;
    language codes are validated at runtime against `settings.LANGUAGES` (`_configured_language_codes`)
    in `ConceptLabel.clean()`, `ConceptNote.clean()`, and `ConceptScheme.save()`. Migration
    regenerated — no language list is frozen. `kind` choices stay (they are not settings-derived).

39. **Read helpers are prefetch-friendly (architecture, medium).** `preferred_label`, `alt_labels`,
    `hidden_labels`, `definition`, and `notes` now iterate the cached related set (`self.labels.all()`
    / `self.concept_notes.all()`) instead of `.filter()`, which bypassed any `prefetch_related`
    cache and forced N+1 on the FR-007 read-by-language path. A bulk caller that
    `select_related("scheme").prefetch_related("labels","concept_notes")` now adds zero queries per
    concept (asserted with `django_assert_num_queries`).

40. **`get_by_uri` matches a '/'-terminated base (security, low).** The prefix test was
    `uri.startswith(base)`, which accepted a sibling path sharing the base as a raw prefix
    (`<base>X/a/b`). Now matches `f"{base}/"`, so only genuinely in-base URIs resolve.

41. **`SKOS_CURIE` removed (architecture, low — YAGNI).** The kind→predicate map had no consumer
    this slice (RDF export is R2/R4); Articles II/III discourage carrying speculative infrastructure
    ahead of its use. It lands with the exporter that first serializes RDF. Supersedes the standalone
    `SKOS_CURIE` mention in §19 — the `Kind` values remain named for their SKOS properties, which is
    all this slice needs.

42. **Deferred: `ConceptNote.value` size cap (security, low/speculative).** Harmless for this
    ORM-only slice (trusted programmatic writes). Flagged for the R5 write layer to impose a
    max length at the request boundary, where untrusted input first arrives — not here.
