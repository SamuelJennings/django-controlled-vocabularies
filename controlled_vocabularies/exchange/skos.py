"""Reading a published SKOS file into records (FS-006).

The RDF boundary: a file becomes an ``rdflib`` graph (:func:`_read_graph`),
the graph is walked into the models R1 built, and the run returns a
structured :class:`~controlled_vocabularies.exchange.report.ImportReport` of
what it did. Models stay the source of truth; RDF is read only at this
boundary and never stored as a graph (Article X).

:func:`import_skos` is the module's one public entry point. It resolves or
creates the vocabulary a file declares, then imports each of its concepts —
identity, preferred/alternative/hidden labels, documentary notes,
broader/narrower and related relationships, and collection membership — and
every value the models have no place for is set aside and named in the
report rather than dropped (Article XI). The whole run is one transaction:
a fatal finding (a missing or refused identity, or a vocabulary that cannot
be resolved) rolls the run back entirely, after every problem in the file
has been collected, not only the first.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import rdflib
import rdflib.util
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.mapping import (
    DCTERMS,
    LABEL_PREDICATES,
    MAPPING_PREDICATES,
    NOTE_PREDICATES,
    SKOS,
)
from controlled_vocabularies.exchange.report import FatalReason, ImportReport, NormalizedReason, SetAsideReason
from controlled_vocabularies.exchange.safety import scan_json_ld, scan_rdf_xml
from controlled_vocabularies.models import (
    Collection,
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptRelation,
    ConceptScheme,
    validate_static_uri,
)

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
    before rdflib ever sees it (research.md R3, decisions.md D9), and JSON-LD
    input is scanned by :func:`~controlled_vocabularies.exchange.safety.scan_json_ld`
    the same way (decisions.md D36) — either way the file is read from
    ``path`` a second time by rdflib itself afterwards, deliberately, rather
    than parsed from the bytes already in memory: rdflib's own file-based
    parse establishes its base URI from the file's own location, the
    behaviour decisions.md D13 measured and future fatal-path fixtures may
    come to depend on, and passing pre-read ``data=`` bytes instead would
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
    elif resolved_format == "json-ld":
        # Same pre-flight discipline, closing the equivalent hole D36 found
        # in JSON-LD's own remote-`@context` route (see the module docstring
        # above and safety.py's own).
        scan_json_ld(path.read_bytes())
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


def _choose_declared_scheme(
    graph: rdflib.Graph,
    declared_nodes: list[rdflib.term.Node],
    concept_nodes: list[rdflib.term.Node],
    target: ConceptScheme | None,
    report: ImportReport,
    *,
    source_label: str,
) -> rdflib.term.Node | None:
    """Pick the one vocabulary a file is declaring, or fail saying it cannot (FR-005).

    A file routinely types more than one ``skos:ConceptScheme`` without being
    about more than one: the second is a vocabulary some concept claims
    membership of, which spec Edge Cases §1 requires be set aside rather than
    refused. So multiplicity itself is not fatal. What decides is which
    declared vocabulary the file's own concepts belong to — the same three
    membership predicates :func:`_conflicting_scheme_ref` reads — and the one
    with the most members is the vocabulary being imported.

    Choosing by any property of the identifier itself, such as taking the
    first in sorted order, would make a curator's import depend on the
    alphabet: a foreign reference sorting ahead of the file's real vocabulary
    would import the wrong one, and D5 makes the file authoritative for
    everything it then writes. A genuine tie, with no caller-named target to
    resolve it, is refused instead. A named target always decides, and one
    matching none of the declared vocabularies falls through to
    :func:`_resolve_scheme`'s existing mismatch check.
    """
    if len(declared_nodes) < 2:
        return declared_nodes[0] if declared_nodes else None
    if target is not None:
        named = [node for node in declared_nodes if str(node) == target.uri]
        if named:
            return named[0]
        return declared_nodes[0]

    members: Counter[str] = Counter()
    for concept_node in concept_nodes:
        for scheme_uri in _scheme_refs(graph, concept_node):
            members[scheme_uri] += 1
    ranked = sorted(declared_nodes, key=lambda node: (-members[str(node)], str(node)))
    best, runner_up = members[str(ranked[0])], members[str(ranked[1])]
    if best > runner_up:
        return ranked[0]

    report.add_fatal(
        FatalReason.VOCABULARY_AMBIGUOUS,
        subject=source_label,
        declared=", ".join(str(node) for node in declared_nodes),
    )
    return None


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
    declared_default_language = _determine_default_language(graph, declared_node, concept_nodes)
    if created:
        # ConceptScheme.save() itself refuses to change default_language once
        # the scheme has concepts (R1 — it is the anchor every concept's
        # identity is built against, decisions.md D4). Recomputing it here on
        # every run would fight that guard the moment it legitimately
        # differs from what a previous run already froze; only a freshly
        # created scheme has no concepts yet to protect, so only a freshly
        # created scheme's default_language is set from the file at all.
        row.default_language = declared_default_language
    elif declared_default_language and declared_default_language != row.effective_default_language:
        # D18 froze this value once the scheme has concepts; D22 (carried
        # from the US-1 review) requires the conflict to be reported rather
        # than silently kept — silence is what D1 forbids. Compared against
        # effective_default_language, not the raw stored field, so a scheme
        # relying on the site default (default_language == "") that agrees
        # with the file in the same effective language is not a conflict.
        report.add_set_aside(
            SetAsideReason.DEFAULT_LANGUAGE_FROZEN,
            subject=declared_uri,
            declared=declared_default_language,
            frozen=row.effective_default_language,
        )
    name = _first_literal(graph, declared_node, SKOS.prefLabel, language=row.effective_default_language)
    if not name:
        # The declared default language (or the site's, on fallback) carries
        # no prefLabel on the scheme itself — fall back to any language
        # rather than leaving name unset (T007's original, simpler rule).
        name = _first_literal(graph, declared_node, SKOS.prefLabel)
    if name:
        row.name = name
    # SKOS defines no description predicate for a skos:ConceptScheme;
    # dcterms:description is the source (decisions.md D21), the same alias
    # CONTEXT.md establishes for a concept's own definition. Unlike name,
    # description is optional on the model and is written unconditionally,
    # including to empty when the file no longer carries one — a description
    # the publisher removed is a value the publisher removed (D5), and
    # nothing anchors identity to it the way default_language is anchored.
    description = _first_literal(graph, declared_node, DCTERMS.description, language=row.effective_default_language)
    if not description:
        description = _first_literal(graph, declared_node, DCTERMS.description)
    row.description = description or ""
    row.static_uri = declared_uri
    row.save()
    if created:
        report.add_created(row.uri)
    else:
        report.add_updated(row.uri)
    return row, declared_uri


def _conflicting_scheme_ref(graph: rdflib.Graph, concept_node: rdflib.term.Node, target_scheme_uri: str) -> str | None:
    """The URI of a *different* vocabulary this concept claims, if any (T009, FR-006).

    Checked against all three ways a concept can declare scheme membership:
    its own ``skos:inScheme``/``skos:topConceptOf``, and the scheme's
    ``skos:hasTopConcept`` naming it. A concept with no scheme reference at
    all is not a conflict — it is read as belonging to the vocabulary being
    imported — so this returns ``None`` both when every reference agrees
    with ``target_scheme_uri`` and when there is no reference to check.
    """
    others = _scheme_refs(graph, concept_node) - {target_scheme_uri}
    return sorted(others)[0] if others else None


def _scheme_refs(graph: rdflib.Graph, concept_node: rdflib.term.Node) -> set[str]:
    """Every vocabulary URI this concept declares membership of, by any of the three predicates."""
    refs = {str(obj) for obj in graph.objects(concept_node, SKOS.inScheme)}
    refs |= {str(obj) for obj in graph.objects(concept_node, SKOS.topConceptOf)}
    refs |= {str(subj) for subj in graph.subjects(SKOS.hasTopConcept, concept_node)}
    return refs


def _preferred_label_in(graph: rdflib.Graph, node: rdflib.term.Node, language: str) -> str | None:
    """The lexicographically-first ``skos:prefLabel`` value on ``node`` in ``language``, or ``None``."""
    values = sorted(
        str(literal)
        for literal in graph.objects(node, SKOS.prefLabel)
        if isinstance(literal, rdflib.Literal) and literal.language == language
    )
    return values[0] if values else None


def _import_labels(
    graph: rdflib.Graph,
    node: rdflib.term.Node,
    concept: Concept,
    default_language: str,
    uri: str,
    report: ImportReport,
) -> None:
    """Store ``concept``'s labels other than its own default-language preferred one (T018, FR-008).

    Replaces whatever labels this concept already held: a label carries no
    identifier of its own to upsert by (unlike the concept itself, R6), and
    the file is authoritative for what it contains (FR-013) — a value the
    publisher has since dropped must not linger. :attr:`LABEL_PREDICATES`
    covers ``skos:prefLabel``/``altLabel``/``hiddenLabel``; a preferred label
    in ``default_language`` is skipped rather than written as a
    :class:`~controlled_vocabularies.models.ConceptLabel` row, because that
    value is already ``concept.label`` (T009) and the model itself refuses a
    second preferred row in that language (models.py
    ``_reject_default_language_preferred``) — this importer must not even
    attempt it.

    A value in a language this application is not configured for is not
    written at all: it is set aside and reported by its own language,
    checked ahead of the write rather than let ``ConceptLabel.clean()``'s own
    refusal raise (T020, FR-014, decisions.md D25) — that exception exists to
    protect a direct, out-of-band write, not to be this importer's control
    flow.
    """
    configured = _configured_language_codes()
    concept.labels.all().delete()
    for predicate, kind in LABEL_PREDICATES.items():
        for literal in graph.objects(node, predicate):
            if not isinstance(literal, rdflib.Literal) or not literal.language:
                continue
            language = literal.language
            if kind == ConceptLabel.Kind.PREFERRED and language == default_language:
                continue
            if language not in configured:
                report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=language)
                continue
            concept.add_label(language=language, kind=kind, text=str(literal))


def _import_notes(
    graph: rdflib.Graph,
    node: rdflib.term.Node,
    concept: Concept,
    uri: str,
    report: ImportReport,
) -> None:
    """Store ``concept``'s documentary notes — the definition and the six SKOS note kinds
    (T019, FR-009) — through :meth:`~controlled_vocabularies.models.Concept.add_note`.

    Replaces whatever notes this concept already held, the same full-replace
    rule :func:`_import_labels` applies and for the same reason: a note
    carries no identifier of its own to upsert by, and the file is
    authoritative for what it contains (FR-013). :attr:`NOTE_PREDICATES`
    covers the native SKOS predicates only. ``dcterms:description`` is a
    separate, concept-level alias for the definition (T021, FR-009,
    decisions.md D24/D21) — read only in a language the concept carries no
    ``skos:definition`` of its own in, and reported as a normalisation rather
    than applied silently, so it is handled after the native predicates
    rather than folded into :attr:`NOTE_PREDICATES` alongside them.

    A value in a language this application is not configured for is set
    aside and reported by its own language rather than written, the same
    ahead-of-the-write filter :func:`_import_labels` applies and for the same
    reason (T020, FR-014, decisions.md D25).
    """
    configured = _configured_language_codes()
    concept.concept_notes.all().delete()
    definition_languages: set[str] = set()
    for predicate, kind in NOTE_PREDICATES.items():
        for literal in graph.objects(node, predicate):
            if not isinstance(literal, rdflib.Literal) or not literal.language:
                continue
            language = literal.language
            if kind == ConceptNote.Kind.DEFINITION:
                definition_languages.add(language)
            if language not in configured:
                report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=language)
                continue
            concept.add_note(language=language, kind=kind, value=str(literal))

    for literal in graph.objects(node, DCTERMS.description):
        if not isinstance(literal, rdflib.Literal) or not literal.language:
            continue
        language = literal.language
        if language in definition_languages:
            # The concept already carries its own skos:definition in this
            # language; the foreign predicate has nothing to contribute here.
            continue
        if language not in configured:
            report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=language)
            continue
        concept.add_note(language=language, kind=ConceptNote.Kind.DEFINITION, value=str(literal))
        report.add_normalized(
            NormalizedReason.FOREIGN_DEFINITION, subject=uri, predicate="dcterms:description", language=language
        )


#: Every predicate a concept node carries that this module already reads and
#: accounts for elsewhere (T021) — the identity/scheme predicates T009 reads,
#: every label and note predicate (:data:`LABEL_PREDICATES`/`NOTE_PREDICATES`),
#: the mapping predicates (reported under their own reason below), and
#: ``dcterms:description`` (the definition alias, also reported under its own
#: reason). Checked so :func:`_import_unheld_values` never double-reports a
#: predicate it, or another function in this module, already accounted for.
_HANDLED_CONCEPT_PREDICATES = frozenset(
    {
        rdflib.RDF.type,
        SKOS.inScheme,
        SKOS.topConceptOf,
        SKOS.notation,
        DCTERMS.description,
        SKOS.broader,
        SKOS.narrower,
        SKOS.related,
    }
    | set(LABEL_PREDICATES)
    | set(NOTE_PREDICATES)
    | set(MAPPING_PREDICATES)
)


def _import_unheld_values(graph: rdflib.Graph, node: rdflib.term.Node, uri: str, report: ImportReport) -> None:
    """Set aside and report the values on ``concept`` the models have no place for (T021, FR-014).

    Three kinds, each named under the reason that fits it (one entry per
    value, not merged, so nothing set aside is hidden behind a count only):
    a ``skos:notation`` (:data:`SetAsideReason.NOTATION`); a cross-vocabulary
    mapping (:data:`MAPPING_PREDICATES`, :data:`SetAsideReason.MAPPING`,
    naming the predicate's CURIE); and any predicate this concept carries
    that is neither handled elsewhere in this module nor itself a SKOS
    predicate (:data:`SetAsideReason.UNMODELLED_PREDICATE`, naming the
    predicate's own URI — there is no curated CURIE table for a predicate
    this module has never seen before).

    A SKOS predicate this module simply does not read *yet* —
    ``skos:broader``/``narrower``/``related`` (US-4) and
    ``skos:member``/``memberList`` (US-5) — is deliberately not reported
    here: the models do have a place for it, so FR-014's "the models have no
    place for" does not apply, only "not yet built" does, and reporting it
    now would be misleading noise that a later story's own read path would
    then need to un-report.
    """
    for _notation in graph.objects(node, SKOS.notation):
        report.add_set_aside(SetAsideReason.NOTATION, subject=uri)

    for mapping_predicate, name in MAPPING_PREDICATES.items():
        for _obj in graph.objects(node, mapping_predicate):
            report.add_set_aside(SetAsideReason.MAPPING, subject=uri, predicate=name)

    for other_predicate, _obj in graph.predicate_objects(node):
        if other_predicate in _HANDLED_CONCEPT_PREDICATES:
            continue
        if str(other_predicate).startswith(str(SKOS)):
            continue
        report.add_set_aside(SetAsideReason.UNMODELLED_PREDICATE, subject=uri, predicate=str(other_predicate))


def _resolve_concept_reference(
    uri: str, successful_concepts: dict[str, Concept], target_scheme: ConceptScheme
) -> Concept | None:
    """Return the :class:`Concept` ``uri`` names, or ``None`` when it cannot back a
    relation or a collection membership (FR-011) — the same resolution rule serves
    both, since decisions.md D30 treats a membership as "the same shape of problem"
    a relationship already is.

    Tries this run's own writes first (``successful_concepts``, keyed by URI —
    every concept this run actually created or updated); when ``uri`` was not
    itself imported this run, falls back to
    :meth:`~controlled_vocabularies.models.ConceptManager.get_by_uri` for a
    concept an earlier import already created (spec Acceptance Scenario US4-6)
    — a relationship or membership the file restates to an end it does not
    separately redeclare this time still lands. A match belonging to a
    *different* vocabulary than the one being imported is treated the same as
    no match at all: neither :class:`ConceptRelation` nor
    :class:`~controlled_vocabularies.models.CollectionMember` ever joins
    records of different schemes (research.md R4), and attempting one across
    schemes would otherwise raise a ``ValidationError`` this importer does not
    catch — the same "collect, don't crash" discipline every other set-aside
    reason follows (decisions.md D29).
    """
    concept = successful_concepts.get(uri)
    if concept is None:
        try:
            concept = Concept.objects.get_by_uri(uri)
        except Concept.DoesNotExist:
            return None
    if concept.scheme_id != target_scheme.pk:
        return None
    return concept


def _import_relations(
    graph: rdflib.Graph,
    target_scheme: ConceptScheme,
    successful_concepts: dict[str, Concept],
    report: ImportReport,
) -> None:
    """Reconcile ``skos:broader``/``skos:narrower``/``skos:related`` into the
    single canonical :class:`~controlled_vocabularies.models.ConceptRelation`
    row research.md R4 defines for each pair, for every concept this run
    created or updated (T023/T024, FR-010/FR-011/FR-013).

    Read only from the concepts this run itself just wrote — a concept set
    aside for another reason (a vocabulary mismatch, no preferred label) has
    no row of its own to attach a relation to, so its predicates are never
    read here: its identity is simply never a key of ``successful_concepts``.

    ``skos:broader`` and ``skos:narrower`` both resolve to the same stored
    BROADER row: :meth:`~controlled_vocabularies.models.Concept.add_broader`'s
    own contract is ``source`` the narrower end, ``target`` the broader end,
    so a ``narrower`` triple's ends are swapped before the pair is looked up.
    ``skos:related`` is symmetric and keyed by an unordered pair for the same
    reason (T024). Both directions stated for the same pair — either shape —
    collapse to the same dict key, so exactly one row results per pair
    (FR-010): the whole file's worth of pairs is read before any of them is
    written, rather than creating one and then the other, so which direction
    the file happened to state first never matters.

    An existing row is only ever a *candidate* for deletion when **both** of
    its ends were created or updated by this run (decisions.md D30): only
    then has the file had the opportunity to speak about the row at all. An
    edge with one end outside ``successful_concepts`` — the file simply does
    not mention that end, the same "does not mention" FR-013 already treats
    as untouched for the concept itself — is left exactly as it is, never
    deleted, whether or not it is restated. A row where both ends were
    written is then made to match the file exactly: deleted if the file no
    longer restates it, kept (or created) if it does. This is computed as one
    whole pass over every concept this run touched, rather than incrementally
    per concept, because a relation is commonly asserted from only one of its
    two ends (``narrower`` from the parent, ``broader`` from the child;
    either end for ``related``) — an incremental per-concept
    delete-and-recreate would delete a row a sibling concept's own pass had
    only just written, depending on which concept happened to be reached
    first.

    An end neither reachable through this run's own writes nor already in the
    database under a matching scheme is set aside and reported, naming both
    ends, and the run continues (FR-011, finished with acceptance coverage at
    T025).

    A pair resolved as broader/narrower always wins over the same pair
    resolved as related (review fix 2, decisions.md D37): SKOS declares the
    two disjoint, and the model itself refuses to store both
    (:meth:`~controlled_vocabularies.models.ConceptRelation._reject_disjointness_violation`).
    Broader/narrower rows are written first, each one checked directly
    against, and clearing, any conflicting stored RELATED row for the same
    pair — not only one the bulk deletion pass above would already have
    caught, since that pass only ever considers a row a candidate when
    *both* its ends were rewritten by this run (D30), and the far end of a
    newly-stated broader edge may instead be a concept only referenced this
    run (D29's ``get_by_uri`` fallback). Related rows are written after, each
    one checked the same way against a conflicting stored BROADER row —
    including one written earlier in this same call — and set aside and
    reported rather than attempted when one is found.
    """
    desired_broader: dict[tuple[str, str], None] = {}
    desired_related: dict[frozenset[str], None] = {}
    for uri in successful_concepts:
        node = rdflib.URIRef(uri)
        for other in graph.objects(node, SKOS.broader):
            desired_broader[(uri, str(other))] = None
        for other in graph.objects(node, SKOS.narrower):
            desired_broader[(str(other), uri)] = None
        for other in graph.objects(node, SKOS.related):
            desired_related[frozenset({uri, str(other)})] = None

    resolved_broader: set[tuple[int, int]] = set()
    resolved_related: set[frozenset[int]] = set()
    concepts_by_pk: dict[int, Concept] = {}

    for narrower_uri, broader_uri in desired_broader:
        narrower_concept = _resolve_concept_reference(narrower_uri, successful_concepts, target_scheme)
        broader_concept = _resolve_concept_reference(broader_uri, successful_concepts, target_scheme)
        if narrower_concept is None or broader_concept is None:
            subject_uri = narrower_uri if narrower_concept is not None else broader_uri
            other_uri = broader_uri if narrower_concept is not None else narrower_uri
            report.add_set_aside(SetAsideReason.MISSING_RELATION_END, subject=subject_uri, other=other_uri)
            continue
        resolved_broader.add((narrower_concept.pk, broader_concept.pk))
        concepts_by_pk[narrower_concept.pk] = narrower_concept
        concepts_by_pk[broader_concept.pk] = broader_concept

    for pair in desired_related:
        if len(pair) < 2:
            # A concept stating skos:related about itself — not a real
            # association (the model's own _reject_self would refuse it);
            # nothing meaningful to reconcile.
            continue
        a_uri, b_uri = tuple(pair)
        a_concept = _resolve_concept_reference(a_uri, successful_concepts, target_scheme)
        b_concept = _resolve_concept_reference(b_uri, successful_concepts, target_scheme)
        if a_concept is None or b_concept is None:
            subject_uri = a_uri if a_concept is not None else b_uri
            other_uri = b_uri if a_concept is not None else a_uri
            report.add_set_aside(SetAsideReason.MISSING_RELATION_END, subject=subject_uri, other=other_uri)
            continue
        resolved_related.add(frozenset({a_concept.pk, b_concept.pk}))
        concepts_by_pk[a_concept.pk] = a_concept
        concepts_by_pk[b_concept.pk] = b_concept

    successful_ids = {concept.pk for concept in successful_concepts.values()}

    # Both ends in successful_ids, not either (decisions.md D30): a row with
    # one end outside this run's own writes is only half spoken about by the
    # file, and FR-013's deletion authority only ever covers what the file
    # actually speaks about.
    existing_broader = ConceptRelation.objects.filter(
        kind=ConceptRelation.Kind.BROADER,
        source_id__in=successful_ids,
        target_id__in=successful_ids,
    )
    for row in existing_broader:
        if (row.source_id, row.target_id) not in resolved_broader:
            row.delete()

    existing_related = ConceptRelation.objects.filter(
        kind=ConceptRelation.Kind.RELATED,
        source_id__in=successful_ids,
        target_id__in=successful_ids,
    )
    for row in existing_related:
        if frozenset({row.source_id, row.target_id}) not in resolved_related:
            row.delete()

    for narrower_pk, broader_pk in resolved_broader:
        already_stored = ConceptRelation.objects.filter(
            source_id=narrower_pk, target_id=broader_pk, kind=ConceptRelation.Kind.BROADER
        ).exists()
        if already_stored:
            continue
        # FIX 2, route 2 (decisions.md D37): an existing RELATED row for this
        # exact pair may not have been a candidate for the bulk deletion pass
        # above — that pass only ever considers a row when BOTH its ends were
        # rewritten by this run (D30), and the far end of a newly-stated
        # broader edge may instead be a concept an earlier import wrote and
        # this run only references (D29's get_by_uri fallback), so it is
        # never in successful_ids. Checked directly and unconditionally, so a
        # stale RELATED row from an earlier run can never survive to make
        # add_broader raise the model's own disjointness ValidationError.
        conflicting_related = ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).filter(
            Q(source_id=narrower_pk, target_id=broader_pk) | Q(source_id=broader_pk, target_id=narrower_pk)
        )
        for row in conflicting_related:
            report.add_set_aside(
                SetAsideReason.RELATION_DISJOINTNESS,
                subject=concepts_by_pk[narrower_pk].static_uri,
                other=concepts_by_pk[broader_pk].static_uri,
            )
            row.delete()
        concepts_by_pk[narrower_pk].add_broader(concepts_by_pk[broader_pk])

    for pk_pair in resolved_related:
        a_pk, b_pk = tuple(pk_pair)
        already_stored = (
            ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED)
            .filter(Q(source_id=a_pk, target_id=b_pk) | Q(source_id=b_pk, target_id=a_pk))
            .exists()
        )
        if already_stored:
            continue
        # FIX 2, the symmetric route (decisions.md D37): the mirror image of
        # the broader-side check just above — a BROADER row surviving from an
        # earlier run for the same D30 reason must be checked before
        # add_related too, or the model's own guard raises here instead.
        conflicting_broader = (
            ConceptRelation.objects.filter(kind=ConceptRelation.Kind.BROADER)
            .filter(Q(source_id=a_pk, target_id=b_pk) | Q(source_id=b_pk, target_id=a_pk))
            .exists()
        )
        if conflicting_broader:
            report.add_set_aside(
                SetAsideReason.RELATION_DISJOINTNESS,
                subject=concepts_by_pk[a_pk].static_uri,
                other=concepts_by_pk[b_pk].static_uri,
            )
            continue
        concepts_by_pk[a_pk].add_related(concepts_by_pk[b_pk])


def _import_collections(
    graph: rdflib.Graph,
    target_scheme: ConceptScheme,
    successful_concepts: dict[str, Concept],
    report: ImportReport,
) -> None:
    """Create or update every ``skos:Collection``/``skos:OrderedCollection`` in
    ``graph`` inside ``target_scheme``, with its membership (T027/T028,
    FR-012).

    Read after every concept this run created or updated already has a
    primary key — membership needs :func:`_resolve_concept_reference` exactly
    as a relationship end does. A collection's own identity is checked with
    the same :func:`_identify` a concept or the vocabulary itself uses (D3): a
    blank-node collection is fatal, the run collects it and continues to the
    next one rather than stopping (FR-003). The structural exception is an
    ordered collection's ``skos:memberList`` itself — an RDF list, made of
    blank nodes by construction (research.md R2) — read through
    ``graph.items()``, which yields the member *URIs* the list carries, never
    the list's own cells, so those blank nodes never reach :func:`_identify`
    at all (D3's own carve-out, T030).

    ``skos:member`` (unordered) or ``skos:memberList`` (ordered, walked in the
    file's own order) name the file's desired membership. Each member URI is
    resolved through :func:`_resolve_concept_reference` — this run's own
    writes first, then an earlier import's; one that resolves to nothing is
    set aside and reported (:data:`SetAsideReason.MISSING_MEMBER`, naming both
    the member and the collection) rather than failing the run (FR-011), and
    the collection is still created holding whatever members did resolve.

    Membership is written only through the model's own API —
    :meth:`~controlled_vocabularies.models.Collection.add`,
    :meth:`~controlled_vocabularies.models.Collection.remove`,
    :meth:`~controlled_vocabularies.models.Collection.set_member_order` —
    never a :class:`~controlled_vocabularies.models.CollectionMember` row
    constructed directly, so the model's own cross-scheme check always runs.

    An existing membership is only ever a *removal* candidate when its member
    concept belongs to ``successful_concepts`` — was itself created or updated
    by this run (decisions.md D30, carried across from relationship
    reconciliation: "collection membership is the same shape of problem").
    A member the file simply does not mention this run at all is not the same
    as one the file's collection statement excludes: the former is untouched,
    exactly as the concept at that end already is
    (``report.absent_from_source``); only the latter is removed. This is not
    re-derived — it is D30's own rule, applied to a second model.

    Finally (T034, FR-013), every existing collection of ``target_scheme``
    whose identity was never seen among ``collection_nodes`` — the file
    simply does not mention it — is left completely untouched, membership
    included, and named in ``report.absent_from_source``, the same tail
    :func:`_import_concepts` already runs for a concept in that position.
    """
    collection_nodes = sorted(
        set(graph.subjects(rdflib.RDF.type, SKOS.Collection))
        | set(graph.subjects(rdflib.RDF.type, SKOS.OrderedCollection)),
        key=str,
    )
    successful_ids = {concept.pk for concept in successful_concepts.values()}
    mentioned_uris: set[str] = set()

    for node in collection_nodes:
        hint = _first_literal(graph, node, SKOS.prefLabel)
        try:
            uri = _identify(node, hint=hint)
        except _FatalIdentity as exc:
            report.add_fatal(exc.reason, exc.subject, **exc.params)
            continue
        mentioned_uris.add(uri)

        ordered = (node, rdflib.RDF.type, SKOS.OrderedCollection) in graph

        try:
            row = Collection.objects.get_by_uri(uri)
            created = False
        except Collection.DoesNotExist:
            row = Collection(scheme=target_scheme)
            created = True
        row.scheme = target_scheme
        row.static_uri = uri
        name = _first_literal(graph, node, SKOS.prefLabel, language=target_scheme.effective_default_language)
        if not name:
            name = _first_literal(graph, node, SKOS.prefLabel)
        if name:
            row.name = name
        row.ordered = ordered
        row.save()
        if created:
            report.add_created(uri)
        else:
            report.add_updated(uri)

        if ordered:
            member_list_node = graph.value(node, SKOS.memberList)
            member_uris = [str(item) for item in graph.items(member_list_node)] if member_list_node is not None else []
        else:
            member_uris = sorted({str(obj) for obj in graph.objects(node, SKOS.member)})

        resolved: list[Concept] = []
        seen_pks: set[int] = set()
        for member_uri in member_uris:
            concept = _resolve_concept_reference(member_uri, successful_concepts, target_scheme)
            if concept is None:
                report.add_set_aside(SetAsideReason.MISSING_MEMBER, subject=member_uri, collection=uri)
                continue
            if concept.pk in seen_pks:
                continue
            seen_pks.add(concept.pk)
            resolved.append(concept)

        resolved_pks = {concept.pk for concept in resolved}
        for membership in list(row.memberships.select_related("concept")):
            if membership.concept_id in successful_ids and membership.concept_id not in resolved_pks:
                row.remove(membership.concept)

        for concept in resolved:
            row.add(concept)

        if ordered:
            current = [
                membership.concept
                for membership in row.memberships.select_related("concept").order_by("position", "id")
            ]
            survivors = [concept for concept in current if concept.pk not in resolved_pks]
            row.set_member_order(resolved + survivors)

    absent = Collection.objects.filter(scheme=target_scheme).exclude(static_uri__in=mentioned_uris)
    for uri in absent.order_by("static_uri").values_list("static_uri", flat=True):
        report.add_absent_from_source(uri)


def _import_concept_content(
    graph: rdflib.Graph,
    node: rdflib.term.Node,
    concept: Concept,
    target_scheme: ConceptScheme,
    uri: str,
    report: ImportReport,
) -> None:
    """Import everything about ``concept`` beyond its identity and default-language label.

    Called once per created-or-updated concept, after it has a primary key
    (T018's label replacement needs one). Grows one call at a time as
    Phase US-3 landed: T018 (labels), T019 (notes), T021 (notation, mappings,
    unmodelled predicates, and the ``dcterms:description`` normalisation).
    """
    _import_labels(graph, node, concept, target_scheme.effective_default_language, uri, report)
    _import_notes(graph, node, concept, uri, report)
    _import_unheld_values(graph, node, uri, report)


def _import_concepts(
    graph: rdflib.Graph,
    target_scheme: ConceptScheme,
    target_scheme_uri: str,
    concept_nodes: list[rdflib.term.Node],
    report: ImportReport,
) -> None:
    """Create or update each of ``concept_nodes`` inside ``target_scheme`` (T009, FR-006).

    For each concept node, in order: its identity is checked (a blank node or
    a refused URI is fatal, D3, exactly as for the vocabulary itself); a
    concept that explicitly claims a *different* vocabulary is set aside and
    reported rather than imported (spec Edge Cases §1); a concept with no
    preferred label in ``target_scheme``'s effective default language is set
    aside and reported (FR-006) rather than crashing the run — required for
    T009 to create concepts at all, even though the acceptance scenario
    dedicated to this case is T022's (decisions.md D17). A matched or newly
    created :class:`Concept` is given a deterministic, scheme-unique slug
    (:func:`_assign_unique_slug`, FR-007) and written through the model's own
    ``save()``.

    Finally (T013/FR-013), every existing concept of ``target_scheme`` whose
    identity was never seen among ``concept_nodes`` — the file simply does not
    mention it, as opposed to mentioning and setting it aside — is left
    completely untouched and named in ``report.absent_from_source``. A concept
    set aside for claiming a *different* vocabulary is not "absent from
    source": the file does mention it, just not as a member of this one.

    Relationships (T023, FR-010/FR-011) are reconciled in one pass over every
    concept this call itself created or updated, once the loop below has
    finished and every one of them has a primary key to relate through — see
    :func:`_import_relations` for why this cannot be folded into the
    per-concept loop instead.
    """
    mentioned_uris: set[str] = set()
    concepts_by_uri: dict[str, Concept] = {}
    for node in concept_nodes:
        hint = _first_literal(graph, node, SKOS.prefLabel)
        try:
            uri = _identify(node, hint=hint)
        except _FatalIdentity as exc:
            report.add_fatal(exc.reason, exc.subject, **exc.params)
            continue
        mentioned_uris.add(uri)

        other = _conflicting_scheme_ref(graph, node, target_scheme_uri)
        if other is not None:
            report.add_set_aside(SetAsideReason.VOCABULARY_MISMATCH, subject=uri, other=other)
            continue

        label = _preferred_label_in(graph, node, target_scheme.effective_default_language)
        if label is None:
            report.add_set_aside(
                SetAsideReason.NO_PREFERRED_LABEL,
                subject=uri,
                language=target_scheme.effective_default_language,
            )
            continue

        try:
            concept = Concept.objects.get_by_uri(uri)
            created = False
        except Concept.DoesNotExist:
            concept = Concept(scheme=target_scheme)
            created = True
        concept.scheme = target_scheme
        concept.static_uri = uri
        concept.label = label
        _assign_unique_slug(concept, target_scheme)
        concept.save()
        concepts_by_uri[uri] = concept
        _import_concept_content(graph, node, concept, target_scheme, uri, report)
        if created:
            report.add_created(uri)
        else:
            report.add_updated(uri)

    _import_relations(graph, target_scheme, concepts_by_uri, report)
    _import_collections(graph, target_scheme, concepts_by_uri, report)

    absent = Concept.objects.filter(scheme=target_scheme).exclude(static_uri__in=mentioned_uris)
    for uri in absent.order_by("static_uri").values_list("static_uri", flat=True):
        report.add_absent_from_source(uri)


def _assign_unique_slug(concept: Concept, scheme: ConceptScheme) -> None:
    """Give ``concept`` a deterministic, scheme-unique slug derived from its label (T010, FR-007).

    Nothing is derived from ``concept.static_uri`` — identity and slug are
    deliberately independent (FR-007's own words). ``Concept.save()`` itself
    already derives a slug from ``label`` when ``slug_is_manual`` is false,
    but it only *refuses* a collision rather than resolving one (research R4
    was written for curator-authored content, where two concepts sharing a
    label is rare and worth a hard stop). A published file is not so
    well-behaved: two source concepts commonly share a preferred label
    (decisions.md D6), so the importer computes the slug itself here — the
    same base derivation, with a deterministic numeric suffix appended only
    when that value already belongs to a *different* concept in the same
    scheme (``concept_nodes`` is processed in a stable, URI-sorted order, so
    which of two colliding concepts gets the plain slug and which gets the
    suffix is the same on every run of the identical file).

    Setting ``slug_is_manual`` stops ``Concept.save()`` from re-deriving (and
    silently overwriting) this value on a later plain save unrelated to this
    importer. It does not pin the slug in the sense a curator's own manual
    slug is pinned: every re-import recomputes it fresh from the (possibly
    since-renamed) label, so an imported concept's slug still moves on a
    rename, exactly as decisions.md D6 requires.
    """
    base = slugify(concept.label, allow_unicode=True)
    candidate = base
    suffix = 1
    while Concept.objects.filter(scheme=scheme, slug=candidate).exclude(pk=concept.pk).exists():
        suffix += 1
        candidate = f"{base}-{suffix}"
    concept.slug = candidate
    concept.slug_is_manual = True


def import_skos(
    file: str | Path,
    *,
    serialization: str | None = None,
    scheme: ConceptScheme | None = None,
) -> ImportReport:
    """Import a published SKOS file and return a structured report (FR-001).

    Reads ``file`` (Turtle, RDF/XML, or JSON-LD — see :func:`_read_graph` for
    the serialization rules) and creates or updates the vocabulary it
    declares, matched by its static URI (research.md R6), along with every
    concept it contains: identity, labels, documentary notes,
    broader/narrower and related relationships, and collection membership.
    ``scheme`` names a target vocabulary for a file that declares none of
    its own, or is checked against one the file does declare — a mismatch
    fails the run and writes nothing (FR-005).

    Re-running an import upserts rather than deleting and recreating: a
    record the file still contains has its content matched to the file
    exactly, including removing a value the file no longer carries, while a
    record the file simply does not mention is left completely untouched
    and named in ``report.absent_from_source`` (FR-013). Anything the file
    carries that the models have no place for — an unconfigured language,
    a notation, a cross-vocabulary mapping, a predicate outside SKOS
    entirely — is set aside and named in the report rather than dropped in
    silence (FR-014, Article XI).

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
        concept_nodes = sorted(graph.subjects(rdflib.RDF.type, SKOS.Concept), key=str)

        declared_node = _choose_declared_scheme(
            graph, declared_nodes, concept_nodes, scheme, report, source_label=source_label
        )
        target_scheme, declared_uri = (
            (None, None)
            if report.fatal
            else _resolve_scheme(graph, declared_node, concept_nodes, scheme, report, source_label=source_label)
        )
        if target_scheme is not None and declared_uri is not None:
            _import_concepts(graph, target_scheme, declared_uri, concept_nodes, report)

        if report.fatal:
            raise SkosImportFailed(report)

    return report
