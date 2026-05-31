"""Unit tests for shared timing helpers."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.shared import timing


def _context(results_dir, start=None):
    context = SimpleNamespace(
        config=SimpleNamespace(userdata={"results_dir": str(results_dir)}),
    )
    if start is not None:
        context._timing_start = start
    return context


def _scenario(name="Launch app", status="passed", feature="Smoke"):
    return SimpleNamespace(
        name=name,
        status=SimpleNamespace(name=status),
        feature=SimpleNamespace(name=feature),
    )


def test_record_start_sets_monotonic_float():
    context = SimpleNamespace()

    with patch("tests.shared.timing.time.monotonic", return_value=12.5):
        timing.record_start(context)

    assert isinstance(context._timing_start, float)
    assert context._timing_start == pytest.approx(12.5)


@pytest.mark.parametrize(
    ("end_time", "expected_violation"),
    [
        (102.5, False),
        (104.25, True),
    ],
)
def test_record_end_writes_jsonl_and_sets_sla_status(
    tmp_path,
    monkeypatch,
    end_time,
    expected_violation,
):
    context = _context(tmp_path, start=100.0)
    scenario = _scenario()
    monkeypatch.setattr(timing, "SLA_SCENARIO_DEFAULT", 3)

    with patch("tests.shared.timing.time.monotonic", return_value=end_time):
        elapsed = timing.record_end(context, scenario)

    assert elapsed == pytest.approx(end_time - 100.0)

    timings_file = tmp_path / "timings.jsonl"
    lines = timings_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert {"scenario", "elapsed", "sla_violated"} <= entry.keys()
    assert entry["scenario"] == scenario.name
    assert entry["elapsed"] == pytest.approx(round(elapsed, 3))
    assert entry["elapsed_s"] == pytest.approx(round(elapsed, 3))
    assert entry["sla_violated"] is expected_violation
    assert entry["feature"] == scenario.feature.name
    assert entry["status"] == scenario.status.name


def test_record_end_without_start_returns_none(tmp_path):
    context = _context(tmp_path)

    assert timing.record_end(context, _scenario()) is None
    assert not (tmp_path / "timings.jsonl").exists()


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("0", False),
        ("false", False),
        ("", False),
    ],
)
def test_sla_strict_env_parsing(monkeypatch, raw_value, expected):
    monkeypatch.setenv("TIMING_SLA_STRICT", raw_value)

    reloaded = importlib.reload(timing)
    try:
        assert reloaded.SLA_STRICT is expected
    finally:
        monkeypatch.delenv("TIMING_SLA_STRICT", raising=False)
        importlib.reload(timing)
