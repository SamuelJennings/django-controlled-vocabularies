# Decisions — 007 Import keeps the languages the site supports

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.
The spec is the contract. This file is why the contract reads the way it does.

## D1 — The feature survived intake, and what it survived on

This feature was very nearly absorbed by its own dependency. [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50)
delivered the language filtering #51 was written to own, mechanically, because `ConceptLabel` and
`ConceptNote` refuse an unconfigured language on the write path the import uses. #50's own
`decisions.md` D2 recorded that and named what it believed was left: the curator-facing quality of
the report, and an additive re-import guarantee that was true by side effect rather than by test.

Neither of those alone justifies a feature loop. A tested guarantee is a test, and a grouping
helper already existed. What kept #51 alive was a third thing neither issue had noticed: matching
was exact string equality against the codes in `settings.LANGUAGES`, so a site configured for
`en-gb` importing a vocabulary published as `en` stored nothing and reported the entire vocabulary
as unreadable. Regional variants are ordinary in published SKOS, so the issue's first sentence —
"keep the languages their site is configured for" — was not in fact satisfied.

The maintainer confirmed at intake that a variant should be kept, and separately that the match
runs in both directions. That is the feature.

## D2 — Matching is by base language, in both directions

Settled with the maintainer at intake rather than derived here, but the reasoning is worth keeping
because it bounds everything below.

*General to specific* — a file's `en` filling an `en-gb` site's slot — is uncontested: one source
value, one destination, no competition. *Specific to general* — a file's `en-gb` filling an `en`
site's slot — is the direction that creates contests, because published vocabularies routinely
carry several variants of one language and the destination may hold only one.

Refusing the second direction was considered. It avoids every contest below and it is the smaller
change. It was rejected because it leaves the exact failure the issue was written about intact: a
site on plain `en` importing a vocabulary published only as `en-gb` still stores nothing and still
reports the whole vocabulary as content it cannot read. A rule that fixes half of a symmetric
problem is harder to explain than either of the rules it sits between.

## D3 — An exact match always wins, and the least specific configured language receives an orphan

Two precedence rules, both following from the same principle: the site's own declaration is better
evidence of what a curator wants than anything inferred from the file.

An exact tag match is never displaced by a variant, because a publisher who tagged a value `en-gb`
and a site that configured `en-gb` agree, and no third value should come between them.

Where several configured languages share a base and none matches exactly — a site on both `en` and
`en-gb` receiving an `en-us` value — the value goes to the least specific, `en`. It is a variant of
neither, so neither has a claim by exactness, and the broader audience is the destination that
serves more readers. Sorting configured codes and taking the first happens to produce the same
answer here, but for the wrong reason, and would diverge on a site configured for `en-gb` and
`en-us` alone.

## D4 — The contest exists only where the destination has one slot

The draft of this spec got this wrong, and the coverage scan caught it. The first version of FR-003
said that where a file offers several variants of one configured language, one wins and the rest are
set aside. That is right for a preferred label and wrong for everything else.

