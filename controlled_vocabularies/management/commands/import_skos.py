"""``import_skos`` — load a published SKOS vocabulary from a terminal (T003, FR-001, FR-002,
FR-004, FR-005, plan.md "Summary").

Delegates the entire import to :func:`~controlled_vocabularies.exchange.skos.import_skos`
(Article II — no reimplementation of reading, matching or writing) and renders the result
through :class:`~controlled_vocabularies.management.rendering.ReportRenderer` from the first
line written; the command never formats a report itself, here or later (plan.md "Rendering").
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.exchange.exceptions import SkosImportError, SkosImportFailed
from controlled_vocabularies.exchange.skos import import_skos
from controlled_vocabularies.management.rendering import ReportRenderer
from controlled_vocabularies.management.sources import SourceResolver


class Command(BaseCommand):
    # django-stubs types BaseCommand.help as `str`; gettext_lazy's proxy satisfies Django itself
    # (str() is called wherever it's printed) but not the stub, hence the cast (Article XII).
    help = cast(str, _("Import a published SKOS vocabulary from a local file or an http(s) URL."))

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("source", help=_("A local filesystem path or an http(s) URL to a SKOS file."))
        parser.add_argument(
            "--format",
            dest="format",
            default=None,
            help=_(
                "The source's serialization (turtle, xml, or json-ld), for a source whose extension or "
                "Content-Type does not name one."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source = options["source"]
        # A missing path is left to import_skos()/from_file's own is_file() check below, which
        # already names it distinctly (FR-002). A path that *exists* but cannot be opened for
        # permission reasons passes that same is_file() check, so it is caught here instead,
        # without touching exchange/skos.py (spec Edge Cases). A URL source never satisfies
        # is_file(), so this check is a no-op for one (decisions.md D13's revisit condition
        # does not arise: a fetched document's temporary file never reaches this branch).
        path = Path(source)
        if path.is_file() and not os.access(path, os.R_OK):
            raise CommandError(str(_("'%(file)s' exists but is not readable.")) % {"file": source})
        resolver = SourceResolver(source, serialization=options["format"])
        try:
            resolved = resolver.resolve()
            report = import_skos(resolved.path, serialization=resolved.serialization, base_uri=resolved.base_uri)
        except (SkosImportError, SkosImportFailed) as exc:
            raise CommandError(str(exc)) from exc
        finally:
            resolver.cleanup()
        for line in ReportRenderer(report).render():
            self.stdout.write(line)
