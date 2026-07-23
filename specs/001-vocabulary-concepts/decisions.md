# Decision record — 001-vocabulary-concepts

Ambiguities resolved without escalation while specifying, with the reasoning that makes each
defensible. Gate-level decisions live on issue #15; this file carries the fine grain.

## Self-resolved at specify

1. **A concept carries one plain preferred label in this slice.**
   Ambiguous because full label modelling belongs to sibling #16, yet the identity design derives
   the concept slug from the preferred label, so this slice needs one. Resolved to a single
   default-language label that #16 later grows into the multilingual model. Grounded in the
   intake discussion: the concept slug is "based off of the preferred label of the concept".

2. **Notation codes are deferred.**
   Notation is identity-adjacent (a language-independent code), so it was a candidate for this
   slice. Excluded: identity here composes from slugs, and no requirement in this slice consumes
   a notation. First feature that needs it models it.

3. **The URI base address is deployment configuration; the mechanism is left to planning.**
   The spec fixes only the composition rule (base + vocabulary slug + concept slug) and its
   determinism. How the base is configured is not a user-visible property of this feature.

4. **Slug collisions are refused, not auto-disambiguated.**
   Two concepts in one vocabulary whose labels slug identically could be silently suffixed
   (`heat-flow-2`) or rejected. Rejected is the honest behaviour for curated vocabularies: a
   silent suffix mints an identifier the curator never chose, and identifiers are this
   feature's whole point. The curator resolves the wording.

5. **Deleting a vocabulary deletes its concepts.**
   A concept cannot exist outside a vocabulary, and lifecycle/protected-removal is sibling #19.
   Documented as an edge case with a test so the behaviour is explicit, not accidental.

## Deferred by design (recorded so later constitution checks read them as deliberate)

- **Constitution Article IX mechanisms** (lifecycle states, deprecation-not-deletion, PROTECT
  references, upsert-by-URI): deferred to siblings #19 (lifecycle) and the import feature
  (upsert). This slice contains no import and no external references, so the invariants have no
  surface here yet. The identity groundwork (URI as identity, never the database key) IS
  honoured here.
- **Identifier freezing at publish** (constitution Article VIII data contract): the publishing
  feature. All identifiers in this slice are computed and dynamic.
- **Architectural note to land as an ADR (agreed at intake):** the internal storage shape is not
  raw JSON-LD/RDF; RDF serializations are produced only at the import/export boundary. To be
  authored when the boundary features arrive, or earlier as a docs change.

## Self-resolved at plan (S3)

Full rationale in `research.md` (R1–R8). Headlines:

- **R1/R6** URI is a computed property (not stored); lookup by URI parses the path — a stored/frozen
  URI column waits for the publishing feature.
- **R2** base address = one Django setting `CONTROLLED_VOCABULARIES_BASE_URI` with a default, read in
  a thin `conf.py`; no settings framework.
- **R3** slugs via `slugify(allow_unicode=True)` so non-Latin labels stay usable; empty-after-slug is
  rejected.
- **R7** factories use `factory_boy` in `tests/`; confirm it ships in `mvp-shared[test]` or add it as a
  test-only dep (US-4 justification) — Implementer checks before writing.
- **R8** the concept's preferred label is a single `CharField` this slice; #16 grows label storage
  without touching the identity mechanism.

## Self-resolved during implementation (US1, T001–T005)

6. **`conf.DEFAULT_BASE_URI = "http://localhost:8000/vocabularies"`.**
   R2 mandates a default but leaves the value to the Implementer. Chose a localhost placeholder
   rather than reusing the `https://example.org/...` spec example: it signals "configure me for a
   real deployment" and keeps the package usable standalone (Django dev-server convention). The
   test suite pins its own `CONTROLLED_VOCABULARIES_BASE_URI` so URI assertions never depend on this
   default. README documentation of the default is T012's job (not in this task set).

7. **Slug collisions surface as `ValidationError` via an explicit pre-save check.**
   R4 says a colliding slug is "refused ... surfaces as a validation error, not auto-suffixed", but
   the DB `unique=True` constraint alone would raise `IntegrityError` (and break the test
   transaction). Added an explicit `ConceptScheme.objects.filter(slug=…).exclude(pk=self.pk).exists()`
   check in `save()` that raises `ValidationError` before hitting the DB, keeping `unique=True` as the
   integrity backstop. Honest, minimal, and matches R4's stated behaviour. The same pattern will
   apply per-scheme for `Concept` in US2.

## S5 CONVERGE — tamper-check triage

8. **tamper-check flag on `tests/settings.py` — reviewed, approved (not a test weakening).**
   The convergence exit gate's `tamper-check.sh` flagged `tests/settings.py` as a
   `modified_preexisting_test` because the filename contains "test". It is a Django settings
   module, not a test-suite file. The only change vs `origin/main` appends
   `CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"` (US-1, needed for
   deterministic URI-composition assertions). No test assertion was modified, deleted, or
   weakened. Approved by Forge per policy D4 (legitimate change recorded here). The heuristic's
   name-based match on a settings module is a known false positive; noting as a candidate
   kit papercut (scope the tamper matcher to `test_*.py`/`*_test.py`, not any path containing
   "test").
