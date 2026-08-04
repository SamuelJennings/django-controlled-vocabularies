"""Fixtures shared by the ``exchange`` package's test modules.

The placeholder predicate below is used by the Article XII standards sweeps that
live in each module alongside the code they check — the report-reason sweep in
``test_report.py``, and the raised-failure sweeps in ``test_skos.py`` and
``test_safety.py``.
"""

import re

import pytest

#: A ``%(name)s``-style named placeholder. Stripping every match out of a
#: message and finding a bare ``%`` left over means something else is there —
#: a positional ``%s``/``%d``, or a stray literal percent — neither of which
#: Article XII's "named placeholders" wording allows.
_NAMED_PLACEHOLDER = re.compile(r"%\([a-zA-Z_][a-zA-Z0-9_]*\)s")


@pytest.fixture
def uses_only_named_placeholders():
    """Return a predicate: does this message use named placeholders and nothing else?"""

    def _predicate(message: str) -> bool:
        return "%" not in _NAMED_PLACEHOLDER.sub("", message)

    return _predicate
