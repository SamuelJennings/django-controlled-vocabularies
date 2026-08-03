"""Pre-flight safety scan of untrusted RDF/XML (research.md R3, decisions.md D9).

Article V names imported RDF as untrusted input. Measured against `rdflib` 7.6's
RDF/XML parser: external entity references do not resolve (a canary file
referenced this way parses to an empty string, nothing leaked), but internal
entity expansion is wide open — eight nested entity declarations in a ~500-byte
document expand to a single 781,250-character literal, unbounded in the
document's own size (research.md R3). That is a denial-of-service route into any
deployment that lets a curator supply a file.

`rdflib.plugins.parsers.rdfxml.create_parser` calls `xml.sax.make_parser()`
itself and accepts no parser argument, so a defused parser cannot be substituted
directly. The fix is a pre-flight scan: the raw bytes are run through
`defusedxml.sax` with a do-nothing content handler first, and only reach
`rdflib` if that returns cleanly (decisions.md D9).
"""

from __future__ import annotations

from xml.sax import ContentHandler

import defusedxml.sax
from defusedxml.common import EntitiesForbidden, ExternalReferenceForbidden
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UnsafeRdfXmlError(ValidationError):
    """Raised when a candidate RDF/XML document fails the pre-flight safety scan.

    A :class:`~django.core.exceptions.ValidationError` subclass so it carries the
    same translatable-message-plus-named-params shape as the rest of the package
    (Article XII); the underlying `defusedxml` exception is chained via
    ``__cause__`` for developer diagnostics, which are exempt from translation.
    """


class _DoNothingContentHandler(ContentHandler):
    """A content handler with no behaviour.

    The scan exists only to let `defusedxml`'s guards fire during parsing; it
    never needs to extract or hold anything from the document.
    """


def scan_rdf_xml(data: bytes) -> None:
    """Refuse ``data`` before it reaches rdflib if it is unsafe RDF/XML (research.md R3).

    Runs ``data`` through `defusedxml.sax` with a do-nothing handler, which
    forbids entity declarations and external references by default (an ordinary
    RDF/XML document — one with no DTD at all — is unaffected). Raises
    :class:`UnsafeRdfXmlError`, naming the cause with a named placeholder
    (Article XII), for a document that declares any entity (the internal
    expansion route, and — since declaring one is enough — the external-entity
    route the same construct carries) or that references an external DTD
    subset. Returns ``None`` for a document that triggers neither.

    This does not check that ``data`` is well-formed or valid RDF/XML — only
    that it is safe to hand to `rdflib`, which reports its own parse errors for
    a document that fails on those grounds instead.
    """
    try:
        defusedxml.sax.parseString(data, _DoNothingContentHandler())
    except EntitiesForbidden as exc:
        raise UnsafeRdfXmlError(
            _(
                "This RDF/XML document was refused before parsing: it declares an entity "
                "('%(name)s') that could expand into a memory-exhaustion attack or resolve "
                "an external reference."
            ),
            params={"name": exc.name or ""},
            code="rdf_xml_entities_forbidden",
        ) from exc
    except ExternalReferenceForbidden as exc:
        raise UnsafeRdfXmlError(
            _(
                "This RDF/XML document was refused before parsing: it references an "
                "external resource ('%(system_id)s') that this application does not fetch."
            ),
            params={"system_id": exc.sysid or ""},
            code="rdf_xml_external_reference_forbidden",
        ) from exc
