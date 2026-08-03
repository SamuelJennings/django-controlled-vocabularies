# Decisions — 005 Concepts keep the identifier they were published under

Rationale too long to sit inline in `spec.md`, plus every ambiguity resolved without asking the
maintainer. Each entry states what was unclear, what was chosen, and why the choice is defensible.

## D1 — The identity split: static URI and local URL

**Ambiguous**: a single composed string currently serves as both a record's identity and the address
it would be viewed at. An imported record needs those to differ, because its identity belongs to its
publisher while it still has to be viewable here.

**Chosen**: two named things. The **static URI** is identity, stored, and belongs to whoever
published the record. The **local URL** is this site's own address for the record, always composed
from the site's configured address, the vocabulary's slug, and the record's slug. For a locally
authored, unpublished record the two are the same string, which is why they look like one thing in
the code today.

**Why defensible**: it is the smallest change that lets an imported record be both truthfully
identified and locally viewable, and it matches how SKOS itself treats a concept's URI (a global
identifier, not a site path). Established in the intake discussion, not inferred.

## D2 — Every record has a permanent URI; the column holds it once it turns static

**Ambiguous**: how a permanent URI behaves before the record is published.

**Chosen**: every record always has one. It is **dynamic** while the record is authored here and
unpublished, composed from the site's configured address and the record's slugs and free to move when
those move. It turns **static** when the record arrives from an external publisher, or when its
vocabulary is published, and never changes afterwards. The difference between the two states is
whether the value can still move, never whether it exists.

**Why defensible**: the maintainer's position is that the identifier is dynamic until publication
and static from then on, which is exactly these two states. An always-present value keeps one rule for
the whole system, avoids every caller special-casing an absent identity, and preserves R1's behaviour
exactly, so this feature is not a breaking change. The alternative — no identifier at all until
publication — would have made lookup fail for unpublished local records and forced a null check into
every consumer for no gain.

*(Corrected 2026-08-03. An earlier draft of this entry claimed an unpublished record has no permanent
URI. That was this run's wording, not the maintainer's, and it is wrong: the URI exists throughout and
only its mutability changes. The column was renamed from `permanent_uri` to `static_uri` at the same
time, because a column named for the whole concept implied records without one had no identity.)*

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

**Ambiguous**: introducing the term "static URI" invites renaming the existing identifier
attribute to match it.

**Chosen**: the existing identifier attribute and the existing lookup-by-identifier keep their names
and meanings, and gain external values and external resolution. Only the local URL is a new name on
the surface.

**Why defensible**: the existing attribute has always denoted the record's identity — that is what
Article IX and the shared glossary say it is — so the static URI is what it already meant, and a
rename would churn every call site and every downstream consumer to say the same thing. Stated as a
requirement rather than left to planning so the change cannot arrive as a rename of a published
package's public surface.

## D8 — Storage shape deferred to planning

**Ambiguous**: whether the static URI is a stored column kept in step on save, a stored column
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

**Chosen**: the entry becomes **static URI**, and **local URL** joins it as a distinct term. Both
land with this feature rather than after it.

**Why defensible**: the shared vocabulary exists so specs, issues, and code use the same words. A
glossary that still names one URI while the models carry two addresses would mislead the very next
feature to read it, which is the import work in #50.

## D10 — Implementer deviation: T006/T007/T008 landed with the T002/T003 foundational commit, ahead of T005's tests

**What happened**: while implementing US-1 (T001–T008), the `uri`/`has_static_uri` rework (T006),
the `save()` validation call (T007), and the cross-model duplicate check (T008) were written in the
same pass as the foundational validator (T002) and field (T003), before `TestStaticUri` (T005) was
authored — inverting tasks.md's prescribed test-first order for Phase 2.

**Remediation taken**: before writing `TestStaticUri`, each test's discriminating power was verified
directly against the already-written implementation by temporarily reverting the relevant code path
(the `self.static_uri or` composition in all three `uri` properties, then separately the `save()`
validation/cross-model-check calls), confirming the exact expected tests failed for the right reason,
then restoring. All 15 tests in `TestStaticUri` were confirmed non-vacuous this way before the
final green run.

