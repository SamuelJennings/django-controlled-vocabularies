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
  unpublished record's identifier accidentally static, which is exactly the distinction the feature
  exists to draw.

## R2 — Static-versus-dynamic is the presence of the stored value, not a separate flag

**Decision**: a record's permanent URI is static when `static_uri` holds a value and dynamic when it
does not. Every record has a permanent URI either way. No boolean field is added.

**Rationale**: FR-003 forbids inferring the state by testing the identifier against the configured base
address, because the address can change and a publisher's address may resemble it. It does not require
a dedicated flag — it requires the fact to be recorded rather than guessed. Column presence *is* a
recorded fact, and it cannot disagree with the data the way a parallel boolean can: a flag says
"static" while the column is empty, and now two fields describe one truth. Publication (R4) freezes a
local record by writing the composed value into the same column, so the representation is already what
the next feature needs.

**Alternatives**:
- *A `uri_is_external` boolean alongside the column* — rejected: a second field that can contradict the
  first, with no state it can express that presence cannot.
- *Deriving it from whether the identifier starts with the configured base* — rejected outright by
  FR-003, and for the reasons FR-003 gives.

## R3 — `uri` stays the accessor name; `local_url` is the new one

**Decision**: `uri` remains the public accessor on all three models and now means the static URI —
stored value or composed fallback. `local_url` is added for this site's address. The stored column is
named separately from the accessor so both can coexist.

**Rationale**: FR-014 requires the published surface to keep its name and meaning. The existing `uri`
has always denoted identity (Article IX, `CONTEXT.md`), which is exactly the static URI, so keeping
the name is the honest choice rather than a compatibility concession. A field literally named `uri`
would collide with the property of that name, which is why the column takes a distinct name and the
property does the resolving.

**Alternatives**:
- *Rename the property to `static_uri` and make `uri` the column* — rejected: churns every call site
  and every downstream consumer to say what the name already said, and breaks a published package's API
  for no behavioural gain.

## R4 — Uniqueness is a per-model database constraint, and nothing else

**Superseded 2026-08-03 by decisions.md D18.** This section originally paired the per-model
constraint with a cross-model validation check, and recorded the race that check loses to a
concurrent write as an accepted cost. Both the check and the acceptance are gone.

**Decision**: each model gets a `UniqueConstraint` on its stored identifier column. Uniqueness
across the three models is not enforced at all.

**Rationale**: identity is already unique by construction, and was before this feature existed. R1
gives `ConceptScheme.slug` a site-wide unique constraint and gives `Concept` and `Collection` a
unique `(scheme, slug)` each. A composed identifier therefore cannot collide, because the parts it
is built from cannot — the same argument R1 used to justify not storing a URI in the first place,
and the reason the composition is structurally unambiguous besides (a scheme composes one segment
below the base, a concept two, a collection three with a literal `collection` segment between).

For two *stored* identifiers to collide across models, a source file would have to declare the same
URI for a `skos:Concept` and a `skos:Collection`. In RDF that asserts the two are the same resource,
so the file is malformed rather than merely awkward, and no real published vocabulary does it.
#50's importer reads the file and can report the offending statement, which is a better error than
an `IntegrityError` naming a constraint the caller never knowingly touched.

The per-model constraint is kept because the column needs an index for `get_by_uri` regardless, and
a unique index is that index.

**Alternatives**:
- *A cross-model validation check* — built, then removed (D18). It cost two indexed queries on every
  save that set an identifier, could not be made race-free without a lock, and defended against a
  malformed source file that the importer catches better.
- *A shared `Identifier` table with a one-to-one from each model* — rejected, and now moot. It buys
  true cross-table uniqueness and costs a join on every identity read, a third table in every
  fixture, and a migration that has to move data if it is ever removed. With the requirement itself
  withdrawn there is nothing left for it to buy.

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
