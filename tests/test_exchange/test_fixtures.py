"""T005 — the published-vocabulary fixtures are discoverable and parse (FR-018, SC-016).

The suite's own fixture set, not built inline: one small vocabulary ("Rock
types") in each of the three supported serializations, an edited copy for the
re-import scenarios, and the malformed documents the fatal paths (D3, FR-004)
need. `rdflib` is a test-only tool here (T005 is Phase 0 — the reader that
makes it a genuine runtime dependency lands at T006, decisions.md D12); every
fixture is exercised the same way a real import would read it.
"""

from pathlib import Path

import pytest
import rdflib

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skos"

ROCKS_URI = rdflib.URIRef("http://example.org/rocks/")
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

# (filename, rdflib format) for the base vocabulary in its three serializations.
BASE_SERIALIZATIONS = [
    ("rocks.ttl", "turtle"),
    ("rocks.rdf", "xml"),
    ("rocks.jsonld", "json-ld"),
]

# Every fixture this task ships, whatever its purpose, must at least be present
# and parse as RDF (fatal-path fixtures are semantically invalid for import,
# never syntactically invalid RDF — that distinction is exactly what makes them
# useful fatal-path material rather than parser-crash material).
ALL_FIXTURES = [
    *BASE_SERIALIZATIONS,
    ("rocks_updated.ttl", "turtle"),
    ("blank_node_concept.ttl", "turtle"),
    ("blank_node_collection.ttl", "turtle"),
    ("refused_uri_scheme.ttl", "turtle"),
]


@pytest.mark.parametrize("filename,fmt", ALL_FIXTURES)
def test_every_fixture_is_discoverable_and_parses(filename, fmt):
    path = FIXTURES / filename
    assert path.is_file(), f"{filename} is not discoverable under tests/fixtures/skos/"
    graph = rdflib.Graph()
    graph.parse(path, format=fmt)
    assert len(graph) > 0, f"{filename} parsed to an empty graph"


@pytest.mark.parametrize("filename,fmt", BASE_SERIALIZATIONS)
def test_base_vocabulary_declares_the_scheme_and_its_top_concepts(filename, fmt):
    graph = rdflib.Graph()
    graph.parse(FIXTURES / filename, format=fmt)
    assert (ROCKS_URI, rdflib.RDF.type, SKOS.ConceptScheme) in graph
    top_concepts = set(graph.objects(ROCKS_URI, SKOS.hasTopConcept))
    assert top_concepts == {
        rdflib.URIRef("http://example.org/rocks/igneous"),
        rdflib.URIRef("http://example.org/rocks/sedimentary"),
    }


@pytest.mark.parametrize("filename,fmt", BASE_SERIALIZATIONS)
def test_base_vocabulary_carries_multilingual_labels_notes_hierarchy_related_and_collections(filename, fmt):
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


def test_the_three_base_serializations_are_isomorphic():
    from rdflib.compare import isomorphic

    graphs = []
    for filename, fmt in BASE_SERIALIZATIONS:
        graph = rdflib.Graph()
        graph.parse(FIXTURES / filename, format=fmt)
        graphs.append(graph)
    assert isomorphic(graphs[0], graphs[1]), "rocks.ttl and rocks.rdf are not isomorphic"
    assert isomorphic(graphs[0], graphs[2]), "rocks.ttl and rocks.jsonld are not isomorphic"


def test_updated_fixture_carries_the_four_re_import_edits():
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


def test_blank_node_concept_fixture_has_no_uri_identity():
    graph = rdflib.Graph()
    graph.parse(FIXTURES / "blank_node_concept.ttl", format="turtle")
    concepts = list(graph.subjects(rdflib.RDF.type, SKOS.Concept))
    assert len(concepts) == 1
    assert isinstance(concepts[0], rdflib.BNode), "the fixture's concept must be a blank node, not a URI"


def test_blank_node_collection_fixture_has_no_uri_identity():
    graph = rdflib.Graph()
    graph.parse(FIXTURES / "blank_node_collection.ttl", format="turtle")
    collections = list(graph.subjects(rdflib.RDF.type, SKOS.Collection))
    assert len(collections) == 1
    assert isinstance(collections[0], rdflib.BNode), "the fixture's collection must be a blank node, not a URI"


def test_refused_uri_scheme_fixture_uses_a_disallowed_scheme():
    from controlled_vocabularies.conf import DEFAULT_ALLOWED_URI_SCHEMES

    graph = rdflib.Graph()
    graph.parse(FIXTURES / "refused_uri_scheme.ttl", format="turtle")
    concepts = list(graph.subjects(rdflib.RDF.type, SKOS.Concept))
    assert len(concepts) == 1
    scheme = str(concepts[0]).split(":", 1)[0]
    assert scheme not in DEFAULT_ALLOWED_URI_SCHEMES, (
        f"fixture's concept scheme '{scheme}' must be outside the default allowlist"
    )
