"""Unit tests for e2e job-summary result counting."""

from scripts.e2e_summary import count_scenarios


def test_count_scenarios_counts_only_scenario_statuses():
    report = [
        {
            "elements": [
                {"type": "background", "status": "passed"},
                {"type": "scenario", "status": "passed"},
                {"type": "scenario", "status": "failed"},
                {"type": "scenario", "status": "skipped"},
                {"type": "scenario", "status": "undefined"},
                {"type": "scenario", "status": "untested"},
            ]
        }
    ]

    assert count_scenarios(report) == {
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "undefined": 1,
        "untested": 1,
    }


def test_count_scenarios_does_not_infer_passed_from_unknown_statuses():
    report = [
        {
            "elements": [
                {"type": "scenario", "status": "undefined"},
                {"type": "scenario", "status": "untested"},
                {"type": "scenario", "status": "error"},
            ]
        }
    ]

    assert count_scenarios(report)["passed"] == 0
