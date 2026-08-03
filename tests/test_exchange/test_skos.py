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

from controlled_vocabularies.exchange.report import FatalReason
from controlled_vocabularies.exchange.safety import UnsafeRdfXmlError
from controlled_vocabularies.exchange.skos import SkosImportError, SkosImportFailed, _read_graph, import_skos
from controlled_vocabularies.models import ConceptScheme
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
    one is being imported. The concept walk lands in T009; until then a
    successful call here writes at most the one ``ConceptScheme`` row."""

    def test_a_declared_vocabulary_is_created_when_not_already_held(self, db):
        report = import_skos(FIXTURES / "rocks.ttl")
        scheme = ConceptScheme.objects.get(static_uri=ROCKS_URI)
        assert scheme.name == "Rock types"
        assert report.created == [ROCKS_URI]
        assert report.updated == []
        assert report.fatal == []

    def test_a_declared_vocabulary_already_held_is_updated_not_duplicated(self, db):
        existing = ConceptSchemeFactory(name="Old name", static_uri=ROCKS_URI)
        report = import_skos(FIXTURES / "rocks.ttl")
        existing.refresh_from_db()
        assert existing.name == "Rock types"
        assert ConceptScheme.objects.filter(static_uri=ROCKS_URI).count() == 1
        assert report.updated == [ROCKS_URI]
        assert report.created == []

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
