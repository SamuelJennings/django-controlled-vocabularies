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

from controlled_vocabularies.exchange.report import FatalReason, SetAsideReason
from controlled_vocabularies.exchange.safety import UnsafeRdfXmlError
from controlled_vocabularies.exchange.skos import SkosImportError, SkosImportFailed, _read_graph, import_skos
from controlled_vocabularies.models import Concept, ConceptRelation, ConceptScheme
from tests.factories import ConceptFactory, ConceptSchemeFactory

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skos"
SECURITY_FIXTURES = Path(__file__).parent.parent / "fixtures" / "security"

SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
ROCKS_URI = "http://example.org/rocks/"


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
