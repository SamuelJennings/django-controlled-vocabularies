# Research — 007 Import keeps the languages the site supports

Technical questions the plan depends on, answered before it was written. Each entry states the
question, what was actually checked, and the decision that follows.

## R1 — Django's own language-variant resolver is close, and does not fit

**Question.** `django.utils.translation.get_supported_language_variant` already matches a requested
language against `settings.LANGUAGES`. Article X says use the framework's own mechanism rather than
inventing one. Does it implement the rule FR-001 to FR-003 describe?

**What was checked.** The installed Django's source, and its behaviour under a configured
`LANGUAGES` of `en`, `en-gb`, `cy`, `sga`:

```
'en'     -> 'en'
'en-gb'  -> 'en-gb'
'en-us'  -> 'en'
'cy'     -> 'cy'
'sga'    -> LookupError
'fr'     -> LookupError
check_for_language('sga') -> False
check_for_language('cy')  -> True
```

**Finding.** It matches in both directions, which is the part that looked promising: specific to
generic through the `rfind("-")` loop, and generic to specific through the non-strict branch that
scans supported codes for one starting with `generic-`. Two of its other semantics disqualify it.

The blocking one is the last two lines above. `sga` is declared in `LANGUAGES` and the resolver
still refuses it, because every candidate must pass `check_for_language`, which asks whether Django
can find a **translation catalog** for that language. Django ships no `sga` catalog, so a site
configured for Old Irish resolves nothing and stores nothing. That is not a hypothetical for this
package: the vocabularies it exists to hold are research vocabularies, and languages Django does not
translate its own admin into are exactly the languages such vocabularies carry. Adopting this
resolver would make the feature silently useless for the case it was written for, and the failure
would look like a language mismatch rather than a missing catalog.

The second is narrower. The non-strict branch returns the first supported code starting with the
generic prefix, in `settings.LANGUAGES` order. FR-002 requires the least specific configured
language, which is a rule about the codes rather than about their declaration order. The two agree
whenever the bare base language is configured, and diverge when it is not — a site on `en-gb` and
`en-au` receiving an `en-us` value gets whichever the project happened to list first.

There is a third difference worth recording without weighing much: the resolver consults
`LANG_INFO[...]["fallback"]`, Django's own table of related-language fallbacks such as `zh-hk` to
`zh-hant`. That is more than "share a base language", and it is behaviour this spec never asked for.

**Decision.** Implement the rule against `settings.LANGUAGES` directly. It is roughly fifteen lines
— split a tag at the first hyphen, lower-case, prefer an exact match, then the least specific
configured language sharing the base. Article X asks for the framework's mechanism where the
framework owns the concern, and the framework's mechanism here answers a different question:
"which language should this HTTP request be served in", where refusing a language with no catalog
is correct. Which language a stored record is filed under is not that question.

**Consequence for the reader.** The reason the code does not call this function needs to be in the
code, not only here. A later maintainer who finds a hand-rolled matcher beside an obvious Django
utility will replace it, and the tests that catch the regression are the ones a site with an
uncatalogued language would need. A docstring and a test named for `sga` are cheaper than that
round trip.

## R2 — Predominance is a property of the whole file, so it is computed once, before concepts

**Question.** FR-003 settles a contest by "the variant the vocabulary predominantly publishes in".
Predominance across what, and computed when?

**Finding.** Across the whole vocabulary being imported, not per concept. A per-concept reading
makes the answer depend on which concepts happen to carry which variant, so two concepts in one
file could resolve the same base language differently, and a curator reading the result could not
explain it. Across the file, one variant wins for the whole run and the outcome is stable.

This means a pass over the graph's language tags before any concept is written, producing a ranking
per base language. `SkosGraph` already walks the graph for other purposes and
`determine_default_language` already counts label languages across concept nodes, so the shape
exists.

**Revised at the design review (S3R, ARCH-003 and ARCH-004).** Two things the first version of this
entry left open, both of which two implementations would have answered differently:

*Where the traversal lives.* The first version gave `LanguageMatcher` a second constructor that
reads a parsed graph. That drags rdflib into the new module and duplicates a count `SkosGraph`
already performs over the same nodes and the same predicate. `SkosGraph` **is** this codebase's RDF
boundary, and it needs one read-only method returning the tag counts — not a second home for graph
reading. `LanguageMatcher` then takes `(configured_languages, counts)`, the pure form it was always
described as, imports nothing from rdflib, and is testable with a dict.

