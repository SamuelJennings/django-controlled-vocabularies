# Decisions — 013 Find a vocabulary

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry records what was unclear, what was chosen, and why the choice is defensible.
Decisions taken *with* the maintainer live in `spec.md` under `## Clarifications`.

## D1 — An entry names a vocabulary without linking to it
**Ambiguous**: a list of vocabularies that cannot be clicked is an unusual thing to ship, and the
data already carries the address every entry would link to — every scheme composes a local URL from
the site's configured address and its own slug, and has done since R1. Nothing serves that address.
The specification could have required the link and left it broken until #141 lands.

**Chosen**: no entry links to the vocabulary it names. #141 turns the name into a link in the same
change that gives it somewhere to lead.

**Why defensible**: the alternative ships a front door whose every door leads to a missing page, in
a release that may sit between the two features for as long as it takes to build the second. It is
also the reason #141 was made to depend on this feature rather than the reverse: the dependency
exists precisely because the second feature completes the first. The cost is one line of the
specification (FR-013) and one line of it deleted later, against a release where the package's first
public page is visibly broken. This is FR-013 and User Story 1.

**ADR:** none — no standing rule, a sequencing decision local to this pair of features.

## D2 — Alphabetical order, not most-recent or largest
**Ambiguous**: nothing in the issue or in grilling states an order, and a list with no stated order
is a list whose order can change between two requests to the same database.

**Chosen**: alphabetically by name, case-insensitively, stable across requests.

**Why defensible**: every other candidate encodes a guess about why the reader came. "Most recently
imported first" serves the administrator who just ran an import and nobody else; "largest first"
asserts that a big vocabulary matters more than a small one. Alphabetical is the only order a reader
can predict before the page loads, which is what makes a list scannable rather than merely sorted.
This is FR-004.

**ADR:** none.

## D3 — The count is concepts, and nothing is excluded from it
**Ambiguous**: a vocabulary holds concepts, collections and ordered collections, and a concept has
a lifecycle in the design that would eventually make a deprecated concept a candidate for exclusion.
"How many concepts it holds" could mean any of several numbers.

**Chosen**: the number of concepts in the vocabulary. Collections are not counted. Nothing is
excluded.

**Why defensible**: a collection groups concepts and is not one, so counting it would report a
vocabulary as larger than it is, twice over for a concept in two collections. Nothing is excluded
because there is nothing to exclude: the `draft` → `published` → `deprecated` lifecycle is design
intent (`docs/brainstorm.md`), the concept model carries no status field today, and a rule written
now for a state that does not exist would be an untested assumption dressed as a requirement. When
R4 builds the lifecycle it decides whether a deprecated concept still counts, which is a decision it
is equipped to make and this feature is not. This is FR-002.

**ADR:** none.

## D4 — Two distinct empty states, never one
**Ambiguous**: a page showing no vocabularies has two causes — the site holds none, or the search
matched none — and the simplest implementation shows the same words for both.

**Chosen**: distinct wording for each. An empty site says the site holds no vocabularies. A search
matching nothing says so, repeats what was searched for, and offers the way back to the full list.

**Why defensible**: the two readers are different people in different situations. An administrator
seeing "no vocabularies here" after an import needs to know the import did not land; a visitor whose
search missed needs to know their search missed, not that the site is empty — and being told a
populated site is empty is a false statement the page has the information to avoid. Repeating the
search term back matters for the same reason a form redisplays what was typed: a mistyped word is
invisible once the box is the only record of it. This is FR-009 and FR-011.

**ADR:** none.

## D5 — Search runs over the whole set, before paging
**Ambiguous**: pagination and search interact, and the failure is silent in the direction that
matters. A search applied to the page being viewed returns plausible results.

**Chosen**: the search selects from every vocabulary the site holds; the results are then divided
into pages. Paging preserves the search.

**Why defensible**: the wrong version fails exactly when the feature is needed. On a short list,
searching one page and searching all of them give the same answer; the divergence starts at the
length that made search worth having, and the result — "no vocabulary matches" on a site that holds
one — is indistinguishable from a correct answer. This is FR-008 and FR-010, and the reason User
Story 2 carries an acceptance scenario that searches from the second page.

**ADR:** none.

## D6 — Imported is read from the identifier, and R4 will complicate it
**Ambiguous**: "authored here" versus "imported" is not a field. The only signal the data carries is
whether the identifier was fixed by someone else — `static_uri` present means the record's identity
belongs to a publisher.

**Chosen**: an entry is shown as imported when its identifier is fixed, and as held here when it is
not.

