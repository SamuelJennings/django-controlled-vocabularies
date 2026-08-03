"""Reading a published SKOS file into records (FS-006).

The RDF boundary: a file becomes an ``rdflib`` graph, the graph is walked into
the models R1 built, and the run returns a structured :class:`ImportReport` of
what it did. Models stay the source of truth; RDF is read only at this
boundary and never stored as a graph (Article X).

The reader itself (``skos.py``) and its public ``import_skos()`` entry point
are a later story (tasks.md Phase US-1); this module grows its re-exports one
task at a time, each landing with the test that covers it.
"""

from controlled_vocabularies.io.report import ImportReport, SetAsideEntry, SetAsideReason

__all__ = ["ImportReport", "SetAsideEntry", "SetAsideReason"]
