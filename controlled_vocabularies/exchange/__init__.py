"""Reading a published SKOS file into records (FS-006).

The RDF boundary: a file becomes an ``rdflib`` graph, the graph is walked into
the models R1 built, and the run returns a structured :class:`ImportReport` of
what it did. Models stay the source of truth; RDF is read only at this
boundary and never stored as a graph (Article X).

:func:`import_skos` (``skos.py``) is the package's public entry point; the
rest of this module's re-exports are the :class:`ImportReport` it returns and
the vocabularies and exceptions that describe what went into it.

:class:`UnsafeRdfXmlError`/:class:`UnsafeJsonLdError` (review fix 19,
decisions.md D52) are exported here, and are :class:`SkosImportError`
subclasses, precisely so a caller that only catches this package's
documented ``(SkosImportError, SkosImportFailed)`` pair still catches a
file the pre-flight safety scan refuses — without needing to know that scan
exists, or to import a third, safety-specific exception type separately.
"""

from controlled_vocabularies.exchange.report import (
    FatalFinding,
    FatalReason,
    ImportReport,
    NormalizedEntry,
    NormalizedReason,
    SetAsideEntry,
    SetAsideReason,
)
from controlled_vocabularies.exchange.safety import UnsafeJsonLdError, UnsafeRdfXmlError
from controlled_vocabularies.exchange.skos import SkosImportError, SkosImportFailed, import_skos

__all__ = [
    "FatalFinding",
    "FatalReason",
    "ImportReport",
    "NormalizedEntry",
    "NormalizedReason",
    "SetAsideEntry",
    "SetAsideReason",
    "SkosImportError",
    "SkosImportFailed",
    "UnsafeJsonLdError",
    "UnsafeRdfXmlError",
    "import_skos",
]
