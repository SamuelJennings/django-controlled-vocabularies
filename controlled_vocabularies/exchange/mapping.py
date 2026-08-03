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
"""

from __future__ import annotations

import rdflib

#: The SKOS namespace every predicate and class this package reads belongs to.
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
