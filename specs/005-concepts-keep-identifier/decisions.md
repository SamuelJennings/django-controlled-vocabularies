# Decisions — 005 Concepts keep the identifier they were published under

Rationale too long to sit inline in `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.

## D1 — The identity split: permanent URI and local URL

**Ambiguous**: a single composed string currently serves as both a record's identity and the address
it would be viewed at. An imported record needs those to differ, because its identity belongs to its
publisher while it still has to be viewable here.

**Chosen**: two named things. The **permanent URI** is identity, stored, and belongs to whoever
published the record. The **local URL** is this site's own address for the record, always composed
from the site's configured address, the vocabulary's slug, and the record's slug. For a locally
authored, unpublished record the two are the same string, which is why they look like one thing in
the code today.

**Why defensible**: it is the smallest change that lets an imported record be both truthfully
identified and locally viewable, and it matches how SKOS itself treats a concept's URI (a global
identifier, not a site path). Established in the intake discussion, not inferred.

## D2 — "Permanent" is a promise earned at publication, not a field that is sometimes empty

**Ambiguous**: whether an unpublished, locally authored record has a permanent URI at all.

**Chosen**: every record always has one. For an unpublished local record it holds the value the
record will publish under and follows the record's slugs; for anything imported or published it is
fixed. The difference between the two states is **fixedness**, never presence.

**Why defensible**: the maintainer's position is that an unpublished vocabulary has no permanent URI
in the promise sense, and that populating the field with the eventual value is still right. A single
always-present value keeps one rule for the whole system, avoids every caller special-casing an
absent identity, and preserves R1's behaviour exactly, so this feature is not a breaking change.
The alternative — no identifier until publication — would have made lookup fail for unpublished
local records and forced a null check into every consumer for no gain.

## D3 — Fixedness is recorded, never inferred from the configured base address

**Ambiguous**: how the system tells a fixed identifier from a provisional one.

**Chosen**: the record records it explicitly.

**Why defensible**: the obvious shortcut — treat any identifier outside the configured base address
as external — breaks in two ordinary situations. The configured address can change, which would
silently reclassify every record in the database, and an external publisher's address may
legitimately sit under the same base. Inference by string comparison would make identity depend on a
setting, which is precisely what Article IX forbids.

## D4 — The local URL gets no routes in this feature

**Ambiguous**: the local URL was described as something resolved dynamically, in the manner of a
Django URL.

**Chosen**: this feature defines the composition rule and exposes the value. It adds no URL
configuration, no views, and no `get_absolute_url`.

**Why defensible**: the package currently has no `urls.py` and no views at all, so a route defined
here would resolve to nothing and a reverse lookup would have no name to find. Serving concept URLs
is roadmap R4 and the browsing interface is R6; each brings the views its routes need. Whether the
local URL is later produced through Django's URL machinery instead of composed directly is a
decision for whichever of those lands first, and nothing here forecloses it.

## D5 — Which identifiers an external publisher may assign

**Ambiguous**: `spec.md` initially required only a "well-formed absolute identifier", which does not
say whether `javascript:`, `data:`, or a 4000-character value is acceptable.

**Chosen**: any absolute URI carrying a scheme, refusing schemes that can carry executable content
(`javascript:`, `data:`, `vbscript:`) and refusing anything longer than 500 characters.

**Why defensible**: a stored identifier is rendered as a link once the browsing interface exists, so
a script-bearing value accepted here becomes a hazard there, and the database is the wrong place to
discover that. A strict allowlist of `http` and `https` was rejected because real vocabularies do use
`urn:` identifiers and refusing them would discard valid content to solve a problem that a short
refusal list already closes. The 500-character bound is far beyond any identifier real SKOS
vocabularies use and stays within the unique-index limit of every mainstream database, including
MySQL's 3072-byte cap on `utf8mb4` — a larger bound would leave the uniqueness requirement
unenforceable as an index on some deployments. Refusing hostile schemes on the way in does not
relieve R6 of escaping what it renders; both are wanted.

## D6 — Fixedness moves one way only

**Ambiguous**: whether a fixed identifier can become provisional again, and whether a re-import
rewrites the identifier it matched on.

**Chosen**: no reversal, ever. A record becomes fixed when created from external content (here) or
when its vocabulary is published (R4). A re-import matches an existing record *by* its identifier and
therefore never has occasion to rewrite it.

**Why defensible**: the draft carried an "other than an explicit re-import" escape hatch in FR-002,
which was sloppy — upsert-by-URI finds the record *using* the identifier, so the matched identifier
is by definition already equal. Removing the hatch makes the guarantee absolute and easier to test. A
record whose identifier was wrongly recorded as fixed is corrected by removing the record, which is
data repair, not a state transition the model needs to support.

## D7 — The published attribute names are kept

**Ambiguous**: introducing the term "permanent URI" invites renaming the existing identifier
attribute to match it.

**Chosen**: the existing identifier attribute and the existing lookup-by-identifier keep their names
and meanings, and gain external values and external resolution. Only the local URL is a new name on
the surface.

**Why defensible**: the existing attribute has always denoted the record's identity — that is what
Article IX and the shared glossary say it is — so the permanent URI is what it already meant, and a
rename would churn every call site and every downstream consumer to say the same thing. Stated as a
requirement rather than left to planning so the change cannot arrive as a rename of a published
package's public surface.

## D8 — Storage shape deferred to planning

**Ambiguous**: whether the permanent URI is a stored column kept in step on save, a stored column
with a computed fallback, or something else; how fixedness is represented; how a provisional value
keeps up with slug and configured-address changes.

**Chosen**: not decided here. `spec.md` fixes the observable guarantees and leaves the mechanism to
planning (S3), guided by `docs/brainstorm.md` and the R1 precedent.

**Why defensible**: every one of those choices is invisible to a curator and testable only through
the guarantees already written down. Fixing them in the specification would constrain the
implementers without adding a single verifiable promise.

## D9 — The glossary splits, and this feature updates it

**Ambiguous**: `CONTEXT.md` defines one term, **URI**, as "the globally stable identifier of a scheme
or concept". After this feature that sentence describes only half of what the code holds.

**Chosen**: the entry becomes **permanent URI**, and **local URL** joins it as a distinct term. Both
land with this feature rather than after it.

**Why defensible**: the shared vocabulary exists so specs, issues, and code use the same words. A
glossary that still names one URI while the models carry two addresses would mislead the very next
feature to read it, which is the import work in #50.

## D10 — Implementer deviation: T006/T007/T008 landed with the T002/T003 foundational commit, ahead of T005's tests

**What happened**: while implementing US-1 (T001–T008), the `uri`/`has_permanent_uri` rework (T006),
the `save()` validation call (T007), and the cross-model duplicate check (T008) were written in the
same pass as the foundational validator (T002) and field (T003), before `TestPermanentUri` (T005) was
authored — inverting tasks.md's prescribed test-first order for Phase 2.

**Remediation taken**: before writing `TestPermanentUri`, each test's discriminating power was verified
directly against the already-written implementation by temporarily reverting the relevant code path
(the `self.permanent_uri or` composition in all three `uri` properties, then separately the `save()`
validation/cross-model-check calls), confirming the exact expected tests failed for the right reason,
then restoring. All 15 tests in `TestPermanentUri` were confirmed non-vacuous this way before the
final green run.

**Why defensible, not swept under the rug**: the safety property test-first exists to protect — tests
that actually exercise the code and would catch a real regression — was verified after the fact rather
than by construction. It was not verified by the more reliable means (red before green, by construction)
and is logged here so a reviewer can weigh it. No test was weakened, skipped, or written to match a
bug; the mutation check above is the evidence.

## D11 — `get_by_uri`'s exact-match step catches `ObjectDoesNotExist`, not `self.model.DoesNotExist`

**Ambiguous**: not called out in `tasks.md` or `research.md`/`data-model.md` — an implementation detail
that surfaced only once `PermanentUriLookupMixin` was made generic.

**Chosen**: `PermanentUriLookupMixin.get_by_uri` catches `django.core.exceptions.ObjectDoesNotExist`
around the exact-match `self.get(permanent_uri=uri)` call, rather than `self.model.DoesNotExist` (what
the pre-existing `ConceptManager.get_by_uri` used, and what each manager's own
`_get_by_local_parse` still raises explicitly).

**Why defensible**: `PermanentUriLookupMixin` is `models.Manager[_PermanentUriModel]`, generic over a
`TypeVar` bound to `models.Model`, so it can back `ConceptSchemeManager`, `ConceptManager`, and
`CollectionManager` from one implementation (research R6's stated goal — one shared mixin, not three
drifting copies). mypy/django-stubs can resolve `.DoesNotExist` off a *concrete* model class
(`type[Concept]`) but not off a still-generic `type[_PermanentUriModel]`, because the attribute is
injected by Django's `ModelBase` metaclass rather than declared on `Model` itself, and the stubs'
special-casing needs a concrete class to hang it on. `Model.DoesNotExist` is always a subclass of
`django.core.exceptions.ObjectDoesNotExist`, so catching the base class here is exactly as precise —
`self.get()` raises no other `ObjectDoesNotExist` subclass in this call — while removing an annotation
mypy cannot check. Each manager's own `_get_by_local_parse` keeps raising `self.model.DoesNotExist`
explicitly (there the model is concrete, not generic), so the observable exception type callers see is
unchanged in every case tested.
