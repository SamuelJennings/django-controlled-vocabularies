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
"""

from __future__ import annotations

import rdflib
from rdflib.namespace import DCTERMS

#: The SKOS namespace every predicate and class this package reads belongs to.
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

#: Dublin Core Terms — currently used only for ``DCTERMS.description`` (D21).
__all__ = ["DCTERMS", "SKOS"]
