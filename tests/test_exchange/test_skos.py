"""``controlled_vocabularies.exchange.skos`` — reading a published SKOS file
into records (tasks.md Phase US-1).

Grows one task at a time, mirroring the module. T006 covers only
``_read_graph``: a file becomes an ``rdflib.Graph``, the serialization is
stated or determined, and RDF/XML is routed through the T004 safety scan
before rdflib ever sees it.
"""

from pathlib import Path

import pytest
import rdflib

import controlled_vocabularies.exchange as exchange
from controlled_vocabularies.exchange.report import FatalReason, NormalizedReason, SetAsideReason
from controlled_vocabularies.exchange.safety import UnsafeRdfXmlError
from controlled_vocabularies.exchange.skos import SkosImportError, SkosImportFailed, _read_graph, import_skos
from controlled_vocabularies.models import Concept, ConceptLabel, ConceptNote, ConceptRelation, ConceptScheme
from tests.factories import ConceptFactory, ConceptSchemeFactory

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skos"
SECURITY_FIXTURES = Path(__file__).parent.parent / "fixtures" / "security"

SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
ROCKS_URI = "http://example.org/rocks/"
ROCKS_SCHEME_URI = rdflib.URIRef(ROCKS_URI)

# (filename, rdflib format) for the base vocabulary in its three serializations.
BASE_SERIALIZATIONS = [
    ("rocks.ttl", "turtle"),
    ("rocks.rdf", "xml"),
    ("rocks.jsonld", "json-ld"),
]

# Every fixture in the directory, whatever its purpose, must at least parse as
# RDF (fatal-path fixtures are semantically invalid for import, never
# syntactically invalid RDF — that distinction is exactly what makes them
# useful fatal-path material rather than parser-crash material). Discovered by
# walking the directory rather than listed by hand, so a fixture added by a
# later story is covered without anyone remembering to register it.
SUFFIX_FORMATS = {".ttl": "turtle", ".rdf": "xml", ".jsonld": "json-ld"}
ALL_FIXTURES = sorted((path.name, SUFFIX_FORMATS[path.suffix]) for path in FIXTURES.iterdir() if path.is_file())


class TestReadGraph:
    @pytest.mark.parametrize(
        "filename,fmt",
        [("rocks.ttl", None), ("rocks.rdf", None), ("rocks.jsonld", None)],
    )
    def test_each_supported_serialization_parses_by_extension(self, filename, fmt):
        graph = _read_graph(FIXTURES / filename, serialization=fmt)
        assert len(graph) > 0
        assert (rdflib.URIRef("http://example.org/rocks/"), rdflib.RDF.type, SKOS.ConceptScheme) in graph

    @pytest.mark.parametrize("fmt", ["turtle", "xml", "json-ld"])
    def test_each_supported_serialization_parses_with_stated_format(self, fmt):
        filename = {"turtle": "rocks.ttl", "xml": "rocks.rdf", "json-ld": "rocks.jsonld"}[fmt]
        graph = _read_graph(FIXTURES / filename, serialization=fmt)
        assert len(graph) > 0

    def test_missing_file_fails_with_a_translatable_message(self, tmp_path):
        missing = tmp_path / "does-not-exist.ttl"
        with pytest.raises(SkosImportError) as exc_info:
            _read_graph(missing)
        assert str(missing) in str(exc_info.value)

    def test_unparseable_file_fails_with_a_translatable_message(self, tmp_path):
        bad = tmp_path / "bad.ttl"
        bad.write_text("this is not turtle @@@ not even close {{{ ]][[ ")
        with pytest.raises(SkosImportError) as exc_info:
            _read_graph(bad)
        assert "bad.ttl" in str(exc_info.value)

    def test_serialization_that_cannot_be_determined_fails(self, tmp_path):
        # A real vocabulary under an extension guess_format does not recognise,
        # and no explicit format given: FR-002's "cannot be determined" half.
        mystery = tmp_path / "vocab.mysteryext"
        mystery.write_bytes((FIXTURES / "rocks.ttl").read_bytes())
        with pytest.raises(SkosImportError):
            _read_graph(mystery)

    def test_serialization_not_among_the_three_supported_fails_even_if_named_explicitly(self):
        # "n3" is a real rdflib format, but not one of FR-002's three — stating
        # it explicitly must not smuggle it past the supported-formats gate.
        with pytest.raises(SkosImportError):
            _read_graph(FIXTURES / "rocks.ttl", serialization="n3")

    def test_rdf_xml_is_routed_through_the_safety_scan_before_rdflib_sees_it(self):
        # Reinstates the measured entity bomb (research.md R3) as input to the
        # public reading path, not just to scan_rdf_xml() directly — proving
        # the two are actually wired together, not merely both present. The
        # scan's own UnsafeRdfXmlError propagates as-is (both it and
        # SkosImportError are ValidationError subclasses; wrapping one inside
        # the other would only blur which stage actually refused the file).
        with pytest.raises(UnsafeRdfXmlError):
            _read_graph(SECURITY_FIXTURES / "entity_bomb.rdf", serialization="xml")

    def test_ordinary_rdf_xml_is_unaffected_by_the_safety_scan(self):
        graph = _read_graph(SECURITY_FIXTURES / "ordinary.rdf", serialization="xml")
        assert len(graph) > 0


class TestImportSkosVocabulary:
    """T007 — the vocabulary itself: created, updated, matched against a named
    target, or refused when neither the file nor the caller can settle which
    one is being imported. These assert on the scheme's own bucket entry
    only — the concept walk (T009) also populates ``created``/``updated``
    for each concept, covered separately in ``TestImportConcepts``."""

    def test_a_declared_vocabulary_is_created_when_not_already_held(self, db):
        report = import_skos(FIXTURES / "rocks.ttl")
        scheme = ConceptScheme.objects.get(static_uri=ROCKS_URI)
        assert scheme.name == "Rock types"
        assert ROCKS_URI in report.created
        assert ROCKS_URI not in report.updated
        assert report.fatal == []

    def test_a_declared_vocabulary_already_held_is_updated_not_duplicated(self, db):
        existing = ConceptSchemeFactory(name="Old name", static_uri=ROCKS_URI)
        report = import_skos(FIXTURES / "rocks.ttl")
        existing.refresh_from_db()
        assert existing.name == "Rock types"
        assert ConceptScheme.objects.filter(static_uri=ROCKS_URI).count() == 1
        assert ROCKS_URI in report.updated
        assert ROCKS_URI not in report.created

    def test_a_named_target_that_matches_the_file_succeeds(self, db):
        target = ConceptSchemeFactory(name="Old name", static_uri=ROCKS_URI)
        report = import_skos(FIXTURES / "rocks.ttl", scheme=target)
        target.refresh_from_db()
        assert target.name == "Rock types"
        assert report.fatal == []

    def test_a_named_target_that_contradicts_the_file_fails_and_writes_nothing(self, db):
        target = ConceptSchemeFactory(name="Unrelated vocabulary", external=True)
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "rocks.ttl", scheme=target)
        assert exc_info.value.report.fatal[0].reason is FatalReason.VOCABULARY_TARGET_MISMATCH
        target.refresh_from_db()
        assert target.name == "Unrelated vocabulary"
        assert not ConceptScheme.objects.filter(static_uri=ROCKS_URI).exists()

    def test_a_file_declaring_no_vocabulary_fails_without_a_named_target(self, db):
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "no_scheme_declared.ttl")
        assert exc_info.value.report.fatal[0].reason is FatalReason.VOCABULARY_UNDETERMINED
        assert ConceptScheme.objects.count() == 0

    def test_a_file_declaring_no_vocabulary_succeeds_with_a_named_target(self, db):
        target = ConceptSchemeFactory(name="Loose concepts")
        report = import_skos(FIXTURES / "no_scheme_declared.ttl", scheme=target)
        assert report.fatal == []


