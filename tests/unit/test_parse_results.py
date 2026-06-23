"""Unit tests for the results parser."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Import helpers directly for unit-level coverage
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.parse_results import (  # noqa: E402
    _normalize_status,
    _scenario_elapsed_seconds,
    _scenario_status,
    parse_results,
)


def test_parse_results_emits_jsonl_per_scenario(tmp_path):
    report = [
        {
            "name": "Smoke",
            "elements": [
                {
                    "type": "background",
                    "name": "Shared setup",
                    "steps": [
                        {"result": {"status": "passed", "duration": 9.0}},
                    ],
                },
                {
                    "type": "scenario",
                    "name": "System boots and GNOME Shell loads",
                    "status": "passed",
                    "steps": [
                        {"result": {"status": "passed", "duration": 1.2}},
                        {"result": {"status": "passed", "duration": 1.1}},
                    ],
                },
                {
                    "type": "scenario",
                    "name": "Skipped scenario",
                    "steps": [
                        {"result": {"status": "skipped"}},
                    ],
                },
                {
                    "type": "scenario",
                    "name": "Failed scenario",
                    "steps": [
                        {"result": {"status": "passed", "duration": 0.3}},
                        {"result": {"status": "failed", "duration": 0.2}},
                    ],
                },
                {
                    "type": "scenario",
                    "name": "Errored scenario",
                    "result": {"status": "hook_error"},
                    "steps": [],
                },
            ],
        }
    ]
    input_path = tmp_path / "results.json"
    input_path.write_text(json.dumps(report), encoding="utf-8")

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "parse_results.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            str(input_path),
            "--image",
            "ghcr.io/ublue-os/bluefin:latest",
            "--suite",
            "smoke",
            "--date",
            "2026-06-01",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    rows = [json.loads(line) for line in completed.stdout.splitlines()]

    assert rows == [
        {
            "date": "2026-06-01",
            "image": "ghcr.io/ublue-os/bluefin:latest",
            "suite": "smoke",
            "scenario": "System boots and GNOME Shell loads",
            "status": "passed",
            "elapsed_s": 2.3,
        },
        {
            "date": "2026-06-01",
            "image": "ghcr.io/ublue-os/bluefin:latest",
            "suite": "smoke",
            "scenario": "Skipped scenario",
            "status": "skipped",
            "elapsed_s": 0,
        },
        {
            "date": "2026-06-01",
            "image": "ghcr.io/ublue-os/bluefin:latest",
            "suite": "smoke",
            "scenario": "Failed scenario",
            "status": "failed",
            "elapsed_s": 0.5,
        },
        {
            "date": "2026-06-01",
            "image": "ghcr.io/ublue-os/bluefin:latest",
            "suite": "smoke",
            "scenario": "Errored scenario",
            "status": "error",
            "elapsed_s": 0,
        },
    ]


# --- _normalize_status ---

@pytest.mark.parametrize("value,expected", [
    ("passed", "passed"),
    ("PASSED", "passed"),
    ("failed", "failed"),
    ("error", "error"),
    ("skipped", "skipped"),
    ("untested", "skipped"),
    ("undefined", "error"),
    ("hook_error", "error"),
    ("unknown_value", None),
    (None, None),
    ("", None),
    ("  passed  ", "passed"),
])
def test_normalize_status(value, expected):
    assert _normalize_status(value) == expected


# --- _scenario_status ---

def test_scenario_status_uses_direct_status():
    assert _scenario_status({"status": "passed", "steps": []}) == "passed"


def test_scenario_status_uses_result_status():
    assert _scenario_status({"result": {"status": "failed"}, "steps": []}) == "failed"


def test_scenario_status_direct_over_result():
    # direct status wins over result block
    assert _scenario_status({"status": "passed", "result": {"status": "failed"}, "steps": []}) == "passed"


def test_scenario_status_all_steps_skipped():
    element = {"steps": [
        {"result": {"status": "skipped"}},
        {"result": {"status": "skipped"}},
    ]}
    assert _scenario_status(element) == "skipped"


def test_scenario_status_mixed_passed_skipped():
    element = {"steps": [
        {"result": {"status": "passed"}},
        {"result": {"status": "skipped"}},
    ]}
    assert _scenario_status(element) == "passed"


def test_scenario_status_failed_in_steps():
    element = {"steps": [
        {"result": {"status": "passed"}},
        {"result": {"status": "failed"}},
    ]}
    assert _scenario_status(element) == "failed"


def test_scenario_status_error_wins_over_failed():
    element = {"steps": [
        {"result": {"status": "failed"}},
        {"result": {"status": "error"}},
    ]}
    assert _scenario_status(element) == "error"


def test_scenario_status_undefined_step():
    element = {"steps": [{"result": {"status": "undefined"}}]}
    assert _scenario_status(element) == "error"


def test_scenario_status_no_steps_no_status():
    # no info → error
    assert _scenario_status({"steps": []}) == "error"


def test_scenario_status_steps_without_result():
    element = {"steps": [{"name": "some step"}]}
    assert _scenario_status(element) == "error"


# --- _scenario_elapsed_seconds ---

def test_elapsed_from_direct_duration():
    assert _scenario_elapsed_seconds({"duration": 3.5, "steps": []}) == 3.5


def test_elapsed_from_result_duration():
    assert _scenario_elapsed_seconds({"result": {"duration": 2.0}, "steps": []}) == 2.0


def test_elapsed_sums_steps_when_no_direct():
    element = {"steps": [
        {"result": {"duration": 1.1}},
        {"result": {"duration": 2.2}},
    ]}
    assert _scenario_elapsed_seconds(element) == 3.3


def test_elapsed_zero_when_no_duration():
    assert _scenario_elapsed_seconds({"steps": []}) == 0


def test_elapsed_skips_missing_step_duration():
    element = {"steps": [
        {"result": {"duration": 1.0}},
        {"result": {}},  # no duration key
    ]}
    assert _scenario_elapsed_seconds(element) == 1.0


def test_elapsed_direct_zero_duration():
    assert _scenario_elapsed_seconds({"duration": 0, "steps": []}) == 0


def test_elapsed_string_duration_coerced():
    assert _scenario_elapsed_seconds({"duration": "1.5", "steps": []}) == 1.5


def test_elapsed_non_numeric_duration_falls_through():
    # invalid direct, falls back to steps sum
    element = {"duration": "bad", "steps": [{"result": {"duration": 0.5}}]}
    assert _scenario_elapsed_seconds(element) == 0.5


# --- parse_results ---

def test_parse_results_skips_background():
    report = [{"name": "Feature", "elements": [
        {"type": "background", "name": "setup", "steps": [{"result": {"status": "passed", "duration": 5.0}}]},
        {"type": "scenario", "name": "S1", "status": "passed", "steps": []},
    ]}]
    rows = list(parse_results(report, date="2026-01-01", image="img", suite="s"))
    assert len(rows) == 1
    assert rows[0]["scenario"] == "S1"


def test_parse_results_empty_report():
    rows = list(parse_results([], date="2026-01-01", image="img", suite="s"))
    assert rows == []


def test_parse_results_empty_elements():
    rows = list(parse_results([{"name": "F", "elements": []}], date="2026-01-01", image="img", suite="s"))
    assert rows == []


def test_parse_results_malformed_element_missing_name():
    report = [{"name": "F", "elements": [{"type": "scenario", "status": "passed", "steps": []}]}]
    rows = list(parse_results(report, date="2026-01-01", image="img", suite="s"))
    assert rows[0]["scenario"] == "unknown"
