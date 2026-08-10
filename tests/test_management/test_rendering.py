"""``controlled_vocabularies.management.rendering`` — an ``ImportReport`` as
translated lines for a terminal (T015, FR-006, FR-007, plan.md "Rendering").

Foundational-phase scope only: the bucket counts (created, updated, set
aside, normalized, absent from source). Grouping set-asides by reason, the
per-language account, per-entry detail at raised verbosity, and the
rehearsal line are US-4/US-3's own tasks, added to this same class later.

Exercised entirely against a hand-built :class:`ImportReport` — nothing here
runs an import (tasks.md T015).
"""

from controlled_vocabularies.exchange.report import (
    ImportReport,
    NormalizedEntry,
    NormalizedReason,
    SetAsideEntry,
    SetAsideReason,
)
from controlled_vocabularies.management.rendering import ReportRenderer


class TestReportRendererBucketCounts:
    def test_a_populated_report_renders_each_bucket_count(self):
        report = ImportReport(
            created=["http://example.org/a", "http://example.org/b"],
            updated=["http://example.org/c"],
            set_aside=[
                SetAsideEntry(
                    reason=SetAsideReason.UNCONFIGURED_LANGUAGE,
                    subject="http://example.org/d",
                    params={"language": "de"},
                )
            ],
            normalized=[
                NormalizedEntry(
                    reason=NormalizedReason.FOREIGN_DEFINITION,
                    subject="http://example.org/e",
                    params={"language": "en", "predicate": "skos:scopeNote"},
                )
            ],
            absent_from_source=["http://example.org/f", "http://example.org/g", "http://example.org/h"],
        )
        lines = [str(line) for line in ReportRenderer(report).render()]
        assert any("2" in line and "created" in line for line in lines)
        assert any("1" in line and "updated" in line for line in lines)
        assert any("1" in line and "set aside" in line for line in lines)
        assert any("1" in line and "normalized" in line for line in lines)
        assert any("3" in line and "absent from the source" in line for line in lines)

    def test_an_empty_report_still_prints_every_section_reading_zero(self):
        lines = [str(line) for line in ReportRenderer(ImportReport()).render()]
        assert len(lines) == 5
        assert all("0" in line for line in lines)


class TestReportRendererRehearsalLine:
    """T014, FR-010, `decisions.md` D9 — a rehearsal's output states plainly that nothing was
    kept; a live run's does not. A flag on the renderer rather than a print in the command, so
    the two renderings differ in exactly one deliberate place (plan.md "Rendering")."""

    def test_a_rehearsal_states_that_nothing_was_kept(self):
        lines = [str(line) for line in ReportRenderer(ImportReport(), rehearsal=True).render()]
        assert any("nothing was kept" in line for line in lines)

    def test_a_live_run_of_the_same_report_does_not_state_that_nothing_was_kept(self):
        lines = [str(line) for line in ReportRenderer(ImportReport()).render()]
        assert not any("nothing was kept" in line for line in lines)