`ConceptLabel`'s uniqueness constraint is `UniqueConstraint(fields=["concept", "language"],
condition=Q(kind="preferred"))` — conditional on the preferred kind. `ConceptNote` declares no
uniqueness constraint at all. So a concept may hold as many alternative labels, hidden labels, and
notes per language as a file offers, and collapsing `en-gb` "Colour" and `en-us` "Color" into one
alternative label would discard content the models were willing to store, inside a feature whose
entire purpose is to stop discarding content.

The rule is therefore scoped: a contest is resolved only where the models hold at most one value of
that kind per language. Everywhere else, every variant value is kept.

This is worth stating as a general shape rather than a fix. The destination's capacity, not the
source's shape, decides whether there is a contest at all.

## D5 — The predominant variant wins a contest, not the alphabetically first

Where a contest does exist and no exact match resolves it, the variant the vocabulary predominantly
publishes in is kept, with ties broken by language code.

Taking whichever variant sorts first is equally deterministic and one line simpler. It was rejected
because it hands a curator on `en` the `en-au` spelling of a vocabulary published overwhelmingly in
`en-gb`, and no reader of the file could reconstruct why. Predominance is a property of the document
the curator is importing, so the answer is at least explicable from the thing in front of them.

The rule is also not new to this codebase. #50 already resolves a vocabulary's default language as
"the language the vocabulary declares itself in, else the language most of its concepts' preferred
labels use, tied deterministically", so this reuses an established rule rather than introducing a
second one that a reader would have to hold separately.

## D6 — Script-differing variants are joined, and this is the rule's sharpest edge

`zh-Hans` and `zh-Hant` share the base language `zh` and are not mutually readable. Under the agreed
rule, a site configured for `zh-Hans` importing a vocabulary published as `zh-Hant` receives content
in a script its readers may not be able to use.

This is recorded rather than fixed. Three reasons:

- The alternative is a script-awareness rule, which the intake discussion never reached and which
  would need its own decision about what counts as a compatible script.
- It is not silent. Every variant substitution is reported as one (FR-006), so the curator can see
  that their `zh-Hans` slot holds `zh-Hant` content and act on it.
- The failure it replaces is worse. Before this feature, that same import stored nothing at all.

It is raised at the Spec gate rather than absorbed, because narrowing the agreed rule is a
maintainer decision and not this feature's to take.

## D7 — The account answers "what should I change", not "what happened"

The issue asks that a curator be "told plainly what was left behind". #50 already records every
set-aside value with its reason and its language, and already groups those records by reason, so
the literal reading of that sentence was satisfied before this feature started.

The gap is what the grouping is *for*. A per-reason total of 359 values in languages the site is not
configured for is a fact a curator can do nothing with. A breakdown showing 312 of them are French
tells them that configuring one language recovers most of the vocabulary, which is a decision.

So the account is a count per published language, exposed as data. Ranking languages by what
configuring them would recover is then arithmetic the caller does, and #52 renders.

It is present and empty after a clean run rather than absent. An absent account and an account of
zero read identically to a person and differently to a caller, and #52 renders from it without
knowing which kind of run produced it.

## D8 — A substitution is reported even though the value was stored

Article XI requires that nothing be applied silently. A value published as `en` and stored under
`en-gb` did make it in, so it is not a set-aside, but it also is not what the file said.

#50 already built the shape for exactly this: `NormalizedEntry`, a bucket separate from set-asides,
holding values that were stored under a different predicate than the file asserted. A variant
substitution is the same kind of event one axis over — stored under a different *language* than the
file asserted — so it belongs in that bucket rather than in a third one, and a caller filtering for
"things that did not make it in" keeps getting a truthful answer.

## D9 — The default language resolves by the same rule

`determine_default_language` in #50 checks `if declared_language in configured`, an exact match. Left
alone, a vocabulary declaring itself in `de-at` on a site configured for `de` would fall back to the
site default, and every concept whose preferred label is `de-at` would then have no label in the
vocabulary's default language — which #50 makes a set-aside, so the concepts would not import at all.

That is the same failure this feature exists to remove, arriving by a different path. The default
language therefore resolves by the same matching rule. This is the one place where the change
reaches beyond labels and notes into which records exist at all, which is why it carries its own
requirement and its own acceptance scenario rather than being left implicit.

## D10 — No compatibility path is owed, and that is a decision

This feature changes what an import stores. A site that imported a vocabulary, upgraded, and
re-imported would gain content it did not have before.

That would ordinarily oblige a migration note. It does not here, because no published release
carries the previous rule: the package is at `0.0.x`, and its first publish is the v0.1.0 milestone
this work sits inside. The absence of a compatibility path is recorded so that it reads as a
decision taken against a checked fact rather than a question nobody asked.

## D11 — New terms go in the glossary, not only in this spec

Base language, variant, and substitution are all new to this project's vocabulary, and two of the
three will appear in messages a curator reads. `CONTEXT.md` is where this project keeps its
glossary, so that is where they belong. A term defined only inside a spec is a term defined nowhere,
as far as a reader of the report is concerned.

## D12 — What the design review changed, and what it did not

The S3R panel — three reviewers, one lens each, run against the plan before any code existed —
returned `request_changes` on all three lenses: four verified high findings, eight medium, ten low.
Every high was checked against the code before it was accepted, and all four held. They are recorded
here as D13 to D16 because each settles something the plan had left to the implementer.

Two things the panel did **not** change are worth recording, so a later reader does not reopen them.
It found no task without spec or constitution provenance, so there was no scope creep to cut. And it
confirmed the two structural judgements the plan had already made: one `LanguageMatcher` with no base
class, no registry and no settings hook is right-sized, and `models.py::_configured_language_codes`
stays where it is, because folding it into `exchange` would invert the dependency.

The panel is also the reason `skos.py::configured_language_codes()` is deleted rather than left in
place. The plan cited that function as its own Article XV justification and then would have shipped
it alongside the class that replaced it.

**Round two** ran the same three lenses against the revised artefacts and returned `approve` on all
three, risk `low`, with no critical or high findings — so the gate is green and one design-review
cycle was spent. Round two's mediums were applied in the same pass rather than carried as watch
items, because each was a one-sentence artefact edit and several corrected factual errors introduced
by the round-one fixes.

Two of those are worth naming, because they are the same mistake twice and a third occurrence is
plausible. The plan's call-site enumeration asserted "these are the whole surface" at four sites, was
falsified at five, reasserted it, and was falsified again at eight — `SkosGraph.first_literal`'s
`language=` filter decides what the vocabulary and its collections are *named*, and its any-language
fallback would have named a `de-at` vocabulary in whatever language sorted first on a `de` site. The
count now carries a warning to check it rather than grep it. Separately, the FR-010 test written to
run "under Django's default `LANGUAGES`" would have run under `tests/settings.py`'s own three-language
list and pinned nothing at all, while reading in the record as an obligation met — the shape of an
unconsumed declaration, and the reason D17's mitigation now names
`@override_settings(LANGUAGES=global_settings.LANGUAGES)` explicitly.

## D13 — The winner rule is one computation, not two that happen to agree

`Concept.label` is chosen in `preferred_label_in` (`skos.py:190`, called once, at `:677`); the
surplus report is computed from `preferred_kept` in `import_labels` (`:530`). They are independent,
and today they agree only because both are `sorted(...)[0]` over the same raw-tag group. The plan
changed the rule in one of them.

Left that way, the failure is not a mismatch a test would call cosmetic. `Concept.label` would hold
one value while the report named that same value as a surplus set-aside, and stored the true winner
nowhere — a report contradicting the database, inside a feature whose subject is telling a curator
the truth about what was kept.

The rule therefore lives on `LanguageMatcher` and both call sites read it. This also puts the
predominance ranking where it is used rather than reaching into the matcher from `import_labels`,
which is Article XV — the article this plan cites as its own justification.

## D14 — A contest loser is not a surplus preferred label

`research.md` R4 reused `SetAsideReason.SURPLUS_PREFERRED_LABEL` for a value beaten by a sibling
variant, on the argument that a second reason would split one concept across two names. The argument
was wrong about the concept.

`SURPLUS_PREFERRED_LABEL` means a concept carries more than one preferred label **in one and the same
language**, and its message says so in the words a curator reads. For a value published `en-us` and
beaten by an `en-gb` sibling, the file carries exactly one `en-us` preferred label, so that sentence
is false. Article XI is not satisfied by surfacing something wrongly.

The deciding argument is FR-008's, though. The account exists so a curator can rank languages by what
configuring them would recover, and the two populations differ on exactly that: nothing recovers a
same-language duplicate, while configuring its published tag recovers a contest loser. One reason
carrying both makes the account tell the curator that configuring a language they already have would
recover content. A closed vocabulary is what keeps two causes with two remedies apart, so the second
member is the article's purpose rather than a departure from it.

## D15 — Determinism needs a rule for equally-specific candidates, and FR-002 has none

D3 settled that an orphan value goes to the least specific configured language sharing its base, and
noted in passing that sorting the codes would give the same answer "for the wrong reason". It never
answered the case where two candidates are **equally** specific and neither matches exactly.

That case is reachable without anyone configuring it. A project that never declares `LANGUAGES`
inherits Django's 99-language default, and `zh-hans` / `zh-hant` is the one base in that list with
two equally-specific variants and no bare base. `configured_language_codes()` returns a `set`, whose
iteration order varies between processes — measured, both orders came back across five fresh runs. So
the same file would store Simplified on one run and Traditional on the next, and SC-006 already
requires the same file to import the same way twice.

The lower code wins, ordered lexicographically, computed over an ordered sequence rather than a set.
This is FR-003's own tie-break one level up rather than a second rule a reader must hold, and it is
the only rule that makes an already-approved success criterion achievable. Recorded here rather than
taken back to the maintainer for that reason — it settles a gap inside an approved requirement, it
changes no approved behaviour, and it is flagged in the plan notification for veto.

## D16 — FR-009's identity guarantee is about concepts, not label rows

FR-009 forbids altering "any record's identifier, local address, or database identity" across a
re-import. Read literally over all records, it cannot hold: #50's importer runs
`concept.labels.all().delete()` and recreates every label and note row on every run, so their primary
keys change by design.

The requirement is not thereby unsatisfiable, it is unscoped. Its second clause — that no other
language's **stored values** are removed or altered — is the guarantee a curator cares about and is
exactly what the full replace preserves. So the identity assertion covers `Concept`, `ConceptScheme`
and `Collection` records, and the value assertion covers label and note rows.

The alternative reading would have made T017 a test that fails against approved, merged behaviour,
and the fix an implementer would reach for — stopping the full replace — is a redesign of the
dependency this feature explicitly extends rather than replaces.

## D17 — The site's configured languages are not what the spec's Assumptions imply

The spec assumes "the site's configured languages are whatever the project declares". That is true of
the code and misleading about the world: the ordinary consuming project declares nothing, and
`settings.LANGUAGES` falls back to Django's own 99-language list.

Base-language matching widens what an untrusted file may write into that default. A vocabulary
published in sixty languages now writes sixty languages' worth of rows into a project whose curator
believes they run an English site — which is #51's own complaint, arriving through the rule that
fixes it.

There is no safer setting to read, and inventing one would contradict the spec's deliberate choice
not to introduce a setting. So this is a documentation and test obligation rather than a guard:
README says plainly that the package stores content for every code in `settings.LANGUAGES` and that
narrowing that list is how a site narrows an import, and the FR-010 invariant test runs one case
under Django's own 99-language default — named explicitly as
`@override_settings(LANGUAGES=django.conf.global_settings.LANGUAGES)`, because `tests/settings.py`
declares its own three-language list and "no override" would mean that list rather than Django's.

## D18 — A concept's local address follows the file, not the concept

Predominance is a property of the whole vocabulary being imported (`research.md` R2), and
`assign_unique_slug` recomputes a concept's slug from its label on every run (`skos.py:769`). Put
together, those two facts have a consequence neither records on its own: where a concept's
default-language preferred label arrives only by variant match, which variant wins depends on the
rest of the file. A publisher's unrelated edits elsewhere in a later release can therefore move an
existing concept to a new local URL, with nothing about that concept having changed.

This is new with this feature. Under exact matching such a concept stored no label at all, so the
coupling could not arise. FR-009 and SC-015 do not cover it either: they hold identity still across a
re-import of *the same file*, and this is a different file.

It is recorded rather than guarded, for the same reason as D6. Pinning the previously-stored variant
would add state and contradict the rule #50 established that the file is authoritative for the
records it contains, and scoping predominance per concept is precisely what R2 rejected — it would
let two concepts in one file resolve the same base language differently. So the remedies are the two
cheap ones: README says a local URL derived from a variant-matched label can move when the published
vocabulary's predominant variant changes, and this entry carries the constraint into #52's and R6's
specification rather than leaving it to be discovered by a broken bookmark.

## D19 — Three names T005–T022's task text described but did not spell, chosen at implementation

`tasks.md` names the shape of three pieces of API surface without dictating their identifiers.
Recorded so a later story doesn't reinvent them differently.

- **`SetAsideReason.VARIANT_NOT_KEPT`** (T022) — the task text calls it "a contest loser" and "a
  second `SetAsideReason` member"; `VARIANT_NOT_KEPT` was chosen to read correctly in
  `set_aside_by_reason()` output and its own docstring without repeating "contest", which names the
  *mechanism* (T021's winner rule) rather than the *outcome* the report describes.
- **`ImportReport.language_account()`** (T004) — the spec's Key Entities name "Language account" as
  a noun; the method is the verb form of the same term, consistent with `set_aside_by_reason()`'s
  own naming (a plain description of what it returns, not "get_" or "compute_").
- **`NormalizedReason.LANGUAGE_SUBSTITUTION`'s params** — T022 states explicitly that a contest
  loser's published tag goes under `language` and its configured destination under `kept_as`.
  T003's own task text names only "the published tag and the language it was stored under" without
  naming params. `kept_as` was reused for T003 too, for the same reason T022 gives: a caller reading
  both a substitution and a contest-loser entry should not have to remember two different names for
  "the configured language something ended up under."

**Revisit if:** #52 (the rendering feature) finds any of the three read awkwardly from a curator-
facing surface — none of the three is exercised by a call site yet, so nothing downstream depends on
the exact spelling.

## D20 — `LanguageMatcher.resolve_winner`'s tie-break is one cascading sort key, not nested branches

T021 states three tiers — exact match, then predominance, then a lexicographic tie-break "within one
tag." Implemented as a single sort key `(tag != configured_language, -count, tag, value)` over the
candidate list, rather than three sequential `if`/`elif` branches testing each tier in turn.

The fourth element (`value`) is not named by T021's three tiers at all; it exists so two candidates
sharing an identical published tag (a literal duplicate, not a variant) still resolve
deterministically rather than by whichever the caller happened to list first. No call site
constructs such a candidate set yet — `import_labels`'s own raw-tag grouping (`skos.py:530`) already
reduces to one value per tag before this method would ever see it — so this tier is currently
unreachable in practice and is recorded rather than tested against a real call site.

**Revisit if:** a future story's candidate construction stops pre-reducing same-tag duplicates
before calling `resolve_winner`, at which point this tier becomes reachable and worth a dedicated
test.

## D21 — The three T005 fixtures share no scheme URI with any existing fixture, and are not `@en`

`variants.ttl`, `en-gb-only.ttl`, and `declares-de-at.ttl` each mint a fresh `http://example.org/...`
namespace (`colours`, `colours-gb`, `farben`) rather than extending `rocks.ttl`'s. `rocks.ttl` is the
base vocabulary a dozen other tests already assert exact content against; adding variant-tagged
values to it would risk an unrelated test's assumption about what languages it carries. None of the
three fixtures uses a bare `en` tag anywhere — deliberately, so each imports, under this phase's
unmodified call sites, as either an ordinary `UNCONFIGURED_LANGUAGE` set-aside (`variants.ttl`,
`en-gb-only.ttl`) or a `NO_PREFERRED_LABEL` set-aside excluding the whole concept from the predicate-
coverage sweep's evidence requirement (`declares-de-at.ttl`, whose only concept carries no `en`
label at all). Both outcomes are already-covered branches of the existing sweep, so no fixture here
needed its own exclusion entry.

