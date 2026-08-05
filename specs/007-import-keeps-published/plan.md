# Implementation Plan: Import keeps the languages the site supports and reports the rest

**Branch**: `007-import-keeps-published` | **Date**: 2026-08-04 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/007-import-keeps-published/spec.md`

## Summary

One new class decides which configured language a published tag belongs to, and every place the
importer currently compares a tag against `settings.LANGUAGES` calls it instead. Today that
comparison is `language not in configured` written out at four sites, so the change is mostly the
replacement of a set-membership test with a resolution that can also answer "under which configured
language, and was that the tag the file used".

The matcher is built once per run from the graph, because settling a contest by the variant the
vocabulary predominantly publishes in needs the whole file counted before the first concept is
written (`research.md` R2). The report gains one new normalisation reason for a substitution and one
derived method for the per-language account. Contest losers reuse the surplus-preferred-label reason
that already exists (`research.md` R4).

No new models, no migration, no new dependency. Django's own `get_supported_language_variant` was
evaluated and rejected with a measurement: it refuses any language Django ships no translation
catalog for, including ones the project declares in `LANGUAGES`, which would make this feature
silently useless for the research vocabularies it exists to serve (`research.md` R1).

## Technical Context

**Language/Version**: Python 3.11+ (package floor), tested on 3.12 and 3.13

**Primary Dependencies**: Django ≥5.2, rdflib 7.6 — all existing. **No new dependency.**

**Storage**: the existing models, unchanged. `ConceptLabel` and `ConceptNote` keep refusing an
unconfigured language on the write path, and this feature keeps writing through
`Concept.add_label` / `Concept.add_note` rather than around them. **No migration.**

**Testing**: pytest + pytest-django. New fixture vocabularies under `tests/fixtures/` carrying
variant tags, alongside those #50 shipped. `@override_settings(LANGUAGES=...)` is the lever for
every scenario, since the site's configuration is the input under test.

**Target Platform**: any Django project installing this app

**Project Type**: installable Django app (library)

**Performance Goals**: none set. The new pre-pass counts language tags across the graph once, which
is linear in triples and runs beside the traversals already there. Nothing here may be quadratic in
concept count (G5).

**Constraints**: matching must not depend on Django translation catalogs (`research.md` R1). The
account must be derived from report entries rather than accumulated beside them (R3). Article XV
requires the new behaviour to be grouped in a class rather than added as further module-level
functions in `skos.py`.

**Scale/Scope**: one new module, four changed methods, two report additions, five stories, no
schema change.

## Constitution Check

| Article | Status | Note |
|---|---|---|
| I — Test-First | Pass | Every task is a test-first pair. The `sga` regression test — a configured language Django has no catalog for — lands with the matcher, because it is the test that stops a later maintainer swapping in Django's resolver. |
| II — Simplicity | Pass | One class, no registry, no strategy object per matching rule. The two report additions are one enum member and one derived method; a third would be a sign the design drifted. |
| III — Anti-Abstraction | Pass | No base class, no interface. The matcher is a plain class with an immutable table built at construction, and it has exactly one implementation because there is exactly one rule. |
| IV — Integration-First | Pass | The account and the substitution entry are the contract #52 consumes, so they are specified and tested before the call sites that populate them are polished. |
| V — Security & data-safety | Pass, with one watch item | Language tags come from an untrusted file. They are used as dictionary keys and reported back, never as paths, queries, or format strings. The pre-pass counts tags, so a file declaring very many distinct tags grows one dictionary — bounded by the graph already held in memory, and noted in Complexity Tracking rather than dismissed. |
| VI — Documentation | Pass | README's import section gains the matching rule, CHANGELOG entry, and `CONTEXT.md` gains the three new glossary terms (FR-014). The rejection of Django's resolver is documented at the code, not only in `research.md`. |
| VII — Dependency discipline | Pass | Nothing added. |
| VIII — Compatibility | **Pass, and the reason is checked rather than assumed** | This changes what an existing import stores. No published release carries the old rule — the package is `0.0.x` and its first publish is the v0.1.0 milestone — so no compatibility path is owed (spec Assumptions, `decisions.md` D10). |
| IX — URI identity | Pass | Untouched. FR-009 forbids this feature from altering any identifier, local address, or database identity, and US-4 tests exactly that across a re-import. |
| X — Stack & architecture norms | **Pass, with a documented departure** | Django's own resolver answers "which language should this request be served in", where refusing an uncatalogued language is correct. Filing a stored record under a language is a different question, and the measurement in `research.md` R1 is why the framework mechanism is not used here. |
| XI — RDF fidelity | Pass | A substitution is reported as one, never applied silently — the article's own requirement, one axis over from the normalisation #50 already reports. Re-import stays additive and upserts by URI. |
| XII — Internationalization | Pass | The new normalisation reason carries a translatable template with named placeholders, in the closed vocabulary the existing reasons live in. |
| XIII — Data-model conventions | Not applicable | No field added, so no indexing decision to record. FR-013 stands as a conditional this feature does not trigger. |
| XIV — Test structure & fixtures | Pass | The new module gets its mirroring `tests/test_exchange/test_languages.py`, grouped into `Test<Subject>` classes. Fixtures are files on disk loaded from the suite, not vocabularies built inline. |
| XV — Cohesion | **Central to the design** | `configured_language_codes()` is today a module-level function in `skos.py`, and this feature would otherwise add three or four siblings around the same subject. They go on one class instead, which is also the extension point a consuming project would subclass. |

## Project Structure

### Documentation (this feature)

```
specs/007-import-keeps-published/
├── spec.md              # approved at the Spec gate
├── decisions.md         # D1–D11, plus anything self-resolved from here on
├── research.md          # R1–R5
├── plan.md              # this file
├── tasks.md             # the task graph
├── progress.md          # append-only stage log
└── feature-state.json   # the ledger
```

### Source Code (repository root)

```
controlled_vocabularies/
├── exchange/
│   ├── languages.py     # NEW — LanguageMatcher and its resolution result
│   ├── report.py        # CHANGED — one NormalizedReason member, one derived account method
│   └── skos.py          # CHANGED — four call sites stop testing set membership
└── ...

