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

**ADR:** none — the spec states it as a requirement, and it binds this one list. Nothing downstream inherits a rule from it.

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

**ADR:** none — the decision defers to R4 rather than settling anything. R4 will need one when it
chooses whether a deprecated concept still counts.

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

**ADR:** none — FR-009 and FR-011 carry it as requirements on this page. If the sibling pages adopt
the same split it becomes a house rule worth recording, and #141 is the place to notice that.

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

**ADR:** none — FR-008 already carries it as a requirement; an ADR would restate the spec rather than explain a choice the spec does not.

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

## D10 — The wrapping form owns `id="filterForm"`; the submit button is written by hand, not inherited
**Ambiguous**: research R4's chosen fix ("wrap django-mvp's search action in a `GET` form of our
own") reads as inheriting `cotton/page/list/actions/search.html` wholesale. Rendering it wholesale
does fix the submission defect, but it also brings the component's own submit button, whose label
is `text="Search"` — a bare string literal, not `{% trans %}`d, with no `c-vars` exposed to override
it. Plan.md's own key design decision #2 additionally commits to "our own `{% trans %}`d submit
button", which the component cannot produce no matter how it is called.

**Chosen**: the block builds the field directly with `<c-form.field>` — the same primitive
`actions/search.html` itself calls, with the same `name="q"`, `value`, `aria-label` and icon-prelabel
slot — inside our own `<form method="get" id="filterForm">`, and renders our own `<c-button
type="submit" text="{% trans "Search" %}">` beside it. The field's own `form="filterForm"` attribute
is kept (matches research R4's framing — redundant rather than wrong, now that the id exists on the
enclosing form) rather than dropped, so the markup stays legible against upstream's own component.

**Why defensible**: the alternative that keeps the component's button (accepting an English-only
label, contrary to the plan) or renders both buttons side by side (confusing, untested by the task's
own acceptance criteria) are both worse than the one extra `<c-form.field>` call this duplicates.
The duplication is the field's config only — one component call — not the six-file duplication R4's
option 2 rejected. Confirmed by rendering the page: exactly one `<form id="filterForm">`, one input
named `q`, one submit button, translated.

**Revisit if**: django-mvp exposes a `button_text` (or similar) var on `actions/search.html` —
raised in the issue this block's own comment names — at which point the block can go back to
rendering the component directly.

**ADR:** none — a workaround for a named upstream defect, scoped to one template and expected to be
reverted. Recording it as an ADR would outlive the problem it describes.

## D11 — `TestVocabularyList.test_page_renders_no_sort_filter_or_create_control` is left red, not edited
**Ambiguous**: that test (T006, US-1) asserts `'name="q"' not in content` — true only because no
search box existed yet. T011 gives the page a search box by design (FR-006, plan.md), so the
assertion is now definitionally false, and the brief's own prohibitions call this scenario out by
name: "Never modify or delete a test you did not author in this story... If one genuinely must
change, mark the task blocked and say why."

**Chosen**: the assertion is left untouched. T011's own acceptance (its new `TestVocabularySearch`
tests, scoped by `-k Search`) is unaffected and green. The pre-existing test fails in the story-end
full-suite run, reported there rather than fixed here.

**Why defensible**: the instruction is explicit and appears twice (skill doc and brief). Editing it
myself — even a one-line, well-justified edit — is exactly the "comply into a known-wrong state"
shape the org has been burned by before (FS-012). The other two assertions in the same test
(`'name="o"' not in content`, `"Add new" not in content`) are still true and untouched; only the
`q` line is stale, and it is stale because the feature it predates was always going to ship in this
same phase (tasks.md: "T011 rewrites the actions block T006 writes... the same test module").
Reviewer/Forge disposition is the likely fix: split the assertion out, or delete it, once someone
other than the story that invalidated it signs off.

**Revisit if**: never, from inside this story — this is Forge's to reconcile, not mine.

**ADR:** none — a triage record, not a design decision.

## D12 — D11's stale test is folded away rather than edited
**Ambiguous**: D11 left `TestVocabularyList.test_page_renders_no_sort_filter_or_create_control`
failing, correctly — an implementer may not edit a test another story authored. That left the
disposition open: split the stale assertion out, delete the stale line, or delete the test.

