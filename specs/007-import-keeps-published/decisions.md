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