**Why defensible, not swept under the rug**: the safety property test-first exists to protect — tests
that actually exercise the code and would catch a real regression — was verified after the fact rather
than by construction. It was not verified by the more reliable means (red before green, by construction)
and is logged here so a reviewer can weigh it. No test was weakened, skipped, or written to match a
bug; the mutation check above is the evidence.

## D11 — `get_by_uri`'s exact-match step catches `ObjectDoesNotExist`, not `self.model.DoesNotExist`

**Ambiguous**: not called out in `tasks.md` or `research.md`/`data-model.md` — an implementation detail
that surfaced only once `StaticUriLookupMixin` was made generic.

**Chosen**: `StaticUriLookupMixin.get_by_uri` catches `django.core.exceptions.ObjectDoesNotExist`
around the exact-match `self.get(static_uri=uri)` call, rather than `self.model.DoesNotExist` (what
the pre-existing `ConceptManager.get_by_uri` used, and what each manager's own
`_get_by_local_parse` still raises explicitly).

**Why defensible**: `StaticUriLookupMixin` is `models.Manager[_StaticUriModel]`, generic over a
`TypeVar` bound to `models.Model`, so it can back `ConceptSchemeManager`, `ConceptManager`, and
`CollectionManager` from one implementation (research R6's stated goal — one shared mixin, not three
drifting copies). mypy/django-stubs can resolve `.DoesNotExist` off a *concrete* model class
(`type[Concept]`) but not off a still-generic `type[_StaticUriModel]`, because the attribute is
injected by Django's `ModelBase` metaclass rather than declared on `Model` itself, and the stubs'
special-casing needs a concrete class to hang it on. `Model.DoesNotExist` is always a subclass of
`django.core.exceptions.ObjectDoesNotExist`, so catching the base class here is exactly as precise —
`self.get()` raises no other `ObjectDoesNotExist` subclass in this call — while removing an annotation
mypy cannot check. Each manager's own `_get_by_local_parse` keeps raising `self.model.DoesNotExist`
explicitly (there the model is concrete, not generic), so the observable exception type callers see is
unchanged in every case tested.

## D12 — A deferred load is not an exemption from fixedness, and fixedness starts at the storing save

**Ambiguous**: T025 delivered the rewrite guard as a snapshot taken in `from_db`, and deliberately
left a record loaded with `static_uri` deferred unconstrained — there was no snapshot to compare
against, so the guard skipped. Reviewing that code found the exemption is reachable from ordinary
code, and found a second hole the same snapshot design created.

**Chosen**: both are closed (T026).

1. A record loaded with the column deferred now has the stored value read back and compared, but
   only once the column has actually been assigned. While the column is still deferred nothing about
   the identifier can have changed, so every identifier check is skipped and the column is never
   fetched — an untouched deferred save costs exactly what it did before.
2. Each `save()` now adopts the value it wrote as the stored one, so the instance that first stores
   an identifier is fixed from that moment rather than from its next load.

**Why**: FR-002 and FR-013 say a stored identifier is never changed, without qualification. Probing
the delivered code showed `Model.objects.only("id").get(pk=...)` followed by an assignment and a
save rewrote a stored identifier silently, and the same route set it to `None`, returning an imported
record to a provisional identity — the exact failure the feature exists to prevent. `.only()` and
`.defer()` are ordinary performance idioms in Django list views, not exotic escape hatches, so an
invariant that any of them bypasses is not an invariant. The second hole was reachable without any
deferral at all: a record created provisional, given an identifier and saved, could be given a
different identifier and saved again from the same in-memory instance, because its snapshot was still
`None`. That is precisely the instance R4's publish action will be holding.

**Cost**: one extra query, paid only on a save that assigns a previously deferred `static_uri`.
Each of the three parts is covered by tests that fail when that part alone is removed.

