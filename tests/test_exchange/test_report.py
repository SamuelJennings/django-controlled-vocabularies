"""T003 — ``ImportReport`` and ``SetAsideEntry`` (FR-015, decisions.md D7).

The report is the structured contract #51 and #52 consume: what was created,
what was updated, what was set aside and why, and what the source no longer
mentions, all inspectable as data rather than only as text (spec Acceptance
Scenario US1-11). Every set-aside reason comes from a closed, translatable
vocabulary (Article XII) rather than freeform prose, so a caller can group and
count without parsing a message.
"""

import pytest
from django.utils.functional import Promise

from controlled_vocabularies.exchange.report import (
    FatalFinding,
    FatalReason,
    ImportReport,
    NormalizedEntry,
    NormalizedReason,
    SetAsideEntry,
    SetAsideReason,
)

# One example params dict per reason, exercising every named placeholder its
# template declares (beyond the universal %(subject)s).
_EXAMPLE_PARAMS = {
    SetAsideReason.UNCONFIGURED_LANGUAGE: {"language": "es"},
    SetAsideReason.UNMODELLED_PREDICATE: {"predicate": "skos:hiddenLabel-ish"},
    SetAsideReason.NOTATION: {},
    SetAsideReason.MAPPING: {"predicate": "skos:exactMatch"},
    SetAsideReason.MISSING_RELATION_END: {"other": "https://example.org/vocab/missing"},
    SetAsideReason.MISSING_MEMBER: {"collection": "https://example.org/vocab/collection/rocks"},
    SetAsideReason.NO_PREFERRED_LABEL: {"language": "en"},
    SetAsideReason.VOCABULARY_MISMATCH: {"other": "https://example.org/vocab/other"},
    SetAsideReason.DEFAULT_LANGUAGE_FROZEN: {"declared": "fr", "frozen": "en"},
}

# One example params dict per fatal reason (T007), the same shape as _EXAMPLE_PARAMS.
_EXAMPLE_FATAL_PARAMS = {
    FatalReason.MISSING_IDENTITY: {},
    FatalReason.REFUSED_IDENTITY: {},
    FatalReason.VOCABULARY_UNDETERMINED: {},
    FatalReason.VOCABULARY_TARGET_MISMATCH: {"target": "https://example.org/vocab/target"},
    FatalReason.VOCABULARY_AMBIGUOUS: {"declared": "https://example.org/vocab/a, https://example.org/vocab/b"},
}

# One example params dict per normalized reason (T021), the same shape as _EXAMPLE_PARAMS.
_EXAMPLE_NORMALIZED_PARAMS = {
    NormalizedReason.FOREIGN_DEFINITION: {"predicate": "dcterms:description", "language": "en"},
}


class TestImportReportBuckets:
    """``ImportReport`` starts with four empty buckets, and each ``add_*``
    method appends only to its own — never fatal, which is tracked apart."""

    def test_import_report_starts_with_four_empty_buckets(self):
        report = ImportReport()
        assert report.created == []
        assert report.updated == []
        assert report.set_aside == []
        assert report.absent_from_source == []

    def test_add_created_and_add_updated_append_to_their_own_bucket(self):
        report = ImportReport()
        report.add_created("https://example.org/vocab/rocks")
        report.add_updated("https://example.org/vocab/rocks/granite")
        assert report.created == ["https://example.org/vocab/rocks"]
        assert report.updated == ["https://example.org/vocab/rocks/granite"]
        # Adding to one bucket never touches another.
        assert report.set_aside == []
        assert report.absent_from_source == []

    def test_add_absent_from_source_appends_the_subject(self):
        report = ImportReport()
        report.add_absent_from_source("https://example.org/vocab/rocks/basalt")
        assert report.absent_from_source == ["https://example.org/vocab/rocks/basalt"]

    def test_add_set_aside_records_reason_subject_and_params_as_data(self):
        report = ImportReport()
        report.add_set_aside(
            SetAsideReason.UNCONFIGURED_LANGUAGE,
            "https://example.org/vocab/rocks/granite",
            language="es",
        )
        assert len(report.set_aside) == 1
        entry = report.set_aside[0]
        assert isinstance(entry, SetAsideEntry)
        # Inspectable as data (spec US1-11): the reason and subject are read directly,
        # never by parsing a rendered message.
        assert entry.reason is SetAsideReason.UNCONFIGURED_LANGUAGE
        assert entry.subject == "https://example.org/vocab/rocks/granite"
        assert entry.params == {"language": "es"}

    def test_set_aside_by_reason_groups_and_counts_without_parsing_prose(self):
        report = ImportReport()
        report.add_set_aside(SetAsideReason.NOTATION, "https://example.org/vocab/rocks/granite")
        report.add_set_aside(SetAsideReason.NOTATION, "https://example.org/vocab/rocks/basalt")
        report.add_set_aside(
            SetAsideReason.UNCONFIGURED_LANGUAGE, "https://example.org/vocab/rocks/granite", language="es"
        )
        grouped = report.set_aside_by_reason()
        assert len(grouped[SetAsideReason.NOTATION]) == 2
        assert len(grouped[SetAsideReason.UNCONFIGURED_LANGUAGE]) == 1
        assert SetAsideReason.MAPPING not in grouped


