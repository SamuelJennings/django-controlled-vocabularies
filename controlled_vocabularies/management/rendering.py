"""Rendering an :class:`~controlled_vocabularies.exchange.report.ImportReport` for a terminal
(T015, T016, FR-006, FR-007, plan.md "Rendering").

The bucket counts an import run leaves behind — created, updated, set aside, normalized, absent
from source — plus the set-aside account: grouped by reason with a count each, and the
per-language account. Every section prints, whatever it holds: a section reading zero and a
section silently missing look identical to a reader but mean different things (FR-008's own
reasoning for ``absent_from_source``, applied here to every bucket) — which is also why each
grouping below is a plain iteration over the report's own accessors: an empty grouping simply
yields nothing, and the bucket count above it already shows the zero. Records absent from the
source named in their own section and per-entry detail at raised verbosity are US-4's own later
tasks, added to this class next rather than anticipated here.
"""

from __future__ import annotations

from collections.abc import Iterator

from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from controlled_vocabularies.exchange.report import ImportReport


class ReportRenderer:
    """Turns an :class:`ImportReport` into translated lines a curator reads at a terminal.

    ``rehearsal`` is the one deliberate difference between a rehearsal's rendering and a live
    run's (T014, FR-010, `decisions.md` D9): when set, one extra line states that nothing was
    kept, so a rehearsal's counts are never mistaken for a completed import.
    """

    def __init__(self, report: ImportReport, *, rehearsal: bool = False) -> None:
        self.report = report
        self.rehearsal = rehearsal

    def render(self) -> Iterator[str]:
        """Yield translated lines: bucket counts, then the set-aside account (grouped by reason,
        then the per-language account), then the rehearsal line."""
        yield str(
            ngettext_lazy("%(count)d record created.", "%(count)d records created.", len(self.report.created))
        ) % {"count": len(self.report.created)}
        yield str(
            ngettext_lazy("%(count)d record updated.", "%(count)d records updated.", len(self.report.updated))
        ) % {"count": len(self.report.updated)}
        yield str(
            ngettext_lazy("%(count)d value set aside.", "%(count)d values set aside.", len(self.report.set_aside))
        ) % {"count": len(self.report.set_aside)}
        yield str(
            ngettext_lazy("%(count)d value normalized.", "%(count)d values normalized.", len(self.report.normalized))
        ) % {"count": len(self.report.normalized)}
        yield str(
            ngettext_lazy(
                "%(count)d record absent from the source.",
                "%(count)d records absent from the source.",
                len(self.report.absent_from_source),
            )
        ) % {"count": len(self.report.absent_from_source)}
        yield from self._render_set_aside_by_reason()
        yield from self._render_language_account()
        if self.rehearsal:
            yield str(_("This was a rehearsal: nothing was kept."))

    def _render_set_aside_by_reason(self) -> Iterator[str]:
        """One line per reason with its count (T016, FR-007), read from
        :meth:`ImportReport.set_aside_by_reason` — never by parsing a rendered message. A reason
        with no entries has no group in that mapping, so it yields no line of its own."""
        for reason, entries in self.report.set_aside_by_reason().items():
            count = len(entries)
            yield str(
                ngettext_lazy(
                    "%(count)d value set aside for '%(reason)s'.",
                    "%(count)d values set aside for '%(reason)s'.",
                    count,
                )
            ) % {"count": count, "reason": reason.label}

    def _render_language_account(self) -> Iterator[str]:
        """The per-language account (T016, FR-007/FR-008), read from
        :meth:`ImportReport.language_account` — how many values a language would recover if
        configured, one line per language."""
        for language, count in self.report.language_account().items():
            yield str(
                ngettext_lazy(
                    "%(count)d value set aside in the language '%(language)s'.",
                    "%(count)d values set aside in the language '%(language)s'.",
                    count,
                )
            ) % {"count": count, "language": language}