**Not covered, deliberately**: `QuerySet.update()` and raw SQL bypass this, as they bypass every
`save()`-based rule in Django, including the slug and default-language rules this app already relies
on. Nothing portable defends against that at the database level for a conditional invariant.

**Also not covered (T037, added on review — verified, not merely inferred)**: `QuerySet.bulk_create()`
bypasses `save()`/`clean()` entirely and issues the `INSERT`s directly — confirmed by probing it
against a scheme and an unsafe scheme, a blank string, and a cross-model duplicate, all three of which
it accepts (the per-model partial `UniqueConstraint` still catches a same-model duplicate at the
database, which is exactly what `TestStaticUriDatabaseUniqueness` deliberately uses `bulk_create`
to exercise). Django's fixture loader (`loaddata`) and the raw deserializer path it uses
(`django.core.serializers`) bypass `save()`/`clean()` the same way fixtures always have for every other
model-level rule in this app. Both are the same class of gap as `QuerySet.update()` and raw SQL above:
nothing portable defends against a conditional, cross-row invariant at the database level for a write
path Django itself designed to skip per-instance validation.

## D13 — An empty string is the absence of an identifier, and is stored as null

**Context**: `static_uri` is `null=True` so the partial `UniqueConstraint`
(`condition=Q(static_uri__isnull=False)`) leaves provisional records unconstrained — any number
of them may coexist holding nothing. An empty string is not null, so it falls *inside* that
constraint, while `uri` returns `self.static_uri or self.local_url` and `has_static_uri`
returns `bool(self.static_uri)`: both read `""` as absent. A record assigned `""` therefore
behaves as provisional in every observable way and still occupies the unique slot, and the second
such record fails at the database.

**Chosen**: `""` normalises to `None` on the way in, in each model's `clean()` and in the shared
save-path checks.

**Why**: probing the delivered code showed two vocabularies created with `static_uri=""` raise
`IntegrityError: UNIQUE constraint failed` on the second, with a message naming a constraint the
caller never knowingly engaged. `""` rather than `None` is the ordinary shape of importer and
serializer code — `node.get("about") or ""` — and #50's importer is the first caller this feature
exists to serve, so leaving it to every caller to remember guarantees the bug arrives there. Django
already normalises the form path (`CharField.formfield` passes `empty_value=None` when the field is
nullable), so this only closes the direct-assignment path, which is the one the importer uses.

**Placement**: after the deferred guard, so an untouched deferred column is still never fetched, and
before the rewrite guard, so clearing a *stored* identifier by assigning `""` is still refused as a
clear (FR-002, FR-013) rather than slipping through as a no-op.

**Alternative rejected**: dropping `null=True` and making `""` the sentinel for absence. That
inverts the problem — the partial constraint would need `condition=~Q(static_uri="")`, which is
the same rule expressed less portably, and it would break every existing `static_uri__isnull`
query already written into the tests and `get_by_uri`.

## D14 — An externally assigned identifier cannot shadow a local record's own address; the reverse direction is a residual limitation

**Context**: a three-lens review found a verified hijack. With the base address
`https://example.org/vocabularies`, a local concept whose `local_url` is
`https://example.org/vocabularies/colours/red` was displaced when another record was saved with
`static_uri` set to that exact string. `get_by_uri` tries a stored match first — correctly, per
FR-003/R6 — so once stored it resolved to the imposter, and the victim was no longer reachable by
its own identity. #50's importer would then write into the wrong record.

**Chosen (T034)**: on save, when a `static_uri` is being stored (assigned and different from what
is already stored) and it sits under this site's configured base address, it is resolved through the
same local-parse machinery `get_by_uri` uses across all three models. If it resolves to a *different*
existing record, the save is refused (`static_uri_shadows_local_url`). If it resolves to nothing,
or to this same record, it is accepted — an external identifier that legitimately sits under this
site's address is still externally assigned (spec.md Edge Case 1); nothing here contradicts that.

