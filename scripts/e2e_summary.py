#!/usr/bin/env python3
"""Count scenario results for the e2e job summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCENARIO_STATUSES = ("passed", "failed", "skipped", "undefined", "untested")


def count_scenarios(report: list[dict[str, Any]]) -> dict[str, int]:
    """Count known statuses on scenario elements, excluding backgrounds."""
    counts = Counter(
        element.get("status")
        for feature in report
        for element in feature.get("elements", [])
        if element.get("type") == "scenario"
        and element.get("status") in SCENARIO_STATUSES
    )
    return {status: counts[status] for status in SCENARIO_STATUSES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_json", type=Path)
    args = parser.parse_args(argv)
    with args.results_json.open(encoding="utf-8") as file_obj:
        report = json.load(file_obj)
    print(json.dumps(count_scenarios(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
