from __future__ import annotations

from datetime import date
from pathlib import Path

from scripts.check_quarantine_age import (
    QuarantineEntry,
    RECOMMENDED_ACTION,
    format_json,
    find_expired_quarantines,
    format_report,
)


def _entry(*, age_days: int, threshold_days: int = 30) -> QuarantineEntry:
    quarantined_on = date(2026, 1, 1)
    return QuarantineEntry(
        feature_file=Path("tests/smoke/features/example.feature"),
        scenario_name="Example scenario",
        quarantined_on=quarantined_on,
        age_days=age_days,
        threshold_days=threshold_days,
    )


def test_scenario_over_30_days_fails():
    expired = find_expired_quarantines([_entry(age_days=31)])

    assert [entry.scenario_name for entry in expired] == ["Example scenario"]


def test_scenario_under_30_days_passes():
    expired = find_expired_quarantines([_entry(age_days=29)])

    assert expired == []


def test_output_format_lists_actionable_details():
    report = format_report([_entry(age_days=45)], max_days=30, grace_days=0)

    assert "ERROR: Found 1 @quarantine scenario(s) older than 30 days" in report
    assert "Feature file: tests/smoke/features/example.feature" in report
    assert "Scenario: Example scenario" in report
    assert "Date quarantined: 2026-01-01" in report
    assert "Age: 45 days" in report
    assert f"Action: {RECOMMENDED_ACTION}" in report


def test_json_output_uses_days_field():
    payload = format_json([_entry(age_days=12)])

    assert '"days": 12' in payload
    assert '"quarantined_on": "2026-01-01"' in payload
    assert '"feature_file": "tests/smoke/features/example.feature"' in payload
