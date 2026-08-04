"""Reading a published SKOS file into records (FS-006).

The RDF boundary: a file becomes an ``rdflib`` graph, the graph is walked into
the models R1 built, and the run returns a structured :class:`ImportReport` of
what it did. Models stay the source of truth; RDF is read only at this
boundary and never stored as a graph (Article X).

:func:`import_skos` (``skos.py``) is the package's public entry point; the
rest of this module's re-exports are the :class:`ImportReport` it returns and
the vocabularies and exceptions that describe what went into it. The whole
exception hierarchy lives in ``exceptions.py``.

Callers catch the pair ``(SkosImportError, SkosImportFailed)``:
:class:`SkosImportError` for a file that could not be turned into usable SKOS
at all, :class:`SkosImportFailed` for one that parsed and had its content
refused. :class:`UnsafeRdfXmlError`/:class:`UnsafeJsonLdError` are
:class:`SkosImportError` subclasses (review fix 19, decisions.md D52) so that
pair also catches a file the pre-flight safety scan refuses, without a caller
needing to know the scan exists or to import a third exception type.
"""

from controlled_vocabularies.exchange.exceptions import (
    SkosImportError,
    SkosImportFailed,
    UnsafeJsonLdError,
    UnsafeRdfXmlError,
)
from controlled_vocabularies.exchange.report import (
    FatalFinding,
    FatalReason,
    ImportReport,
    NormalizedEntry,
    NormalizedReason,
    SetAsideEntry,
    SetAsideReason,
)
from controlled_vocabularies.exchange.skos import import_skos

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
