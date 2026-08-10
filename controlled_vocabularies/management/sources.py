"""Classifying and, for a URL, fetching a management-command source (T007-T009, plan.md
"Source resolution", research.md R3/R4, decisions.md D3).

:class:`SourceResolver` takes the raw ``source`` argument and answers what it is, before
:class:`~controlled_vocabularies.management.commands.import_skos.Command` acts on it. A
one-character parsed scheme is a Windows drive letter (``urlsplit("C:/vocab.ttl").scheme``
is ``"c"``), not a network protocol, so it is not mistaken for one (research.md R3).
"""

from __future__ import annotations

from urllib.parse import urlsplit

from django.core.management.base import CommandError
from django.utils.translation import gettext_lazy as _

_URL_PREFIXES = ("http://", "https://")


class SourceResolver:
    """Classify ``source`` and, for a URL, fetch it into a local file (T007-T009)."""

    def __init__(self, source: str, *, serialization: str | None = None) -> None:
        self.source = source
        self.serialization = serialization

    def classify(self) -> str:
        """Return ``"url"`` or ``"path"`` for :attr:`source` (T007, research.md R3).

        A value beginning ``http://``/``https://``, case-insensitively, is a URL. Anything
        else is a path unless its parsed scheme is longer than one character, which is
        refused as an unsupported source.
        """
        if self.source.lower().startswith(_URL_PREFIXES):
            return "url"
        scheme = urlsplit(self.source).scheme
        if len(scheme) <= 1:
            return "path"
        raise CommandError(
            str(_("'%(source)s' names a source this command does not support ('%(scheme)s' is not http or https)."))
            % {"source": self.source, "scheme": scheme}
        )