**Chosen**: delete the test. `TestVocabularySearch.test_the_rendered_page_carries_a_search_input_and_nothing_else`
already asserted no sort control and no filter control over the same rendered page, so the only
claim the older test still made on its own was that nothing here creates a vocabulary. That
assertion moved across, and the test it came from is gone.

**Why defensible**: editing the stale line would have left two tests making overlapping claims
about the same block of markup, which drift apart the first time one is updated and the other is
not. The older test's own name and its remaining assertions were both a description of a page that
no longer exists — the empty toolbar US-1 left behind — rather than of anything the finished
feature does. Deleting a test is normally a signal worth stopping for, which is why the decision is
recorded here and named in the pull request rather than folded silently into a commit.

**ADR:** none — a convergence triage record, not a design decision.

## D13 — A search of nothing but whitespace is not a search
**Ambiguous**: `?q=%20%20` filters nothing, because the search mixin strips the term before
testing whether there is one. The view was already reading the stripped term for its empty states,
but the page was branching on the raw value, so the box came back prefilled with the whitespace and
the way-back link offered to undo a search that had not happened.

**Chosen**: put the stripped term in the context under its own name and branch the page on that.
The raw value keeps whatever it means to the mixin. The page never reads it.

**Why defensible**: "a search is in force" now means one thing everywhere on the page, and it means
the same thing the queryset means. Stripping in the template instead would have put the same rule in
two places, and the second copy is the one that drifts.

**ADR:** none — an internal consistency fix, not a design choice.

## D14 — A long description is shortened in the template, not clamped in CSS
**Ambiguous**: an entry has to stay scannable when a description runs to several paragraphs. The
usual answer is a `line-clamp-*` class, which keeps the whole text in the page and shortens only
what is drawn.

**Chosen**: shorten the text itself, with `truncatewords`.

**Why defensible**: the class would not work. This package ships no stylesheet — the browsing page
uses the prebuilt one django-mvp distributes, which is generated by scanning django-mvp's own
templates. A utility class upstream does not already use is simply absent from that file, so the
class renders, matches nothing and reports nothing. `line-clamp-3` is absent today, checked rather
than assumed. The wider point outlives this one class: any utility class this package writes and
django-mvp does not already use is a silent no-op for projects loading the prebuilt stylesheet, so
behaviour that has to hold cannot be placed in one.

**Revisit if**: the package gains a stylesheet build of its own, or django-mvp starts distributing a
safelist a consumer can rely on. A clamp is the better rendering when it can be trusted to apply.

**ADR:** none — one template's rendering, and the constraint behind it belongs in the packaging
notes rather than a standing decision.

## D15 — The SQLite case-folding limit is disclosed rather than worked around
**Ambiguous**: the requirement says search ignores letter case, and the spec's edge cases name a
search differing only by case in a non-Latin script. On SQLite that does not hold: `LIKE` folds
ASCII letters and no others, so `Ökologie` is found by `ÖKOLOGIE` and not by `ökologie`. SQLite is
the only database this repo tests. PostgreSQL, which the package supports and which its
consuming projects run, folds the whole of Unicode.

**Chosen**: state the difference — in the README where the search is described, in the requirement,
and in a test that pins both halves — and change no query. Recorded as
docs/adr/0014-database-collation-differences-are-disclosed-not-repaired.md, because every later
search surface in this package meets the same wall.

**Why defensible**: there is no repair above the database (`Lower()` compiles to the same ASCII-only
`LOWER()`), and the two below it — registering a case-folding function on the project's connections,
or maintaining a normalised column — each cost more than the difference. The reason this could not
be left as it was is the failure mode rather than the limit itself: the reader is shown the no-match
empty state, which looks exactly like a correct answer. The existing non-Latin test could not have
caught it either, since Japanese has no case and the assertion passes either way.

**ADR:** docs/adr/0014-database-collation-differences-are-disclosed-not-repaired.md