class TestSetAsideEntry:
    """A ``SetAsideEntry`` is a frozen record — nothing downstream can mutate
    a reason, subject or params after it has been reported."""

    def test_set_aside_entry_is_immutable(self):
        entry = SetAsideEntry(reason=SetAsideReason.NOTATION, subject="https://example.org/vocab/x")
        with pytest.raises((AttributeError, TypeError)):
            entry.subject = "changed"


class TestSetAsideReasonVocabulary:
    """Every member of the closed ``SetAsideReason`` vocabulary is lazily
    translatable, carries a named ``%(subject)s`` placeholder, and renders
    with its own example params (Article XII)."""

    @pytest.mark.parametrize("reason", list(SetAsideReason))
    def test_every_reason_has_a_translatable_label(self, reason):
        assert isinstance(reason.label, Promise), f"{reason} label is not lazily translatable"

    @pytest.mark.parametrize("reason", list(SetAsideReason))
    def test_every_reason_template_is_translatable_with_a_named_subject_placeholder(self, reason):
        assert isinstance(reason.template, Promise), f"{reason} template is not lazily translatable"
        assert "%(subject)s" in str(reason.template), f"{reason} template lacks a named %(subject)s placeholder"

    @pytest.mark.parametrize("reason", list(SetAsideReason))
    def test_every_reason_renders_with_its_example_params(self, reason):
        entry = SetAsideEntry(reason=reason, subject="https://example.org/vocab/x", params=_EXAMPLE_PARAMS[reason])
        rendered = entry.render()
        assert isinstance(rendered, str)
        assert "https://example.org/vocab/x" in rendered
        for value in _EXAMPLE_PARAMS[reason].values():
            assert value in rendered


class TestFatalBucketAndFinding:
    """T007 — the fatal bucket starts empty, ``add_fatal`` records reason,
    subject and params as data, and a recorded ``FatalFinding`` is frozen."""

    def test_import_report_starts_with_an_empty_fatal_bucket(self):
        assert ImportReport().fatal == []

    def test_add_fatal_records_reason_subject_and_params_as_data(self):
        report = ImportReport()
        report.add_fatal(FatalReason.MISSING_IDENTITY, "https://example.org/vocab/rocks/blank")
        assert len(report.fatal) == 1
        entry = report.fatal[0]
        assert isinstance(entry, FatalFinding)
        assert entry.reason is FatalReason.MISSING_IDENTITY
        assert entry.subject == "https://example.org/vocab/rocks/blank"
        assert entry.params == {}

    def test_fatal_finding_is_immutable(self):
        finding = FatalFinding(reason=FatalReason.MISSING_IDENTITY, subject="https://example.org/vocab/x")
        with pytest.raises((AttributeError, TypeError)):
            finding.subject = "changed"


class TestFatalReasonVocabulary:
    """Every member of the closed ``FatalReason`` vocabulary is lazily
    translatable, carries a named ``%(subject)s`` placeholder, and renders
    with its own example params (Article XII)."""

    @pytest.mark.parametrize("reason", list(FatalReason))
    def test_every_fatal_reason_has_a_translatable_label(self, reason):
        assert isinstance(reason.label, Promise), f"{reason} label is not lazily translatable"

    @pytest.mark.parametrize("reason", list(FatalReason))
    def test_every_fatal_reason_template_is_translatable_with_a_named_subject_placeholder(self, reason):
        assert isinstance(reason.template, Promise), f"{reason} template is not lazily translatable"
        assert "%(subject)s" in str(reason.template), f"{reason} template lacks a named %(subject)s placeholder"

    @pytest.mark.parametrize("reason", list(FatalReason))
    def test_every_fatal_reason_renders_with_its_example_params(self, reason):
        entry = FatalFinding(reason=reason, subject="https://example.org/vocab/x", params=_EXAMPLE_FATAL_PARAMS[reason])
        rendered = entry.render()
        assert isinstance(rendered, str)
        assert "https://example.org/vocab/x" in rendered
        for value in _EXAMPLE_FATAL_PARAMS[reason].values():
            assert value in rendered


