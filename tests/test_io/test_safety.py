"""T004 — the pre-flight safety scan of untrusted RDF/XML (research.md R3, decisions.md D9).

`rdflib`'s RDF/XML parser calls `xml.sax.make_parser()` itself, so a defused
parser cannot be substituted directly; `scan_rdf_xml` is the pre-flight check
that stands in front of it. This reinstates the actual measured defect — the
eight-level nested-entity bomb from research.md R3 — as the test input, rather
than a mock, so the control is proven against the real one.
"""

from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.utils.functional import Promise

from controlled_vocabularies.io.safety import UnsafeRdfXmlError, scan_rdf_xml

FIXTURES = Path(__file__).parent.parent / "fixtures" / "security"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_the_measured_entity_bomb_is_refused_with_a_translatable_message():
    # research.md R3: eight nested entity declarations, each repeating the previous
    # one five times, expand to a single 781,250-character literal from ~500 bytes.
    # This is that exact document, not a stand-in.
    with pytest.raises(UnsafeRdfXmlError) as excinfo:
        scan_rdf_xml(_read("entity_bomb.rdf"))
    err = excinfo.value
    assert isinstance(err, ValidationError)
    assert isinstance(err.message, Promise), "entity-bomb refusal message is not lazily translatable"
    assert "%(name)s" in str(err.message), "entity-bomb refusal message lacks a named %(name)s placeholder"
    assert err.params == {"name": "e0"}
    assert "e0" in err.messages[0]
    assert err.code == "rdf_xml_entities_forbidden"
    assert isinstance(err.__cause__, Exception), "the underlying defusedxml exception must be chained"


def test_an_ordinary_rdf_xml_document_passes_untouched():
    # No DTD, no entities: scan_rdf_xml is a no-op and raises nothing.
    assert scan_rdf_xml(_read("ordinary.rdf")) is None


def test_a_document_declaring_an_external_entity_is_refused_not_silently_emptied():
    # research.md R3's own canary probe: a document referencing a file on disk via
    # a declared external entity. Before this scan it parsed cleanly with the
    # reference resolving to an empty string; now declaring the entity at all is
    # enough to refuse the document outright.
    with pytest.raises(UnsafeRdfXmlError) as excinfo:
        scan_rdf_xml(_read("external_entity.rdf"))
    err = excinfo.value
    assert isinstance(err.message, Promise), "external-entity refusal message is not lazily translatable"
    assert "%(name)s" in str(err.message)
    assert err.params == {"name": "xxe"}
    assert err.code == "rdf_xml_entities_forbidden"


def test_a_document_referencing_an_external_dtd_subset_is_refused():
    # A distinct route to the same untrusted-fetch problem: no entity is declared,
    # but the doctype itself points at an external resource.
    with pytest.raises(UnsafeRdfXmlError) as excinfo:
        scan_rdf_xml(_read("external_dtd.rdf"))
    err = excinfo.value
    assert isinstance(err.message, Promise), "external-DTD refusal message is not lazily translatable"
    assert "%(system_id)s" in str(err.message)
    assert err.params == {"system_id": "http://example.org/nonexistent.dtd"}
    assert "http://example.org/nonexistent.dtd" in err.messages[0]
    assert err.code == "rdf_xml_external_reference_forbidden"