**Revisit if:** US-1/US-3 wire the matcher into the five call sites and these fixtures start
resolving differently — their own dedicated tests (`test_variants_fixture_...`,
`test_en_gb_only_fixture_...`, `test_declares_de_at_fixture_...`) assert only raw RDF content, not
import behaviour, so they should keep passing unchanged; the predicate-coverage sweep's behaviour
for these three files, however, will change once real values start landing instead of being set
aside, and is worth re-checking at that point.

## D22 — The predicate-coverage sweep's own evidence rules predate base-language matching, and T008 is where that catches up

D21 named this exactly: once `variants.ttl`, `en-gb-only.ttl` and `declares-de-at.ttl` stop being
wholly set aside and start landing real content, `TestEverySkosPredicateIsReadOrReported` needed a
second look. T008 is that point, and the sweep's own helpers — `_coverage_label_covered` and
`_coverage_note_covered` in `test_skos.py` — carried two assumptions this feature breaks by design,
not by accident.

The first: their landed-row query filtered on `language=language`, where `language` is the
literal's own **published** tag read straight from the graph. FR-001/FR-006 now store a value under
a *resolved* configured language that can differ from what was published — that is the entire
feature — so a value landing correctly under `de` for a `de-at`-published literal is invisible to a
query still asking for `language="de-at"`. The fix drops the language filter from both helpers'
landed-row checks (kind/text/concept — or kind/value/concept for notes — is specific enough for
this sweep's own purpose, which its docstring states as "read into a record or named in the
report," not "read into a record under this exact tag"; *which* language it landed under is what
T008's own dedicated tests verify).

The second: `_coverage_label_covered`'s recognised-reason list — `UNCONFIGURED_LANGUAGE`,
`SURPLUS_PREFERRED_LABEL` — predates `VARIANT_NOT_KEPT` (T022) ever actually firing. T022's reason
was added in the foundational phase but no call site wrote it until T008's default-language-branch
discriminator. `VARIANT_NOT_KEPT` joins the list, keyed by `language` exactly as
`UNCONFIGURED_LANGUAGE` already is (both carry the *published* tag under that param name).

Both gaps are unavoidable for any correct T008: storing under a resolved language and reporting a
losing variant under `VARIANT_NOT_KEPT` are what FR-001/FR-005/FR-006 require, not implementation
choices this story could have made differently. The sweep's own test function and its assertion —
"every predicate is read into a record or named in the report" — are unchanged; only the helpers'
stale assumption about *how* to find that evidence is corrected, which is the maintenance D21
already flagged as expected here.

## D23 — T006's own test is scoped to `determine_default_language`, not to a concept actually importing

`tasks.md`'s T006 entry names two things to test: the default-language resolution itself, and "every
concept is named rather than set aside." Both are true of US-1 once it is complete, but not both are
true after T006's own commit alone. `declares-de-at.ttl`'s one concept carries no exact-tag
preferred label anywhere — its only `skos:prefLabel` is `"Rot"@de-at` — so naming it needs T007's
winner rule (`preferred_label_in` returning candidates, `import_concepts` reading
`resolve_winner`), not just a corrected default language. Tested as written, T006's commit would be
red until T007 landed, which `craft-increments` treats as a stall condition, not a valid slice
boundary.

T006's own tests therefore assert directly against `SchemeResolver.determine_default_language`'s
observable effect — the scheme's own `default_language`/`effective_default_language` fields via
`resolve_scheme`, which runs and settles regardless of whether any concept later imports — covering
both the declared-language branch and the commonest-fallback branch resolving through the matcher,
plus the unconfigured-language regression. "Every concept is named" for exactly this fixture is
T007's own stated acceptance test ("a concept whose only preferred label is a variant of the default
language still names the concept and derives its slug the way an exact match would") — the same
claim, proven where it is actually achievable.

**Revisit if:** never — this is how the two tasks' test coverage was always going to divide once
`declares-de-at.ttl`'s exact content (no exact-tag label anywhere) is accounted for; it is recorded
so a later reader does not look for "every concept is named" inside T006's own commit and conclude
it is missing.

## D24 — A default-language-branch loser's reason is decided against the tag T007 actually chose, not against `default_language` itself

T008's task text says a loser's published tag is compared "against the winner's" to choose between
`SURPLUS_PREFERRED_LABEL` and `VARIANT_NOT_KEPT` — the same discriminator T014 (US-3) states for
every other configured language. Two readings were available for what "the winner" means inside
`import_labels`, and they disagree on one reachable case.

*Reading A* — compare the loser's tag against `default_language` itself (the configured code). A
raw-tag-group duplicate under a *variant* (two `de-at`-tagged preferred labels, no exact `de` tag
anywhere) would then read as `VARIANT_NOT_KEPT`, because `"de-at" != "de"`. But its message —
"another variant was kept for the site's `de` instead" — is false: the value that *was* kept is
tagged `de-at` too, the exact same variant, not another one. Article XI's "surfaced to the user,
never silent" is not met by surfacing something wrongly (the same argument D14 already made against
reusing `SURPLUS_PREFERRED_LABEL` for a true contest loser, run in reverse here).

