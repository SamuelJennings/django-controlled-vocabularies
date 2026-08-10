# Decisions — 008 Run an import from the command line

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.
The spec is the contract. This file is why the contract reads the way it does.

## D1 — The command takes a URL as well as a path, and that is a scope addition

The issue says "a command that takes a file". At intake the maintainer widened it: a vendored
vocabulary is pointed at by filesystem path, and one taken straight from its publisher is pointed
at by the address it is served from.

This is worth recording rather than absorbing quietly, because [#50](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/50)
put "importing from a URL rather than a file" explicitly out of scope. The exclusion was not an
oversight there. It was the right call for a feature whose subject was reading SKOS. But it means
this feature carries the package's first outbound network request, with failure modes no other
part of the codebase has: an address that does not resolve, a server that answers with an error or
with a landing page, a redirect chain, a connection that never completes. Those are the substance
of US-2, and they are why it is a story of its own rather than a second argument shape inside US-1.

## D2 — The command offers no way to name a target vocabulary

The issue says the command takes "a target vocabulary", and the programmatic entry point accepts
one. It is not exposed.

The maintainer's ruling at intake was direct: the source declares which vocabulary it is, and a
source declaring no `skos:ConceptScheme` is not SKOS, so it is refused. Two behaviours the
existing `resolve_scheme` supports therefore become unreachable from the command line, and both
were considered and dropped:

- **Supplying a vocabulary for a source that declares none.** `FatalReason.VOCABULARY_UNDETERMINED`
  fires when no scheme is declared and no target is given. With no flag, every such source is
  refused. That is now the intended outcome rather than a gap.
- **Refusing a run whose source declares a vocabulary other than the one expected.**
  `FatalReason.VOCABULARY_TARGET_MISMATCH` exists to catch a deployment script pointed at the
  wrong address. The maintainer ruled that pointing at the wrong file is a downstream mistake and
  not this package's to prevent.

The wider instruction behind the second is recorded because it reaches past this feature: the
implementation so far has put too much weight on controlling what an operator might do. This spec
takes the narrower position deliberately, and the same position should be taken across the rest of
R2's surface rather than treated as a local exception. It is also why the "operator is trusted"
assumption is stated in `spec.md` rather than left implicit — an unstated position reads as an
omission to a reviewer, and gets filed as a finding.

Neither entry point changes: `import_skos` keeps its `scheme` parameter for programmatic callers
who have a genuine reason to use it. What is decided here is what the command exposes.

## D3 — A source is a path or a URL, told apart by the value

No flag chooses between the two forms. A value beginning `http://` or `https://` is fetched, and
anything else is opened from disk. A value carrying any other scheme is refused as unsupported.

A flag was rejected as making the operator restate what the value already carries. The
alternative failure — a path mistaken for a URL, or the reverse — is not reachable, since no
filesystem path begins with a URL scheme.

Refusing an unrecognised scheme, rather than falling through to the filesystem, is the one place
this spec adds a check rather than removing one, and it is not a guard against operator error. A
value like `ftp://example.org/vocab.ttl` is a clearly stated intention that this feature does not
serve. Handing it to the filesystem produces "no such file or directory: ftp://example.org/vocab.ttl",
which is true, useless, and points the operator at the wrong problem. Naming the real reason costs
one branch.

## D4 — A rehearsal is a real run inside a transaction that is abandoned

The alternative is a predictive rehearsal: read the source, work out what would happen, report it,
never touch the database.

It was rejected on two grounds. First, it is a second implementation of the import, and it drifts
from the first the moment either changes — the classic failure of a preview that stops matching
what it previews. Second, and decisively, it is silent about exactly the outcomes an operator runs
a rehearsal to find. Several of the reasons a value is set aside are refusals by the models
themselves at write time: `EMPTY_SLUG` when no usable slug can be derived, `VALUE_TOO_LONG` when a
field rejects a value on length, `STORED_SLUG_INVALID` when an already-stored slug no longer passes
validation. A prediction that never writes discovers none of them, so it would report a clean run
for a file that will not import.

Running the real import and abandoning the transaction gets all of this for free, because
`SkosImporter.run` already wraps its work in `transaction.atomic()`. The rehearsal is the same code
producing the same report, which is what makes SC-003 — rehearsal report equals live report — a
meaningful assertion rather than a check that two implementations agree today.

The cost is that a rehearsal takes as long as a real import and does the same database work before
discarding it. For a vocabulary of any realistic size that is seconds, and an operator who asked
for a rehearsal has already accepted waiting.

## D5 — Set-asides exit zero, and only a refusal exits non-zero

A deployment script needs one bit from the exit status, and the question it can act on is whether
the vocabulary is present. A run that stored the vocabulary and set aside four hundred French
labels has answered yes.

Exiting non-zero on any set-aside was rejected because it makes the normal outcome look like a
failure: [#51](https://github.com/SamuelJennings/django-controlled-vocabularies/issues/51) exists
precisely because importing a published vocabulary into a site configured for a subset of its
languages *always* sets values aside. A script that halts on that halts on every import it will
ever run.

A strictness flag — exit non-zero if anything was set aside — was also considered and dropped. It
is a guard against a situation nobody has, and it is the shape of over-specification the maintainer
ruled against at intake. If a deployment ever genuinely needs to fail on set-asides, the report is
available programmatically and the caller can decide.

## D6 — Counts by default, entries on request, carried by `--verbosity`

An import of a large external vocabulary can set aside several hundred values. Printing them all
answers "what happened" and buries "what should I change", which is the question #51 was written to
make answerable — its per-language account exists so that adding one language to a site is a
decision made from evidence.

So the default output is counts: per bucket, and within the set-aside bucket per reason, with the
per-language breakdown. Individual entries print at raised verbosity.

Django's `--verbosity` already means exactly this and every management command an operator has ever
run supports it, so it carries the choice rather than a new flag. A bespoke `--detail` would be a
second thing to learn for the same idea.

`report.set_aside_by_reason()` and `report.language_account()` already return this grouped, so the
rendering reads structured data and parses no rendered message — the constraint `report.py`'s own
module docstring names for this feature.

## D7 — Records the source no longer mentions are reported apart from set-asides

`ImportReport.absent_from_source` and `ImportReport.set_aside` are different kinds of fact and are
rendered separately. A set-aside value is incoming content that was refused. An absent-from-source
record is existing data that was left exactly as it was, because other data may already reference
it and retiring a concept properly is deprecation, which arrives with R4.

Collapsing them into one number would tell an operator that something is wrong with their file when
nothing is. The distinction is #50's, not this feature's. What is decided here is that the
rendering preserves it.

## D8 — Retrieval is assumed to need no new runtime dependency

The package's runtime dependencies are Django, `rdflib` and `defusedxml`. Article VII asks for a
stated justification before a fourth, and the standard library covers fetching bytes over HTTP for
one call site.

This is recorded as an assumption rather than a decision because it is a planning question, and it
has one real constraint attached: the bytes must reach the existing safety scan before anything
parses them, so handing a URL straight to `rdflib`'s own remote parsing is not available — that
would skip the scan `UnsafeRdfXmlError` and `UnsafeJsonLdError` exist to raise. Whatever fetches
must return bytes to the path a local file already takes.

## D9 — The rehearsal names itself in its own output

A rehearsal's report is, by construction, identical to a live run's. That is the point, and it is
also the risk: an operator scrolling back through a terminal sees "created 212 concepts" and has no
way to tell which kind of run produced it.

So FR-010 requires the output to say that nothing was kept. It is one line, and it is the only
difference between the two renderings, which is why it has to be deliberate rather than assumed.
