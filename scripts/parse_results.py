#!/usr/bin/env python3
"""Convert behave JSON output into per-scenario JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STATUS_MAP = {
    "passed": "passed",
    "failed": "failed",
    "error": "error",
    "skipped": "skipped",
    "untested": "skipped",
    "undefined": "error",
    "hook_error": "error",
}


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None
    return STATUS_MAP.get(str(value).strip().lower())


def _scenario_status(element: dict[str, Any]) -> str:
    direct_statuses = [
        _normalize_status(element.get("status")),
        _normalize_status(element.get("result", {}).get("status")),
    ]
    for status in direct_statuses:
        if status is not None:
            return status

    step_statuses = [
        _normalize_status(step.get("result", {}).get("status"))
        for step in element.get("steps", [])
    ]
    step_statuses = [status for status in step_statuses if status is not None]

    if "error" in step_statuses:
        return "error"
    if "failed" in step_statuses:
        return "failed"
    if step_statuses and all(status == "skipped" for status in step_statuses):
        return "skipped"
    if "passed" in step_statuses:
        return "passed"
    return "error"


def _scenario_elapsed_seconds(element: dict[str, Any]) -> float:
    for candidate in (element.get("duration"), element.get("result", {}).get("duration")):
        value = _coerce_float(candidate)
        if value is not None:
            return round(value, 3)

    durations = [
        _coerce_float(step.get("result", {}).get("duration"))
        for step in element.get("steps", [])
    ]
    total = sum(duration for duration in durations if duration is not None)
    return round(total, 3)


def _iter_scenarios(report: list[dict[str, Any]]):
    for feature in report:
        for element in feature.get("elements", []):
            if element.get("type") == "background":
                continue
            yield element


def parse_results(report: list[dict[str, Any]], *, date: str, image: str, suite: str):
    for element in _iter_scenarios(report):
        yield {
            "date": date,
            "image": image,
            "suite": suite,
            "scenario": element.get("name", "unknown"),
            "status": _scenario_status(element),
            "elapsed_s": _scenario_elapsed_seconds(element),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_json", type=Path, help="Path to behave JSON output")
    parser.add_argument("--image", required=True, help="Image under test")
    parser.add_argument("--suite", required=True, help="Behave suite name")
    parser.add_argument("--date", required=True, help="Run date in YYYY-MM-DD format")
    args = parser.parse_args(argv)

    with args.results_json.open(encoding="utf-8") as file_obj:
        report = json.load(file_obj)

    for entry in parse_results(report, date=args.date, image=args.image, suite=args.suite):
        sys.stdout.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