*Reading B (chosen)* — compare the loser's tag against the tag `import_concepts`' own
`resolve_winner` call actually chose for the default-language slot (`default_language_winner_tag`,
recomputed in `import_labels` from the identical `preferred_label_in`/`resolve_winner` call —
T021's "one winner, one computation" guarantees it agrees with `import_concepts`' own answer without
threading the value through `_import_concept_content`'s parameters). A same-tag duplicate — the
loser's tag equals whichever tag actually won — keeps `SURPLUS_PREFERRED_LABEL`, true regardless of
whether that shared tag happens to equal `default_language` exactly or is itself a variant. A
different-tag loser takes `VARIANT_NOT_KEPT`. This is the literal reading of T014's own words ("a
loser whose published tag equals the winner's *tag*") and the only one that keeps
`SURPLUS_PREFERRED_LABEL`'s message true in every case T008 can reach.

Reported under `SURPLUS_PREFERRED_LABEL`, the `language` param is always the *resolved* configured
code (`default_language`), never the raw tag that happens to be shared — consistent with T004's own
invariant that this reason's `language` names a configured code the site already holds, not a
published tag configuring something would recover.

**Revisit if:** T013/T014 (US-3) re-key `preferred_by_language` onto the resolved language for every
configured slot, not only the default one — at that point this same discriminator should read
identically for both, and worth checking that `import_labels`'s two now-separate computations (this
one, and T013's) still agree by construction rather than by coincidence.

## D25 — A pre-existing test class lost its `class` statement during US-1's insertions, and is reinstated

**Decided at:** US-1 convergence review (orchestrator), after `tamper-check` flagged
`tests/test_exchange/test_skos.py` and the flag was triaged line by line.

T007–T009 inserted three new test classes immediately above
`TestConceptsImpliedByMembershipButNeverGivenAnRdfType`. The insertion landed *between* that class's
`class` statement and its docstring: the `class` line was removed and the docstring left behind as a
bare string expression, so its five node-typing tests were silently re-parented onto
`TestLanguageSubstitutionIsReported` — a class about language substitution, which has nothing to do
with them.

Nothing failed. The methods still ran, the count was unchanged at 745, and every gate was green,
because pytest neither knows nor cares which class a test method hangs off. That is what makes this
worth a decision record rather than a silent fix: the defect is invisible to every machine check the
loop runs, and only the tamper-check flag plus a by-hand read of the deleted lines surfaced it.

**Chosen:** reinstate the `class` statement verbatim above its own docstring. No test body, name or
assertion is touched, and the count stays at 745.

**Rejected:** leaving it. Article X's testing structure requires class grouping to carry meaning, and
a class whose name says "language substitution" holding tests about `rdf:type` inference defeats
that. It would also have made the next reader of a failure in those five tests look in the wrong
place entirely.

**Revisit if:** a later story again inserts classes adjacent to an existing one — the same shape can
recur, and the only thing that caught it was reading the diff's deletions rather than trusting a
green suite.

## D26 — T011 and T012 are test-only tasks, and their tests passed on the first run

`ImportReport.language_account()` (T004) and the set-aside population it folds over
(`UNCONFIGURED_LANGUAGE` since #50, `VARIANT_NOT_KEPT` since US-1's T008) were both already
implemented and merged before this phase started. US-2's own tasks.md text asks only that the
account be exercised "from a real import rather than a hand-built report" (T011) and "end to end"
for a clean run (T012) — neither names a production change, and none was needed or made.

`craft-tdd`'s warning that a test passing on first run is usually testing nothing just written does
not apply the same way here: both tests assert a specific, falsifiable claim — an exact per-language
breakdown with distinct multiplicities for T011, and `report.set_aside == []` alongside
`language_account() == {}` for T012 — rather than a tautology, an unexercised fixture, or a wrong
import. Each was written before being run, and each was run and read before being trusted; both
happened to confirm behaviour already correct rather than drive new behaviour into existence. This
is recorded so a later reader does not look for a code change in either commit and conclude one is
missing, the same shape D23 recorded for T006.

**Revisit if:** never — this is simply what a coverage task looks like when the feature it covers
was implemented in an earlier phase.

## D27 — T013 unifies the default-language and general-language winner computations into one dict, closing the gap D24 flagged

D24 (US-1) resolved a discriminator question for the default-language branch and named exactly what
it was leaving open: "T013/T014 (US-3) re-key `preferred_by_language` onto the resolved language for
every configured slot, not only the default one — at that point this same discriminator should read
identically for both, and worth checking that `import_labels`'s two now-separate computations (this
one, and T013's) still agree by construction rather than by coincidence."

Before T013, `import_labels` ran two independent computations: `default_language_candidates` /
`default_language_winner_tag`, built via `preferred_label_in` and `resolve_winner` (T008, correct);
and `preferred_by_language` / `preferred_kept`, grouped by the *raw published tag* and reduced with
`sorted(values)[0]` — the same shape D13 named as the pre-T021 defect, never actually removed from
this call site because T008's own scope was the default-language branch alone. The second
computation is what the general (non-default) branch read, and grouping by raw tag meant two
*different* tags resolving to the same non-default configured language were invisible to each other
— each was its own singleton "winner" — so both reached `concept.add_label()` and the second call
raised `ConceptLabel.clean()`'s own uniqueness `ValidationError`, uncaught. This was a live, minimal
crash: `surplus_preferred_label.ttl` doesn't reach it (its two `de`-tagged values are the same raw
tag), so no test in the suite before T013 exercised a two-*different*-tag contest in a non-default
language.

**Chosen:** one dict, `preferred_winner_by_language: dict[str, tuple[str, str]]`, built once from
`preferred_label_in(node)` grouped by *resolved* language and reduced with `resolve_winner` per
group — literally the same call `import_concepts` makes for `Concept.label`, over the identical
candidate source. `default_language_winner_tag` is now a read of this dict's `default_language`
entry rather than a second traversal. This is what makes D24's "agree by construction, not by
coincidence" checkable at all: before T013 there were two independently-derived winners that
happened to answer the same question the same way; after, there is one.

**Rejected:** leaving the two computations separate and only patching the general branch's grouping
key. That would still let the default and general branches drift independently if a later change
touched one and not the other — the exact failure mode D13 and D24 both named, just deferred rather
than closed.

## D28 — T014's discriminator is copied logic, not a shared helper

The default-language branch's own tag comparison (`published_tag.lower() != winner_tag.lower()`)
and T014's general-branch version are the identical two lines, not factored into a shared method.
Considered and rejected: the two branches differ in what happens *after* the comparison — the
default branch's winner path is a bare `continue` (the value already lives on `concept.label`), the
general branch's winner path falls through to `concept.add_label(...)` and a possible
`LANGUAGE_SUBSTITUTION` normalisation — so a shared helper would need to either return a tri-state
the caller re-branches on (no simpler than the two lines it replaces) or grow a callback parameter
for "what to do with the winner", which is exactly the kind of hook `craft-increments`' simplicity
rule warns off building for two call sites. Two identical comparisons reading the same
`preferred_winner_by_language` dict is the smaller diff.

**Revisit if:** a third call site ever needs this same discriminator — at that point a named helper
earns its complexity.

## D29 — T015 needed no production change, and its own test proves why

FR-004's asymmetry — alternative labels, hidden labels and notes carry no per-language cardinality
limit — was never something T013/T014 touched: both changes are scoped to
`if kind == ConceptLabel.Kind.PREFERRED:` branches, and every other kind already fell straight
through to the unconditional `concept.add_label(...)` at the bottom of the loop, both before and
after T013/T014. `variants.ttl` (T005) already carries `en-gb`/`en-us` variants of an alternative
label and a note for exactly this population, built and reserved for this purpose since the
foundational phase (its own comment: "the contest population US-3 needs is exercised"). T015's tests
run this fixture and assert both variants land — SC-007 — with no code change, the same shape D26
recorded for T011/T012: a coverage task for behaviour a design decision (D4) already delivered.

The one thing worth naming: `colour`'s *preferred* label also carries an `en-gb`/`en-us` contest
(the concept's default-language slot), and it correctly produces exactly one loser entry. A test
asserting "no set-aside entry for this subject" would have been wrong — it would pass today and
break the moment someone (correctly) added a second preferred-label fixture value — so the test
asserts `len(losses) == 1` (the expected preferred-label loser, and nothing more), not `== 0`. A
`SetAsideEntry` carries no predicate or kind, only `language`, so a loss can't be attributed to "the
alternative label" versus "the preferred label" by inspecting the entry itself; count is the
distinguishing signal here, not membership.

**Revisit if:** never — the asymmetry's underlying rule is a `craft-simplify` case for staying
where it is: no cardinality contest is not an omission needing a control-flow branch, it is the
model's own constraint (or its absence) already deciding whether one is needed.

## D30 — T016 needed no production change, and its two tests are the same shape as D26/D29

FR-009's additive guarantee — a re-import after a language is added stores that language's values
for the concepts already present — is, per its own spec section, already true as a consequence of
`import_labels`/`import_concepts` resolving every published tag through `LanguageMatcher` on every
run: nothing in the matching path remembers which languages a previous run saw configured, so a
second run under a wider `LANGUAGES` simply matches more of the same file's tags than the first did.
T016 is a coverage task by tasks.md's own text, the same shape D26 recorded for T011/T012 and D29
for T015: two tests, each asserting a falsifiable claim rather than a tautology, both passed on
first run, no production code changed.

`rocks.ttl` — already the reference fixture per D16 — was reused rather than a new one written: its
`igneous`/`granite`/`sedimentary` concepts each carry an exact `fr` preferred label with no variant
contest to entangle, and the file's `fr` occurrences are countable by hand (three, one per concept),
which is what makes `first_report.language_account().get("fr") == 3` a real assertion rather than a
guess at the fixture's shape. The two-run scenario is driven through `import_skos` from the file on
disk both times, `override_settings(LANGUAGES=...)` between them, per the brief's acceptance text —
no report or model object is hand-built.

**Revisit if:** never — the same reasoning as D26/D29 applies: a coverage task for behaviour a prior
phase's design already delivers has nothing left to drive into existence.

## D31 — T017's identity assertion is scoped to Concept/ConceptScheme/Collection exactly as D16 requires, and it too needed no production change

T017's own tasks.md text spells out the scope D16 already settled: `Concept`, `ConceptScheme` and
`Collection` keep their URI, `static_uri`, slug, local URL and pk across the re-import; `ConceptLabel`
and `ConceptNote` rows do not, by #50's design, and are asserted on their values instead. Nothing
about adding a configured language touches identity assignment at all — `assign_unique_slug` and
`static_uri` resolution both run from the concept's own URI and label exactly as before, unrelated to
which languages are configured — so, like T016, this needed no production change. The same shape as
D26/D29/D30, recorded here rather than re-derived.

The identity test snapshots `(pk, uri, static_uri, slug, local_url)` for the scheme, all five
`rocks.ttl` concepts, and both collections before the second run and compares after — over every
record the fixture defines, not a sample, so a regression in any one of them would be caught. The
content test checks `granite`'s alternative label, hidden label and scope note alongside its and
`igneous`'s preferred label and definition — the label kinds T013/T014's contest could plausibly
disturb if the winner computation were ever keyed on the *set* of configured languages rather than
resolving each value independently, which it is not, but which is exactly the kind of coupling this
test would catch if introduced later.

**Revisit if:** never, for the same reason D30 gives — this is what a coverage task looks like when
the guarantee is already true by construction.

## D32 — T018's coverage lives in `test_standards.py` alongside `test_report.py`'s existing sweep, deliberately overlapping it

`tests/test_exchange/test_report.py` already parametrizes `TestSetAsideReasonVocabulary`,
`TestNormalizedReasonVocabulary`, and `TestReasonTemplatesUseOnlyNamedPlaceholders` over
`list(SetAsideReason)` and `list(NormalizedReason)`. Both closed vocabularies already contain
`VARIANT_NOT_KEPT` (T022) and `LANGUAGE_SUBSTITUTION` (T003), added in the foundational phase, so
those three sweeps already assert every claim T018's own text asks for — translatable, named
`%(subject)s`, no positional placeholder anywhere — for both reasons, without any new code. A
`TestSetAsideReasonVocabulary`-shaped test for either would be redundant with what already runs.

T018's own text names a different target: "the standards suite," not "the reason vocabulary's own
test module," and its acceptance says to follow the form of `test_standards.py`'s existing
translatable-message tests specifically. That module (Article XII home for validation-message
translatability) had no coverage of either reason at all — its own walk is over model field
metadata and `ValidationError` messages, not over `report.py`'s closed vocabularies. Two tests were
added there, `test_language_substitution_reason_message_uses_named_placeholders` and
`test_variant_not_kept_reason_message_uses_named_placeholders`, each following the file's own
form: a `Promise` check, a named-placeholder check against the raw template, and a rendered-message
check with real values substituted in — the same shape as
`test_static_uri_unsafe_scheme_message_uses_named_placeholders` two sections up.

The overlap with `test_report.py` is real and intentional, not an oversight to collapse. The two
suites hold two different things to the same standard from two different angles: `test_report.py`'s
sweep proves the *whole vocabulary* — present and future members alike — never regresses to a
positional placeholder; `test_standards.py`'s two new tests are this feature's own, targeted
evidence that its two specific additions meet Article XII, living where `tasks.md` and the brief
both said to put it. Neither makes the other redundant enough to delete.

**How RED was proven**, since neither test's assertion had ever failed before this task: `report.py`
was edited locally, twice in turn — once to make `LANGUAGE_SUBSTITUTION`'s template a bare,
non-lazy string with a positional `%s`, once to make `VARIANT_NOT_KEPT`'s template keep its
`gettext_lazy` wrapper but swap both its named placeholders for positional ones — running the two
new tests after each edit to observe the correct test fail for the reported reason, then reverting
with `git checkout` before the next edit. Neither edit was committed; `report.py` is byte-identical
to `HEAD~3` in this story's final diff.

**Revisit if:** never — this is the shape T018's own acceptance text specifies, and the redundancy
with `test_report.py` is documented here precisely so a later reader does not "simplify" one suite
away believing it duplicates the other for no reason.

## D33 — The identity-anchoring label never moves because of configuration

The S6 architecture lens found, and I reproduced independently, that adding a configured language
sharing a base with one the site already holds changes an existing concept's stored name, its slug,
and therefore its public URL — with the imported file byte-identical. On the branch's own
`variants.ttl`, configuring `en-gb` alongside `en` moved a concept from
`/vocabularies/colours/colour` to `/vocabularies/colours/color`.

The cause is a composition rather than a bug in any one place. `Concept.label` is the preferred
label in the vocabulary's default language. That default is frozen after the first import, and
correctly so, because it anchors every concept's identity. But the *winner* of the contest for that
slot is a function of which variants are configured: the moment `en-gb` becomes configured in its
own right, it stops being a candidate for `en`, and the `en` slot falls to the `en-us` value. The
slug is then re-derived from the new name on every run, by D6's own rule.

This breaks FR-009 and SC-015, and it is the harm Article IX exists to prevent — a local address
that downstream data already holds, moving for a reason that has nothing to do with the vocabulary.
SC-015's test could not catch it, because it only ever adds a language sharing no base with an
existing one.

**Two fixes were available and the choice is not close.**

*Pin the slug for an existing concept*, as `default_language` is already pinned. Rejected on two
counts. It leaves `Concept.label` itself still flipping, so the displayed name changes and only the
URL is held still — half a fix. And it overturns D6 from
[#49](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/49), a landed,
merged decision that a local URL follows a publisher's rename while the identifier does not.
Breaking a shipped decision to patch a symptom of a different one is the wrong trade.

*Resolve the default-language contest over the whole base-language group*, independent of which
variants happen to be configured. Chosen, and narrowed to that one slot: it is the only slot that
anchors identity, so it is the only one where configuration must not reach. Every other slot keeps
FR-002's placement, which is what maximises stored content.

**The cost, stated plainly.** A value can now fill both its own exact slot and the default-language
slot, so `Colour@en-gb` is stored under `en-gb` *and* under `en`. And the `en-us` spelling remains a
reported contest loser rather than being stored. That second point is the one worth sitting with,
and it is why this is defensible: it is *exactly what already happened* before the language was
added. The curator's picture does not change when they configure `en-gb`, which is the entire
guarantee US-4 promises. Stability across the re-import is the property being bought, and paying for
it with an outcome that was already true is a cheap price.

The rule states in one sentence, which is how it will be remembered and how the README will carry
it: **the label a concept is named by never moves because of configuration.**

Spec amended rather than worked around: FR-016 added, FR-002 annotated with the carve-out, SC-022
added with the explicit requirement that its test add a *base-sharing* language. Sam delegated this
decision explicitly ("your choice ... you make an informed decision") after I put both options and
their consequences to him, so it is recorded here rather than re-gated.

## D34 — Three defects the panel found, and why each is a real regression

Recorded together because they share a shape: each is a case where variant matching newly routes a
value down a path that was previously unreachable, and the path was not ready for it. All three were
reproduced against the branch and shown to behave correctly on `main`.

**SEC-001 — an unconfigured default language stores nothing.** `effective_default_language` falls
back to `settings.LANGUAGE_CODE`, which is validated nowhere against `settings.LANGUAGES`. The
matcher can only ever return a configured code, so when the default is unconfigured, no published
tag can resolve to it and every concept is set aside for want of a preferred label. Django's own
defaults are precisely this shape: `LANGUAGE_CODE = "en-us"`, and the 99-code default `LANGUAGES`
contains no `en-us`. The previous exact-equality comparison matched, so this is a regression against
a configuration most consuming projects have by simply never overriding it. It is reported as one
problem naming the unconfigured default, not as one missing-label entry per concept — a curator
reading ten thousand identical entries learns nothing from the tenth.

**SEC-002 — an over-long label aborts the whole run.** Values in a variant tag now reach
`Concept.add_label`, whose `full_clean` raises on text beyond 255 characters. Nothing catches it, so
one verbose alternative label in a hostile or merely careless file rolls back an entire import.
Guarded the way `EMPTY_SLUG` already guards the slug: catch the refusal, set the value aside with
its own reason, carry on. Article V names imported RDF untrusted, and a single field length should
not be able to deny the whole import.

**CORR-001 — the account is blind exactly where it matters most.** A concept skipped for having no
preferred label never reaches the code that records its other values, so none of its languages enter
the account. The failure lands precisely on the concept that was wholly lost, which is the one a
curator most needs to be told about. FR-008's sufficiency clause and SC-012 both fail. Fixed by
accounting the skipped concept's own published tags before continuing.

## D35 — A local address is derived from the published identifier, never from a translated label

Supersedes D33, which is withdrawn before any code implemented it, and overturns
[#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50)'s D6.

**The maintainer's correction, which is the right one.** A published vocabulary gives every record
an identifier with a stable path. That path does not move when a label is translated, corrected, or
read in a different language, because it was never made of a label. This application's own addresses
must behave the same way: `/{vocabulary}/{record}` is composed from published identifiers and never
from a translated value.

**D33 was the wrong layer, and worth naming as such.** It held the default-language label still so
that a slug derived from that label would stay still. That is a symptom treated one step away from
its cause: the slug should not have been derived from a translated value in the first place, and
every rule built to stabilise the label was scaffolding around a mistake. It also cost a carve-out
in FR-002, which now stands as the Spec gate approved it.

**R1 already built the mechanism, and #50 declined to use it.** `Concept.set_slug` marks a slug
manual so `save()` stops re-deriving it, and its docstring says why it exists: *"this same mechanism
later carries an imported vocabulary's own slugs unchanged (spec R2)."* #50's `assign_unique_slug`
went the other way and said so plainly — *"Nothing is derived from `concept.static_uri` — identity
and slug are deliberately independent"* — and pinned the reasoning in D6: an identifier made of
opaque codes produces an unreadable local address. That is a real cost and it is the smaller one.
Readability of a URL is a preference. A URL that moves under data already pointing at it is a
correctness failure, and Article IX names downstream-data safety as the thing that must not break.

**The scope is wider than the case the review found.** `ConceptScheme.save()` re-derives its slug
from its name on every save with no manual mechanism at all, so a vocabulary's name arriving in a
different language moves the address of *every record it holds*. Measured:

```
before: scheme.slug=colours | concept.local_url=.../vocabularies/colours/clay
after : scheme.slug=colors  | concept.local_url=.../vocabularies/colors/clay
```

`static_uri` was unchanged throughout. Both segments of the address were label-derived, so both are
in scope, and the vocabulary needs the pinning mechanism the concept already has.

**Two rules decided here rather than escalated, because both follow from the identifier itself.**

*Which part of the identifier.* The fragment where the identifier has one, otherwise the last
segment of its path. SKOS vocabularies use fragment identifiers constantly
(`http://example.org/scheme#clay`), and for those the fragment is the record's name in every sense
that matters.

*Collisions.* Two records in one vocabulary can end in the same segment when their paths differ.
The suffix that separates them is derived from the identifiers, not from read order, so the same
file yields the same slugs however it is traversed. #50's existing suffix rule is order-dependent
and is replaced rather than reused.

**Why this lands in this feature rather than its own.** It changes behaviour #50 shipped, which
normally argues for separate work. FR-009 is the reason it cannot wait: this feature's approved spec
already promises that a re-import does not alter a record's local address, and with label-derived
slugs that promise is unkeepable. The fix is not scope added on top of FS-007, it is what makes
FS-007's own approved requirement true. Shipping D33's workaround instead would mean landing code
written to be deleted.

**Cost, named rather than hidden.** Local addresses for vocabularies published under opaque codes
become opaque — `/vocabularies/v-113/00123` where today they read `/soil-types/clay`. D6 called that
out and it remains true. It is accepted because the addresses are correct and permanent, which is
what a vocabulary's consumers need from them, and because a readable-but-unstable address is worse
than an opaque stable one for every use a URL is put to.

## D36 — Fix cycle 1 landed the withdrawn FR-016, and removing it is booked rather than reverted now

The fix-cycle implementer was dispatched before FR-016 was withdrawn, so T023 built
`LanguageMatcher.resolve_identity_winner()` and three tests around it. A subagent's brief is fixed
at dispatch, so the withdrawal could not reach a child already running. The code is on the branch
and it is green.

It is not reverted in place. `git revert` on T023 conflicts against T024–T027, which touch the same
region of `skos.py`, and hand-resolving a revert is exactly the kind of edit that lands untested.
Removal is instead a task in the FR-017–FR-020 dispatch: delete `resolve_identity_winner` and its
call sites, restore the FR-002 rule the carve-out displaced, and replace T023's three tests with
slug-level stability assertions — which is where the guarantee belongs once a local address is
derived from the published identifier rather than from a label.

Until that task lands, the branch carries an implementation of a withdrawn requirement. Named here
so it cannot be mistaken for an intended behaviour by a later reader of the diff.

## D37 — The craft-skill receipt gate red-blocked a clean report, and the cause is a mid-flight registry bump

`forge check-receipts` failed the fix-cycle report: it echoed `craft-tdd/2026-08-04/c95488d8` where
the registry now holds `craft-tdd/2026-08-05/eae3b6c7`.

The child was honest. Its transcript shows it loaded the skill and that the body it was given —
staged under `/tmp/openclaw/openclaw-claude-skills-*` at dispatch — ended with the 2026-08-04
receipt. A concurrent run on another repo edited `craft-tdd` and bumped its receipt in both the file
and the registry *while this child was running*. The dispatch brief, written at dispatch, recorded
the receipt that was then current; `forge check-skills` passed for the same reason.

So the gate compares a value fixed at dispatch against a registry that moves, and any skill edit
during a long child run retroactively fails a report that did nothing wrong. Overridden here on the
evidence above, which is a human judgement over a red gate and is recorded as such. The delta the
child missed is the per-task test-scope narrowing of 2026-08-05 — a cost rule, not a correctness
rule, and its only effect was that the child ran the full suite more often than it needed to.

**The deeper defect the diagnosis exposed.** The brief hands the child the receipt it is supposed to
echo, so echoing it has never proved a read. That is a kit fix, not a feature fix, and it is booked
as a retro proposal with the two gaps already recorded there.

## D38 — T029 rewrites the pre-existing tests and fixture that encoded D6, rather than leaving them red

`craft-tdd`/`craft-increments` both prohibit editing or deleting a test not authored in this cycle,
on pain of exactly the failure D25 and the FIX-1 note about broadened assertions describe: an
implementer quietly weakening coverage to make their own bug disappear. Five pieces of pre-existing
test material did not survive T029 unedited, and none of the five is that failure — each is the
literal, named codification of D6, which D35 (this same story, maintainer-approved) states in its
own words "overturns."

- `tests/test_exchange/test_skos.py::TestConceptSlugs` — its class docstring cited "decisions.md
  D6" by name and asserted a concept's slug is "never derived from the identifier." Rewritten to
  assert FR-017/D35's opposite rule instead of left red: `test_slug_is_never_derived_from_the_identifier`
  is gone, replaced by two identifier-shape tests (SC-026) and a publisher-rename stability test
  (SC-027, using the existing `rocks.ttl`/`rocks_updated.ttl` pair rather than a new fixture — T014's
  own test already proves the label change lands, this one adds that the slug and `local_url` do not
  follow it). `test_two_concepts_sharing_a_label_get_distinct_deterministic_slugs`'s expected values
  changed from `"quartz"`/`"quartz-2"` to `"quartz-a"`/`"quartz-b"`, because `duplicate_slug.ttl`'s
  two concepts collide on label, not on identifier, and D35 slugs from the identifier —
  demonstrating the collision no longer exists is the point, not an incidental side effect.
  `test_reimporting_the_identical_file_keeps_each_concept_s_slug` needed no change: it asserts
  before/after equality with no literal value, so it is agnostic to what changed.
- `tests/test_exchange/test_skos.py::TestConceptLabelIsSelectedByTheWinnerRule::test_an_exact_match_is_not_displaced_by_a_more_predominant_variant` —
  asserted `target.slug == "alpha"` as a side effect of asserting `target.label == "Alpha"`. The
  label assertion (the test's actual subject) is untouched; the slug assertion is corrected to
  `"target"`, the URI's own last path segment.
- `tests/fixtures/skos/empty_slug_label.ttl` and its two tests
  (`TestEmptySlugLabelIsSetAsideNotCrashed`) — FIX 5/D39's `EMPTY_SLUG` guard existed because a
  label made only of characters `slugify()` strips (`"±"`) used to produce an unusable *slug*. Under
  D35 the slug no longer reads the label at all, so that fixture's `symbol` concept now imports
  cleanly with slug `"symbol"` — the guard is real but nothing in the story's existing test material
  reaches it any more. The fixture's `symbol` concept was renamed to carry the unusable value in its
  own identifier instead (`<.../emptyslug/symbol#±>`), which is what can produce an empty slug under
  the new rule, and the two tests' expected subject URI updated to match. The guard itself
  (`assign_unique_slug`'s pre-write `slugify(...)` check) is untouched; only what triggers it moved.
- `tests/test_exchange/test_skos.py::TestExactMatchPreferredLabelFailingOnItsOwnMeritsIsNotBackfilledByAVariant` —
  demonstrated the spec's "exact match wins the contest and then fails on its own merits, and the
  variant does not silently take its place" edge case through the same `EMPTY_SLUG` mechanism, using
  an inline `"±"` label. That mechanism no longer reaches through the label either, so the edge case
  needed a different, still-live way for an exact match to "fail on its own merits": the label is
  now 300 characters, which trips the pre-existing, label-keyed `VALUE_TOO_LONG` guard (SEC-002,
  D34) instead — a real, unrelated failure mode this story does not touch, chosen because it is
  still driven by the label's own content rather than the identifier's.

None of the five was weakened: every rewritten assertion is exact-value equality, same as what it
replaced, and every test that needed no change (the two before/after comparisons) was left alone.
The full suite was green (335/335 in `test_skos.py`, 792/790 overall) before this entry was written.
**Revisit if:** a later reviewer wants these five kept as their own dated regression tests against
D6 specifically — they are not, on the view that a superseded rule's test is not evidence worth
preserving once the rule it tested is gone, the same position D25 takes about a test's home
mattering more than its literal survival.

## D39 — `SchemeResolver.resolve_scheme` recomputes the scheme's slug on every touch, not only on creation

T030's own task text reads naturally as "assign once, at creation" — the same shape T029 gives a
concept. Concept's own mechanism does not actually work that way, though: `assign_unique_slug` runs
unconditionally for every concept `import_concepts` touches, created or matched-existing alike, and
that is safe only because `concept.static_uri` is invariant once a concept is matched — recomputing
the base from it always reproduces the value already stored.

The same invariant holds for a scheme: `_get_or_create_scheme(declared_uri)` matches an existing row
by `get_by_uri(declared_uri)`, so on every re-import of the same vocabulary, `declared_uri` is by
construction the identifier that row was already matched on. Recomputing
`identifier_slug_segment(declared_uri)` on every call therefore always reproduces the slug already
stored, exactly as for a concept, so gating on `created` would add a branch that changes nothing
observable. Doing it unconditionally is also what keeps a scheme created outside the importer (a
curator's own row, given a `static_uri` directly, matched by a later import) reachable by the same
rule the moment it is: a scheme's `slug_is_manual` defaulting `False` on creation is exactly the
guard T031 relies on for locally-authored records with no `static_uri` at all, and it stays correct
for a scheme that is never matched by an import.

**Revisit if:** never — this is the same reasoning `assign_unique_slug` already relies on,
transplanted to the one call site that creates or matches a scheme rather than a concept.

## D40 — T032 needed no production change beyond T029's own

FR-020/SC-029 asks that a collision between two identifiers resolve "from the identifiers, not from
read order." `ConceptImporter.import_concepts` already sorts `concept_nodes` by the full identifier
string before ever processing one (`sorted(..., key=str)`, present since #50), so the order a file's
own author declares its concepts in was never actually consulted — a fact D6's own suffix rule
happened not to depend on either, because a fixture demonstrating it (`duplicate_slug.ttl`) collided
concepts on their *label*, and D6 derived the suffix base from the label, not the identifier.

Once T029 changed `assign_unique_slug`'s base to `identifier_slug_segment(concept.static_uri)`, two
concepts colliding on their identifier's own last segment resolve through the same pre-existing
`taken_slugs` mechanism (FIX 16, D49) T029 left untouched: the URI-sort decides who claims the bare
slug on a first import, and `taken_slugs`, seeded from each concept's own stored slug on every
re-import, reads a concept's prior answer back before ever minting a new suffix — so a slug never
depends on which pass of the file assigned it first. This is the same shape D26/D29/D30/D31 already
recorded: a coverage task (`TestConceptSlugCollisionIsIdentifierDerived`, two tests, both a specific
falsifiable claim rather than a tautology) that passed on first run because the design was already
correct, this time as a consequence of T029 rather than of an earlier phase.

**Revisit if:** never — the same shape as D26/D29/D30/D31, recorded so a later reader does not look
for a second collision algorithm and conclude one is missing.
