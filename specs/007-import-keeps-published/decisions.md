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