class TestChoosingBetweenDeclaredVocabularies:
    """T007 — which vocabulary a file with more than one declared is about.

    Typing a second ``skos:ConceptScheme`` is ordinary: it is how a concept
    names a vocabulary it belongs to elsewhere, which spec Edge Cases §1
    requires be set aside rather than refused. So the file's own concepts
    decide, and only a genuine tie with no named target is refused.
    """

    def test_the_vocabulary_most_of_the_concepts_belong_to_is_the_one_imported(self, db):
        report = import_skos(FIXTURES / "mixed_scheme_membership.ttl")
        assert ConceptScheme.objects.get().static_uri == "http://example.org/minerals/"
        assert report.fatal == []

    def test_the_choice_does_not_depend_on_the_order_of_the_identifiers(self, db, tmp_path):
        # The same file with the two vocabularies' identifiers swapped so the
        # foreign one now sorts first. Sorted-first selection would import it.
        source = (FIXTURES / "mixed_scheme_membership.ttl").read_text()
        swapped = source.replace("http://example.org/other/", "http://example.org/aaa-other/")
        renamed = tmp_path / "swapped.ttl"
        renamed.write_text(swapped)
        import_skos(renamed)
        assert ConceptScheme.objects.get().static_uri == "http://example.org/minerals/"

    def test_two_vocabularies_with_an_equal_claim_fail_without_a_named_target(self, db):
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "two_vocabularies.ttl")
        finding = exc_info.value.report.fatal[0]
        assert finding.reason is FatalReason.VOCABULARY_AMBIGUOUS
        assert "http://example.org/alpha/" in finding.render()
        assert "http://example.org/beta/" in finding.render()
        assert ConceptScheme.objects.count() == 0
        assert Concept.objects.count() == 0

    def test_a_named_target_decides_between_them(self, db):
        target = ConceptSchemeFactory(name="Beta vocabulary", static_uri="http://example.org/beta/")
        report = import_skos(FIXTURES / "two_vocabularies.ttl", scheme=target)
        assert report.fatal == []
        assert ConceptScheme.objects.count() == 1
        assert Concept.objects.get(scheme=target).static_uri == "http://example.org/beta/two"


class TestImportedVocabularyDefaultLanguage:
    """T008 — FR-005/decisions.md D4: the imported vocabulary's default
    language comes from the file where the file says, and only ever a
    language the site is configured for."""

    def test_a_vocabulary_declared_in_a_configured_non_default_language_uses_it(self, db):
        import_skos(FIXTURES / "french_vocabulary.ttl")
        scheme = ConceptScheme.objects.get(static_uri="http://example.org/geology/")
        assert scheme.default_language == "fr"
        assert scheme.effective_default_language == "fr"
        assert scheme.name == "Types de roches"

    def test_a_vocabulary_declared_in_an_unconfigured_language_falls_back_to_the_site_default(self, db):
        import_skos(FIXTURES / "unconfigured_language_vocabulary.ttl")
        scheme = ConceptScheme.objects.get(static_uri="http://example.org/geology2/")
        # Neither "es" (declared) nor "es" (commonest concept label language)
        # is configured, so nothing overrides the site default.
        assert scheme.effective_default_language == "en"

    def test_default_language_is_not_recomputed_for_a_scheme_that_already_has_concepts(self, db):
        # ConceptScheme.save() itself refuses to change default_language once
        # concepts exist (R1's own guard — it anchors their identity). A
        # scheme matched by URI that already has concepts from an earlier
        # run must not trip that guard just because this run recomputed a
        # (possibly identical, possibly not) value from the file.
        scheme = ConceptSchemeFactory(name="Geology", static_uri="http://example.org/geology/", default_language="")
        ConceptFactory(scheme=scheme, label="Existing concept")
        report = import_skos(FIXTURES / "french_vocabulary.ttl")
        assert report.fatal == []
        scheme.refresh_from_db()
        assert scheme.default_language == ""


