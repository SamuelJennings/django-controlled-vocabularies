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

from controlled_vocabularies.io.report import ImportReport, SetAsideEntry, SetAsideReason

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
}


def test_import_report_starts_with_four_empty_buckets():
    report = ImportReport()
    assert report.created == []
    assert report.updated == []
    assert report.set_aside == []
    assert report.absent_from_source == []


def test_add_created_and_add_updated_append_to_their_own_bucket():
    report = ImportReport()
    report.add_created("https://example.org/vocab/rocks")
    report.add_updated("https://example.org/vocab/rocks/granite")
    assert report.created == ["https://example.org/vocab/rocks"]
    assert report.updated == ["https://example.org/vocab/rocks/granite"]
    # Adding to one bucket never touches another.
    assert report.set_aside == []
    assert report.absent_from_source == []


def test_add_absent_from_source_appends_the_subject():
    report = ImportReport()
    report.add_absent_from_source("https://example.org/vocab/rocks/basalt")
    assert report.absent_from_source == ["https://example.org/vocab/rocks/basalt"]


def test_add_set_aside_records_reason_subject_and_params_as_data():
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


def test_set_aside_by_reason_groups_and_counts_without_parsing_prose():
    report = ImportReport()
    report.add_set_aside(SetAsideReason.NOTATION, "https://example.org/vocab/rocks/granite")
    report.add_set_aside(SetAsideReason.NOTATION, "https://example.org/vocab/rocks/basalt")
    report.add_set_aside(SetAsideReason.UNCONFIGURED_LANGUAGE, "https://example.org/vocab/rocks/granite", language="es")
    grouped = report.set_aside_by_reason()
    assert len(grouped[SetAsideReason.NOTATION]) == 2
    assert len(grouped[SetAsideReason.UNCONFIGURED_LANGUAGE]) == 1
    assert SetAsideReason.MAPPING not in grouped


@pytest.mark.parametrize("reason", list(SetAsideReason))
def test_every_reason_has_a_translatable_label(reason):
    assert isinstance(reason.label, Promise), f"{reason} label is not lazily translatable"


@pytest.mark.parametrize("reason", list(SetAsideReason))
def test_every_reason_template_is_translatable_with_a_named_subject_placeholder(reason):
    assert isinstance(reason.template, Promise), f"{reason} template is not lazily translatable"
    assert "%(subject)s" in str(reason.template), f"{reason} template lacks a named %(subject)s placeholder"


@pytest.mark.parametrize("reason", list(SetAsideReason))
def test_every_reason_renders_with_its_example_params(reason):
    entry = SetAsideEntry(reason=reason, subject="https://example.org/vocab/x", params=_EXAMPLE_PARAMS[reason])
    rendered = entry.render()
    assert isinstance(rendered, str)
    assert "https://example.org/vocab/x" in rendered
    for value in _EXAMPLE_PARAMS[reason].values():
        assert value in rendered


def test_set_aside_entry_is_immutable():
    entry = SetAsideEntry(reason=SetAsideReason.NOTATION, subject="https://example.org/vocab/x")
    with pytest.raises((AttributeError, TypeError)):
        entry.subject = "changed"
