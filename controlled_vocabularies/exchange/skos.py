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
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.mapping import SKOS
from controlled_vocabularies.exchange.report import FatalReason, ImportReport
from controlled_vocabularies.exchange.safety import scan_rdf_xml
from controlled_vocabularies.models import ConceptScheme, validate_static_uri

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


class SkosImportFailed(ValidationError):
    """Raised when a run collects one or more fatal findings (FR-004, decisions.md D3/D8).

    Carries the run's partial :class:`~controlled_vocabularies.exchange.report.ImportReport`
    (its :attr:`~controlled_vocabularies.exchange.report.ImportReport.fatal` bucket is what
    matters here) so a caller can see exactly what was wrong, even though the transaction
    this was raised inside has already rolled back everything the run wrote (T011,
    ``research.md`` R7 — the run is all-or-nothing, but the report still names every problem,
    per FR-004's "MUST fail the run and be named in the report").
    """

    def __init__(self, report: ImportReport) -> None:
        self.report = report
        super().__init__(
            _("The import was refused: %(count)s problem(s) were found. See the report for details."),
            params={"count": len(report.fatal)},
            code="skos_import_failed",
        )


class _FatalIdentity(Exception):
    """Internal signal that a node's identity is fatal (D3/FR-004); carries the finding to record."""

    def __init__(self, reason: FatalReason, subject: str, **params: str) -> None:
        self.reason = reason
        self.subject = subject
        self.params = params
        super().__init__(subject)


def _identify(node: rdflib.term.Node, *, hint: str | None = None) -> str:
    """Return ``node``'s usable identifier, or raise :class:`_FatalIdentity` (FR-004, D3).

    A blank node supplies no identifier that survives re-serialization
    (decisions.md D3) and is always fatal — the structural exception, an
    ordered collection's member list, never reaches this function since it is
    read as a list, not as a candidate record. A ``URIRef`` is checked
    through :func:`~controlled_vocabularies.models.validate_static_uri`, the
    same identity rule the models themselves enforce on a stored
    ``static_uri`` (research.md R6), so a scheme outside the configured
    allowlist is refused here exactly as it would be on save.

    ``hint`` — typically the node's own preferred label, when one could be
    read before the identity check ran — makes the fatal message point a
    curator at *something* recognisable in their file when the node itself
    has no URI to show; it falls back to the node's own (opaque, per-parse)
    string form when nothing better is available.
    """
    subject = hint or str(node)
    if isinstance(node, rdflib.BNode):
        raise _FatalIdentity(FatalReason.MISSING_IDENTITY, subject=subject)
    uri = str(node)
    try:
        validate_static_uri(uri)
    except ValidationError as exc:
        raise _FatalIdentity(FatalReason.REFUSED_IDENTITY, subject=uri) from exc
    return uri


def _first_literal(
    graph: rdflib.Graph,
    node: rdflib.term.Node,
    predicate: rdflib.URIRef,
    *,
    language: str | None = None,
) -> str | None:
    """The lexicographically-first literal value of ``predicate`` on ``node``, or ``None``.

    Deterministic rather than "whichever rdflib happens to yield first" — the
    graph's own iteration order is not something to depend on for a value
    that ends up in a stored record (T010's "no source of nondeterminism"
    concern applies here just as much as to slugs). ``language``, when given,
    restricts to literals tagged with that language.
    """
    values = sorted(
        str(literal)
        for literal in graph.objects(node, predicate)
        if language is None or getattr(literal, "language", None) == language
    )
    return values[0] if values else None


def _get_or_create_scheme(uri: str) -> ConceptScheme:
    """Return the :class:`ConceptScheme` matching ``uri``, or a new unsaved one (research.md R6)."""
    try:
        return ConceptScheme.objects.get_by_uri(uri)
    except ConceptScheme.DoesNotExist:
        return ConceptScheme(static_uri=uri)


def _configured_language_codes() -> set[str]:
    """The language codes the application is configured for (``settings.LANGUAGES``).

    A small, local duplicate of the identical one-liner in ``models.py``
    (which keeps its own copy private) rather than reaching into that
    module's internals — Article III's "prefer duplication over the wrong
    abstraction" applied to a single set-comprehension.
    """
    return {code for code, _label in settings.LANGUAGES}


def _label_languages(graph: rdflib.Graph, node: rdflib.term.Node, predicate: rdflib.URIRef) -> list[str]:
    """The language tags of ``predicate``'s literal values on ``node`` (empty-tag values excluded).

    A small typed narrowing point: ``graph.objects()`` yields the general
    ``rdflib.term.Node`` type, which has no ``.language`` attribute — only
    ``rdflib.Literal`` does. Isolating the ``isinstance`` check here once
    keeps the two callers below plain comprehensions.
    """
    return [
        literal.language
        for literal in graph.objects(node, predicate)
        if isinstance(literal, rdflib.Literal) and literal.language
    ]