class TestImportConcepts:
    """T009 — concepts land inside the vocabulary being imported, each
    holding its published identifier and its default-language preferred
    label; scheme membership is read via any of the three SKOS predicates;
    a concept claiming a different vocabulary is set aside, not imported."""

    def test_every_concept_in_the_base_vocabulary_is_created_with_its_identifier_and_label(self, db):
        report = import_skos(FIXTURES / "rocks.ttl")
        assert Concept.objects.count() == 5
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        assert granite.label == "Granite"
        assert granite.scheme.static_uri == "http://example.org/rocks/"
        assert set(report.created) >= {
            "http://example.org/rocks/",
            "http://example.org/rocks/granite",
            "http://example.org/rocks/igneous",
            "http://example.org/rocks/basalt",
            "http://example.org/rocks/sedimentary",
            "http://example.org/rocks/quartz",
        }

    def test_scheme_membership_via_hasTopConcept_inScheme_and_topConceptOf_all_attach_correctly(self, db):
        import_skos(FIXTURES / "mixed_scheme_membership.ttl")
        scheme = ConceptScheme.objects.get(static_uri="http://example.org/minerals/")
        attached = set(Concept.objects.filter(scheme=scheme).values_list("static_uri", flat=True))
        assert attached == {
            "http://example.org/minerals/quartz",
            "http://example.org/minerals/feldspar",
            "http://example.org/minerals/mica",
        }

    def test_a_concept_claiming_a_different_vocabulary_is_set_aside_not_imported(self, db):
        report = import_skos(FIXTURES / "mixed_scheme_membership.ttl")
        assert not Concept.objects.filter(static_uri="http://example.org/minerals/foreign").exists()
        mismatches = [entry for entry in report.set_aside if entry.reason is SetAsideReason.VOCABULARY_MISMATCH]
        assert len(mismatches) == 1
        assert mismatches[0].subject == "http://example.org/minerals/foreign"
        assert mismatches[0].params["other"] == "http://example.org/other/"

    def test_a_concept_with_no_preferred_label_in_the_default_language_is_set_aside_and_the_rest_imports(self, db):
        report = import_skos(FIXTURES / "no_default_language_label.ttl")
        assert Concept.objects.filter(scheme__static_uri="http://example.org/quarry/").count() == 2
        assert not Concept.objects.filter(static_uri="http://example.org/quarry/c").exists()
        set_aside = [entry for entry in report.set_aside if entry.reason is SetAsideReason.NO_PREFERRED_LABEL]
        assert len(set_aside) == 1
        assert set_aside[0].subject == "http://example.org/quarry/c"
        assert set_aside[0].params["language"] == "en"

    def test_reimporting_the_identical_file_updates_rather_than_duplicates_concepts(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite_pk = Concept.objects.get(static_uri="http://example.org/rocks/granite").pk
        report = import_skos(FIXTURES / "rocks.ttl")
        assert Concept.objects.count() == 5
        assert Concept.objects.get(static_uri="http://example.org/rocks/granite").pk == granite_pk
        assert "http://example.org/rocks/granite" in report.updated
        assert "http://example.org/rocks/granite" not in report.created


class TestConceptSlugs:
    """T010 — FR-007/decisions.md D6: an imported concept's slug is derived
    from its label by the model's own rule, disambiguated by a deterministic
    numeric suffix when two concepts in one vocabulary derive the same
    value; never derived from the identifier."""

    def test_two_concepts_sharing_a_label_get_distinct_deterministic_slugs(self, db):
        import_skos(FIXTURES / "duplicate_slug.ttl")
        first = Concept.objects.get(static_uri="http://example.org/quarry2/quartz-a")
        second = Concept.objects.get(static_uri="http://example.org/quarry2/quartz-b")
        assert first.slug == "quartz"
        assert second.slug == "quartz-2"
        assert first.static_uri != second.static_uri

    def test_reimporting_the_identical_file_keeps_each_concept_s_slug(self, db):
        import_skos(FIXTURES / "duplicate_slug.ttl")
        first_slug_before = Concept.objects.get(static_uri="http://example.org/quarry2/quartz-a").slug
        second_slug_before = Concept.objects.get(static_uri="http://example.org/quarry2/quartz-b").slug

        import_skos(FIXTURES / "duplicate_slug.ttl")

        assert Concept.objects.get(static_uri="http://example.org/quarry2/quartz-a").slug == first_slug_before
        assert Concept.objects.get(static_uri="http://example.org/quarry2/quartz-b").slug == second_slug_before
        assert Concept.objects.filter(scheme__static_uri="http://example.org/quarry2/").count() == 2

    def test_slug_is_never_derived_from_the_identifier(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        # The URI's own last path segment is "igneous"; the label is "Igneous
        # rock". If the slug tracked the identifier it would read "igneous",
        # not "igneous-rock".
        assert igneous.slug == "igneous-rock"


class TestFatalFindingsAndAtomicity:
    """T011 — FR-003/FR-004, decisions.md D3/D8, research.md R7: a missing or
    refused identity fails the whole run; a file with more than one such
    problem reports all of them in one run; the transaction rolls back so
    the database is exactly as it was before the run started."""

    def test_a_blank_node_concept_fails_the_run_and_writes_nothing(self, db):
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "blank_node_concept.ttl")
        assert exc_info.value.report.fatal[0].reason is FatalReason.MISSING_IDENTITY
        assert ConceptScheme.objects.count() == 0
        assert Concept.objects.count() == 0

    def test_a_refused_uri_scheme_concept_fails_the_run_and_writes_nothing(self, db):
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "refused_uri_scheme.ttl")
        assert exc_info.value.report.fatal[0].reason is FatalReason.REFUSED_IDENTITY
        assert ConceptScheme.objects.count() == 0
        assert Concept.objects.count() == 0

    def test_every_fatal_problem_in_one_file_is_collected_not_just_the_first(self, db):
        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "multiple_fatal_problems.ttl")
        reasons = {finding.reason for finding in exc_info.value.report.fatal}
        assert reasons == {FatalReason.MISSING_IDENTITY, FatalReason.REFUSED_IDENTITY}
        assert len(exc_info.value.report.fatal) == 2

    def test_a_multi_problem_file_rolls_back_even_its_ordinary_concept(self, db):
        with pytest.raises(SkosImportFailed):
            import_skos(FIXTURES / "multiple_fatal_problems.ttl")
        # The scheme and the one perfectly valid concept alongside the two
        # fatal ones must not survive either — the run is all-or-nothing.
        assert ConceptScheme.objects.count() == 0
        assert not Concept.objects.filter(static_uri="http://example.org/mixed/ordinary").exists()

    def test_a_fatal_reimport_rolls_back_a_scheme_field_update_too(self, db):
        # The scheme row is written to (its name set to the file's own) before
        # the fatal concepts are even reached — proving the rollback undoes
        # that write, not just the concept creation, is the point here.
        existing = ConceptSchemeFactory(name="Original name", static_uri="http://example.org/mixed/")
        concept_count_before = Concept.objects.count()

        with pytest.raises(SkosImportFailed):
            import_skos(FIXTURES / "multiple_fatal_problems.ttl")

        existing.refresh_from_db()
        assert existing.name == "Original name"
        assert Concept.objects.count() == concept_count_before


