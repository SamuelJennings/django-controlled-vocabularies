"""Reading a published SKOS file into records (FS-006).

The RDF boundary: a file becomes an ``rdflib`` graph (:meth:`SkosGraph.from_file`), the graph is
walked into the models R1 built, and the run returns a structured
:class:`~controlled_vocabularies.exchange.report.ImportReport` of what it did (Article X: RDF is
read only at this boundary, never stored as a graph).

:func:`import_skos` is the module's one public entry point, a thin wrapper over
:class:`SkosImporter`. It resolves or creates the vocabulary a file declares, then imports each
concept — identity, labels, notes, relationships, and collection membership — setting aside
anything the models have no place for rather than dropping it (Article XI). The whole run is one
transaction: a fatal finding rolls the run back entirely, after every problem has been collected,
not only the first.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import rdflib
import rdflib.util
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.exceptions import (
    SkosImportError,
    SkosImportFailed,
    UnsafeJsonLdError,
    UnsafeRdfXmlError,
)
from controlled_vocabularies.exchange.languages import LanguageMatcher
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


class _FatalIdentity(Exception):
    """Internal signal that a node's identity is fatal (D3/FR-004); carries the finding to record."""

    def __init__(self, reason: FatalReason, subject: str, **params: str) -> None:
        self.reason = reason
        self.subject = subject
        self.params = params
        super().__init__(subject)


class SkosGraph:
    """Wraps the parsed ``rdflib.Graph`` and the pure, read-only queries the importer runs
    against it — the RDF boundary itself.
    """

    def __init__(self, graph: rdflib.Graph) -> None:
        self.graph = graph

    @classmethod
    def from_file(cls, file: str | Path, *, serialization: str | None = None) -> SkosGraph:
        """Read ``file`` into a :class:`SkosGraph` (research.md R1, FR-002).

        ``serialization`` is the caller-stated format; when omitted it is guessed from the file's
        extension. Either way the result must be one of :data:`_SUPPORTED_FORMATS`, or the run
        fails naming the file (FR-002).

        RDF/XML and JSON-LD are scanned by :mod:`~controlled_vocabularies.exchange.safety` before
        rdflib ever sees them (research.md R3, D9, D36) — either way rdflib then reads the file a
        second time from ``path`` itself, deliberately: its file-based parse establishes its base
        URI from the file's own location (D13), which pre-read ``data=`` bytes would silently
        change.

        A file that cannot be found or parsed raises :class:`SkosImportError` rather than letting
        rdflib's own exception escape. The pre-flight scan itself is wrapped the same way (review
        fix 18, D51): a malformed document can make the scan raise a bare exception outside this
        try/except otherwise. The *deliberate* refusals,
        :class:`~controlled_vocabularies.exchange.exceptions.UnsafeRdfXmlError` and
        :class:`~controlled_vocabularies.exchange.exceptions.UnsafeJsonLdError`, are excluded from that
        wrapping and propagate as themselves (D36).
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
        graph = rdflib.Graph()
        try:
            if resolved_format == "xml":
                # Pre-flight only — the bytes read here are not what gets parsed (see the base-URI
                # note above), so a second, larger read is a deliberate, small cost on RDF/XML input.
                scan_rdf_xml(path.read_bytes())
            elif resolved_format == "json-ld":
                # Same pre-flight discipline, closing the equivalent hole D36 found in JSON-LD's own
                # remote-`@context` route.
                scan_json_ld(path.read_bytes())
            graph.parse(str(path), format=resolved_format)
        except (UnsafeRdfXmlError, UnsafeJsonLdError):
            raise
        except Exception as exc:
            raise SkosImportError(
                _("'%(file)s' could not be parsed as %(format)s: %(error)s"),
                params={"file": str(path), "format": resolved_format, "error": str(exc)},
                code="skos_parse_failed",
            ) from exc
        return cls(graph)

    @staticmethod
    def identify(node: rdflib.term.Node, *, hint: str | None = None) -> str:
        """Return ``node``'s usable identifier, or raise :class:`_FatalIdentity` (FR-004, D3).

        A blank node supplies no identifier that survives re-serialization and is always fatal —
        an ordered collection's own member list is read as a list, never as a candidate record, so
        it never reaches this function. A ``URIRef`` is checked through
        :func:`~controlled_vocabularies.models.validate_static_uri`, the same identity rule the
        models enforce on a stored ``static_uri`` (research.md R6).

        ``hint`` — typically the node's own preferred label, when one could be read before the
        identity check ran — gives the fatal message something recognisable to point a curator at
        when the node itself has no URI to show.
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

    def first_literal(
        self,
        node: rdflib.term.Node,
        predicate: rdflib.URIRef,
        *,
        language: str | None = None,
    ) -> str | None:
        """The lexicographically-first literal value of ``predicate`` on ``node``, or ``None``.

        Deterministic rather than "whichever rdflib happens to yield first" — the graph's own
        iteration order is not something to depend on for a value that ends up in a stored record
        (T010). ``language``, when given, restricts to literals tagged with that language.
        """
        values = sorted(
            str(literal)
            for literal in self.graph.objects(node, predicate)
            if language is None or getattr(literal, "language", None) == language
        )
        return values[0] if values else None

    def label_languages(self, node: rdflib.term.Node, predicate: rdflib.URIRef) -> list[str]:
        """The language tags of ``predicate``'s literal values on ``node`` (empty-tag values excluded)."""
        return [
            literal.language
            for literal in self.graph.objects(node, predicate)
            if isinstance(literal, rdflib.Literal) and literal.language
        ]

    def preferred_label_in(self, node: rdflib.term.Node) -> list[tuple[str, str]]:
        """Every ``(published tag, value)`` pair ``node`` carries a ``skos:prefLabel`` in (T007).

        Unfiltered by language: which pair fills a configured language's slot is decided by
        :meth:`~controlled_vocabularies.exchange.languages.LanguageMatcher.resolve_winner`, and that
        policy does not belong on this RDF boundary (Article XV) — the caller, which already holds
        the matcher, resolves and picks a winner from what this returns.
        """
        return sorted(
            (str(literal.language), str(literal))
            for literal in self.graph.objects(node, SKOS.prefLabel)
            if isinstance(literal, rdflib.Literal) and literal.language
        )

    def preferred_label_tag_counts(self, concept_nodes: Iterable[rdflib.term.Node]) -> dict[str, int]:
        """How often each published language tag appears across ``concept_nodes``'
        own ``skos:prefLabel`` values (T002, research.md R2, decisions.md D4/D5).

        That predicate and that node set, and no other: the vocabulary's own
        ``skos:prefLabel`` and every collection's are excluded, because
        :meth:`SchemeResolver.determine_default_language` already counts exactly
        this population (``skos.py:327``) and a contest can only ever turn on it
        (D4). A caller passing a wider node set would silently change that
        already-shipped rule.
        """
        counts: dict[str, int] = {}
        for node in concept_nodes:
            for language in self.label_languages(node, SKOS.prefLabel):
                counts[language] = counts.get(language, 0) + 1
        return counts

    def scheme_refs(self, concept_node: rdflib.term.Node) -> set[str]:
        """Every vocabulary URI this concept declares membership of, by any of the three predicates."""
        refs = {str(obj) for obj in self.graph.objects(concept_node, SKOS.inScheme)}
        refs |= {str(obj) for obj in self.graph.objects(concept_node, SKOS.topConceptOf)}
        refs |= {str(subj) for subj in self.graph.subjects(SKOS.hasTopConcept, concept_node)}
        return refs

    def conflicting_scheme_ref(self, concept_node: rdflib.term.Node, target_scheme_uri: str) -> str | None:
        """The URI of a *different* vocabulary this concept claims, if any (T009, FR-006).

        A concept with no scheme reference at all is not a conflict — it is read as belonging to
        the vocabulary being imported — so this returns ``None`` both when every reference agrees
        with ``target_scheme_uri`` and when there is no reference to check.
        """
        others = self.scheme_refs(concept_node) - {target_scheme_uri}
        return sorted(others)[0] if others else None

    def implied_concept_nodes(self) -> set[rdflib.term.Node]:
        """Nodes the file identifies as concepts through a scheme-membership predicate, but never
        types with ``rdf:type skos:Concept`` at all (review fix 17, decisions.md D50).

        Restricted to a node carrying **no** ``rdf:type`` whatsoever — one the file does type, as
        something other than ``skos:Concept``, is left entirely to whatever that type already
        makes of it, never reclassified.
        """
        candidates: set[rdflib.term.Node] = set(self.graph.subjects(SKOS.inScheme, None))
        candidates |= set(self.graph.subjects(SKOS.topConceptOf, None))
        candidates |= set(self.graph.objects(None, SKOS.hasTopConcept))
        return {node for node in candidates if next(self.graph.objects(node, rdflib.RDF.type), None) is None}

    @staticmethod
    def skos_curie(predicate: rdflib.URIRef) -> str:
        """The ``skos:xxx`` CURIE for a predicate in the SKOS namespace (report display only, FIX 15, D48)."""
        return f"skos:{str(predicate)[len(str(SKOS)) :]}"


