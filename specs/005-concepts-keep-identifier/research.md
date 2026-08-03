# Research — 005-concepts-keep-identifier

Design decisions taken at planning, each with the alternatives weighed and why they lost.

## R1 — The stored column holds only externally assigned identifiers; provisional ones stay composed

**Decision**: each of `ConceptScheme`, `Concept`, and `Collection` gains one nullable stored column
holding an externally assigned identifier. A record with no value in that column composes its
identifier on read exactly as R1 does today. The `uri` accessor returns the stored value when there is
one and the composed value otherwise.

**Rationale**: FR-005 requires a provisional identifier to follow both a rename *and* a change to the
site's configured base address. A column that is always populated and re-synced on `save()` cannot
satisfy the second half — every already-saved row would keep the old address until something touched
it, and the database would quietly hold a value that disagrees with the setting. Composing on read has
no staleness to manage, no resync command to write, and no migration to run when the address changes.
It is also the smallest possible change from the R1 code: the composition already exists and is
already the only behaviour, so this feature *adds* a stored override rather than replacing anything.

The largest bonus is the upgrade path. Because a pre-existing row simply has no stored value, it keeps
composing exactly as it did before, so FR-009 and the Article IX "migrations preserve concept URIs"
invariant are satisfied by construction, with no data migration and nothing to get wrong.

**Alternatives**:
- *Always-stored, re-synced on save* — the shape the intake discussion gestured at. Rejected: fails
  FR-005's configured-address clause, needs a resync command nobody asked for, and introduces a second
  source of truth for a value that is otherwise derivable.
- *Stored for everything, with the base address frozen at first save* — rejected: it makes an
  unpublished record's identifier accidentally permanent, which is exactly the distinction the feature
  exists to draw.

## R2 — Fixedness is the presence of the stored value, not a separate flag

**Decision**: a record is fixed when its stored identifier column holds a value, and provisional when
it does not. No boolean field is added.

**Rationale**: FR-003 forbids inferring fixedness by testing the identifier against the configured base
address, because the address can change and a publisher's address may resemble it. It does not require
a dedicated flag — it requires the fact to be recorded rather than guessed. Column presence *is* a
recorded fact, and it cannot disagree with the data the way a parallel boolean can: a flag says
"fixed" while the column is empty, and now two fields describe one truth. Publication (R4) freezes a
local record by writing the composed value into the same column, so the representation is already what
the next feature needs.

**Alternatives**:
- *A `uri_is_external` boolean alongside the column* — rejected: a second field that can contradict the
  first, with no state it can express that presence cannot.
- *Deriving it from whether the identifier starts with the configured base* — rejected outright by
  FR-003, and for the reasons FR-003 gives.

## R3 — `uri` stays the accessor name; `local_url` is the new one

**Decision**: `uri` remains the public accessor on all three models and now means the permanent URI —
stored value or composed fallback. `local_url` is added for this site's address. The stored column is
named separately from the accessor so both can coexist.

**Rationale**: FR-014 requires the published surface to keep its name and meaning. The existing `uri`
has always denoted identity (Article IX, `CONTEXT.md`), which is exactly the permanent URI, so keeping
the name is the honest choice rather than a compatibility concession. A field literally named `uri`
would collide with the property of that name, which is why the column takes a distinct name and the
property does the resolving.

**Alternatives**:
- *Rename the property to `permanent_uri` and make `uri` the column* — rejected: churns every call site
  and every downstream consumer to say what the name already said, and breaks a published package's API
  for no behavioural gain.

## R4 — Uniqueness is a per-model database constraint plus a cross-model validation check

**Decision**: each model gets a `UniqueConstraint` on its stored identifier column. A cross-model check
at validation refuses an externally assigned identifier already held by a record of a different type.

**Rationale**: FR-006 wants no two records to share an identifier, enforced by the database. Within a
table that is a single constraint. *Across* the three tables no portable database constraint exists —
cross-table uniqueness would need a shared identity table with a one-to-one from each model, which is a
substantial architectural addition to prevent a collision that requires a source file to assign one URI
to both a concept and a collection. The per-model constraints cover the case that actually occurs (the
same concept identifier twice), and the validation check covers the rest.