class TestReportPopulatedByARealRun:
    """T012 — FR-015: a real run's report distinguishes what was created,
    what was updated, and what was set aside with its reason, all as data a
    caller reads directly rather than parses from prose."""

    def test_a_first_import_reports_everything_as_created_nothing_as_updated(self, db):
        report = import_skos(FIXTURES / "rocks.ttl")
        expected = {
            "http://example.org/rocks/",
            "http://example.org/rocks/igneous",
            "http://example.org/rocks/granite",
            "http://example.org/rocks/basalt",
            "http://example.org/rocks/sedimentary",
            "http://example.org/rocks/quartz",
        }
        assert set(report.created) == expected
        assert report.updated == []
        assert report.set_aside == []
        assert report.fatal == []
        # No duplicates within the bucket either — each URI reported exactly once.
        assert len(report.created) == len(expected)

    def test_a_reimport_reports_everything_as_updated_nothing_as_created(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        report = import_skos(FIXTURES / "rocks.ttl")
        assert set(report.updated) == {
            "http://example.org/rocks/",
            "http://example.org/rocks/igneous",
            "http://example.org/rocks/granite",
            "http://example.org/rocks/basalt",
            "http://example.org/rocks/sedimentary",
            "http://example.org/rocks/quartz",
        }
        assert report.created == []

    def test_set_aside_entries_carry_their_reason_subject_and_params_as_data(self, db):
        report = import_skos(FIXTURES / "no_default_language_label.ttl")
        assert len(report.set_aside) == 1
        entry = report.set_aside[0]
        assert entry.reason is SetAsideReason.NO_PREFERRED_LABEL
        assert entry.subject == "http://example.org/quarry/c"
        assert entry.params == {"language": "en"}
        # A caller groups/counts without parsing report.render() output.
        grouped = report.set_aside_by_reason()
        assert len(grouped[SetAsideReason.NO_PREFERRED_LABEL]) == 1

    def test_created_updated_and_set_aside_all_coexist_in_one_run(self, db):
        # Pre-seed one of mixed_scheme_membership.ttl's concepts so this run
        # exercises created, updated, and set-aside together.
        scheme = ConceptSchemeFactory(name="Minerals", static_uri="http://example.org/minerals/")
        Concept.objects.create(scheme=scheme, static_uri="http://example.org/minerals/quartz", label="Old quartz")

        report = import_skos(FIXTURES / "mixed_scheme_membership.ttl")

        assert "http://example.org/minerals/quartz" in report.updated
        assert {"http://example.org/minerals/feldspar", "http://example.org/minerals/mica"} <= set(report.created)
        assert any(entry.reason is SetAsideReason.VOCABULARY_MISMATCH for entry in report.set_aside)
        assert report.fatal == []


class TestIdempotentReimport:
    """T013 — FR-004/FR-013: importing an identical file twice creates
    nothing new and recreates nothing. Every record's primary key is stable
    across both runs, and a foreign-key reference made *between* the two
    runs still resolves to the same row afterward — the acceptance scenario
    specifically distinguishes this from merely re-reading the same URI."""

    def test_every_primary_key_is_stable_across_two_identical_runs(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        scheme_pk = ConceptScheme.objects.get(static_uri=ROCKS_URI).pk
        concept_pks = {c.static_uri: c.pk for c in Concept.objects.filter(scheme_id=scheme_pk)}
        assert len(concept_pks) == 5

        import_skos(FIXTURES / "rocks.ttl")

        scheme = ConceptScheme.objects.get(static_uri=ROCKS_URI)
        assert scheme.pk == scheme_pk
        assert ConceptScheme.objects.filter(static_uri=ROCKS_URI).count() == 1
        assert Concept.objects.filter(scheme=scheme).count() == len(concept_pks)
        for uri, pk in concept_pks.items():
            assert Concept.objects.get(static_uri=uri).pk == pk

    def test_a_reference_made_between_two_runs_still_resolves_after_the_second(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        basalt = Concept.objects.get(static_uri="http://example.org/rocks/basalt")
        relation = ConceptRelation.objects.create(source=granite, target=basalt, kind=ConceptRelation.Kind.BROADER)

        import_skos(FIXTURES / "rocks.ttl")

        relation.refresh_from_db()
        assert relation.source_id == granite.pk
        assert relation.target_id == basalt.pk
        assert relation.source.static_uri == "http://example.org/rocks/granite"
        assert relation.target.static_uri == "http://example.org/rocks/basalt"


class TestAuthoritativeUpdateForContainedRecords:
    """T014 — FR-013/decisions.md D5: for a record the file still contains, the
    file is authoritative for that record's own content. `rocks_updated.ttl`
    corrects granite's preferred label; the corrected value must land, and the
    concept must keep its identifier and database identity while it does.

    `rocks_updated.ttl` (T005) also drops granite's alternative label and its
    `related` edge to quartz, matching the spec's full Independent Test framing
    — but `import_skos()` does not read `skos:altLabel` or `skos:related` at
    all yet (that's US-3/US-4, T018-T026, explicitly out of this story's scope
    per the brief's prohibitions). Asserting their removal here is therefore not
    yet meaningful; decisions.md D20 records the scoping and why it is safe to
    defer to the stories that actually build those read paths, reusing this
    same fixture pair.
    """

    def test_a_corrected_preferred_label_lands_and_keeps_the_concept_s_identity(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite_before = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        pk_before = granite_before.pk

        report = import_skos(FIXTURES / "rocks_updated.ttl")

        granite_after = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        assert granite_after.pk == pk_before
        assert granite_after.label == "Granite (revised)"
        assert "http://example.org/rocks/granite" in report.updated
        assert "http://example.org/rocks/granite" not in report.created


class TestRecordsAbsentFromSource:
    """T015 — FR-013: a record the file no longer mentions is left exactly as
    it is and named in the report's absent-from-source bucket. `rocks_updated.ttl`
    drops quartz entirely; a concept elsewhere already referencing it (standing in
    for "something downstream may already reference it", D5's own reasoning) must
    still resolve to it afterward."""

    def test_a_concept_dropped_from_the_file_is_untouched_and_named_absent(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        quartz = Concept.objects.get(static_uri="http://example.org/rocks/quartz")
        quartz_pk, quartz_label = quartz.pk, quartz.label
        basalt = Concept.objects.get(static_uri="http://example.org/rocks/basalt")
        reference = ConceptRelation.objects.create(source=basalt, target=quartz, kind=ConceptRelation.Kind.RELATED)

        report = import_skos(FIXTURES / "rocks_updated.ttl")

        quartz_after = Concept.objects.get(static_uri="http://example.org/rocks/quartz")
        assert quartz_after.pk == quartz_pk
        assert quartz_after.label == quartz_label
        assert "http://example.org/rocks/quartz" in report.absent_from_source
        assert "http://example.org/rocks/quartz" not in report.updated
        assert "http://example.org/rocks/quartz" not in report.created

        reference.refresh_from_db()
        assert reference.target_id == quartz_pk
        assert reference.target.static_uri == "http://example.org/rocks/quartz"

    def test_a_concept_still_mentioned_in_the_file_is_not_reported_absent(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        report = import_skos(FIXTURES / "rocks_updated.ttl")
        assert "http://example.org/rocks/granite" not in report.absent_from_source
        assert "http://example.org/rocks/basalt" not in report.absent_from_source


class TestVocabularyMetadataUpdate:
    """T016 — FR-013: the vocabulary's own name and description update from
    the file on re-import, identifier unchanged. SKOS defines no description
    predicate for a ``skos:ConceptScheme``; decisions.md D21 records
    ``dcterms:description`` as the source, the same alias CONTEXT.md already
    establishes for a concept's own ``definition``."""

    def test_a_description_is_read_from_dcterms_description(self, db):
        import_skos(FIXTURES / "vocabulary_metadata.ttl")
        scheme = ConceptScheme.objects.get(static_uri="http://example.org/gems/")
        assert scheme.name == "Gemstones"
        assert scheme.description == "A vocabulary of gemstone types."

    def test_a_changed_name_and_description_land_on_reimport_with_identifier_unchanged(self, db):
        import_skos(FIXTURES / "vocabulary_metadata.ttl")
        scheme_pk = ConceptScheme.objects.get(static_uri="http://example.org/gems/").pk

        import_skos(FIXTURES / "vocabulary_metadata_updated.ttl")

        scheme = ConceptScheme.objects.get(static_uri="http://example.org/gems/")
        assert scheme.pk == scheme_pk
        assert scheme.static_uri == "http://example.org/gems/"
        assert scheme.name == "Precious stones"
        assert scheme.description == "An updated vocabulary of gemstones and precious stones."

    def test_a_description_removed_from_the_file_is_cleared_not_left_stale(self, db):
        import_skos(FIXTURES / "vocabulary_metadata.ttl")

        import_skos(FIXTURES / "vocabulary_metadata_description_removed.ttl")

        scheme = ConceptScheme.objects.get(static_uri="http://example.org/gems/")
        assert scheme.description == ""


class TestFrozenDefaultLanguageConflictIsReported:
    """Carried from the US-1 review (decisions.md D18/D22): D18 froze an
    existing, concept-bearing scheme's ``default_language`` by silently
    skipping recomputation on every non-creating run. That protects the
    database but says nothing to the curator — a re-imported file that
    genuinely declares a different default language now gets reported."""

    def test_a_conflicting_declared_default_language_is_reported_not_silently_dropped(self, db):
        scheme = ConceptSchemeFactory(name="Geology", static_uri="http://example.org/geology/", default_language="")
        ConceptFactory(scheme=scheme, label="Existing concept")

        report = import_skos(FIXTURES / "french_vocabulary.ttl")

        scheme.refresh_from_db()
        assert scheme.default_language == ""
        conflicts = [entry for entry in report.set_aside if entry.reason is SetAsideReason.DEFAULT_LANGUAGE_FROZEN]
        assert len(conflicts) == 1
        assert conflicts[0].subject == "http://example.org/geology/"
        assert conflicts[0].params == {"declared": "fr", "frozen": "en"}

    def test_an_agreeing_declared_default_language_produces_no_conflict(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        report = import_skos(FIXTURES / "rocks.ttl")
        assert not any(entry.reason is SetAsideReason.DEFAULT_LANGUAGE_FROZEN for entry in report.set_aside)


class TestAtomicityOnAPopulatedDatabase:
    """T017 — FR-003: a run that fails partway leaves the database exactly as
    it was, asserted against an already-populated database rather than an
    empty one, so the test fails if the transaction boundary only protected
    creation. T011 already proved this for a scheme field write and for a
    plain creation; this proves it for an *update to an already-existing
    concept*, which a creation-only rollback would let through."""

    def test_a_failed_reimport_leaves_a_populated_database_exactly_as_it_was(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite_before = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        pk_before, label_before = granite_before.pk, granite_before.label
        concept_count_before = Concept.objects.count()
        scheme = ConceptScheme.objects.get(static_uri=ROCKS_URI)
        name_before = scheme.name

        with pytest.raises(SkosImportFailed) as exc_info:
            import_skos(FIXTURES / "reimport_rolls_back_an_update.ttl")
        assert exc_info.value.report.fatal[0].reason is FatalReason.MISSING_IDENTITY

        granite_after = Concept.objects.get(pk=pk_before)
        assert granite_after.label == label_before
        assert Concept.objects.count() == concept_count_before
        assert not Concept.objects.filter(label="Ghost concept").exists()
        scheme.refresh_from_db()
        assert scheme.name == name_before


class TestConceptLabels:
    """T018 — FR-008/research.md R5: preferred labels in configured languages
    other than the default, and alternative and hidden labels, are stored
    against their concept through ``Concept.add_label``, each with its own
    kind and language. The preferred label in the vocabulary's default
    language is ``Concept.label`` itself (T009) and is never also written as
    a ``ConceptLabel`` row — ``ConceptLabel.clean()`` refuses that (models.py
    ``_reject_default_language_preferred``), and this importer must not even
    attempt it."""

    def test_preferred_labels_in_other_configured_languages_are_stored(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        others = {(row.language, row.text) for row in igneous.labels.filter(kind=ConceptLabel.Kind.PREFERRED)}
        assert others == {("de", "Magmatisches Gestein"), ("fr", "Roche ignée")}

    def test_default_language_preferred_label_is_not_duplicated_as_a_concept_label(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        assert igneous.label == "Igneous rock"
        assert not igneous.labels.filter(language="en", kind=ConceptLabel.Kind.PREFERRED).exists()

    def test_alternative_and_hidden_labels_are_stored_with_their_own_kind_and_language(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        quartz = Concept.objects.get(static_uri="http://example.org/rocks/quartz")
        assert granite.alt_labels("en") == ["Magma rock"]
        assert granite.hidden_labels("en") == ["Granit rock"]
        assert quartz.alt_labels("de") == ["Quartz"]

    def test_reimport_removes_an_alternative_label_the_publisher_dropped_leaving_the_concept_intact(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite_pk = Concept.objects.get(static_uri="http://example.org/rocks/granite").pk
        assert Concept.objects.get(pk=granite_pk).alt_labels("en") == ["Magma rock"]

        import_skos(FIXTURES / "rocks_updated.ttl")

        granite = Concept.objects.get(pk=granite_pk)
        assert granite.alt_labels("en") == []
        assert granite.hidden_labels("en") == ["Granit rock"]
        assert granite.pk == granite_pk


class TestConceptNotes:
    """T019 — FR-009/research.md R5: the definition and each of the six SKOS
    documentary note kinds are stored against their concept, each in its own
    language, through ``Concept.add_note``."""

    def test_definition_and_each_note_kind_are_stored_against_the_right_concept(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        basalt = Concept.objects.get(static_uri="http://example.org/rocks/basalt")
        sedimentary = Concept.objects.get(static_uri="http://example.org/rocks/sedimentary")
        quartz = Concept.objects.get(static_uri="http://example.org/rocks/quartz")

        assert igneous.definition("en") == "Rock formed by the cooling and solidification of magma or lava."
        assert granite.notes("en", ConceptNote.Kind.SCOPE) == ["Used here for coarse-grained intrusive igneous rock."]
        assert basalt.notes("en", ConceptNote.Kind.EXAMPLE) == ["Columnar basalt at the Giant's Causeway."]
        assert sedimentary.notes("en", ConceptNote.Kind.EDITORIAL) == [
            "Confirm classification against the regional survey before publishing."
        ]
        assert quartz.notes("en", ConceptNote.Kind.HISTORY) == [
            "Reclassified from 'Silica minerals' in the 2020 revision."
        ]
        assert quartz.notes("en", ConceptNote.Kind.CHANGE) == ["Definition tightened in 2022."]
        assert quartz.notes("en", ConceptNote.Kind.NOTE) == ["See also feldspar for a related silicate."]

    def test_reimport_removes_a_note_the_publisher_dropped_leaving_the_concept_intact(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        basalt_pk = Concept.objects.get(static_uri="http://example.org/rocks/basalt").pk
        assert Concept.objects.get(pk=basalt_pk).notes("en", ConceptNote.Kind.EXAMPLE) == [
            "Columnar basalt at the Giant's Causeway."
        ]

        import_skos(FIXTURES / "rocks_updated.ttl")

        basalt = Concept.objects.get(pk=basalt_pk)
        assert basalt.notes("en", ConceptNote.Kind.EXAMPLE) == []
        assert basalt.label == "Basalt"
        assert basalt.pk == basalt_pk


class TestUnconfiguredLanguageValuesAreSetAside:
    """T020 — FR-014: a label or note in a language the site is not configured
    for is stored nowhere and is named in the report with its language, and
    the concept still imports on whatever configured-language content it
    carries. Filtered ahead of the write rather than caught from the models'
    own refusal (decisions.md D25) — ``ConceptLabel.clean()``/``ConceptNote.clean()``
    would refuse these too, but the importer must not rely on that exception
    as its control flow."""

    def test_labels_and_notes_in_an_unconfigured_language_are_set_aside_and_named(self, db):
        report = import_skos(FIXTURES / "unconfigured_language_values.ttl")
        schist = Concept.objects.get(static_uri="http://example.org/quarry3/schist")
        entries = [
            entry
            for entry in report.set_aside
            if entry.reason is SetAsideReason.UNCONFIGURED_LANGUAGE and entry.subject == schist.static_uri
        ]
        # Two alternative labels and one scope note, each named individually
        # rather than merged into a single "some values were dropped" entry.
        assert len(entries) == 3
        assert all(entry.params["language"] == "es" for entry in entries)

    def test_the_concept_still_imports_on_its_configured_language_content(self, db):
        import_skos(FIXTURES / "unconfigured_language_values.ttl")
        schist = Concept.objects.get(static_uri="http://example.org/quarry3/schist")
        assert schist.label == "Schist"
        assert schist.alt_labels("es") == []
        assert schist.notes("es") == []


class TestUnheldValuesAndNormalisation:
    """T021 — FR-014: a notation, a mapping to another vocabulary, and a
    predicate from outside SKOS entirely are each set aside and reported
    rather than passed over in silence, and the concepts still import
    successfully. FR-009: a foreign ``dcterms:description`` read as a
    concept's definition, because the concept carries no ``skos:definition``
    of its own, is reported as a normalisation rather than applied silently
    (decisions.md D24 in mapping.py, D21's precedent extended from the scheme
    level to the concept level)."""

    def test_the_concepts_still_import_successfully(self, db):
        report = import_skos(FIXTURES / "unmodelled_and_normalised_values.ttl")
        assert report.fatal == []
        assert Concept.objects.filter(scheme__static_uri="http://example.org/hardware/").count() == 2

    def test_a_notation_is_set_aside(self, db):
        report = import_skos(FIXTURES / "unmodelled_and_normalised_values.ttl")
        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.NOTATION]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/hardware/widget"

    def test_a_mapping_predicate_is_set_aside_naming_the_predicate(self, db):
        report = import_skos(FIXTURES / "unmodelled_and_normalised_values.ttl")
        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.MAPPING]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/hardware/widget"
        assert entries[0].params["predicate"] == "skos:exactMatch"

    def test_a_predicate_from_outside_skos_is_set_aside_naming_the_predicate(self, db):
        report = import_skos(FIXTURES / "unmodelled_and_normalised_values.ttl")
        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.UNMODELLED_PREDICATE]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/hardware/widget"
        assert entries[0].params["predicate"] == "http://example.org/ns#customAttribute"

    def test_a_foreign_description_is_read_as_the_definition_and_reported_as_normalised(self, db):
        report = import_skos(FIXTURES / "unmodelled_and_normalised_values.ttl")
        gadget = Concept.objects.get(static_uri="http://example.org/hardware/gadget")
        assert gadget.definition("en") == "A small mechanical device."
        assert len(report.normalized) == 1
        entry = report.normalized[0]
        assert entry.reason is NormalizedReason.FOREIGN_DEFINITION
        assert entry.subject == "http://example.org/hardware/gadget"
        assert entry.params["predicate"] == "dcterms:description"
        assert entry.params["language"] == "en"

    def test_a_concept_with_its_own_definition_is_not_normalised(self, db):
        # rocks.ttl's igneous carries a native skos:definition; nothing about
        # a run that never needs the dcterms alias should land in
        # report.normalized.
        report = import_skos(FIXTURES / "rocks.ttl")
        assert report.normalized == []

    def test_broader_related_and_collection_membership_are_not_reported_as_unmodelled(self, db):
        # skos:broader/related/member/memberList are SKOS predicates this
        # importer does not read yet (US-4/US-5), but the models do have a
        # place for them — they must never be reported as UNMODELLED_PREDICATE
        # merely because this story doesn't build that read path yet.
        report = import_skos(FIXTURES / "rocks.ttl")
        assert not any(entry.reason is SetAsideReason.UNMODELLED_PREDICATE for entry in report.set_aside)


class TestNoPreferredLabelFinishedByUS3:
    """T022 — FR-006: a concept with no preferred label in the vocabulary's
    default language is set aside under ``NO_PREFERRED_LABEL`` and named in
    the report, and the rest of the vocabulary imports. Built at T009
    (decisions.md D17) because FR-006 states it in the same sentence as
    concept creation itself; D17 left it deliberately minimal and named this
    task as where it is finished. Nothing about the shape D17 chose disagrees
    with what US-3 built on top of it, so "finished" here means acceptance
    coverage proving the rest of the vocabulary imports *with* its own US-3
    content (labels, in this fixture) alongside the set-aside concept, not a
    production change."""

    def test_the_concept_with_no_default_language_label_is_set_aside_and_named(self, db):
        report = import_skos(FIXTURES / "no_default_language_label.ttl")
        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.NO_PREFERRED_LABEL]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/quarry/c"
        assert entries[0].params["language"] == "en"
        assert not Concept.objects.filter(static_uri="http://example.org/quarry/c").exists()

    def test_the_rest_of_the_vocabulary_imports_with_its_own_content_intact(self, db):
        import_skos(FIXTURES / "no_default_language_label.ttl")
        assert Concept.objects.filter(scheme__static_uri="http://example.org/quarry/").count() == 2
        b = Concept.objects.get(static_uri="http://example.org/quarry/b")
        assert b.label == "B"
        assert b.alt_labels("en") == ["B-alt"]


class TestBroaderAndNarrowerRelations:
    """T023 — FR-010/research.md R4: ``skos:broader`` and ``skos:narrower`` both
    land as the single ``ConceptRelation`` row the models define, ``source`` the
    narrower end and ``target`` the broader end, whichever direction the file
    states it from. Both directions stated for the same pair still produce
    exactly one row, never two."""

    def test_a_narrower_triple_lands_with_the_ends_the_right_way_round(self, db):
        # rocks.ttl's igneous states "skos:narrower basalt" — igneous is the
        # broader end, basalt the narrower one, so the canonical row must read
        # source=basalt, target=igneous, even though the file names igneous first.
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        basalt = Concept.objects.get(static_uri="http://example.org/rocks/basalt")
        assert list(basalt.broader()) == [igneous]
        assert basalt in igneous.narrower()
        assert ConceptRelation.objects.get(source=basalt, target=igneous, kind=ConceptRelation.Kind.BROADER)

    def test_a_broader_triple_lands_with_the_ends_the_right_way_round(self, db):
        # rocks.ttl's granite states "skos:broader igneous" directly — granite
        # is already the narrower end, so no swap is needed.
        import_skos(FIXTURES / "rocks.ttl")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        assert list(granite.broader()) == [igneous]
        assert ConceptRelation.objects.get(source=granite, target=igneous, kind=ConceptRelation.Kind.BROADER)

    def test_both_directions_of_one_pair_produce_exactly_one_row(self, db):
        # relation_both_directions.ttl states the parent/child pair from both
        # ends: parent's own "narrower child" and child's own "broader parent".
        import_skos(FIXTURES / "relation_both_directions.ttl")
        parent = Concept.objects.get(static_uri="http://example.org/hierarchy/parent")
        child = Concept.objects.get(static_uri="http://example.org/hierarchy/child")
        assert (
            ConceptRelation.objects.filter(source=child, target=parent, kind=ConceptRelation.Kind.BROADER).count() == 1
        )
        assert ConceptRelation.objects.filter(kind=ConceptRelation.Kind.BROADER).count() == 1

    def test_reimporting_the_identical_file_does_not_duplicate_the_relation(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        import_skos(FIXTURES / "rocks.ttl")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        igneous = Concept.objects.get(static_uri="http://example.org/rocks/igneous")
        assert (
            ConceptRelation.objects.filter(source=granite, target=igneous, kind=ConceptRelation.Kind.BROADER).count()
            == 1
        )


class TestRelatedRelations:
    """T024 — FR-010: ``skos:related`` is stored once as a symmetric
    association, including when the file states it from both concepts."""

    def test_a_related_pair_stated_once_is_stored_as_one_symmetric_relation(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        granite = Concept.objects.get(static_uri="http://example.org/rocks/granite")
        quartz = Concept.objects.get(static_uri="http://example.org/rocks/quartz")
        assert quartz in granite.related()
        assert granite in quartz.related()
        assert ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).count() == 1

    def test_both_directions_of_one_related_pair_produce_exactly_one_row(self, db):
        # relation_both_directions.ttl states east-related-west AND
        # west-related-east — both name the same unordered pair.
        import_skos(FIXTURES / "relation_both_directions.ttl")
        east = Concept.objects.get(static_uri="http://example.org/hierarchy/east")
        west = Concept.objects.get(static_uri="http://example.org/hierarchy/west")
        assert west in east.related()
        assert ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).count() == 1

    def test_reimporting_the_identical_file_does_not_duplicate_the_related_row(self, db):
        import_skos(FIXTURES / "rocks.ttl")
        import_skos(FIXTURES / "rocks.ttl")
        assert ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).count() == 1


class TestRelationEndpointsMissingOrKnown:
    """T025 — FR-011: a relationship end that is neither in the file nor
    already in the database is set aside and reported, naming both ends, and
    the run still succeeds; a relationship end already in the database from
    an earlier import is stored even when this file does not separately
    redeclare it. Builds no new production behaviour of its own — T023's
    ``_resolve_relation_concept``/``_import_relations`` (research.md R4,
    decisions.md D29) already has to make exactly this distinction to avoid
    crashing on an ordinary, partial published file, so this task's own job
    is acceptance coverage proving it, the same shape decisions.md D17/T022
    already established for this story's predecessor."""

    def test_an_end_already_in_the_database_from_an_earlier_import_is_stored(self, db):
        import_skos(FIXTURES / "relation_endpoints.ttl")
        alpha_pk = Concept.objects.get(static_uri="http://example.org/relendpoints/alpha").pk
        beta_pk = Concept.objects.get(static_uri="http://example.org/relendpoints/beta").pk

        import_skos(FIXTURES / "relation_endpoints_updated.ttl")

        assert ConceptRelation.objects.filter(
            source_id=alpha_pk, target_id=beta_pk, kind=ConceptRelation.Kind.BROADER
        ).exists()
        # beta is untouched — the file no longer mentions it as a concept at all.
        assert Concept.objects.filter(pk=beta_pk).exists()

    def test_an_end_neither_in_the_file_nor_the_database_is_set_aside_naming_both_ends(self, db):
        import_skos(FIXTURES / "relation_endpoints.ttl")

        report = import_skos(FIXTURES / "relation_endpoints_updated.ttl")

        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.MISSING_RELATION_END]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/relendpoints/alpha"
        assert entries[0].params["other"] == "http://example.org/relendpoints/ghost"
        assert not Concept.objects.filter(static_uri="http://example.org/relendpoints/ghost").exists()

    def test_the_run_succeeds_and_every_other_relationship_still_lands(self, db):
        import_skos(FIXTURES / "relation_endpoints.ttl")

        report = import_skos(FIXTURES / "relation_endpoints_updated.ttl")

        assert report.fatal == []
        alpha = Concept.objects.get(static_uri="http://example.org/relendpoints/alpha")
        beta = Concept.objects.get(static_uri="http://example.org/relendpoints/beta")
        assert beta in alpha.broader()

    def test_an_end_that_exists_but_in_a_different_vocabulary_is_set_aside_not_a_crash(self, db):
        # ConceptRelation only ever joins concepts of the same scheme
        # (models.py _reject_cross_scheme); asserting one across vocabularies
        # must not raise an uncaught ValidationError (decisions.md D29).
        import_skos(FIXTURES / "rocks.ttl")

        report = import_skos(FIXTURES / "relation_cross_scheme_target.ttl")

        assert report.fatal == []
        outsider = Concept.objects.get(static_uri="http://example.org/outsiders/outsider")
        assert list(outsider.broader()) == []
        entries = [entry for entry in report.set_aside if entry.reason is SetAsideReason.MISSING_RELATION_END]
        assert len(entries) == 1
        assert entries[0].subject == "http://example.org/outsiders/outsider"
        assert entries[0].params["other"] == "http://example.org/rocks/granite"


class TestFixtureCorpus:
    """T005 — the published-vocabulary fixtures are discoverable and parse (FR-018, SC-016).

    The suite's own fixture set, not built inline: one small vocabulary ("Rock
    types") in each of the three supported serializations, an edited copy for the
    re-import scenarios, and the malformed documents the fatal paths (D3, FR-004)
    need. `rdflib` is a test-only tool here (T005 is Phase 0 — the reader that
    makes it a genuine runtime dependency lands at T006, decisions.md D12); every
    fixture is exercised the same way a real import would read it.
    """

    def test_the_fixture_directory_is_not_empty(self):
        # Guards the discovery above: an empty or moved directory would otherwise
        # parametrize to nothing and report as a clean pass.
        assert len(ALL_FIXTURES) >= len(BASE_SERIALIZATIONS)

    @pytest.mark.parametrize("filename,fmt", ALL_FIXTURES)
    def test_every_fixture_is_discoverable_and_parses(self, filename, fmt):
        path = FIXTURES / filename
        assert path.is_file(), f"{filename} is not discoverable under tests/fixtures/skos/"
        graph = rdflib.Graph()
        graph.parse(path, format=fmt)
        assert len(graph) > 0, f"{filename} parsed to an empty graph"

    @pytest.mark.parametrize("filename,fmt", BASE_SERIALIZATIONS)
    def test_base_vocabulary_declares_the_scheme_and_its_top_concepts(self, filename, fmt):
        graph = rdflib.Graph()
        graph.parse(FIXTURES / filename, format=fmt)
        assert (ROCKS_SCHEME_URI, rdflib.RDF.type, SKOS.ConceptScheme) in graph
        top_concepts = set(graph.objects(ROCKS_SCHEME_URI, SKOS.hasTopConcept))
        assert top_concepts == {
            rdflib.URIRef("http://example.org/rocks/igneous"),
            rdflib.URIRef("http://example.org/rocks/sedimentary"),
        }

    @pytest.mark.parametrize("filename,fmt", BASE_SERIALIZATIONS)
    def test_base_vocabulary_carries_multilingual_labels_notes_hierarchy_related_and_collections(self, filename, fmt):
        graph = rdflib.Graph()
        graph.parse(FIXTURES / filename, format=fmt)
        granite = rdflib.URIRef("http://example.org/rocks/granite")
        quartz = rdflib.URIRef("http://example.org/rocks/quartz")
        igneous = rdflib.URIRef("http://example.org/rocks/igneous")

        # Multilingual preferred labels (en/de/fr — the test settings' configured languages).
        granite_labels = {(o.language, str(o)) for o in graph.objects(granite, SKOS.prefLabel)}
        assert granite_labels == {("en", "Granite"), ("de", "Granit"), ("fr", "Granite")}

        # Notes of several kinds, spread across concepts.
        assert (igneous, SKOS.definition, None) in graph
        assert (granite, SKOS.scopeNote, None) in graph
        assert (quartz, SKOS.historyNote, None) in graph
        assert (quartz, SKOS.changeNote, None) in graph
        assert (quartz, SKOS.note, None) in graph

        # A broader/narrower hierarchy and a related pair.
        assert (granite, SKOS.broader, igneous) in graph
        assert (granite, SKOS.related, quartz) in graph

        # An unordered and an ordered collection.
        unordered = rdflib.URIRef("http://example.org/rocks/collection/silica-bearing")
        ordered = rdflib.URIRef("http://example.org/rocks/collection/example-sequence")
        assert (unordered, rdflib.RDF.type, SKOS.Collection) in graph
        assert set(graph.objects(unordered, SKOS.member)) == {granite, quartz}
        assert (ordered, rdflib.RDF.type, SKOS.OrderedCollection) in graph
        member_list = graph.value(ordered, SKOS.memberList)
        assert list(graph.items(member_list)) == [
            rdflib.URIRef("http://example.org/rocks/basalt"),
            granite,
            rdflib.URIRef("http://example.org/rocks/sedimentary"),
        ]

    def test_the_three_base_serializations_are_isomorphic(self):
        from rdflib.compare import isomorphic

        graphs = []
        for filename, fmt in BASE_SERIALIZATIONS:
            graph = rdflib.Graph()
            graph.parse(FIXTURES / filename, format=fmt)
            graphs.append(graph)
        assert isomorphic(graphs[0], graphs[1]), "rocks.ttl and rocks.rdf are not isomorphic"
        assert isomorphic(graphs[0], graphs[2]), "rocks.ttl and rocks.jsonld are not isomorphic"

    def test_updated_fixture_carries_the_four_re_import_edits(self):
        graph = rdflib.Graph()
        graph.parse(FIXTURES / "rocks_updated.ttl", format="turtle")
        granite = rdflib.URIRef("http://example.org/rocks/granite")
        quartz = rdflib.URIRef("http://example.org/rocks/quartz")

        # 1. A corrected preferred label.
        assert (granite, SKOS.prefLabel, rdflib.Literal("Granite (revised)", lang="en")) in graph
        assert (granite, SKOS.prefLabel, rdflib.Literal("Granite", lang="en")) not in graph

        # 2. A removed alternative label.
        assert (granite, SKOS.altLabel, None) not in graph

        # 3. A concept dropped from the file entirely (taking its related edge and
        # its collection membership with it) — still present in an already-imported
        # database, so the re-import scenario names it as absent from this source.
        assert (quartz, rdflib.RDF.type, SKOS.Concept) not in graph
        assert (granite, SKOS.related, quartz) not in graph
        unordered = rdflib.URIRef("http://example.org/rocks/collection/silica-bearing")
        assert quartz not in set(graph.objects(unordered, SKOS.member))

        # 4. A changed collection order.
        ordered = rdflib.URIRef("http://example.org/rocks/collection/example-sequence")
        member_list = graph.value(ordered, SKOS.memberList)
        assert list(graph.items(member_list)) == [
            granite,
            rdflib.URIRef("http://example.org/rocks/sedimentary"),
            rdflib.URIRef("http://example.org/rocks/basalt"),
        ]

    def test_blank_node_concept_fixture_has_no_uri_identity(self):
        graph = rdflib.Graph()
        graph.parse(FIXTURES / "blank_node_concept.ttl", format="turtle")
        concepts = list(graph.subjects(rdflib.RDF.type, SKOS.Concept))
        assert len(concepts) == 1
        assert isinstance(concepts[0], rdflib.BNode), "the fixture's concept must be a blank node, not a URI"

    def test_blank_node_collection_fixture_has_no_uri_identity(self):
        graph = rdflib.Graph()
        graph.parse(FIXTURES / "blank_node_collection.ttl", format="turtle")
        collections = list(graph.subjects(rdflib.RDF.type, SKOS.Collection))
        assert len(collections) == 1
        assert isinstance(collections[0], rdflib.BNode), "the fixture's collection must be a blank node, not a URI"

    def test_refused_uri_scheme_fixture_uses_a_disallowed_scheme(self):
        from controlled_vocabularies.conf import DEFAULT_ALLOWED_URI_SCHEMES

        graph = rdflib.Graph()
        graph.parse(FIXTURES / "refused_uri_scheme.ttl", format="turtle")
        concepts = list(graph.subjects(rdflib.RDF.type, SKOS.Concept))
        assert len(concepts) == 1
        scheme = str(concepts[0]).split(":", 1)[0]
        assert scheme not in DEFAULT_ALLOWED_URI_SCHEMES, (
            f"fixture's concept scheme '{scheme}' must be outside the default allowlist"
        )


class TestExchangePackage:
    """T002 — the ``controlled_vocabularies.exchange`` package exists and is
    importable. The package is the module tree the import feature lands in
    (plan.md Project Structure); this only asserts the scaffold itself is in
    place. Homed here rather than in a file of its own because the package's
    own surface — ``import_skos`` and its exceptions — is exercised by this
    module more than any other in ``exchange``.
    """

    def test_package_is_importable(self):
        assert exchange is not None

    def test_package_has_a_module_docstring(self):
        # A public package gets documented (Article VI); this catches an
        # accidentally-empty __init__.py before anything is re-exported from it.
        assert exchange.__doc__, "controlled_vocabularies.exchange has no module docstring"