def _localized_literal(
    skos_graph: SkosGraph,
    matcher: LanguageMatcher,
    node: rdflib.term.Node,
    predicate: rdflib.URIRef,
    target_language: str,
) -> str | None:
    """The value of ``predicate`` on ``node`` whose published tag resolves to ``target_language``
    through ``matcher`` (T008, call sites 6/7/8), or ``None``.

    ``SkosGraph.first_literal``'s own ``language=`` filter is an exact match; resolving a variant
    tag to ``target_language`` is configured-language policy, which stays off ``SkosGraph``
    (Article XV), so it happens here, reading only the graph's public, read-only queries. Without
    this, a site importing a vocabulary declared in a variant of its default language names every
    concept correctly and then falls through to :meth:`SkosGraph.first_literal`'s own any-language
    fallback — ``sorted(...)[0]`` across every language in the file — for the record's own name.
    """
    candidates = [
        (tag, value)
        for tag in sorted(set(skos_graph.label_languages(node, predicate)))
        if (value := skos_graph.first_literal(node, predicate, language=tag)) is not None
        if matcher.resolve(tag).configured_language == target_language
    ]
    if not candidates:
        return None
    (_winning_tag, value), _losers = matcher.resolve_winner(target_language, candidates)
    return value


def report_unmodelled_predicates(
    skos_graph: SkosGraph,
    node: rdflib.term.Node,
    uri: str,
    handled: frozenset[rdflib.URIRef],
    report: ImportReport,
) -> None:
    """Set aside and report a predicate ``node`` carries that is neither in ``handled`` — already
    accounted for elsewhere, for whatever kind of node this is — nor itself a SKOS predicate
    this module has no read path for *yet* (FIX 12, D45; generalises D27's own concept-only
    rule past the single node kind it was written for). A SKOS predicate with no read path is
    deliberately not reported: the models do have a place for it, only "not yet built" applies.
    Called once per node this module treats as a record with its own identity — a concept, the
    vocabulary's own scheme node, and a collection — each with its own ``handled`` set naming
    what it already reads.
    """
    for other_predicate, _obj in skos_graph.graph.predicate_objects(node):
        if other_predicate in handled:
            continue
        if str(other_predicate).startswith(str(SKOS)):
            continue
        report.add_set_aside(SetAsideReason.UNMODELLED_PREDICATE, subject=uri, predicate=str(other_predicate))


