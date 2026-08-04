"""T031 — Standards test extension (FR-016, spec User Story 6 Acceptance
Scenarios 1 and 4): every message this feature puts in front of a person —
a report reason or a raised failure — is translatable and uses named
placeholders, and developer-facing diagnostics are named as exempt rather
than silently skipped.

The individual message tests already scattered across ``test_report.py``,
``test_skos.py``, and ``test_safety.py`` each assert their own message's
specific placeholders when it is raised. This file adds the two things
those leave open: a closed-world sweep over *every* member of the three
closed report-reason vocabularies (``list(SetAsideReason)`` etc. — a reason
added later without its own dedicated test is still caught here), and one
assertion per failure-raising site that the placeholders used are *only*
ever the named form, never a positional one.
"""

import re
from pathlib import Path

import pytest
from django.utils.functional import Promise

from controlled_vocabularies.exchange.report import FatalReason, NormalizedReason, SetAsideReason
from controlled_vocabularies.exchange.safety import UnsafeRdfXmlError, scan_rdf_xml
from controlled_vocabularies.exchange.skos import SkosImportError, SkosImportFailed, _read_graph, import_skos

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skos"
SECURITY_FIXTURES = Path(__file__).parent.parent / "fixtures" / "security"

#: A ``%(name)s``-style named placeholder. Stripping every match out of a
#: message and finding a bare ``%`` left over means something else is there —
#: a positional ``%s``/``%d``, or a stray literal percent — neither of which
#: Article XII's "named placeholders" wording allows.
_NAMED_PLACEHOLDER = re.compile(r"%\([a-zA-Z_][a-zA-Z0-9_]*\)s")


def _uses_only_named_placeholders(message: str) -> bool:
    return "%" not in _NAMED_PLACEHOLDER.sub("", message)


class TestReportReasonTemplatesUseOnlyNamedPlaceholders:
    """Acceptance Scenario 1, applied as one sweep across all three
    report-reason vocabularies. ``test_report.py`` already asserts each
    template is lazily translatable and carries a named ``%(subject)s``;
    this additionally asserts there is nothing *besides* named placeholders
    in any of them — the "named rather than positional" half FR-016 states
    but the per-reason tests don't themselves check for the absence of."""

    @pytest.mark.parametrize("reason", list(SetAsideReason) + list(FatalReason) + list(NormalizedReason))
    def test_reason_template_has_no_positional_placeholder(self, reason):
        template = str(reason.template)
        assert _uses_only_named_placeholders(template), (
            f"{reason} template carries something other than a named placeholder: {template!r}"
        )


class TestFailureMessagesUseOnlyNamedPlaceholders:
    """The same "named, not positional" check, extended to the messages
    ``skos.py`` and ``safety.py`` raise directly rather than adding to
    ``ImportReport`` — every ``raise …Error(_("…"), …)`` call site in the
    ``exchange`` package is exercised once here.

    Acceptance Scenario 4's developer-diagnostics exemption is the raw
    upstream exception (rdflib's own parse error; ``defusedxml``'s own guard
    exception) each of the two chained refusals below carries on
    ``__cause__``: named and asserted present here, rather than the
    exemption being an unstated gap in this standards sweep. It is the
    *only* thing this feature ever puts in front of a person that Article
    XII does not hold to a translatable, named-placeholder standard —
    everything else raised or reported by this package is checked, above or
    below.
    """

    def test_missing_file_message(self, tmp_path):
        with pytest.raises(SkosImportError) as excinfo:
            _read_graph(tmp_path / "does-not-exist.ttl")
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "skos_file_not_found"

    def test_unsupported_serialization_message(self):
        with pytest.raises(SkosImportError) as excinfo:
            _read_graph(FIXTURES / "rocks.ttl", serialization="n3")
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "skos_format_unsupported"

    def test_unparseable_file_message_and_its_developer_diagnostic_exemption(self, tmp_path):
        bad = tmp_path / "bad.ttl"
        bad.write_text("this is not turtle @@@ not even close {{{ ]][[ ")
        with pytest.raises(SkosImportError) as excinfo:
            _read_graph(bad)
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "skos_parse_failed"
        # Developer-diagnostic exemption: the raw rdflib parser exception is
        # chained onto __cause__, not translated — only the curator-facing
        # wrapper message just checked above is held to Article XII.
        assert err.__cause__ is not None, "the underlying rdflib exception must be chained for developer diagnostics"

    @pytest.mark.django_db
    def test_import_failed_message(self):
        with pytest.raises(SkosImportFailed) as excinfo:
            import_skos(FIXTURES / "blank_node_concept.ttl")
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "skos_import_failed"

    def test_entity_bomb_message_and_its_developer_diagnostic_exemption(self):
        with pytest.raises(UnsafeRdfXmlError) as excinfo:
            scan_rdf_xml((SECURITY_FIXTURES / "entity_bomb.rdf").read_bytes())
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "rdf_xml_entities_forbidden"
        # Developer-diagnostic exemption: the raw defusedxml guard exception
        # is chained, not translated (safety.py's own docstring says so).
        assert err.__cause__ is not None, (
            "the underlying defusedxml exception must be chained for developer diagnostics"
        )

    def test_external_dtd_message_and_its_developer_diagnostic_exemption(self):
        with pytest.raises(UnsafeRdfXmlError) as excinfo:
            scan_rdf_xml((SECURITY_FIXTURES / "external_dtd.rdf").read_bytes())
        err = excinfo.value
        assert isinstance(err.message, Promise)
        assert _uses_only_named_placeholders(str(err.message))
        assert err.code == "rdf_xml_external_reference_forbidden"
        assert err.__cause__ is not None, (
            "the underlying defusedxml exception must be chained for developer diagnostics"
        )
