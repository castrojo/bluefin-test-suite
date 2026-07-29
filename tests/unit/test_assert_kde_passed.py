"""Unit tests for scripts/assert_kde_passed.py.

The guard is the last line of defence against a false green: a KDE run where
behave exits 0 but every scenario was skipped/undefined/untested. These tests
lock in that only ``status == 'passed'`` scenarios count as coverage.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.assert_kde_passed import (  # noqa: E402
    count_statuses,
    format_breakdown,
    main,
)

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "assert_kde_passed.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scenario(name: str, status: str) -> dict:
    return {"type": "scenario", "name": name, "status": status}


def _report(*statuses: str) -> list[dict]:
    return [
        {
            "name": "KDE smoke",
            "elements": [
                _scenario(f"scenario {index}", status)
                for index, status in enumerate(statuses)
            ],
        }
    ]


def _write(tmp_path: Path, report) -> Path:
    path = tmp_path / "results.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Exit-code behaviour
# ---------------------------------------------------------------------------


def test_all_passed_exits_zero(tmp_path, capsys):
    path = _write(tmp_path, _report("passed", "passed", "passed"))
    assert main([str(path)]) == 0
    assert "passed=3" in capsys.readouterr().out


def test_no_scenarios_at_all_exits_one(tmp_path, capsys):
    path = _write(tmp_path, [])
    assert main([str(path)]) == 1
    assert "::error::KDE suite reported 0 passing scenarios" in capsys.readouterr().out


def test_all_skipped_exits_one(tmp_path, capsys):
    path = _write(tmp_path, _report("skipped", "skipped"))
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "skipped=2" in out
    assert "::error::KDE suite reported 0 passing scenarios" in out


def test_all_undefined_exits_one(tmp_path, capsys):
    """The original false-green bug: undefined must never score as passing."""
    path = _write(tmp_path, _report("undefined", "undefined", "undefined"))
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "passed=0" in out
    assert "undefined=3" in out
    assert "::error::KDE suite reported 0 passing scenarios" in out


def test_all_untested_exits_one(tmp_path, capsys):
    path = _write(tmp_path, _report("untested", "untested"))
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "untested=2" in out
    assert "::error::KDE suite reported 0 passing scenarios" in out


def test_unknown_status_counts_as_other_and_exits_one(tmp_path, capsys):
    path = _write(tmp_path, _report("hook_error"))
    assert main([str(path)]) == 1
    assert "other=1" in capsys.readouterr().out


def test_mixed_passed_and_failed_exits_zero(tmp_path, capsys):
    """behave_rc gates real failures; this guard only asserts passed > 0."""
    path = _write(tmp_path, _report("passed", "failed", "skipped"))
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "passed=1 failed=1" in out


# ---------------------------------------------------------------------------
# Non-scenario elements
# ---------------------------------------------------------------------------


def test_backgrounds_are_not_counted_as_passed(tmp_path, capsys):
    report = [
        {
            "name": "KDE smoke",
            "elements": [
                {"type": "background", "name": "Shared setup", "status": "passed"},
                _scenario("real scenario", "passed"),
            ],
        }
    ]
    path = _write(tmp_path, report)
    assert main([str(path)]) == 0
    assert "passed=1" in capsys.readouterr().out


def test_only_backgrounds_exits_one(tmp_path, capsys):
    report = [
        {
            "name": "KDE smoke",
            "elements": [
                {"type": "background", "name": "Setup A", "status": "passed"},
                {"type": "background", "name": "Setup B", "status": "passed"},
            ],
        }
    ]
    path = _write(tmp_path, report)
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "passed=0" in out
    assert "::error::KDE suite reported 0 passing scenarios" in out


def test_feature_without_elements_key_is_tolerated(tmp_path, capsys):
    path = _write(tmp_path, [{"name": "Empty feature"}, {"name": "Null", "elements": None}])
    assert main([str(path)]) == 1
    assert "passed=0" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------


def test_missing_results_file_exits_one(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.json"
    assert main([str(missing)]) == 1
    assert "::error::No results.json found after KDE suite run" in capsys.readouterr().out


def test_malformed_json_exits_one_without_traceback(tmp_path, capsys):
    path = tmp_path / "results.json"
    path.write_text("not json at all {{{", encoding="utf-8")
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "::error::Could not parse" in out
    assert "Traceback" not in out


@pytest.mark.parametrize("payload", ['{"features": []}', "42", '"string"'])
def test_non_list_json_exits_one(tmp_path, capsys, payload):
    path = tmp_path / "results.json"
    path.write_text(payload, encoding="utf-8")
    assert main([str(path)]) == 1
    assert "::error::Could not parse" in capsys.readouterr().out


def test_non_dict_feature_entry_exits_one(tmp_path, capsys):
    path = _write(tmp_path, ["oops"])
    assert main([str(path)]) == 1
    assert "::error::Could not parse" in capsys.readouterr().out


def test_non_dict_element_entry_exits_one(tmp_path, capsys):
    path = _write(tmp_path, [{"name": "f", "elements": ["oops"]}])
    assert main([str(path)]) == 1
    assert "::error::Could not parse" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Helpers and CLI
# ---------------------------------------------------------------------------


def test_count_statuses_tallies_every_status():
    counts = count_statuses(
        _report("passed", "failed", "skipped", "undefined", "untested", "weird")
    )
    assert counts == {
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "undefined": 1,
        "untested": 1,
        "other": 1,
    }


def test_format_breakdown_shape():
    counts = count_statuses(_report("passed"))
    assert format_breakdown(counts) == (
        "KDE suite breakdown: passed=1 failed=0 skipped=0 "
        "undefined=0 untested=0 other=0"
    )


def test_cli_defaults_to_results_results_json(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "results.json").write_text(
        json.dumps(_report("passed")), encoding="utf-8"
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "passed=1" in completed.stdout


def test_cli_exits_one_on_all_undefined(tmp_path):
    path = _write(tmp_path, _report("undefined"))
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(path)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "::error::KDE suite reported 0 passing scenarios" in completed.stdout
    assert "Traceback" not in completed.stderr