class SchemeResolver:
    """Resolves which vocabulary a file belongs to: the one it declares, or a caller-named target
    (FR-005).
    """

    #: Predicates the vocabulary's own scheme node carries that :meth:`resolve_scheme` already
    #: reads and accounts for (FIX 12, decisions.md D45): its own identity, name
    #: (``skos:prefLabel``), top concepts, and description. ``skos:hasTopConcept`` is read *about*
    #: a concept, not held for the concept, so it is not shared with :class:`ConceptImporter`'s
    #: own handled set.
    _HANDLED_PREDICATES = frozenset(
        {
            rdflib.RDF.type,
            SKOS.prefLabel,
            SKOS.hasTopConcept,
            DCTERMS.description,
        }
    )

    def __init__(
        self,
        skos_graph: SkosGraph,
        report: ImportReport,
        *,
        target: ConceptScheme | None,
        source_label: str,
        matcher: LanguageMatcher,
    ) -> None:
        self.skos_graph = skos_graph
        self.report = report
        self.target = target
        self.source_label = source_label
        self.matcher = matcher

    @staticmethod
    def _get_or_create_scheme(uri: str) -> ConceptScheme:
        """Return the :class:`ConceptScheme` matching ``uri``, or a new unsaved one (research.md R6)."""
        try:
            return ConceptScheme.objects.get_by_uri(uri)
        except ConceptScheme.DoesNotExist:
            return ConceptScheme(static_uri=uri)

    def determine_default_language(self, declared_node: rdflib.term.Node, concept_nodes: list[rdflib.term.Node]) -> str:
        """The imported vocabulary's default language, per FR-005 (T008, decisions.md D4).

        Taken from the file where the file says: the vocabulary's own ``skos:prefLabel``, when
        tagged with exactly one language, else the language most of ``concept_nodes``' own
        preferred labels use, tied deterministically by language code. Either way the resolved
        language is found through :attr:`matcher` (T006, FR-007, decisions.md D9) rather than
        exact set membership — a vocabulary declaring itself in a variant of a configured language
        (``de-at`` on a ``de`` site) resolves to that configured language rather than falling
        through to the site's own default. When no configured language shares a base with either
        candidate, this returns ``""``, which :attr:`ConceptScheme.default_language` already
        treats as "fall back to the site's own default" (``effective_default_language``) — the
        mechanism R1 built, reused rather than duplicated.
        """
        declared_languages = set(self.skos_graph.label_languages(declared_node, SKOS.prefLabel))
        if len(declared_languages) == 1:
            (declared_language,) = declared_languages
            resolved = self.matcher.resolve(declared_language).configured_language
            if resolved:
                return resolved

        counts: dict[str, int] = {}
        for node in concept_nodes:
            for language in self.skos_graph.label_languages(node, SKOS.prefLabel):
                counts[language] = counts.get(language, 0) + 1
        if counts:
            commonest = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
            resolved = self.matcher.resolve(commonest).configured_language
            if resolved:
                return resolved

        return ""

    def choose_declared_scheme(
        self,
        declared_nodes: list[rdflib.term.Node],
        concept_nodes: list[rdflib.term.Node],
    ) -> rdflib.term.Node | None:
        """Pick the one vocabulary a file is declaring, or fail saying it cannot (FR-005).

        A file routinely types more than one ``skos:ConceptScheme`` without being about more than
        one: a second is merely a vocabulary some concept claims membership of, set aside rather
        than refused (spec Edge Cases §1) — so multiplicity itself is not fatal. What decides is
        which declared vocabulary the file's own concepts belong to, by the same three membership
        predicates :meth:`SkosGraph.scheme_refs` reads; the one with the most members wins, never
        any property of the identifier itself such as sorted order (D5 makes the file authoritative
        for what it writes, not the alphabet). A genuine tie with no caller-named target to resolve
        it is refused. A named target always decides; one matching none of the declared
        vocabularies falls through to :meth:`resolve_scheme`'s own mismatch check.
        """
        if len(declared_nodes) < 2:
            return declared_nodes[0] if declared_nodes else None
        if self.target is not None:
            named = [node for node in declared_nodes if str(node) == self.target.uri]
            if named:
                return named[0]
            return declared_nodes[0]

        members: Counter[str] = Counter()
        for concept_node in concept_nodes:
            for scheme_uri in self.skos_graph.scheme_refs(concept_node):
                members[scheme_uri] += 1
        ranked = sorted(declared_nodes, key=lambda node: (-members[str(node)], str(node)))
        best, runner_up = members[str(ranked[0])], members[str(ranked[1])]
        if best > runner_up:
            return ranked[0]

        self.report.add_fatal(
            FatalReason.VOCABULARY_AMBIGUOUS,
            subject=self.source_label,
            declared=", ".join(str(node) for node in declared_nodes),
        )
        return None

    def resolve_scheme(
        self,
        declared_node: rdflib.term.Node | None,
        concept_nodes: list[rdflib.term.Node],
    ) -> tuple[ConceptScheme | None, str | None]:
        """Resolve, create or update the vocabulary being imported into (FR-005, T007).

        The file is authoritative for which vocabulary is being imported: when it declares none, a
        caller-named target is required; when it declares one, a given target must agree with it (a
        mismatch is fatal, nothing is written). Matches an existing record via ``get_by_uri``
        (research.md R6); otherwise creates one holding the file's identifier.

        Returns ``(scheme, declared_uri)`` — ``declared_uri`` is what concepts are later checked
        against for "belongs to a different vocabulary" (T009) — or ``(None, None)`` when
        resolution itself is fatal, in which case ``report.fatal`` already carries why.
        """
        if declared_node is None:
            if self.target is None:
                self.report.add_fatal(FatalReason.VOCABULARY_UNDETERMINED, subject=self.source_label)
                return None, None
            return self.target, self.target.uri

        hint = self.skos_graph.first_literal(declared_node, SKOS.prefLabel)
        try:
            declared_uri = self.skos_graph.identify(declared_node, hint=hint)
        except _FatalIdentity as exc:
            self.report.add_fatal(exc.reason, exc.subject, **exc.params)
            return None, None

        if self.target is not None and self.target.uri != declared_uri:
            self.report.add_fatal(FatalReason.VOCABULARY_TARGET_MISMATCH, subject=declared_uri, target=self.target.uri)
            return None, None

        row = self.target if self.target is not None else self._get_or_create_scheme(declared_uri)
        created = row.pk is None
        declared_default_language = self.determine_default_language(declared_node, concept_nodes)
        if created:
            # ConceptScheme.save() itself refuses to change default_language once the scheme has
            # concepts (R1 — it is the anchor every concept's identity is built against, D4); only
            # a freshly created scheme has no concepts yet to protect.
            row.default_language = declared_default_language
        elif declared_default_language and declared_default_language != row.effective_default_language:
            # D18 froze this value once the scheme has concepts; D22 requires the conflict be
            # reported rather than silently kept. Compared against effective_default_language, not
            # the raw stored field, so a scheme relying on the site default that agrees with the
            # file in the same effective language is not a conflict.
            self.report.add_set_aside(
                SetAsideReason.DEFAULT_LANGUAGE_FROZEN,
                subject=declared_uri,
                declared=declared_default_language,
                frozen=row.effective_default_language,
            )
        name = _localized_literal(
            self.skos_graph, self.matcher, declared_node, SKOS.prefLabel, row.effective_default_language
        )
        if not name:
            # The declared default language (or the site's, on fallback) carries no prefLabel on
            # the scheme itself — fall back to any language rather than leaving name unset.
            name = self.skos_graph.first_literal(declared_node, SKOS.prefLabel)
        if name:
            row.name = name
        # SKOS defines no description predicate for a skos:ConceptScheme; dcterms:description is
        # the source (D21), the same alias CONTEXT.md establishes for a concept's own definition.
        # Unlike name, description is written unconditionally, including to empty when the file no
        # longer carries one — nothing anchors identity to it the way default_language is anchored.
        description = _localized_literal(
            self.skos_graph, self.matcher, declared_node, DCTERMS.description, row.effective_default_language
        )
        if not description:
            description = self.skos_graph.first_literal(declared_node, DCTERMS.description)
        row.description = description or ""
        row.static_uri = declared_uri
        row.save()
        if created:
            self.report.add_created(row.uri)
        else:
            self.report.add_updated(row.uri)
        # FIX 12 (D45): the scheme node itself can carry a non-SKOS predicate this module has no
        # place for, exactly as a concept or a collection can.
        report_unmodelled_predicates(
            self.skos_graph, declared_node, declared_uri, self._HANDLED_PREDICATES, self.report
        )
        return row, declared_uri


