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
from controlled_vocabularies.models import Concept, ConceptScheme
from tests.factories import ConceptSchemeFactory

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
