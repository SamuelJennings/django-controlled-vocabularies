"""The structured outcome of one import run (FR-015, decisions.md D7).

``ImportReport`` is the feature's public contract alongside the import itself: #51
groups and counts what was set aside for a curator, and #52 renders a command-line
summary and a rehearsal preview from it, neither re-reading the file nor parsing
prose (spec Acceptance Scenario US1-11). Four buckets, each inspectable as data:
what was created, what was updated, what was set aside with a reason, and what the
source no longer mentions.

A set-aside reason is drawn from the closed :class:`SetAsideReason` vocabulary,
never freeform text (Article XII, FR-016). An entry stores its reason, its
subject, and any reason-specific parameters as plain data — the same shape
:class:`~django.core.exceptions.ValidationError` uses — so the message renders in
the caller's active language at display time rather than being baked into one
language at creation time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import TextChoices
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


class SetAsideReason(TextChoices):
    """The closed vocabulary of reasons an import cannot store something (FR-014).

    Covers what the spec's Key Entities and FR-014 name: a language the site is
    not configured for, a predicate or construct the models have no place for, a
    relationship or membership end missing from both the file and the database, a
    concept with no usable preferred label, and a record claiming a vocabulary
    other than the one being imported. Not "fatal" findings (a missing or blank-node
    identity) — those fail the whole run rather than being set aside (D3, D8) and
    are not part of this vocabulary.

    ``DEFAULT_LANGUAGE_FROZEN`` (US-2, decisions.md D18/D22) is the one member
    naming a conflict at the vocabulary level rather than a value that could
    not be stored: a re-imported file's declared default language differing
    from the one already frozen on an existing, concept-bearing scheme.
    ``RELATION_DISJOINTNESS`` (review fix, decisions.md D37) names a pair
    stated, in one file or split across two runs, as both a hierarchical
    (broader/narrower) and a related relation — SKOS declares the two
    mutually exclusive (models.py ``ConceptRelation._reject_disjointness_violation``);
    the hierarchical relation always wins and the related statement is the
    one set aside. ``SURPLUS_PREFERRED_LABEL`` (review fix, decisions.md D38)
    names a preferred label beyond the first a concept carries in one
    language — the model allows only one ``PREFERRED`` row per (concept,
    language) — whichever value is not the deterministically-kept one is
    the one set aside, in the vocabulary's default language exactly as much
    as in any other configured language. ``EMPTY_SLUG`` (review fix,
    decisions.md D39) names a concept whose preferred label is made up only
    of characters ``slugify()`` strips — the label itself is fine, but the
    slug it derives is empty, which the model refuses to store; the concept
    is set aside rather than crash the run on that refusal.
    ``ALREADY_IN_ANOTHER_VOCABULARY`` (review fix 8/9, decisions.md D42) names
    a concept or collection whose identity is already held by a *different*
    vocabulary than the one being imported: moving a record between
    vocabularies is a curatorial act, never a side effect of reading a file,
    so the existing record is left exactly where it is rather than
    reassigned.
    """

    UNCONFIGURED_LANGUAGE = "unconfigured_language", _("language not configured")
    UNMODELLED_PREDICATE = "unmodelled_predicate", _("predicate not modelled")
    NOTATION = "notation", _("notation")
    MAPPING = "mapping", _("mapping to another vocabulary")
    MISSING_RELATION_END = "missing_relation_end", _("relationship end not found")
    MISSING_MEMBER = "missing_member", _("collection member not found")
    NO_PREFERRED_LABEL = "no_preferred_label", _("no preferred label in default language")
    VOCABULARY_MISMATCH = "vocabulary_mismatch", _("belongs to a different vocabulary")
    DEFAULT_LANGUAGE_FROZEN = "default_language_frozen", _("default language already fixed")
    RELATION_DISJOINTNESS = "relation_disjointness", _("broader/narrower and related both claimed for a pair")
    SURPLUS_PREFERRED_LABEL = "surplus_preferred_label", _("surplus preferred label in a language")
    EMPTY_SLUG = "empty_slug", _("preferred label produces no usable slug")
    ALREADY_IN_ANOTHER_VOCABULARY = "already_in_another_vocabulary", _("already belongs to another vocabulary")

    @property
    def template(self) -> Promise:
        """The translatable, named-placeholder message template for this reason.

        Every template declares ``%(subject)s`` (the record or value at fault);
        reasons that need more context declare their own named placeholders
        alongside it (Article XII) — supplied via :attr:`SetAsideEntry.params`.
        """
        return _REASON_TEMPLATES[self]


_REASON_TEMPLATES: dict[SetAsideReason, Promise] = {
    SetAsideReason.UNCONFIGURED_LANGUAGE: _(
        "'%(subject)s' carries a value in the language '%(language)s', which the site "
        "is not configured for; it was not stored."
    ),
    SetAsideReason.UNMODELLED_PREDICATE: _(
        "'%(subject)s' carries the predicate '%(predicate)s', which the models have no place for; it was not stored."
    ),
    SetAsideReason.NOTATION: _(
        "'%(subject)s' carries a notation, which the models have no place for; it was not stored."
    ),
    SetAsideReason.MAPPING: _(
        "'%(subject)s' carries a mapping to another vocabulary ('%(predicate)s'), which the "
        "models have no place for; it was not stored."
    ),
    SetAsideReason.MISSING_RELATION_END: _(
        "The relationship between '%(subject)s' and '%(other)s' was not stored because "
        "'%(other)s' is neither in this file nor already in the database."
    ),
    SetAsideReason.MISSING_MEMBER: _(
        "'%(subject)s' was not added to the collection '%(collection)s' because it is neither "
        "in this file nor already in the database."
    ),
    SetAsideReason.NO_PREFERRED_LABEL: _(
        "'%(subject)s' has no preferred label in the vocabulary's default language '%(language)s' and was set aside."
    ),
    SetAsideReason.VOCABULARY_MISMATCH: _(
        "'%(subject)s' claims the vocabulary '%(other)s', not the one being imported, and was set aside."
    ),
    SetAsideReason.DEFAULT_LANGUAGE_FROZEN: _(
        "'%(subject)s' declares its default language as '%(declared)s', but this vocabulary's default "
        "language is already fixed to '%(frozen)s' because it already has concepts; the declared value "
        "was not applied."
    ),
    SetAsideReason.RELATION_DISJOINTNESS: _(
        "'%(subject)s' and '%(other)s' are joined as broader/narrower, so the related statement between "
        "them was set aside; a broader/narrower pair and a related pair are mutually exclusive."
    ),
    SetAsideReason.SURPLUS_PREFERRED_LABEL: _(
        "'%(subject)s' carries more than one preferred label in the language '%(language)s'; only one is "
        "kept and the surplus value was set aside."
    ),
    SetAsideReason.EMPTY_SLUG: _(
        "'%(subject)s' has a preferred label made up only of characters this application strips when "
        "deriving a URL slug, so no usable slug could be derived from it; it was set aside."
    ),
    SetAsideReason.ALREADY_IN_ANOTHER_VOCABULARY: _(
        "'%(subject)s' already belongs to the vocabulary '%(current)s'; importing it into '%(target)s' "
        "would move it between vocabularies, so it was left where it is."
    ),
}


@dataclass(frozen=True)
class SetAsideEntry:
    """One value the import could not store, with what it was and why (FR-014/FR-015).

    ``subject`` names the record or value at fault — typically a URI. ``params``
    carries whatever else :attr:`SetAsideReason.template` needs (a language, a
    predicate CURIE, the other end of a relationship), keyed by name, the same
    shape :class:`~django.core.exceptions.ValidationError` uses. Both are read
    directly by a caller that groups or counts (spec US1-11); :meth:`render` is
    for display only.
    """

    reason: SetAsideReason
    subject: str
    params: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        """This entry's message in the caller's active language (Article XII)."""
        return str(self.reason.template) % {"subject": self.subject, **self.params}


class FatalReason(TextChoices):
    """The closed vocabulary of reasons a run fails outright (FR-004, decisions.md D3/D8).

    Deliberately separate from :class:`SetAsideReason`: everything in that
    vocabulary lets the rest of the file still import; everything here means
    the whole run fails and the transaction rolls back (T011,
    ``research.md`` R7). Covers the small fatal set decisions.md D8 names —
    a missing or refused record identity — plus the two ways the vocabulary
    itself cannot be resolved (FR-005): the file names none and the caller
    named no target, or the caller's named target contradicts the file's own.
    """

    MISSING_IDENTITY = "missing_identity", _("identifier missing or blank")
    REFUSED_IDENTITY = "refused_identity", _("identifier refused by the identity rules")
    VOCABULARY_UNDETERMINED = "vocabulary_undetermined", _("vocabulary not declared and no target named")
    VOCABULARY_TARGET_MISMATCH = "vocabulary_target_mismatch", _("declared vocabulary does not match the named target")
    VOCABULARY_AMBIGUOUS = "vocabulary_ambiguous", _("the file declares more than one vocabulary and none was named")

    @property
    def template(self) -> Promise:
        """The translatable, named-placeholder message template for this reason.

        Every template declares ``%(subject)s``, the same shape
        :class:`SetAsideReason.template` uses (Article XII).
        """
        return _FATAL_TEMPLATES[self]


_FATAL_TEMPLATES: dict[FatalReason, Promise] = {
    FatalReason.MISSING_IDENTITY: _(
        "'%(subject)s' has no identifier that survives re-serialization (a blank node); the run was refused."
    ),
    FatalReason.REFUSED_IDENTITY: _("'%(subject)s' is not an identifier the application accepts; the run was refused."),
    FatalReason.VOCABULARY_UNDETERMINED: _(
        "'%(subject)s' declares no vocabulary of its own, and no target vocabulary was named; the run was refused."
    ),
    FatalReason.VOCABULARY_TARGET_MISMATCH: _(
        "'%(subject)s' is not the vocabulary named as the import's target ('%(target)s'); the run was refused."
    ),
    FatalReason.VOCABULARY_AMBIGUOUS: _(
        "'%(subject)s' declares more than one vocabulary (%(declared)s) and none was named as the import's "
        "target; the run was refused."
    ),
}


@dataclass(frozen=True)
class FatalFinding:
    """One reason a run failed outright, with what it was and why (FR-004/FR-015).

    The fatal counterpart of :class:`SetAsideEntry`, with the same shape —
    ``subject`` names the record or file at fault, ``params`` carries whatever
    else the reason's template needs — kept as a distinct type because a
    fatal finding is never one of :class:`SetAsideReason`'s reasons
    (decisions.md's report.py docstring: fatal findings "are not part of
    this vocabulary").
    """

    reason: FatalReason
    subject: str
    params: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        """This entry's message in the caller's active language (Article XII)."""
        return str(self.reason.template) % {"subject": self.subject, **self.params}


class NormalizedReason(TextChoices):
    """The closed vocabulary of predicates this import stores under a different
    model field than the one the file itself asserted (T021, FR-009, decisions.md D24).

    Deliberately separate from :class:`SetAsideReason`: every set-aside entry
    names a value that was *not* stored; every entry here names one that
    *was*, just not verbatim under the source's own predicate. Article XI's
    "never applied silently" reaches both — a value that made it in under a
    different name still needs to be visible as a normalisation, not only a
    value that did not make it in at all.
    """

    FOREIGN_DEFINITION = "foreign_definition", _("definition read from a foreign predicate")

    @property
    def template(self) -> Promise:
        """The translatable, named-placeholder message template for this reason.

        Every template declares ``%(subject)s``, the same shape
        :class:`SetAsideReason.template` uses (Article XII).
        """
        return _NORMALIZED_TEMPLATES[self]


_NORMALIZED_TEMPLATES: dict[NormalizedReason, Promise] = {
    NormalizedReason.FOREIGN_DEFINITION: _(
        "'%(subject)s' has no '%(language)s' definition of its own; its '%(predicate)s' value in "
        "that language was stored as its definition instead."
    ),
}


@dataclass(frozen=True)
class NormalizedEntry:
    """One value this import stored under a predicate other than the one the file asserted
    (FR-009/FR-015), with what it was and why. The normalised counterpart of
    :class:`SetAsideEntry`, with the same shape — ``subject`` names the record at
    fault, ``params`` carries whatever else the reason's template needs — but kept as
    a distinct type because a normalised value is never one of :class:`SetAsideReason`'s
    reasons: it *was* stored.
    """

    reason: NormalizedReason
    subject: str
    params: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        """This entry's message in the caller's active language (Article XII)."""
        return str(self.reason.template) % {"subject": self.subject, **self.params}


@dataclass
class ImportReport:
    """The structured outcome of one import run (FR-015, decisions.md D7).

    Six buckets, each a plain list a caller reads directly rather than parsing:
    :attr:`created` and :attr:`updated` hold the URIs of records the run wrote,
    :attr:`set_aside` holds a :class:`SetAsideEntry` per value the run could not
    store, :attr:`absent_from_source` holds the URIs of records the file no
    longer mentions (FR-013) — left untouched, only named — :attr:`normalized`
    holds a :class:`NormalizedEntry` per value the run *did* store, but under a
    different predicate than the one the file asserted (T021, FR-009), and
    :attr:`fatal` holds a :class:`FatalFinding` per reason the whole run was
    refused (FR-004): non-empty only on a failed run, and always empty on one
    that returned successfully.
    """

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    set_aside: list[SetAsideEntry] = field(default_factory=list)
    absent_from_source: list[str] = field(default_factory=list)
    normalized: list[NormalizedEntry] = field(default_factory=list)
    fatal: list[FatalFinding] = field(default_factory=list)

    def add_created(self, subject: str) -> None:
        """Record that ``subject`` was created by this run."""
        self.created.append(subject)

    def add_updated(self, subject: str) -> None:
        """Record that ``subject`` was updated by this run."""
        self.updated.append(subject)

    def add_absent_from_source(self, subject: str) -> None:
        """Record that ``subject`` exists here but is no longer in the source (FR-013)."""
        self.absent_from_source.append(subject)

    def add_set_aside(self, reason: SetAsideReason, subject: str, **params: str) -> None:
        """Record that ``subject`` was not stored, for ``reason``, with any extra ``params``
        its message template needs."""
        self.set_aside.append(SetAsideEntry(reason=reason, subject=subject, params=params))

    def add_normalized(self, reason: NormalizedReason, subject: str, **params: str) -> None:
        """Record that ``subject`` was stored under a predicate other than the one the
        file asserted, for ``reason``, with any extra ``params`` its message template
        needs (T021, FR-009). The value *is* stored — this is visibility, not a refusal,
        so it is tracked apart from :attr:`set_aside`."""
        self.normalized.append(NormalizedEntry(reason=reason, subject=subject, params=params))

    def add_fatal(self, reason: FatalReason, subject: str, **params: str) -> None:
        """Record that ``subject`` is why the whole run was refused, for ``reason``, with any
        extra ``params`` its message template needs (FR-004). A run with anything in
        :attr:`fatal` raises rather than returning; the caller reads this bucket from the
        raised exception, not from a normal return value."""
        self.fatal.append(FatalFinding(reason=reason, subject=subject, params=params))

    def set_aside_by_reason(self) -> dict[SetAsideReason, list[SetAsideEntry]]:
        """Group :attr:`set_aside` entries by reason, for a curator-facing count per reason
        (#51) without parsing any rendered message."""
        grouped: dict[SetAsideReason, list[SetAsideEntry]] = {}
        for entry in self.set_aside:
            grouped.setdefault(entry.reason, []).append(entry)
        return grouped