class ConceptImporter:
    """Creates or updates each concept in the target vocabulary, and everything about it beyond
    identity (FR-006 onward).
    """

    #: Every predicate a concept node carries that this module already reads and accounts for
    #: elsewhere (T021): the identity/scheme predicates T009 reads, every label and note predicate
    #: (:data:`LABEL_PREDICATES`/`NOTE_PREDICATES`), the mapping predicates, and
    #: ``dcterms:description`` (the definition alias).
    _HANDLED_PREDICATES = frozenset(
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

    def __init__(
        self,
        skos_graph: SkosGraph,
        report: ImportReport,
        target_scheme: ConceptScheme,
        target_scheme_uri: str,
        *,
        matcher: LanguageMatcher,
    ) -> None:
        self.skos_graph = skos_graph
        self.report = report
        self.target_scheme = target_scheme
        self.target_scheme_uri = target_scheme_uri
        self.matcher = matcher
        self._mentioned_uris: set[str] = set()

    def import_labels(self, node: rdflib.term.Node, concept: Concept, default_language: str, uri: str) -> None:
        """Store ``concept``'s labels other than its own default-language preferred one (T018, FR-008).

        Replaces whatever labels this concept already held: a label carries no identifier to upsert
        by, and the file is authoritative for what it contains (FR-013). :data:`LABEL_PREDICATES`
        covers ``skos:prefLabel``/``altLabel``/``hiddenLabel``; a preferred label whose *resolved*
        language is ``default_language`` (T008: compared through the matcher, not the raw published
        tag) is skipped — that slot is already ``concept.label`` (T009), and the model refuses a
        second preferred row in that language.

        A value sharing no base language with any configured one is set aside and reported by its
        own published tag, checked ahead of the write rather than letting ``ConceptLabel.clean()``'s
        own refusal raise (T020, FR-014, D25) — that exception protects a direct, out-of-band write,
        not this importer's control flow.

        A second ``skos:prefLabel`` resolving to one configured language — default or not — is the
        same shape of problem for a cardinality reason: the model allows only one ``PREFERRED`` row
        per (concept, language), so the contest is keyed on the *resolved* language and settled once
        per language by :meth:`~controlled_vocabularies.exchange.languages.LanguageMatcher.resolve_winner`
        (T013/T021) — not by grouping on the raw published tag, which let two *different* tags
        resolving to one non-default language both reach ``add_label()`` and crash the run on the
        model's own refusal, because each tag was its own singleton group and neither ever saw the
        other. This is the identical computation ``import_concepts`` already runs for
        ``Concept.label`` over the identical ``preferred_label_in`` candidates, so the two agree by
        construction rather than by coincidence (decisions.md D13). In every configured language's
        slot, default or not, a loser is discriminated by its own published tag against the tag the
        winner computation chose (T014): the same tag is a same-language duplicate and keeps
        ``SURPLUS_PREFERRED_LABEL`` (FIX 4, D38); a different tag is a losing variant and takes
        ``VARIANT_NOT_KEPT`` (T022, decisions.md D14) — the two populations have different remedies,
        which is what :meth:`~controlled_vocabularies.exchange.report.ImportReport.language_account`
        exists to tell apart.
        """
        concept.labels.all().delete()

        # One winner per resolved configured language this concept carries a skos:prefLabel
        # candidate for (T013/T021), read once here rather than grouped by raw published tag.
        preferred_candidates_by_language: dict[str, list[tuple[str, str]]] = {}
        for tag, value in self.skos_graph.preferred_label_in(node):
            resolved = self.matcher.resolve(tag).configured_language
            if resolved is not None:
                preferred_candidates_by_language.setdefault(resolved, []).append((tag, value))
        preferred_winner_by_language: dict[str, tuple[str, str]] = {
            language: self.matcher.resolve_winner(language, candidates)[0]
            for language, candidates in preferred_candidates_by_language.items()
        }
        # The identity-anchoring slot's own winner (FR-016, decisions.md D33) — contested
        # over every tag sharing default_language's base, not only the ones that still
        # resolve exactly to it once a sibling variant gains its own configured slot. Read
        # independently of preferred_winner_by_language[default_language], which a
        # separately-configured sibling variant would otherwise silently narrow.
        identity_winner = self.matcher.resolve_identity_winner(
            default_language, self.skos_graph.preferred_label_in(node)
        )
        default_language_winner_tag = identity_winner[0][0] if identity_winner is not None else None

        for predicate, kind in LABEL_PREDICATES.items():
            for literal in self.skos_graph.graph.objects(node, predicate):
                if not isinstance(literal, rdflib.Literal) or not literal.language:
                    # FIX 15 (D48): a plain literal with no language tag, or an object that is not
                    # even a Literal (e.g. skos:altLabel pointing at a URI), used to be dropped
                    # with no report entry.
                    self.report.add_set_aside(
                        SetAsideReason.NO_LANGUAGE_TAG, subject=uri, predicate=self.skos_graph.skos_curie(predicate)
                    )
                    continue
                published_tag = literal.language
                resolved_language = self.matcher.resolve(published_tag).configured_language
                if kind == ConceptLabel.Kind.PREFERRED and resolved_language == default_language:
                    if (
                        default_language_winner_tag is not None
                        and published_tag.lower() != default_language_winner_tag.lower()
                    ):
                        self.report.add_set_aside(
                            SetAsideReason.VARIANT_NOT_KEPT,
                            subject=uri,
                            language=published_tag,
                            kept_as=default_language,
                        )
                    elif str(literal) != preferred_winner_by_language[default_language][1]:
                        # FIX 4 (D38): the winner already lives as concept.label; a same-tag loser
                        # in this language must still be named, not merely skipped.
                        self.report.add_set_aside(
                            SetAsideReason.SURPLUS_PREFERRED_LABEL, subject=uri, language=default_language
                        )
                    continue
                if resolved_language is None:
                    self.report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=published_tag)
                    continue
                if kind == ConceptLabel.Kind.PREFERRED:
                    winner_tag, winner_value = preferred_winner_by_language[resolved_language]
                    if published_tag.lower() != winner_tag.lower() or str(literal) != winner_value:
                        # T014: the same discriminator the default-language branch already applies
                        # (D24) — a same-tag loser is a same-language duplicate, a different-tag
                        # loser is a contest loser recoverable by configuring its published tag.
                        if published_tag.lower() == winner_tag.lower():
                            self.report.add_set_aside(
                                SetAsideReason.SURPLUS_PREFERRED_LABEL, subject=uri, language=resolved_language
                            )
                        else:
                            self.report.add_set_aside(
                                SetAsideReason.VARIANT_NOT_KEPT,
                                subject=uri,
                                language=published_tag,
                                kept_as=resolved_language,
                            )
                        continue
                concept.add_label(language=resolved_language, kind=kind, text=str(literal))
                if resolved_language.lower() != published_tag.lower():
                    # T009, FR-006: a value stored under a resolved language other than its
                    # published tag is a normalisation, never applied silently (decisions.md D8).
                    self.report.add_normalized(
                        NormalizedReason.LANGUAGE_SUBSTITUTION,
                        subject=uri,
                        language=published_tag,
                        kept_as=resolved_language,
                    )

    def _import_notes(self, node: rdflib.term.Node, concept: Concept, uri: str) -> None:
        """Store ``concept``'s documentary notes — the definition and the six SKOS note kinds
        (T019, FR-009) — through :meth:`~controlled_vocabularies.models.Concept.add_note`.

        Replaces whatever notes this concept already held, the same full-replace rule and reason as
        :meth:`import_labels`. :data:`NOTE_PREDICATES` covers the native SKOS predicates only;
        ``dcterms:description`` is a separate, concept-level definition alias (T021, FR-009,
        D24/D21) — read only in a language with no ``skos:definition`` of its own, and reported as a
        normalisation rather than applied silently. A tag sharing no base language with any
        configured one is set aside the same way :meth:`import_labels` filters one (T020, FR-014,
        D25). Notes carry no per-language cardinality limit (decisions.md D4), so — unlike
        :meth:`import_labels` — there is no contest here and no per-tag winner to compute: every
        variant value resolves and is stored.
        """
        concept.concept_notes.all().delete()
        definition_languages: set[str] = set()
        for predicate, kind in NOTE_PREDICATES.items():
            for literal in self.skos_graph.graph.objects(node, predicate):
                if not isinstance(literal, rdflib.Literal) or not literal.language:
                    # FIX 15 (D48): same defect as import_labels's identical branch.
                    self.report.add_set_aside(
                        SetAsideReason.NO_LANGUAGE_TAG, subject=uri, predicate=self.skos_graph.skos_curie(predicate)
                    )
                    continue
                published_tag = literal.language
                resolved_language = self.matcher.resolve(published_tag).configured_language
                if resolved_language is None:
                    self.report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=published_tag)
                    continue
                if kind == ConceptNote.Kind.DEFINITION:
                    definition_languages.add(resolved_language)
                concept.add_note(language=resolved_language, kind=kind, value=str(literal))
                if resolved_language.lower() != published_tag.lower():
                    # T009, FR-006 (decisions.md D8).
                    self.report.add_normalized(
                        NormalizedReason.LANGUAGE_SUBSTITUTION,
                        subject=uri,
                        language=published_tag,
                        kept_as=resolved_language,
                    )

        for literal in self.skos_graph.graph.objects(node, DCTERMS.description):
            if not isinstance(literal, rdflib.Literal) or not literal.language:
                # FIX 15 (D48): the dcterms:description alias carries the identical defect.
                self.report.add_set_aside(SetAsideReason.NO_LANGUAGE_TAG, subject=uri, predicate="dcterms:description")
                continue
            published_tag = literal.language
            resolved_language = self.matcher.resolve(published_tag).configured_language
            if resolved_language is not None and resolved_language in definition_languages:
                # The concept already carries its own skos:definition in this language.
                continue
            if resolved_language is None:
                self.report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, subject=uri, language=published_tag)
                continue
            concept.add_note(language=resolved_language, kind=ConceptNote.Kind.DEFINITION, value=str(literal))
            self.report.add_normalized(
                NormalizedReason.FOREIGN_DEFINITION,
                subject=uri,
                predicate="dcterms:description",
                language=resolved_language,
            )
            if resolved_language.lower() != published_tag.lower():
                # T009, FR-006: a second, independent axis of normalisation from the predicate
                # substitution just reported — the language changed too (decisions.md D8).
                self.report.add_normalized(
                    NormalizedReason.LANGUAGE_SUBSTITUTION,
                    subject=uri,
                    language=published_tag,
                    kept_as=resolved_language,
                )

    def _import_unheld_values(self, node: rdflib.term.Node, uri: str) -> None:
        """Set aside and report the values on ``concept`` the models have no place for (T021, FR-014).

        Three kinds, each named under the reason that fits it, one entry per value: a
        ``skos:notation``; a cross-vocabulary mapping (:data:`MAPPING_PREDICATES`); and any
        predicate this concept carries that is neither handled elsewhere in this module nor itself
        a SKOS predicate (:func:`report_unmodelled_predicates`). A SKOS predicate this module
        simply does not read *yet* (``skos:broader``/``narrower``/``related``,
        ``skos:member``/``memberList``) is deliberately not reported here — the models do have a
        place for it, just not built yet.
        """
        for _notation in self.skos_graph.graph.objects(node, SKOS.notation):
            self.report.add_set_aside(SetAsideReason.NOTATION, subject=uri)

        for mapping_predicate, name in MAPPING_PREDICATES.items():
            for _obj in self.skos_graph.graph.objects(node, mapping_predicate):
                self.report.add_set_aside(SetAsideReason.MAPPING, subject=uri, predicate=name)

        report_unmodelled_predicates(self.skos_graph, node, uri, self._HANDLED_PREDICATES, self.report)

    def _import_concept_content(self, node: rdflib.term.Node, concept: Concept, uri: str) -> None:
        """Import everything about ``concept`` beyond its identity and default-language label.

        Called once per created-or-updated concept, after it has a primary key (label replacement
        needs one).
        """
        self.import_labels(node, concept, self.target_scheme.effective_default_language, uri)
        self._import_notes(node, concept, uri)
        self._import_unheld_values(node, uri)

    def import_concepts(self, concept_nodes: list[rdflib.term.Node]) -> dict[str, Concept]:
        """Create or update each of ``concept_nodes`` inside the target vocabulary (T009, FR-006).

        For each node, in order: identity is checked (a blank node or refused URI is fatal, D3); a
        concept claiming a *different* vocabulary is set aside (spec Edge Cases §1); a concept with
        no preferred label in the target's effective default language is set aside (FR-006) rather
        than crashing the run. A matched or created :class:`Concept` gets a deterministic,
        scheme-unique slug (:meth:`assign_unique_slug`, FR-007). A URI already belonging to a
        different vocabulary is left there, set aside naming both (review fix 8, D42); a URI already
        held by a :class:`Collection` is set aside rather than made to identify two records at once
        (review fix 10, D43).

        Returns the concepts created or updated, keyed by URI — what :class:`RelationImporter` and
        :class:`CollectionImporter` resolve references against, and what
        :meth:`report_absent_concepts` compares against afterwards.

        ``taken_slugs`` (FIX 16, D49) is fetched once rather than once per concept: a scheme-wide
        slug collision check that used to cost one query per suffix attempt (quadratic across a
        shared-label group, D6) now costs nothing per concept beyond the one shared lookup.
        """
        concepts_by_uri: dict[str, Concept] = {}
        # slug -> the static_uri of the concept currently holding it, seeded from every concept
        # already in target_scheme and kept current as each concept below is assigned its own
        # final slug (FIX 16, D49).
        taken_slugs: dict[str, str | None] = dict(
            Concept.objects.filter(scheme=self.target_scheme).values_list("slug", "static_uri")
        )
        for node in concept_nodes:
            hint = self.skos_graph.first_literal(node, SKOS.prefLabel)
            try:
                uri = self.skos_graph.identify(node, hint=hint)
            except _FatalIdentity as exc:
                self.report.add_fatal(exc.reason, exc.subject, **exc.params)
                continue
            self._mentioned_uris.add(uri)

            other = self.skos_graph.conflicting_scheme_ref(node, self.target_scheme_uri)
            if other is not None:
                self.report.add_set_aside(SetAsideReason.VOCABULARY_MISMATCH, subject=uri, other=other)
                continue

            default_language = self.target_scheme.effective_default_language
            # FR-016, decisions.md D33 (S6 ARCH-001): the identity-anchoring slot's contest
            # runs over every tag sharing default_language's base, not only the ones that
            # resolve exactly to it — configuring a sibling variant in its own right must
            # never move an existing concept's stored label, slug or local URL.
            identity_winner = self.matcher.resolve_identity_winner(
                default_language, self.skos_graph.preferred_label_in(node)
            )
            if identity_winner is None:
                self.report.add_set_aside(SetAsideReason.NO_PREFERRED_LABEL, subject=uri, language=default_language)
                continue
            (winning_tag, label), _losers = identity_winner

            if not slugify(label, allow_unicode=True):
                # FIX 5 (D39): a label made up only of characters slugify() strips derives an empty
                # slug, which Concept.save() refuses — checked ahead of the write (D25) rather than
                # letting that guard's own ValidationError escape. The reported reason names the
                # slug, not the label, since the label itself is fine.
                self.report.add_set_aside(SetAsideReason.EMPTY_SLUG, subject=uri)
                continue

            try:
                concept = Concept.objects.get_by_uri(uri)
                created = False
            except Concept.DoesNotExist:
                # FIX 10 (D43): before minting a new record for this URI, check the *other*
                # identity space — a Collection may already hold it.
                try:
                    Collection.objects.get_by_uri(uri)
                except Collection.DoesNotExist:
                    pass
                else:
                    self.report.add_set_aside(SetAsideReason.URI_HELD_BY_DIFFERENT_KIND, subject=uri)
                    continue
                concept = Concept(scheme=self.target_scheme)
                created = True

            if not created and concept.scheme_id != self.target_scheme.pk:
                # FIX 8 (D42): a concept matched here already belongs to a *different* vocabulary.
                # Moving a record between vocabularies is a curatorial act, never a side effect of
                # reading a file.
                self.report.add_set_aside(
                    SetAsideReason.ALREADY_IN_ANOTHER_VOCABULARY,
                    subject=uri,
                    current=concept.scheme.uri,
                    target=self.target_scheme.uri,
                )
                continue

            concept.scheme = self.target_scheme
            concept.static_uri = uri
            concept.label = label
            self.assign_unique_slug(concept, taken_slugs)
            concept.save()
            if winning_tag.lower() != default_language.lower():
                # T009, FR-006: concept.label is stored content too — a value that made it in
                # under a different language than published is a normalisation, not a silent
                # substitution (decisions.md D8).
                self.report.add_normalized(
                    NormalizedReason.LANGUAGE_SUBSTITUTION, subject=uri, language=winning_tag, kept_as=default_language
                )
            concepts_by_uri[uri] = concept
            self._import_concept_content(node, concept, uri)
            if created:
                self.report.add_created(uri)
            else:
                self.report.add_updated(uri)

        return concepts_by_uri

    def report_absent_concepts(self) -> None:
        """Report every existing concept of the target vocabulary that :meth:`import_concepts`
        never saw mentioned (T013, FR-013) — left completely untouched. A concept set aside for
        claiming a *different* vocabulary is not "absent from source": the file does mention it.

        Called by the orchestrator after relations and collections have been reconciled (FIX 7/20,
        D41/D53: filtered and sorted in Python by ``.uri`` rather than a database ``__in`` clause
        sized by the file's own concept count).
        """
        absent = [
            concept
            for concept in Concept.objects.filter(scheme=self.target_scheme)
            if concept.static_uri not in self._mentioned_uris
        ]
        for concept in sorted(absent, key=lambda row: row.uri):
            self.report.add_absent_from_source(concept.uri)

    @staticmethod
    def assign_unique_slug(concept: Concept, taken_slugs: dict[str, str | None]) -> None:
        """Give ``concept`` a deterministic, scheme-unique slug derived from its label (T010, FR-007).

        Nothing is derived from ``concept.static_uri`` — identity and slug are deliberately
        independent. ``Concept.save()`` only *refuses* a collision rather than resolving one
        (research R4, written for curator-authored content where a shared label is rare); a
        published file is not so well-behaved (two source concepts commonly share one, D6), so the
        importer resolves it itself: the same base derivation, with a deterministic numeric suffix
        appended only when that value already belongs to a *different* concept in the same scheme.

        ``taken_slugs`` (FIX 16, D49) maps every claimed slug to its claimant's ``static_uri`` —
        fetched once by :meth:`import_concepts`, mutated in place here so the next concept in the
        run sees it as taken. Keyed by ``static_uri`` rather than ``pk``, since a newly created
        concept has no pk yet at the point its slug is decided.

        ``slug_is_manual`` stops ``Concept.save()`` from re-deriving this value on a later,
        unrelated save; it does not pin the slug the way a curator's own manual slug is pinned —
        every re-import recomputes it fresh from the (possibly since-renamed) label, per D6.
        """
        base = slugify(concept.label, allow_unicode=True)
        candidate = base
        suffix = 1
        while taken_slugs.get(candidate, concept.static_uri) != concept.static_uri:
            suffix += 1
            candidate = f"{base}-{suffix}"
        concept.slug = candidate
        concept.slug_is_manual = True
        taken_slugs[candidate] = concept.static_uri