Provisional identifiers need no constraint at all: composition is structurally unique already. A scheme
composes one segment below the base, a concept two, and a collection three with a literal `collection`
segment in the middle, and slugs cannot contain a separator — so no two provisional identifiers can
collide, which is the same argument R1 used to justify not storing a URI in the first place.

**The race, stated plainly (T037)**: the *cross-model* half of this decision — the validation check
that covers "the rest" above — is exactly the "no constraint, application checks only" alternative
rejected two paragraphs below, for exactly the reason given there: it loses to a concurrent write. Two
saves for a concept and a collection carrying the same externally assigned identifier, committed
concurrently, can each run the cross-model `.exists()` probe before the other's row commits, each see
nothing held elsewhere, and both succeed — the per-model constraint cannot catch this because the
collision is *across* tables. This is not a new risk introduced later; it was already true of R4 as
designed and is accepted for the reason given above (a substantial architectural addition to close a
collision that requires a source file to deliberately assign one URI to both a concept and a
collection). Recorded here rather than left implicit, since the alternatives list otherwise reads as
though the rejected shape and the chosen one differ in this respect, when for the cross-model case they
do not.

**Alternatives**:
- *A shared `Identifier` table with a one-to-one from each model* — rejected as premature. It buys true
  cross-table uniqueness and costs a join on every identity read, a third table in every fixture, and a
  migration that has to move data if it is ever removed. Revisit if a real vocabulary produces a
  cross-type collision.
- *No constraint, application checks only* — rejected: FR-006 requires the database to enforce it, and
  application-only uniqueness loses to concurrent writes. (Adopted anyway for the cross-model half
  specifically, per the race noted above — the per-model constraints still give the database the last
  word on the case that actually occurs.)

## R5 — Accepting an identifier: absolute, no script-bearing scheme, 500 characters

**Decision**: validation requires an absolute URI carrying a scheme, refuses `javascript`, `data`, and
`vbscript`, and caps length at 500 characters. Refusals raise translatable messages with named
placeholders.

**Rationale**: settled at S1 and recorded in `decisions.md` D5. The planning-level point is *where* it
runs: on the field's validators so it holds for `full_clean()`, and in `save()` so it also holds on the
path an importer will actually use. The R1 slug work already established that `save()` never calls
`full_clean()` in Django, so validation placed only on the field would not protect the import path —
the same trap `Concept.slug` had to be defended against.

**Alternatives**:
- *Django's `URLValidator` alone* — rejected: it is built for `http`/`https`/`ftp` and rejects `urn:`
  identifiers, which real vocabularies use.
- *Validation in the importer instead of the model* — rejected: it would leave the model accepting
  values the specification says can never be stored, and #50 is not the only future writer.

## R6 — Lookup resolves the stored column first, then falls back to the existing parse

**Decision**: lookup by identifier queries the stored column for an exact match, and on no match falls
back to R1's existing base-relative parse. Lookup is added to all three models through one shared
manager mixin rather than being reimplemented per model.

**Rationale**: an external identifier is an indexed equality lookup, which is both correct and the fast
path at the scale G5 anticipates. A provisional identifier has no stored value to match, so the
existing parse remains the only way to resolve it, and it already works. Order matters: stored first
means a fixed identifier is never mistaken for a composable one, even if it happens to sit under this
site's own address, which is the case FR-003 and the edge-case list call out.

#50 needs to resolve a vocabulary by identifier as well as a concept, so putting the behaviour on a
mixin shared by the three managers avoids writing it three times and drifting.

**Alternatives**:
- *Parse first, stored second* — rejected: an external identifier resembling this site's address would
  resolve to the wrong record.
- *Concept-only lookup, as R1 shipped* — rejected: the import work upserts schemes and collections by
  identifier too, and would otherwise reimplement this immediately.

## R7 — No routes, no views

**Decision**: `local_url` is composed and returned as a value. No `urls.py`, no view, no
`get_absolute_url`.

**Rationale**: settled at S1 (`decisions.md` D4). The package has no URL configuration at all, so a
route added here would resolve to nothing and a reverse lookup would have no view to name. R4 and R6
bring the views their routes need.