**Residual limitation, not fixed here**: the reverse direction — a later slug or base-address change
that moves a local record's *own* composed address onto an identifier some other record already has
stored — is not defended against. By the time that collision would occur, the stored identifier is
already fixed (D6: fixedness moves one way only), so the only correct response would be refusing the
rename or address change that creates the collision. That responsibility belongs with R4's
publication lifecycle, which owns freezing and renaming policy, not with the save path this feature
adds. Recorded here rather than silently left, per the review's instruction.

## D15 — Accepted URI schemes are an allowlist, not a denylist; this supersedes the D5 gate decision

**Context**: D5 chose "refuse `javascript`/`data`/`vbscript`, accept everything else" — a denylist of
three script-bearing schemes. A three-lens review found that shape wrong for the actual hazard: a
stored `static_uri` is rendered as a link once the browsing interface exists, so the accepted set
needs to be small and known-safe, not merely known-not-hostile. Under the denylist, `file:///etc/passwd`,
`about:blank`, `blob:`, `jar:`, `filesystem:`, and `view-source:` were all accepted for that field.

**Chosen (T035)**: accept only `http`, `https`, `urn`, `doi`, `info`, `ark` by default — the schemes
real SKOS vocabularies actually use — overridable via the new
`CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES` setting, read through `conf.get_allowed_uri_schemes()`
in the same style as the base address (`conf.get_base_uri()`). The D5 denylist stays as a second,
belt-and-braces gate inside the allowlist branch: even a downstream project that overrides the
allowlist to include `javascript` is still refused it.

**This supersedes D5's shape, not its content**: D5 explicitly rejected "a strict allowlist of `http`
and `https`" because real vocabularies use `urn:` identifiers and refusing them would discard valid
content. This allowlist is not that — it is `http`/`https` plus the non-http identifier schemes D5
itself named as the reason not to restrict to `http`/`https` alone (`urn:`), extended with `doi`,
`info`, and `ark`, the other non-http schemes real SKOS vocabularies carry. D5's own reasoning is why
this allowlist is shaped the way it is; only the closed-vs-open shape of the check changes.

## D16 — The field is `static_uri`, not `permanent_uri`; "permanent" is reserved for the `uri` accessor

**Context**: the field, validator, constraints, and every message shipped through T037 as
`permanent_uri`/`validate_permanent_uri`. An orchestrator correction (post-T037) rejected that name:
"permanent" was being used two ways in the same sentence — the `uri` accessor, which is a record's
permanent identity and always answers, and the stored column, which is empty for most of a record's
life. Reusing "permanent" for the column let prose drift into claiming an unpublished record "has no
permanent URI," which is false — it has one (`uri`), it just is not yet static.

**Chosen**: rename the column, validator, private helpers, error codes, and constraint names to
`static_uri`/`validate_static_uri`/`has_static_uri` everywhere (`models.py`, migration 0005 —
regenerated in place since the feature is unreleased, not layered with a second rename migration —
tests, and this spec set). `uri` keeps its name and stays the always-answering accessor
(`self.static_uri or self.local_url`); "static" now names only the fixed, verbatim-held state, and
"dynamic" names the composed, rename-following one. Every `static_uri` `help_text` was reworded to
say it holds the identifier "once it is fixed... and is never recomputed after that," rather than
describing the unfixed state as an absence.

**Why defensible**: this is a naming and prose correction only — `has_static_uri`'s truth table,
`uri`'s composition, and every constraint are byte-identical to `has_permanent_uri`'s before it
(verified by the full suite passing unchanged after the rename). It closes a real ambiguity: "permanent"
read naturally as a claim about the record's identity (correct) when applied to `uri`, and as a claim
about the column's contents (also seemingly correct, but misleading once "provisional" records are
described as lacking it) when applied to the field. One English word cannot honestly carry both.

**Revisit if**: R4 introduces vocabulary-level publication and needs a third state (e.g. "static because
published" vs. "static because externally assigned") — at that point `has_static_uri` alone may need to
say which, and D2's two-state framing — dynamic until fixed, static from then on — would need revisiting
alongside it.