class _ConceptReferenceResolverMixin:
    """Shared by :class:`RelationImporter` and :class:`CollectionImporter`, both of which resolve a
    URI back to the :class:`Concept` it identifies (D30 treats a membership as the same shape of
    problem a relationship already is) — a small shared base rather than duplicating the method,
    since neither importer is a more natural home for it than the other.

    A subclass must set ``self.target_scheme`` before calling :meth:`_resolve_concept_reference`.
    """

    target_scheme: ConceptScheme

    def _resolve_concept_reference(self, uri: str, successful_concepts: dict[str, Concept]) -> Concept | None:
        """Return the :class:`Concept` ``uri`` names, or ``None`` when it cannot back a relation or
        a collection membership (FR-011).

        Tries this run's own writes first (``successful_concepts``, keyed by URI); otherwise falls
        back to :meth:`~controlled_vocabularies.models.ConceptManager.get_by_uri` for a concept an
        earlier import already created (spec Acceptance Scenario US4-6). A match belonging to a
        *different* vocabulary than the one being imported is treated as no match at all
        (research.md R4, D29) — the same "collect, don't crash" discipline every other set-aside
        reason follows.
        """
        concept = successful_concepts.get(uri)
        if concept is None:
            try:
                concept = Concept.objects.get_by_uri(uri)
            except Concept.DoesNotExist:
                return None
        if concept.scheme_id != self.target_scheme.pk:
            return None
        return concept


