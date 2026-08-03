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
    """

    UNCONFIGURED_LANGUAGE = "unconfigured_language", _("language not configured")
    UNMODELLED_PREDICATE = "unmodelled_predicate", _("predicate not modelled")
    NOTATION = "notation", _("notation")
    MAPPING = "mapping", _("mapping to another vocabulary")
    MISSING_RELATION_END = "missing_relation_end", _("relationship end not found")
    MISSING_MEMBER = "missing_member", _("collection member not found")
    NO_PREFERRED_LABEL = "no_preferred_label", _("no preferred label in default language")
    VOCABULARY_MISMATCH = "vocabulary_mismatch", _("belongs to a different vocabulary")

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


@dataclass
class ImportReport:
    """The structured outcome of one import run (FR-015, decisions.md D7).

    Five buckets, each a plain list a caller reads directly rather than parsing:
    :attr:`created` and :attr:`updated` hold the URIs of records the run wrote,
    :attr:`set_aside` holds a :class:`SetAsideEntry` per value the run could not
    store, :attr:`absent_from_source` holds the URIs of records the file no
    longer mentions (FR-013) — left untouched, only named — and :attr:`fatal`
    holds a :class:`FatalFinding` per reason the whole run was refused
    (FR-004): non-empty only on a failed run, and always empty on one that
    returned successfully.
    """

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    set_aside: list[SetAsideEntry] = field(default_factory=list)
    absent_from_source: list[str] = field(default_factory=list)
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
