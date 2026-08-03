"""Reading a published SKOS file into records (FS-006, tasks.md Phase US-1).

The RDF boundary: a file becomes an ``rdflib`` graph (:func:`_read_graph`,
T006), the graph is walked into the models R1 built, and the run returns a
structured :class:`~controlled_vocabularies.exchange.report.ImportReport` of
what it did. Models stay the source of truth; RDF is read only at this
boundary and never stored as a graph (Article X).

Grows one task at a time: this module currently covers reading a file into a
graph (T006). Later tasks in the same phase add vocabulary matching, concept
creation, slugging, and fatal-finding collection on top of it.
"""

from __future__ import annotations

from pathlib import Path

import rdflib
import rdflib.util
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.safety import scan_rdf_xml

#: The three serializations FR-002 requires this feature to read. Anything
#: else — an unrecognised extension with no explicit ``format``, or an
#: explicit ``format`` naming a serialization outside this set — fails the
#: run rather than being handed to rdflib on the chance it understands it:
#: FR-002 names exactly these three, not "whatever rdflib happens to parse".
_SUPPORTED_FORMATS = frozenset({"turtle", "xml", "json-ld"})


class SkosImportError(ValidationError):
    """Raised when a candidate file cannot be read as SKOS at all (FR-002).

    Covers a missing file, a serialization that cannot be determined or is
    not one of the three this feature reads, and a file that fails to parse
    as the serialization it is read as. A :class:`~django.core.exceptions.ValidationError`
    subclass so it carries the same translatable, named-placeholder message
    shape as the rest of the package (Article XII).
    """


def _read_graph(file: str | Path, *, serialization: str | None = None) -> rdflib.Graph:
    """Read ``file`` into an ``rdflib.Graph`` (research.md R1, FR-002).

    ``serialization`` is the caller-stated format ("turtle", "xml", or
    "json-ld"); when omitted it is guessed from the file's extension
    (``rdflib.util.guess_format``), the ordinary case for a curator-supplied
    file. Either way the result must be one of :data:`_SUPPORTED_FORMATS`, or
    the run fails with a translatable message naming the file (FR-002's
    "cannot be determined" half).

    RDF/XML input is scanned by :func:`~controlled_vocabularies.exchange.safety.scan_rdf_xml`
    before rdflib ever sees it (research.md R3, decisions.md D9) — the file is
    read from ``path`` a second time by rdflib itself afterwards, deliberately,
    rather than parsed from the bytes already in memory: rdflib's own
    file-based parse establishes its base URI from the file's own location,
    the behaviour decisions.md D13 measured and future fatal-path fixtures
    may come to depend on, and passing pre-read ``data=`` bytes instead would
    silently change that base.

    A file that cannot be found, or one that fails to parse as its
    serialization, raises :class:`SkosImportError` (FR-002's "cannot be
    read" half) rather than letting rdflib's own exception — untranslated,
    shaped for a developer — escape to the caller.
    """
    path = Path(file)
    if not path.is_file():
        raise SkosImportError(
            _("'%(file)s' could not be found."),
            params={"file": str(path)},
            code="skos_file_not_found",
        )
    resolved_format = serialization or rdflib.util.guess_format(str(path))
    if resolved_format not in _SUPPORTED_FORMATS:
        raise SkosImportError(
            _("'%(file)s' is not in a serialization this application reads (Turtle, RDF/XML, or JSON-LD)."),
            params={"file": str(path)},
            code="skos_format_unsupported",
        )
    if resolved_format == "xml":
        # Pre-flight only — the bytes read here are not what gets parsed
        # (see the base-URI note above), so a second, larger read is a
        # deliberate, small cost on RDF/XML input only.
        scan_rdf_xml(path.read_bytes())
    graph = rdflib.Graph()
    try:
        graph.parse(str(path), format=resolved_format)
    except Exception as exc:
        raise SkosImportError(
            _("'%(file)s' could not be parsed as %(format)s: %(error)s"),
            params={"file": str(path), "format": resolved_format, "error": str(exc)},
            code="skos_parse_failed",
        ) from exc
    return graph