def _determine_default_language(
    graph: rdflib.Graph,
    declared_node: rdflib.term.Node,
    concept_nodes: list[rdflib.term.Node],
) -> str:
    """The imported vocabulary's default language, per FR-005 (T008, decisions.md D4).

    Taken from the file where the file says: the language the vocabulary
    declares itself in — its own ``skos:prefLabel``, when tagged with
    exactly one language — else the language most of its concepts' own
    preferred labels use, counted across ``concept_nodes`` and tied deterministically by
    language code. Either way the resolved language must be one the site is
    configured for (``settings.LANGUAGES``); when neither is, this returns
    ``""``, which :attr:`ConceptScheme.default_language` already treats as
    "fall back to the site's own default" (``effective_default_language``) —
    the mechanism R1 built, reused rather than duplicated.
    """
    configured = _configured_language_codes()
    declared_languages = set(_label_languages(graph, declared_node, SKOS.prefLabel))
    if len(declared_languages) == 1:
        (declared_language,) = declared_languages
        if declared_language in configured:
            return declared_language

    counts: dict[str, int] = {}
    for node in concept_nodes:
        for language in _label_languages(graph, node, SKOS.prefLabel):
            counts[language] = counts.get(language, 0) + 1
    if counts:
        commonest = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        if commonest in configured:
            return commonest

    return ""


def _resolve_scheme(
    graph: rdflib.Graph,
    declared_node: rdflib.term.Node | None,
    concept_nodes: list[rdflib.term.Node],
    target: ConceptScheme | None,
    report: ImportReport,
    *,
    source_label: str,
) -> tuple[ConceptScheme | None, str | None]:
    """Resolve, create or update the vocabulary being imported into (FR-005, T007).

    The file is the authority for which vocabulary is being imported. When it
    declares none, a caller-named ``target`` is required (FR-005's "MUST fail
    ... unless the caller names the target"); when it declares one, a given
    ``target`` must agree with it (a mismatch is fatal and nothing is
    written). Matches an existing record via ``get_by_uri`` (research.md R6);
    otherwise a new one is created holding the file's identifier.

    ``source_label`` names the file itself, used as the fatal subject when
    there is no RDF node to identify (the file declares no vocabulary at
    all) — every other fatal subject below names an RDF term instead.

    Returns ``(scheme, declared_uri)`` on success — ``declared_uri`` is the
    URI concepts are checked against for "belongs to a different vocabulary"
    (T009) — or ``(None, None)`` when resolution itself is fatal, in which
    case ``report.fatal`` already carries why and the caller must not attempt
    to import any concepts.
    """
    if declared_node is None:
        if target is None:
            report.add_fatal(FatalReason.VOCABULARY_UNDETERMINED, subject=source_label)
            return None, None
        return target, target.uri

    hint = _first_literal(graph, declared_node, SKOS.prefLabel)
    try:
        declared_uri = _identify(declared_node, hint=hint)
    except _FatalIdentity as exc:
        report.add_fatal(exc.reason, exc.subject, **exc.params)
        return None, None

    if target is not None and target.uri != declared_uri:
        report.add_fatal(FatalReason.VOCABULARY_TARGET_MISMATCH, subject=declared_uri, target=target.uri)
        return None, None

    row = target if target is not None else _get_or_create_scheme(declared_uri)
    created = row.pk is None
    row.default_language = _determine_default_language(graph, declared_node, concept_nodes)
    name = _first_literal(graph, declared_node, SKOS.prefLabel, language=row.default_language or None)
    if not name:
        # The declared default language (or the site's, on fallback) carries
        # no prefLabel on the scheme itself — fall back to any language
        # rather than leaving name unset (T007's original, simpler rule).
        name = _first_literal(graph, declared_node, SKOS.prefLabel)
    if name:
        row.name = name
    row.static_uri = declared_uri
    row.save()
    if created:
        report.add_created(row.uri)
    else:
        report.add_updated(row.uri)
    return row, declared_uri


def import_skos(
    file: str | Path,
    *,
    serialization: str | None = None,
    scheme: ConceptScheme | None = None,
) -> ImportReport:
    """Import a published SKOS file and return a structured report (FR-001).

    Reads ``file`` (see :func:`_read_graph` for the serialization rules) and
    creates or updates the vocabulary it declares, matched by its static URI
    (research.md R6). ``scheme`` names a target vocabulary for a file that
    declares none of its own, or is checked against one the file does
    declare — a mismatch fails the run and writes nothing (FR-005).

    The whole run sits inside one transaction (FR-003, research.md R7): a
    fatal finding — a missing or refused identity, or a vocabulary that
    cannot be resolved — is collected rather than raised immediately, so a
    file with more than one problem reports all of them; only once nothing
    further can be checked does :class:`SkosImportFailed` actually raise,
    which is what triggers the rollback. A successful run's ``report.fatal``
    is always empty.
    """
    graph = _read_graph(file, serialization=serialization)
    report = ImportReport()
    source_label = str(file)

    with transaction.atomic():
        declared_nodes = sorted(graph.subjects(rdflib.RDF.type, SKOS.ConceptScheme), key=str)
        declared_node = declared_nodes[0] if declared_nodes else None
        concept_nodes = sorted(graph.subjects(rdflib.RDF.type, SKOS.Concept), key=str)

        # The concept walk itself (T009) attaches here once it lands; T007/T008
        # only resolve the vocabulary and its default language.
        _resolve_scheme(graph, declared_node, concept_nodes, scheme, report, source_label=source_label)

        if report.fatal:
            raise SkosImportFailed(report)

    return report