tests/
├── test_exchange/
│   ├── test_languages.py    # NEW — mirrors the new module (Article XIV)
│   ├── test_report.py       # CHANGED — the account
│   └── test_skos.py         # CHANGED — the behavioural scenarios
└── fixtures/
    └── variants.ttl         # NEW — one vocabulary carrying several variants of one base language
```

### The four call sites

These are the whole surface of the change in `skos.py`, and naming them here is what keeps the
stories from overlapping in ways their titles hide.

1. `SchemeResolver.determine_default_language` — resolves the vocabulary's default language.
   Currently `if declared_language in configured`. This is the one place the change decides whether
   records exist at all, because a concept with no preferred label in the default language is set
   aside (`decisions.md` D9).
2. `SkosGraph.preferred_label_in` — selects `Concept.label` by exact tag equality. Must select
   through the matcher, or the default language resolves correctly and then finds no label.
3. `ConceptImporter.import_labels` — the contest lives here. Its `preferred_by_language` grouping
   must key on the resolved configured language rather than the raw tag, and the winner within a
   resolved language is decided by exact-match-first, then predominance, then the existing
   lexicographic tie-break within one tag.
4. `ConceptImporter._import_notes` — two branches plus the `dcterms:description` alias. Notes carry
   no per-language cardinality limit, so there is no contest here: every variant value is stored
   (FR-004). This asymmetry with `import_labels` is the single most likely place for an implementer
   to over-apply the contest rule.

## Complexity Tracking

| Concern | Why it is accepted |
|---|---|
| A hand-rolled matcher beside an obvious Django utility | Measured, not assumed: Django's resolver refuses any language it has no translation catalog for, including ones the project declares. `research.md` R1 carries the transcript. The mitigation is a test named for that case, so the swap-it-back regression fails loudly. |
| A pre-pass over the graph before concepts are written | Predominance is a property of the file, and computing it per concept would let two concepts in one file resolve the same base language differently (`research.md` R2). One linear pass beside traversals already there. |
| One dictionary keyed by every distinct language tag in the file | A hostile file could declare many thousands of distinct tags. The graph itself is already fully in memory by then, so this adds a fraction of an existing cost rather than a new unbounded one. Recorded rather than guarded, because a guard here would be a limit invented without a threshold. |
| Four stories touching one module | The decomposition is behavioural, not modular, so the stories cut across the same four methods. Dispatch is sequential and each story rebases on the last (`research.md` R5). Under parallel fan-out these would not be candidates. |
