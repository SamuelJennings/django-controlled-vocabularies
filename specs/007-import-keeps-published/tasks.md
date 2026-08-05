# Tasks — 007 Import keeps the languages the site supports and reports the rest

Every task is test-first (Article I): the failing test comes before the code that satisfies it, in
the same task. Task ids are stable and never reused. Stories here are **not** independently
dispatchable in parallel — they cut across the same four methods of `exchange/skos.py`
(`research.md` R5), so they run sequentially, each rebased on the last.

**Tasks have no issues** — this file and `feature-state.json` are the whole task record.

## Phase 0 — Foundational (sequential, blocks every story)

- **T001** — `exchange/languages.py`: the `LanguageMatcher` class and the small frozen result it
  returns (the configured language a tag resolved to, and whether that was the tag the file used).
  Construction takes the configured languages and the per-base-language predominance ranking, and
  the instance is immutable afterwards. Resolution rules, all in this task: case-insensitive
  comparison; an exact match always wins (FR-002); otherwise the least specific configured language
  sharing the base (FR-002); otherwise no match (FR-001). Tests: every rule above as its own case,
  plus **the `sga` regression** — a site configured for a language Django ships no translation
  catalog for still resolves it — which is the test that stops a later maintainer replacing this
  with `django.utils.translation.get_supported_language_variant` (`research.md` R1). The docstring
  states that rejection and why, at the code.
- **T002** — The predominance pre-pass: a constructor path that builds a `LanguageMatcher` from a
  parsed graph, counting how often each published tag appears across the vocabulary's labels so a
  contest can be settled by the variant it predominantly publishes in (FR-003, `research.md` R2).
  Tests: the ranking reflects the whole file rather than any one concept, ties resolve by language
  code, and a file whose predominant variant is a language the site does not hold at all decides
  nothing about which configured variant wins (spec Edge Cases).
- **T003** — `report.py`: `NormalizedReason.LANGUAGE_SUBSTITUTION` with its translatable,
  named-placeholder template, naming the published tag and the language the value was stored under
  (FR-006, Article XII). Tests: the entry is inspectable as data, renders in the caller's active
  language, and sits in the normalised bucket rather than the set-aside one, so a caller filtering
  for "things that did not make it in" still gets a truthful answer (`research.md` R4).
- **T004** — `report.py`: the per-published-language account (FR-008) as a method folding
  `set_aside`, not a field accumulated beside it (`research.md` R3). Tests: counts cover every value
  not stored for a language reason and no value that was stored; the result is present and empty
  after a run that left nothing behind; a caller can rank languages by what configuring them would
  recover without parsing any rendered message.
- **T005** — Fixture vocabularies under `tests/fixtures/` (FR-015): one vocabulary carrying several
  variants of one base language across preferred labels, alternative labels, and notes; one
  published in a single variant only, for the both-directions scenarios; and one declaring itself in
  a variant of a configured language, for the default-language path. Test: each is discoverable from
  the suite and parses.

## Phase US-1 — A vocabulary published in a variant of the site's language imports (#69, P1)

- **T006** — `SchemeResolver.determine_default_language` resolves through the matcher instead of
  testing set membership (FR-007, call site 1). Tests: a vocabulary declaring itself `de-at` on a
  site configured for `de` resolves its default language to `de`, and every concept is named rather
  than set aside for having no label in the default language — the failure `decisions.md` D9
  describes.
- **T007** — `SkosGraph.preferred_label_in` selects `Concept.label` through the matcher (call site
  2). Tests: a concept whose only preferred label is a variant of the default language still names
  the concept and derives its slug the way an exact match would (spec Edge Cases).
- **T008** — `ConceptImporter.import_labels` and `_import_notes` stop testing set membership and
  resolve instead, storing a matched value under its resolved configured language (FR-001, call
  sites 3 and 4). Tests: the two directions of SC-001 and SC-002 end to end from a fixture file; a
  tag differing only in case is an exact match (SC-004); a tag sharing no base language with any
  configured language is still stored nowhere and still named in the report (SC-003).
- **T009** — Every value stored under a language other than its published tag is reported as a
  substitution (FR-006). Tests: the substitution is named, is distinguishable from a value that was
  not stored at all, and does not appear in the not-stored account.
- **T010** — The invariant test for FR-010: across every matching path in this feature, no content is
  stored in any language absent from the site's configuration (SC-017). This is the test that would
  fail if a later change made the matcher permissive.

## Phase US-2 — A curator can see what was left behind and what it would take to keep it (#70, P1)

- **T011** — The account populated from a real import rather than a hand-built report: a fixture
  carrying values in three languages the site does not hold produces counts per published language
  (SC-011, SC-012). Tests drive from the file, the way a curator reaches it.
- **T012** — The clean-run case end to end: an import that left nothing behind yields an account
  that is present and empty (SC-013), so #52 can render from it without asking which kind of run
  produced it.

## Phase US-3 — Competing variants resolve the same way every time (#71, P2)

- **T013** — The contest in `import_labels`: `preferred_by_language` keys on the resolved configured
  language rather than the raw tag, and the winner is decided exact-match-first, then predominance,
  then the existing lexicographic tie-break within one tag (FR-003, call site 3). Tests: SC-005 and
  SC-006, including that importing the same file twice stores the same value both times.
- **T014** — Contest losers are set aside and reported with their **published** tag, reusing
  `SetAsideReason.SURPLUS_PREFERRED_LABEL` rather than adding a near-duplicate reason (FR-005,
  `research.md` R4). Tests: SC-008, and that the run still succeeds.
- **T015** — The asymmetry, as its own task because it is the most likely thing to get wrong
  (FR-004): alternative labels, hidden labels, and notes have no per-language cardinality limit, so
  several variants resolving to one configured language are **all** stored and none set aside
  (SC-007). Test: a concept carrying `en-gb` and `en-us` alternative labels on an `en` site keeps
  both.

## Phase US-4 — Adding a language and re-importing fills it in (#72, P2)

- **T016** — The additive re-import guarantee (FR-009): import under one configured language,
  reconfigure for two, re-import the same file, and assert the new language's values are stored for
  concepts already present (SC-014). Test drives the whole path from files on disk.
- **T017** — The nothing-else-changed half of the same guarantee (SC-015, SC-016): every identifier,
  local address, and database identity is unchanged across that re-import, content in the languages
  already stored is unchanged, and the newly stored values are no longer counted as left behind.

## Phase US-5 — Translatable messages, deliberate indexing, and reusable test material (#73, P3)

- **T018** — The standards test covers this feature's new message (Article XII): translatable, named
  placeholders, in the closed reason vocabulary (SC-018).
- **T019** — `CONTEXT.md` gains base language, variant, and substitution as glossary entries
  (FR-014, SC-019), so the vocabulary of the report matches the vocabulary of the documentation.
- **T020** — README's import section states the matching rule and its script caveat, and CHANGELOG
  records the behaviour change (Article VI). Public markdown, so it is humanized before it lands.

## Not in this feature

- Rendering any of this at a terminal — #52 owns it, and FR-011 forbids adding a surface here.
- Any script-awareness narrowing of the base-language rule. Raised at the Spec gate, approved as
  specified, and a change to it is a new decision rather than an implementation choice
  (`decisions.md` D6).