**Why defensible**: it is the only signal available, and it is correct for every vocabulary that can
exist today. It is knowingly incomplete for one that cannot yet: publishing a vocabulary from this
site (R4) also fixes its identifier, at which point a locally authored vocabulary would read as
imported. That is R4's to settle — it is the feature that creates the second way for an identifier
to become fixed, and it will have to distinguish them for export and for the curator interface as
well as for this page. Recording the limit here means R4 meets it as a known consequence rather than
as a bug report from this page. This is FR-003 and the fourth assumption in `spec.md`.

**ADR:** none — R4 will need one if it chooses a mechanism rather than a field.

## D7 — T001 and T005 land in one commit; the repo's own pre-commit gate requires it
**Ambiguous**: T001 declares `django-mvp` as an optional dependency and its acceptance says
`deptry` runs clean. But nothing under `controlled_vocabularies/` imports `mvp` until T005's
`ui/checks.py` does, and this repo's `.pre-commit-config.yaml` runs `deptry` as a commit-time hook
— not just a story-end check. A first attempt to commit T001's `pyproject.toml`/`poetry.lock`
alone was rejected by the hook: `DEP002 'django-mvp' defined as a dependency but not used in the
codebase`. Committing `checks.py`'s import without T001's dependency declaration fails the inverse
way — `DEP001`, an import with nothing declaring it. The two halves are only ever valid together.

**Chosen**: `ui/checks.py` genuinely does `try: import mvp` inside `check_mvp_installed` (not
`importlib.util.find_spec`, which `deptry`'s static scan does not count as usage), and T001's
`pyproject.toml`/`poetry.lock`/workflow changes land in the same commit as T005's `checks.py` and
`apps.py`. T002, T003 and T004 land as their own separate commits in between — none of them touch
`pyproject.toml` or import `mvp`, so the gate has no opinion on them. Task IDs T001 and T005 both
appear in that commit's subject and body so the mapping from commit to task stays traceable.

**Why defensible**: this is a tooling constraint discovered while implementing, not a design
choice — the gate is correct (an optional dependency nobody imports yet, and an import nobody
declared, are both real defects to catch in a shipped commit) and there is no way to satisfy it
one task at a time without a throwaway import or a temporary `per_rule_ignores` entry, either of
which is scope invented purely to appease the hook and removed moments later.

**ADR:** none — a Phase 1 commit-sequencing note, not a design choice future work revisits.

## D8 — `tests/urls.py` is untouched by T003; the ui mount waits for T006
**Ambiguous**: T003's own text in `tasks.md` says `tests/urls.py` should mount
`controlled_vocabularies.ui.urls` under a non-empty prefix. But that module is created by T006
(Phase 2, US-1), which is out of Phase 1's scope — my brief's prohibitions name "the ui view,
templates, urls" as US-1's work, not Phase 1's, and T003's acceptance criterion in the brief
tests only `INSTALLED_APPS` and `manage.py check`, not a urls.py mount.

**Chosen**: leave `tests/urls.py` exactly as it was before this story. `tests/settings.py`'s
`ROOT_URLCONF` still resolves to it unchanged. T006 adds the `include()` line when
`controlled_vocabularies/ui/urls.py` exists to point it at.

**Why defensible**: `include("controlled_vocabularies.ui.urls")` imports its target the moment
`tests/urls.py` itself is loaded (Django's URL resolver, unlike a settings string, is not lazy
about a string `include()` target) — mounting it now would raise `ModuleNotFoundError` from
`manage.py check`'s own URL-resolution checks, failing T003's actual, brief-given acceptance
before it could ever pass. Nothing downstream in this phase reads `tests/urls.py`'s ui mount;
T004's boot proof resolves against `tests.urls_core` instead.

**ADR:** none — a scope boundary already drawn by the brief's own prohibitions, not a new choice.

## D9 — The two tamper flags on US-1's diff are the plan's own instruction
**Ambiguous**: the guardrail flags `tests/settings.py` and `tests/urls.py` as pre-existing test
files this branch modified. That is the shape of a suite being bent to fit the code, and it is
checked precisely because a plausible reason is always available.

**Chosen**: both accepted, neither escalated.

**Why defensible**: they are test *configuration*, not assertions, and both changes are the ones
T003 and T006 were written to make — the test project cannot render a page whose app it does not
install or whose routes it does not mount. Read against `main`, the diff on both files is additive:
the ui stack appended to `INSTALLED_APPS`, django-mvp's context processor and settings added, and
one `include()` added under a prefix. No existing assertion, fixture or setting was weakened or
removed, and the full suite that ran against the old configuration still passes — 1395 tests before
US-1's own, and green afterwards. Verified by reading the diff, not by the flag's own explanation.

**ADR:** none — a triage record, not a design decision.
