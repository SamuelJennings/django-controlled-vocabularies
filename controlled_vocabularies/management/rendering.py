"""Rendering an :class:`~controlled_vocabularies.exchange.report.ImportReport` for a terminal
(T015, FR-006, FR-007, plan.md "Rendering").

Foundational-phase scope: the bucket counts an import run leaves behind — created, updated, set
aside, normalized, absent from source. Every section prints, whatever it holds: a section reading
zero and a section silently missing look identical to a reader but mean different things (FR-008's
own reasoning for ``absent_from_source``, applied here to every bucket). Grouping set-asides by
reason and by language, per-entry detail at raised verbosity, and the rehearsal line are US-4's
and US-3's own tasks, added to this class later rather than anticipated here.
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
        """Yield one line per bucket, in the order tasks.md T015 names them."""
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
        if self.rehearsal:
            yield str(_("This was a rehearsal: nothing was kept."))