*What is counted.* The denominator is **`skos:prefLabel` only** — not every label predicate, and not
notes. That is the reading consistent with D4 (a contest exists only where the destination holds one
value, and only preferred labels do) and with D5 (the rule reuses the count
`determine_default_language` already performs). Because it is the same denominator, the one new
`SkosGraph` method feeds both, and the second traversal disappears rather than being justified.

**Decision.** One counting method on `SkosGraph`. The matcher is built once per run from those
counts, before `import_concepts`, and is immutable for the run. Two consequences the plan carries:
the vocabulary's default language must be resolved *after* the matcher exists, and `SkosImporter.run`
builds the matcher and passes it to `SchemeResolver` and `ConceptImporter` as a constructor argument
rather than letting them build it for themselves.

## R3 — The account is derived, not accumulated

**Question.** FR-008 wants counts of what was not stored, per published language. Does that need a
new bucket on the report, kept in step as entries are added?

**Finding.** No. Every value not stored for a language reason is already a `SetAsideEntry` carrying
its reason and its `language` param, and `ImportReport.set_aside_by_reason` already groups by
reason. The count is a fold over data the report holds.

Deriving it keeps one source of truth. A parallel counter maintained alongside the entries can
disagree with them, and the first symptom is a curator being told a number that the entry list
contradicts.

**Decision.** A method on `ImportReport` that folds `set_aside`, not a field that accumulates. It
returns an empty mapping rather than nothing when there is nothing to report (FR-008), so a caller
never distinguishes "clean run" from "feature absent".

## R4 — A substitution is a normalisation, and a contest loser needs its own name

**Question.** Two report vocabularies could grow here. What actually needs adding?

**Finding, first version.** One new member, not two.

A value stored under a configured language other than its published tag is a value that *was*
stored, under something other than what the file said. `NormalizedReason` is exactly that bucket
and #50's docstring says so in as many words. It needs one new member and one message template.
**That half stands.**

The second half did not. It reused `SetAsideReason.SURPLUS_PREFERRED_LABEL` for contest losers,
passing the published tag as `language`, on the argument that a near-duplicate reason would split one
concept across two names.

**Overturned at the design review (S3R, SPEC-002, verified).** The argument had the concept wrong.
`SURPLUS_PREFERRED_LABEL` means *a concept carries more than one preferred label in one and the same
language* — #50 added it for exactly that, and its template (`report.py:140`) says so in words a
curator reads: "'%(subject)s' carries more than one preferred label in the language '%(language)s'".
For a value published `en-us` and beaten by an `en-gb` sibling, the file carries exactly one `en-us`
preferred label, so that sentence is **false**. Article XI's "surfaced to the user, never silent" is
not met by surfacing it wrongly.

The two populations also have different remedies, which is what FR-008's account exists to tell a
curator apart:

- A same-language duplicate: nothing the curator configures will recover it. The file simply asserts
  two preferred labels in one language.
- A variant contest loser: configuring its published tag **does** recover it.

Folding both under one reason makes the account fail its stated purpose — FR-008 requires it to be
"sufficient for a caller to rank languages by what configuring them would recover", and a
same-language duplicate counted under `en` on an `en` site tells the curator that configuring a
language they already have would recover content. Folding neither drops the losers FR-005 requires to
be reported. A closed vocabulary exists precisely so that two causes with two remedies carry two
names.

**Decision.** Add `NormalizedReason.LANGUAGE_SUBSTITUTION` for a stored-under-another-language value.
Add a second `SetAsideReason` member for a variant contest loser, with its own truthful template
naming both the published tag and the configured language it lost to. `SURPLUS_PREFERRED_LABEL`
keeps its existing meaning, unchanged.

## R5 — The stories all touch one module, so they run sequentially

**Question.** Stories are the unit of dispatch and each Implementer works in its own worktree. Four
of the five stories here change `exchange/skos.py`. Does that collide?

**Finding.** It would, under parallel fan-out. Every language decision in the importer lives in
`import_labels`, `_import_notes`, `determine_default_language`, and `preferred_label_in`, and the
stories cut across those methods by behaviour rather than by file.

The pipeline's Phase 1 budget is one worktree, so dispatch is sequential regardless. This is
recorded so the constraint is deliberate rather than incidental: even under Phase 2, these stories
would not be parallel candidates, and a future reader deciding to fan them out should know that the
decomposition is behavioural, not modular.

**Decision.** Sequential dispatch, each story rebased on the previous. The foundational phase lands
the matcher and the report changes first, so every story afterwards edits call sites rather than
racing to create the same new module.
