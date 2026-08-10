"""``import_skos`` — load a published SKOS vocabulary from a terminal (T003, FR-001, FR-002,
FR-004, FR-005, plan.md "Summary").

Delegates the entire import to :func:`~controlled_vocabularies.exchange.skos.import_skos`
(Article II — no reimplementation of reading, matching or writing) and renders the result
through :class:`~controlled_vocabularies.management.rendering.ReportRenderer` from the first
line written; the command never formats a report itself, here or later (plan.md "Rendering").
"""

from __future__ import annotations

from typing import Any, cast

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.exceptions import SkosImportError, SkosImportFailed
from controlled_vocabularies.exchange.skos import import_skos
from controlled_vocabularies.management.rendering import ReportRenderer


class Command(BaseCommand):
    # django-stubs types BaseCommand.help as `str`; gettext_lazy's proxy satisfies Django itself
    # (str() is called wherever it's printed) but not the stub, hence the cast (Article XII).
    help = cast(str, _("Import a published SKOS vocabulary from a local file."))

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("source", help=_("A local filesystem path to a SKOS file."))
        parser.add_argument(
            "--format",
            dest="format",
            default=None,
            help=_(
                "The source's serialization (turtle, xml, or json-ld), for a file whose extension does not name one."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source = options["source"]
        try:
            report = import_skos(source, serialization=options["format"])
        except (SkosImportError, SkosImportFailed) as exc:
            raise CommandError(str(exc)) from exc
        for line in ReportRenderer(report).render():
            self.stdout.write(line)