## D16 — The search term is bounded in this view, not left to upstream
**Ambiguous**: django-mvp's search mixin ORs one condition per word per search field with no
bound, straight from `?q=`. Past roughly 400 words the expression exceeds SQLite's parser depth
limit and the page raises `OperationalError`, which is a 500 on a page anyone can reach from a
query string short enough to fit an ordinary request line. The defect is upstream's, and the
standing rule is to raise an upstream defect rather than work around it.

**Chosen**: file it upstream (django-mvp#281) **and** bound the term here, in `setup()`, before
anything has read it. The bound is 100 words.

**Why defensible**: this is handling input at our own boundary rather than reworking upstream's
markup or logic, and it stays correct whether or not upstream grows a bound of its own — a view
that caps its own input is not a fork of anything. Bounding in `setup()` rather than in the
queryset is what keeps the filtered queryset, the page's context and the empty states agreeing on
what was searched for, since the mixin reads the request directly rather than through a method a
subclass could override.

The bound's own cost is named rather than hidden: matching is OR, so dropping words drops matches,
and a truncated search answers a narrower question than the one asked. That is why 100 and not 10 —
far above any search a person means, far below where the database gives out. A test pins both
halves, the 200 and the truncation.

**Revisit if**: django-mvp caps the expression itself, or the search stops being OR across words.
The first makes this redundant rather than wrong; the second changes what truncation costs.

**ADR:** none — one view's input handling against a named upstream defect, expected to outlive the
defect but not to bind anything else.

## D17 — The demo's boot test proves the root redirect by URL resolution, not by request

**Ambiguous**: T015's test needs to prove the demo's root address is wired to the vocabulary
list (FR-015, scenario 4). The obvious way is `django.test.Client().get("/", follow=True)` and
asserting on the redirect chain — but that requires a migrated database (the view queries
`ConceptScheme`) and `"testserver"` in `ALLOWED_HOSTS`, neither of which the demo's own
settings should carry only to satisfy this test: a migrated scratch database duplicates what
T016's seed test already proves, and `"testserver"` in a settings file a reader treats as the
real configuration is exactly the kind of test-only value plan.md's Complexity Tracking already
rules out for this module.

**Chosen**: `django.urls.resolve("/")` against the demo's own urlconf, asserting the matched
view is `RedirectView` with `pattern_name="controlled_vocabularies_ui:vocabulary-list"` and
`url_name="home"`. No database, no test client, no settings changed to accommodate the test.

**Why defensible**: this proves exactly what FR-015 requires — the root address is configured to
lead to the list — without asserting anything about the view's runtime behaviour, which is
already covered by `test_ui/test_views.py` and, end to end over real HTTP, by T017's unattended
walk (FR-017). A resolution check and a live-server walk are complementary evidence, not a gap
between them.

**Revisit if**: this test starts standing in for the smoke walk rather than beside it — at that
point it should assert less, not more.

**ADR:** none — one test's own method, not a package-wide rule.

## D18 — `seed_demo` is tested by passing a `Command` instance to `call_command`

**Ambiguous**: T016's test needs to run the real `seed_demo` command against the test database
and assert on what it left behind. The ordinary way, `call_command("seed_demo")`, resolves the
command by name through `django.core.management.get_commands()`, which walks `INSTALLED_APPS`
— and `demo` is deliberately not one of `tests.settings`' installed apps (T015, D17): it carries
only the front end's own settings and urlconf for the pytest process, not the demo project's.

**Chosen**: `call_command(Command())` — passing an already-imported `Command` instance rather
than a name string. This is `call_command`'s own documented second calling convention, not a
workaround: it runs the identical `execute()`/`handle()` path — argument parsing, `self.style`,
`self.stdout` — that `manage.py seed_demo` runs, against a command object the test imports
directly (`from demo.management.commands.seed_demo import Command`).

**Why defensible**: nothing about the command is faked — the same `ConceptScheme`/`Concept`
models, the same `import_skos`, the same file paths a real run uses (craft-tdd, "real over fake
over stub over mock"). The only thing bypassed is command-name *discovery*, which depends on
`demo` being an installed app and has nothing to do with what the command itself does. T017's
unattended walk additionally proves the command runs correctly through the real
`manage.py seed_demo` CLI, over a live server, so the discovery path this test skips is proved
elsewhere.

**Revisit if**: `demo` is ever added to a shared test settings module for an unrelated reason —
at that point `call_command("seed_demo")` becomes available and this indirection can go.

**ADR:** none — one test's own method.

## D19 — `demo/settings.py` sets `LANGUAGE_CODE` explicitly, one line past the README

**Ambiguous**: `seed_demo` failed by hand — `SkosImportFailed`,
`DEFAULT_LANGUAGE_UNCONFIGURED` — even though the identical import already passed under
`tests.settings` in every automated test. The difference is `LANGUAGE_CODE`: Django's own
default is `"en-us"`, and Django's own default `LANGUAGES` list does not contain `"en-us"` as an
exact member (it holds `"en"` and several regional variants, not that one) — so
`ConceptScheme.effective_default_language` resolves to a code the importer's own configuration
check refuses to import against, before a single concept is stored. `tests.settings` never hits
this because it sets `LANGUAGE_CODE = "en"` explicitly; `demo/settings.py`, written to match only
README.md's "Finding a vocabulary" section, did not set it at all and inherited Django's
default.

**Chosen**: `LANGUAGE_CODE = "en"` in `demo/settings.py`, with a comment naming the failure it
prevents.

**Why defensible**: this is not a disagreement with the README — the "Finding a vocabulary"
section documents the `ui` stack's own requirements, not the general Django project settings a
`startproject` scaffold already supplies (`ALLOWED_HOSTS`, `TIME_ZONE`, `USE_I18N`, all of which
`demo/settings.py` also sets without README backing). `LANGUAGE_CODE` belongs in that same
category: ordinary project boilerplate, needed here only because Django's own default happens to
be a code its own default `LANGUAGES` list does not contain. No package behaviour changed;
`controlled_vocabularies/` is untouched.

**Revisit if**: the package ever tolerates an unconfigured default language (a design change,
not a demo one) — at that point this line stops being load-bearing rather than becoming wrong.

**ADR:** none — one settings module's own value, discovered by the by-hand verification T017
requires and folded into that task's commit since T015 (where `demo/settings.py` was written)
is already landed.

## D20 — `non-mirror-paths` entries are exact files, an apostrophe broke the array

**Ambiguous**: `forge verify`'s conformance step flagged `tests/test_demo/test_demo.py` and
`tests/test_demo/test_seed.py` as mirroring no source module, even though T015 declared
`"tests/test_demo/"` as a directory-prefix exception in `pyproject.toml`. The parser
(`forgekit/conformance.py`) extracts the array's text and then matches quoted strings with a
regex too naive to know TOML comments from string literals — an apostrophe in an in-array
comment ("module's subject") was read as a string delimiter, corrupting every entry after it.
`test_smoke.py` was never actually covered by the declaration at all; it passed only because
it is a standing, cross-repo exception hard-coded in the tool itself (`NON_MIRROR_FILES`),
unrelated to anything this story wrote.

**Chosen**: list the three `tests/test_demo/` files explicitly, and move the explanatory
comment above the array (matching the file's own existing style for the `test_ui/` entries),
written with no apostrophe.

**Why defensible**: matches the tool's own documented convention exactly (explicit files,
comment outside the array) rather than inventing a directory-prefix shorthand the tool's
regex-based parser cannot safely round-trip. Confirmed by importing
`forgekit.conformance.declared_non_mirror_paths` directly and reading its output before and
after.

**Revisit if**: the parser is ever hardened past regex extraction — this workaround for its
current form should not be read as guidance beyond it.

**ADR:** none — one repo's own `pyproject.toml` entry, discovered by running the org's own
verify tool rather than by reading its source in advance.

## D21 — the demo project registers the vocabulary model, the package still registers nothing

**Ambiguous**: User Story 3 promises a reader can "add a vocabulary by hand to see it appear",
and README.md turns that into a documented instruction — run `createsuperuser`, sign in at
`/admin/` — with `demo/urls.py` mounting the admin for exactly that purpose. Nothing anywhere
in the repository registers `ConceptScheme` with an admin site: the package registers nothing
deliberately, because a curator interface is R5 and a package that registered its own models
would take that decision away from every project installing it. Following the documented steps
led to an admin index holding only users and groups. Confirmed by reading `admin.site._registry`
under `demo.settings`, which returned `['auth.Group', 'auth.User']`.

**Chosen**: a `demo/admin.py` registering the model with a `ModelAdmin` whose form carries
`name`, `description`, `default_language` and `static_uri`. The package is untouched.

**Why defensible**: the registration belongs to the project that documents it, which is what a
real installing project would do, so the demo demonstrates the actual arrangement rather than a
privileged one. The four-field form is not decoration — `slug` is unique, required and derived
from `name` on every save while `slug_is_manual` is unset, so a bare `admin.site.register()`
serves a form demanding a value the model is about to compute, and the submission is refused.
The gate in `tests/test_demo/test_admin.py` walks the whole documented instruction (sign in, GET
the form, POST it, read the list back) rather than asserting registration, and was proved
against both failure shapes: with `demo/admin.py` removed it fails on the missing form, and with
the model registered bare it fails on the refused submission.

**Revisit if**: R5 lands a curator interface the package itself ships, at which point the demo
should use that rather than declaring its own.

**ADR:** none — a demo project's own wiring, decided by what the story already promised.

## D22 — The demo wires the whole package, not only the part this feature added
**Ambiguous**: `demo/settings.py` was built from the README's browsing section alone, which
documents what the `ui` extra needs and nothing else. That section is not wrong — it adds to the
package's base configuration rather than replacing it — but a demo built from it starts with three
warnings from the package's own system checks: the core routes are not mounted, `django_tomselect`
is not installed, and its middleware is absent.

**Chosen**: the demo installs `django_tomselect` and its middleware and mounts
`controlled_vocabularies.urls`, so it starts silently. The test asserts on `run_checks()` rather
than on `manage.py check`'s exit code.

**Why defensible**: the demo's whole purpose is to be read as an example of how to wire this
package. An example that warns on every startup is a worked example of the mistake, and the reader
most likely to copy it is the one least able to tell which warnings are safe to ignore. The
management command exits zero on warnings, so an exit-code assertion would have passed this
configuration forever — which is exactly what happened. `run_checks()` is what makes the silence
the thing under test.

The README gains a sentence saying the browsing section adds to the base configuration rather than
replacing it, because a reader following it in isolation hit the same three warnings the demo did.

**Revisit if**: the package's checks grow a warning a demonstration genuinely cannot satisfy — at
which point the test needs a named exception, not a weakened assertion.

**ADR:** none — a demo configuration decision, local to this repository.

## D23 — No page template of our own; the blocked tests are skipped and named
**Ambiguous**: django-mvp's shipped search control is inert on a page that renders search without
a filter control — its input and button carry `form="filterForm"` and only the filter action
defines that element. An earlier revision of this feature overrode django-mvp's page template to
supply the missing form, its own translatable submit button, and the link back to the unsearched
list. That made every requirement pass.

**Chosen**: the override is deleted. This package ships the row partial and nothing else, and the
page is django-mvp's own. Three tests are skipped, each naming django-mvp/django-mvp#282 and the
condition that unskips it: the box's own submission, the link back to the full list, and the
whitespace-only prefill.

**Why defensible**: the maintainer's ruling, and the reasoning generalises past this feature. A
template override in a consumer is invisible once it works, and it outlives the upstream release
that made it unnecessary — nothing ever goes red to say "you can delete this now". django-mvp
exists so that consuming packages do not carry their own copies of its markup; a shell whose
consumers all carry overrides has stopped being a shell, and every override makes the next upstream
fix harder to adopt. A skipped test with a reason is the opposite: it is visible in every run, it
names what it waits for, and it turns back into coverage the moment upstream ships.

The cost is stated rather than hidden. Until #282 lands, the search box on the page cannot be
submitted from a browser — a request carrying `?q=` still filters exactly as specified, and every
test of that behaviour still runs. FR-006's control and FR-009's link back are, for now, delivered
by the query string alone. The README says so.

**Revisit if**: #282 lands. Unskip all three, delete the README's paragraph, and check whether the
actions area is reachable without an override before writing anything.

**ADR:** docs/adr/0015-upstream-defects-are-waited-on-not-worked-around.md — this is a standing
rule about how this package treats its interface dependency, not a decision about one page.
