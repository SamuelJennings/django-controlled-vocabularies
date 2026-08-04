"""SKOS predicate -> model mapping (research.md R4).

Fixed by what R1's models already define — no new modelling, just naming the
correspondence ``skos.py`` walks against. This grows one predicate at a time as
each story in ``tasks.md`` needs it, rather than being populated up front with
entries nothing yet reads (Article II — no speculative table). User Story 1
needs only the namespace itself, plus the identity and scheme-membership
predicates it reads directly (``skos:prefLabel``, ``skos:inScheme``,
``skos:topConceptOf``, ``skos:hasTopConcept``), all reachable as plain
attributes of :data:`SKOS` without a lookup table. Labels, notes, relations,
and collections are named here once their owning story (US-3/4/5) adds the
code that reads them.

User Story 2 adds :data:`DCTERMS` for exactly one predicate,
``dcterms:description`` — SKOS defines no description predicate for a
``skos:ConceptScheme``, so a vocabulary's description is read from the same
Dublin Core term CONTEXT.md already names as the import alias for a concept's
own ``definition`` (decisions.md D21). ``rdflib.namespace.DCTERMS`` is a
built-in namespace object, so nothing new is declared here beyond importing it.

User Story 3 (tasks.md T018/T019/T021) adds the label, note, and mapping
predicate tables below, exactly the growth this module's docstring already
anticipated.
"""

from __future__ import annotations

import rdflib
from rdflib.namespace import DCTERMS

from controlled_vocabularies.models import ConceptLabel, ConceptNote

#: The SKOS namespace every predicate and class this package reads belongs to.
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

#: SKOS label predicate -> :class:`~controlled_vocabularies.models.ConceptLabel.Kind`
#: (T018, FR-008). ``skos:prefLabel`` in the vocabulary's effective default
#: language is not looked up through this table at all — that value is
#: ``Concept.label`` itself (T009), and a ``ConceptLabel`` row would duplicate
#: the identity anchor, which ``ConceptLabel.clean()`` refuses.
LABEL_PREDICATES: dict[rdflib.URIRef, str] = {
    SKOS.prefLabel: ConceptLabel.Kind.PREFERRED,
    SKOS.altLabel: ConceptLabel.Kind.ALTERNATIVE,
    SKOS.hiddenLabel: ConceptLabel.Kind.HIDDEN,
}

#: SKOS documentary-note predicate -> :class:`~controlled_vocabularies.models.ConceptNote.Kind`
#: (T019, FR-009). ``dcterms:description`` is a *separate*, concept-level
#: alias for :attr:`ConceptNote.Kind.DEFINITION` (CONTEXT.md, decisions.md
#: D21/D24), read only where the file carries no ``skos:definition`` of its
#: own in that language, and reported as a normalisation rather than applied
#: silently (FR-009) — so it is handled in ``skos.py`` directly rather than
#: listed here alongside the predicates that need no such reporting.
NOTE_PREDICATES: dict[rdflib.URIRef, str] = {
    SKOS.definition: ConceptNote.Kind.DEFINITION,
    SKOS.scopeNote: ConceptNote.Kind.SCOPE,
    SKOS.example: ConceptNote.Kind.EXAMPLE,
    SKOS.editorialNote: ConceptNote.Kind.EDITORIAL,
    SKOS.historyNote: ConceptNote.Kind.HISTORY,
    SKOS.changeNote: ConceptNote.Kind.CHANGE,
    SKOS.note: ConceptNote.Kind.NOTE,
}

#: SKOS mapping predicates (T021, FR-014) — cross-vocabulary links to concepts
#: in *other* vocabularies. CONTEXT.md is explicit that these "live in the
#: JSON document, not the relation M2M", and the JSON document is exactly the
#: escrow store decisions.md D1 defers past this feature, so a mapping has no
#: model to write to yet: it is set aside and reported (FR-014) under its own
#: readable CURIE rather than a raw URI.
MAPPING_PREDICATES: dict[rdflib.URIRef, str] = {
    SKOS.exactMatch: "skos:exactMatch",
    SKOS.closeMatch: "skos:closeMatch",
    SKOS.broadMatch: "skos:broadMatch",
    SKOS.narrowMatch: "skos:narrowMatch",
    SKOS.relatedMatch: "skos:relatedMatch",
    SKOS.mappingRelation: "skos:mappingRelation",
}

#: Dublin Core Terms — currently used only for ``DCTERMS.description`` (D21).
__all__ = ["DCTERMS", "LABEL_PREDICATES", "MAPPING_PREDICATES", "NOTE_PREDICATES", "SKOS"]