class RelationImporter(_ConceptReferenceResolverMixin):
    """Reconciles ``skos:broader``/``skos:narrower``/``skos:related`` into stored
    :class:`~controlled_vocabularies.models.ConceptRelation` rows (FR-010/FR-011).
    """

    def __init__(self, skos_graph: SkosGraph, report: ImportReport, target_scheme: ConceptScheme) -> None:
        self.skos_graph = skos_graph
        self.report = report
        self.target_scheme = target_scheme

    def import_relations(self, successful_concepts: dict[str, Concept]) -> None:
        """Reconcile ``skos:broader``/``skos:narrower``/``skos:related`` into the single canonical
        BROADER/RELATED row research.md R4 defines for each pair, for every concept this run
        created or updated (T023/T024, FR-010/FR-011/FR-013).

        Read only from ``successful_concepts`` — a concept set aside for another reason has no row
        to attach a relation to. ``skos:narrower`` resolves to the same stored BROADER row as
        ``skos:broader`` with its ends swapped
        (:meth:`~controlled_vocabularies.models.Concept.add_broader`'s contract: ``source`` is the
        narrower end); ``skos:related`` is symmetric, keyed by an unordered pair — either direction
        for the same pair collapses to the same dict key, so which one the file states first never
        matters.

        An existing row is only ever a *deletion* candidate when **both** its ends were created or
        updated this run (D30): only then has the file had the opportunity to speak about it at
        all. This is computed as one whole pass over every concept touched, not incrementally per
        concept, because a relation is commonly asserted from only one of its two ends — an
        incremental delete-and-recreate would delete a row a sibling's own pass had only just
        written.

        A broader/narrower pair always wins over the same pair resolved as related (review fix 2,
        D37): SKOS declares the two disjoint, and the model refuses to store both
        (:meth:`~controlled_vocabularies.models.ConceptRelation._reject_disjointness_violation`).
        Broader/narrower rows are written first, each clearing any conflicting stored RELATED row
        for the same pair — not only one the bulk deletion pass above would catch, since that pass
        only considers a row when *both* ends were rewritten this run (D30), and the far end of a
        newly-stated broader edge may instead be a concept only referenced this run (D29's
        ``get_by_uri`` fallback). Related rows are written after, checked the same way against a
        conflicting BROADER row, and set aside rather than attempted when one is found.
        """
        graph = self.skos_graph.graph
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
            if narrower_uri == broader_uri:
                # FIX 6 (D40): a concept stating skos:broader/skos:narrower about itself is not a
                # real hierarchy edge (the model's own _reject_self would refuse it); nothing
                # meaningful to reconcile.
                continue
            narrower_concept = self._resolve_concept_reference(narrower_uri, successful_concepts)
            broader_concept = self._resolve_concept_reference(broader_uri, successful_concepts)
            if narrower_concept is None or broader_concept is None:
                subject_uri = narrower_uri if narrower_concept is not None else broader_uri
                other_uri = broader_uri if narrower_concept is not None else narrower_uri
                self.report.add_set_aside(SetAsideReason.MISSING_RELATION_END, subject=subject_uri, other=other_uri)
                continue
            resolved_broader.add((narrower_concept.pk, broader_concept.pk))
            concepts_by_pk[narrower_concept.pk] = narrower_concept
            concepts_by_pk[broader_concept.pk] = broader_concept

        for pair in desired_related:
            if len(pair) < 2:
                # A concept stating skos:related about itself — the model's own _reject_self would
                # refuse it; nothing meaningful to reconcile.
                continue
            a_uri, b_uri = tuple(pair)
            a_concept = self._resolve_concept_reference(a_uri, successful_concepts)
            b_concept = self._resolve_concept_reference(b_uri, successful_concepts)
            if a_concept is None or b_concept is None:
                subject_uri = a_uri if a_concept is not None else b_uri
                other_uri = b_uri if a_concept is not None else a_uri
                self.report.add_set_aside(SetAsideReason.MISSING_RELATION_END, subject=subject_uri, other=other_uri)
                continue
            resolved_related.add(frozenset({a_concept.pk, b_concept.pk}))
            concepts_by_pk[a_concept.pk] = a_concept
            concepts_by_pk[b_concept.pk] = b_concept

        successful_ids = {concept.pk for concept in successful_concepts.values()}

        # Both ends in successful_ids, not either (D30): a row with one end outside this run's own
        # writes is only half spoken about by the file.
        #
        # FIX 20 (D53): scoped by source__scheme=target_scheme — one bind parameter — rather than
        # source_id__in=successful_ids, target_id__in=successful_ids (2N parameters together).
        # Django does not chunk an `__in` clause for PostgreSQL, whose 65,535-bind-parameter limit
        # this reaches around 33k concepts, inside the "tens of thousands" the spec targets. Every
        # ConceptRelation row already has both ends in the same scheme
        # (ConceptRelation._reject_cross_scheme), so scoping by source's scheme alone already scopes
        # target's too; "both ends in successful_ids" is then checked in Python against the
        # in-memory set, reproducing the original SQL-level condition exactly.
        existing_broader = ConceptRelation.objects.filter(
            kind=ConceptRelation.Kind.BROADER, source__scheme=self.target_scheme
        )
        for row in existing_broader:
            if row.source_id not in successful_ids or row.target_id not in successful_ids:
                continue
            if (row.source_id, row.target_id) not in resolved_broader:
                row.delete()

        existing_related = ConceptRelation.objects.filter(
            kind=ConceptRelation.Kind.RELATED, source__scheme=self.target_scheme
        )
        for row in existing_related:
            if row.source_id not in successful_ids or row.target_id not in successful_ids:
                continue
            if frozenset({row.source_id, row.target_id}) not in resolved_related:
                row.delete()

        for narrower_pk, broader_pk in resolved_broader:
            already_stored = ConceptRelation.objects.filter(
                source_id=narrower_pk, target_id=broader_pk, kind=ConceptRelation.Kind.BROADER
            ).exists()
            if already_stored:
                continue
            # FIX 2, route 2 (D37): an existing RELATED row for this exact pair may not have been a
            # candidate for the bulk deletion pass above — that pass only considers a row when
            # *both* its ends were rewritten by this run (D30), and the far end of a newly-stated
            # broader edge may instead be a concept only referenced this run (D29). Checked directly
            # and unconditionally, so a stale RELATED row from an earlier run can never survive to
            # make add_broader raise the model's own disjointness ValidationError.
            conflicting_related = ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).filter(
                Q(source_id=narrower_pk, target_id=broader_pk) | Q(source_id=broader_pk, target_id=narrower_pk)
            )
            for row in conflicting_related:
                self.report.add_set_aside(
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
            # FIX 2, the symmetric route (D37): the mirror image of the broader-side check just
            # above — a BROADER row surviving from an earlier run for the same D30 reason must be
            # checked before add_related too, or the model's own guard raises here instead.
            conflicting_broader = (
                ConceptRelation.objects.filter(kind=ConceptRelation.Kind.BROADER)
                .filter(Q(source_id=a_pk, target_id=b_pk) | Q(source_id=b_pk, target_id=a_pk))
                .exists()
            )
            if conflicting_broader:
                self.report.add_set_aside(
                    SetAsideReason.RELATION_DISJOINTNESS,
                    subject=concepts_by_pk[a_pk].static_uri,
                    other=concepts_by_pk[b_pk].static_uri,
                )
                continue
            concepts_by_pk[a_pk].add_related(concepts_by_pk[b_pk])


class CollectionImporter(_ConceptReferenceResolverMixin):
    """Creates or updates every ``skos:Collection``/``skos:OrderedCollection`` in the target
    vocabulary, with its membership (T027/T028, FR-012).
    """

    #: Predicates a collection node carries that :meth:`import_collections` already reads and
    #: accounts for (FIX 12, D45): its own identity, name, and membership (both ``skos:member`` and
    #: ``skos:memberList``, per FIX 11).
    _HANDLED_PREDICATES = frozenset(
        {
            rdflib.RDF.type,
            SKOS.prefLabel,
            SKOS.member,
            SKOS.memberList,
        }
    )

    def __init__(
        self, skos_graph: SkosGraph, report: ImportReport, target_scheme: ConceptScheme, *, matcher: LanguageMatcher
    ) -> None:
        self.skos_graph = skos_graph
        self.report = report
        self.target_scheme = target_scheme
        self.matcher = matcher

    def import_collections(self, successful_concepts: dict[str, Concept]) -> None:
        """Create or update every ``skos:Collection``/``skos:OrderedCollection`` in the graph inside
        the target vocabulary, with its membership (T027/T028, FR-012).

        Run after every concept this run created or updated already has a primary key — membership
        needs :meth:`_resolve_concept_reference` exactly as a relationship end does. A collection's
        identity is checked with the same :meth:`SkosGraph.identify` a concept or the vocabulary
        itself uses (D3): a blank-node collection is fatal, collected, and the run continues (FR-003).
        The structural exception is ``skos:memberList`` itself — an RDF list, made of blank nodes by
        construction (research.md R2) — read through ``graph.items()``, which yields the member
        *URIs*, never the list's own cells, so those blank nodes never reach ``identify``. A URI
        matching an existing collection already in a different vocabulary is left untouched, set
        aside naming both (review fix 9, D42); a URI matching no collection but already held by a
        :class:`Concept` is set aside rather than made to identify two records at once (fix 10, D43).

        ``skos:member`` (unordered) or ``skos:memberList`` (ordered, in file order) name the desired
        membership. An ordered collection with no ``memberList`` falls back to ``member``, sorted;
        when both are present, ``memberList`` governs order and any ``member`` it omits is appended
        after, sorted (review fix 11, D44 — ``memberList`` narrows ``member`` rather than replacing
        it). Each member URI is resolved through :meth:`_resolve_concept_reference`; one that
        resolves to nothing is set aside (:data:`SetAsideReason.MISSING_MEMBER`) rather than failing
        the run (FR-011), and the collection is still created holding whatever did resolve.

        Membership is written only through the model's own API (``Collection.add``/``remove``/
        ``set_member_order``), never a :class:`~controlled_vocabularies.models.CollectionMember` row
        constructed directly, so the model's cross-scheme check always runs. An existing membership
        is only ever a *removal* candidate when its member belongs to ``successful_concepts`` (D30,
        the same rule relationship reconciliation follows, applied to a second model).

        Finally (T034, FR-013), every existing collection of the target vocabulary never seen among
        ``collection_nodes`` is left completely untouched and named in ``report.absent_from_source``.
        """
        graph = self.skos_graph.graph
        collection_nodes = sorted(
            set(graph.subjects(rdflib.RDF.type, SKOS.Collection))
            | set(graph.subjects(rdflib.RDF.type, SKOS.OrderedCollection)),
            key=str,
        )
        successful_ids = {concept.pk for concept in successful_concepts.values()}
        mentioned_uris: set[str] = set()

        for node in collection_nodes:
            hint = self.skos_graph.first_literal(node, SKOS.prefLabel)
            try:
                uri = self.skos_graph.identify(node, hint=hint)
            except _FatalIdentity as exc:
                self.report.add_fatal(exc.reason, exc.subject, **exc.params)
                continue
            mentioned_uris.add(uri)

            ordered = (node, rdflib.RDF.type, SKOS.OrderedCollection) in graph

            try:
                row = Collection.objects.get_by_uri(uri)
                created = False
            except Collection.DoesNotExist:
                # FIX 10 (D43): the mirror image of the same check in
                # ConceptImporter.import_concepts — this URI may already be held by a Concept
                # instead. The two identity spaces are checked independently of each other.
                try:
                    Concept.objects.get_by_uri(uri)
                except Concept.DoesNotExist:
                    pass
                else:
                    self.report.add_set_aside(SetAsideReason.URI_HELD_BY_DIFFERENT_KIND, subject=uri)
                    continue
                row = Collection(scheme=self.target_scheme)
                created = True

            if not created and row.scheme_id != self.target_scheme.pk:
                # FIX 9 (D42): the same rule FIX 8 gives a concept, applied to a collection.
                # Reassigning it (and its membership) to target_scheme is exactly the state
                # CollectionMember._reject_cross_scheme exists to prevent.
                self.report.add_set_aside(
                    SetAsideReason.ALREADY_IN_ANOTHER_VOCABULARY,
                    subject=uri,
                    current=row.scheme.uri,
                    target=self.target_scheme.uri,
                )
                continue

            row.scheme = self.target_scheme
            row.static_uri = uri
            name = _localized_literal(
                self.skos_graph, self.matcher, node, SKOS.prefLabel, self.target_scheme.effective_default_language
            )
            if not name:
                name = self.skos_graph.first_literal(node, SKOS.prefLabel)
            if name:
                row.name = name
            row.ordered = ordered
            row.save()
            if created:
                self.report.add_created(uri)
            else:
                self.report.add_updated(uri)
            report_unmodelled_predicates(self.skos_graph, node, uri, self._HANDLED_PREDICATES, self.report)

            if ordered:
                member_list_node = graph.value(node, SKOS.memberList)
                if member_list_node is not None:
                    try:
                        ordered_uris = [str(item) for item in graph.items(member_list_node)]
                    except ValueError as exc:
                        # FIX 18 (D51): a malformed skos:memberList whose rdf:rest chain loops back
                        # on itself instead of terminating in rdf:nil makes graph.items() raise a
                        # bare ValueError. Not collected as a per-record set-aside: an infinite list
                        # has no well-defined membership to import "the rest of", so the whole run
                        # is refused rather than silently importing a partial one.
                        raise SkosImportError(
                            _(
                                "'%(subject)s' has a skos:memberList that does not terminate (its rdf:rest "
                                "chain loops back on itself); the import was refused."
                            ),
                            params={"subject": uri},
                            code="skos_cyclic_member_list",
                        ) from exc
                    # FIX 11 (D44): skos:memberList narrows skos:member rather than replacing it —
                    # a skos:member the memberList omits is still an explicit membership assertion
                    # and must not disappear (Article XI). Appended after memberList's own order, in
                    # the same deterministic sorted order the unordered branch below already uses.
                    member_only = sorted({str(obj) for obj in graph.objects(node, SKOS.member)} - set(ordered_uris))
                    member_uris = ordered_uris + member_only
                else:
                    # FIX 11 (D44): an ordered collection asserted only with skos:member — no
                    # memberList at all — still has real, explicit membership to import; read the
                    # same deterministic sorted way the unordered branch already reads skos:member.
                    member_uris = sorted({str(obj) for obj in graph.objects(node, SKOS.member)})
            else:
                member_uris = sorted({str(obj) for obj in graph.objects(node, SKOS.member)})

            resolved: list[Concept] = []
            seen_pks: set[int] = set()
            for member_uri in member_uris:
                concept = self._resolve_concept_reference(member_uri, successful_concepts)
                if concept is None:
                    self.report.add_set_aside(SetAsideReason.MISSING_MEMBER, subject=member_uri, collection=uri)
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

        # FIX 7 (D41): a row whose static_uri is NULL — a locally authored collection the file
        # could never mention, since it carries no external identifier — is reported by its own
        # .uri, never the raw column, which for such a row would be None; sorted in Python since
        # .uri is not a database column .order_by() can reach.
        #
        # FIX 20 (D53): filtered in Python against the in-memory mentioned_uris set rather than
        # .exclude(static_uri__in=mentioned_uris) — the same __in-sized-by-file concern
        # RelationImporter's own fix addresses, here for a string __in rather than an integer one.
        absent = [
            collection
            for collection in Collection.objects.filter(scheme=self.target_scheme)
            if collection.static_uri not in mentioned_uris
        ]
        for collection in sorted(absent, key=lambda row: row.uri):
            self.report.add_absent_from_source(collection.uri)


class SkosImporter:
    """Orchestrates one run of :func:`import_skos`: holds the graph, report, target vocabulary, and
    the transaction, and drives :class:`SchemeResolver`, :class:`ConceptImporter`,
    :class:`RelationImporter` and :class:`CollectionImporter` in sequence (FR-001, FR-003).
    """

    def __init__(
        self,
        file: str | Path,
        *,
        serialization: str | None = None,
        scheme: ConceptScheme | None = None,
    ) -> None:
        self.file = file
        self.serialization = serialization
        self.target = scheme
        self.report = ImportReport()

    def run(self) -> ImportReport:
        """Import :attr:`file` and return the run's :class:`ImportReport` (FR-001).

        Re-running an import upserts rather than deleting and recreating: a record the file still
        contains has its content matched to the file exactly, including removing a value the file
        no longer carries, while a record the file simply does not mention is left completely
        untouched and named in ``report.absent_from_source`` (FR-013). Anything the file carries
        that the models have no place for is set aside and named in the report rather than dropped
        in silence (FR-014, Article XI).

        The whole run sits inside one transaction (research.md R7): a fatal finding is collected
        rather than raised immediately, so a file with more than one problem reports all of them;
        only once nothing further can be checked does :class:`SkosImportFailed` actually raise,
        which is what triggers the rollback. A successful run's ``report.fatal`` is always empty.
        """
        skos_graph = SkosGraph.from_file(self.file, serialization=self.serialization)
        source_label = str(self.file)

        with transaction.atomic():
            declared_nodes = sorted(skos_graph.graph.subjects(rdflib.RDF.type, SKOS.ConceptScheme), key=str)
            # FIX 17 (D50): a node the file identifies as a concept only through
            # skos:inScheme/topConceptOf/hasTopConcept — never through rdf:type skos:Concept — is
            # folded in here, before scheme disambiguation runs, so it is neither invisible to the
            # import nor to choose_declared_scheme's own membership count.
            concept_nodes = sorted(
                set(skos_graph.graph.subjects(rdflib.RDF.type, SKOS.Concept)) | skos_graph.implied_concept_nodes(),
                key=str,
            )
            # The matcher is built once per run, before any concept is written, from
            # the whole file's predominance counts (research.md R2) — settling a
            # variant contest needs the whole file counted first. Passed as a
            # constructor argument rather than let each collaborator build its own
            # (plan.md "One winner, one computation").
            matcher = LanguageMatcher.from_settings(skos_graph.preferred_label_tag_counts(concept_nodes))

            resolver = SchemeResolver(
                skos_graph, self.report, target=self.target, source_label=source_label, matcher=matcher
            )
            declared_node = resolver.choose_declared_scheme(declared_nodes, concept_nodes)
            target_scheme, declared_uri = (
                (None, None) if self.report.fatal else resolver.resolve_scheme(declared_node, concept_nodes)
            )

            if target_scheme is not None and declared_uri is not None:
                # SEC-001, decisions.md D34: effective_default_language falls back to
                # settings.LANGUAGE_CODE unvalidated against settings.LANGUAGES — Django's own
                # shipped defaults are exactly this shape. resolve() can only ever return a code
                # taken verbatim from LANGUAGES, so if this value is not itself an exact member
                # (is_exact), no candidate could ever match it and every concept would be set
                # aside one at a time for no gain to a curator. Caught once, here, naming the
                # misconfiguration instead.
                if not matcher.resolve(target_scheme.effective_default_language).is_exact:
                    self.report.add_fatal(
                        FatalReason.DEFAULT_LANGUAGE_UNCONFIGURED,
                        subject=declared_uri,
                        language=target_scheme.effective_default_language,
                    )
                else:
                    concept_importer = ConceptImporter(
                        skos_graph, self.report, target_scheme, declared_uri, matcher=matcher
                    )
                    successful_concepts = concept_importer.import_concepts(concept_nodes)
                    RelationImporter(skos_graph, self.report, target_scheme).import_relations(successful_concepts)
                    CollectionImporter(skos_graph, self.report, target_scheme, matcher=matcher).import_collections(
                        successful_concepts
                    )
                    concept_importer.report_absent_concepts()

            if self.report.fatal:
                raise SkosImportFailed(self.report)

        return self.report


def import_skos(
    file: str | Path,
    *,
    serialization: str | None = None,
    scheme: ConceptScheme | None = None,
) -> ImportReport:
    """Import a published SKOS file and return a structured report (FR-001).

    A thin wrapper over :class:`SkosImporter` — see :meth:`SkosImporter.run` for the transaction,
    upsert, and set-aside semantics. ``scheme`` names a target vocabulary for a file that declares
    none of its own, or is checked against one the file does declare — a mismatch fails the run
    and writes nothing (FR-005).
    """
    return SkosImporter(file, serialization=serialization, scheme=scheme).run()
