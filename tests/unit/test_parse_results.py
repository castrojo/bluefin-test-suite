"""Unit tests for the nightly results parser."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