class TestReasonVocabulariesAreDisjoint:
    """decisions.md D3/D8: a fatal finding is never one of the set-aside
    reasons — the two closed vocabularies never overlap."""

    def test_set_aside_reason_and_fatal_reason_are_disjoint_vocabularies(self):
        set_aside_values = {reason.value for reason in SetAsideReason}
        fatal_values = {reason.value for reason in FatalReason}
        assert set_aside_values.isdisjoint(fatal_values)


class TestImportReportNormalizedBucket:
    """T021 — the normalised bucket starts empty, ``add_normalized`` records
    reason, subject and params as data without touching any other bucket, and
    a recorded ``NormalizedEntry`` is frozen. Deliberately apart from
    :attr:`ImportReport.set_aside`: a normalised value *was* stored (T021,
    FR-009, decisions.md D24) — only under a different predicate than the
    file itself asserted — whereas everything in ``set_aside`` was not."""

    def test_import_report_starts_with_an_empty_normalized_bucket(self):
        assert ImportReport().normalized == []

    def test_add_normalized_records_reason_subject_and_params_as_data(self):
        report = ImportReport()
        report.add_normalized(
            NormalizedReason.FOREIGN_DEFINITION,
            "https://example.org/vocab/rocks/gadget",
            predicate="dcterms:description",
            language="en",
        )
        assert len(report.normalized) == 1
        entry = report.normalized[0]
        assert isinstance(entry, NormalizedEntry)
        assert entry.reason is NormalizedReason.FOREIGN_DEFINITION
        assert entry.subject == "https://example.org/vocab/rocks/gadget"
        assert entry.params == {"predicate": "dcterms:description", "language": "en"}
        # Adding a normalized entry never touches any other bucket.
        assert report.set_aside == []
        assert report.fatal == []

    def test_normalized_entry_is_immutable(self):
        entry = NormalizedEntry(reason=NormalizedReason.FOREIGN_DEFINITION, subject="https://example.org/vocab/x")
        with pytest.raises((AttributeError, TypeError)):
            entry.subject = "changed"


class TestNormalizedReasonVocabulary:
    """Every member of the closed ``NormalizedReason`` vocabulary is lazily
    translatable, carries a named ``%(subject)s`` placeholder, and renders
    with its own example params (Article XII)."""

    @pytest.mark.parametrize("reason", list(NormalizedReason))
    def test_every_normalized_reason_has_a_translatable_label(self, reason):
        assert isinstance(reason.label, Promise), f"{reason} label is not lazily translatable"

    @pytest.mark.parametrize("reason", list(NormalizedReason))
    def test_every_normalized_reason_template_is_translatable_with_a_named_subject_placeholder(self, reason):
        assert isinstance(reason.template, Promise), f"{reason} template is not lazily translatable"
        assert "%(subject)s" in str(reason.template), f"{reason} template lacks a named %(subject)s placeholder"

    @pytest.mark.parametrize("reason", list(NormalizedReason))
    def test_every_normalized_reason_renders_with_its_example_params(self, reason):
        entry = NormalizedEntry(
            reason=reason, subject="https://example.org/vocab/x", params=_EXAMPLE_NORMALIZED_PARAMS[reason]
        )
        rendered = entry.render()
        assert isinstance(rendered, str)
        assert "https://example.org/vocab/x" in rendered
        for value in _EXAMPLE_NORMALIZED_PARAMS[reason].values():
            assert value in rendered


class TestNormalizedReasonIsDisjointFromSetAsideAndFatal:
    """A normalised value was stored; a set-aside or fatal one was not
    (decisions.md D24) — the three closed vocabularies never share a value."""

    def test_normalized_reason_shares_no_value_with_set_aside_or_fatal_reason(self):
        normalized_values = {reason.value for reason in NormalizedReason}
        set_aside_values = {reason.value for reason in SetAsideReason}
        fatal_values = {reason.value for reason in FatalReason}
        assert normalized_values.isdisjoint(set_aside_values)
        assert normalized_values.isdisjoint(fatal_values)


class TestReasonTemplatesUseOnlyNamedPlaceholders:
    """T031 (FR-016, spec User Story 6 Acceptance Scenario 1) — one closed-world
    sweep across all three report-reason vocabularies. The per-reason tests above
    assert each template is lazily translatable and carries a named
    ``%(subject)s``; this asserts there is nothing *besides* named placeholders in
    any of them — the "named rather than positional" half FR-016 states but the
    per-reason tests don't check for the absence of. A reason added later without
    its own dedicated test is still caught here."""

    @pytest.mark.parametrize("reason", list(SetAsideReason) + list(FatalReason) + list(NormalizedReason))
    def test_reason_template_has_no_positional_placeholder(self, reason, uses_only_named_placeholders):
        template = str(reason.template)
        assert uses_only_named_placeholders(template), (
            f"{reason} template carries something other than a named placeholder: {template!r}"
        )
