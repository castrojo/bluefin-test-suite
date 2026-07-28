#!/usr/bin/env python3
"""Assert a KDE behave run reported at least one passing scenario.

Backstop against a false green: if the KDE suite silently self-disables (for
example the webdriver is unreachable), behave can exit 0 with every scenario
skipped/undefined/untested. This guard counts ``passed`` positively so those
statuses can never be mistaken for coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_RESULTS = Path("results/results.json")

COUNTED_STATUSES = ("passed", "failed", "skipped", "undefined", "untested")


def count_statuses(report: Any) -> dict[str, int]:
    """Count scenario statuses in a behave JSON report.

    Non-scenario elements (backgrounds) are ignored. Any status outside
    ``COUNTED_STATUSES`` is tallied under ``other``.
    """
    counts = {status: 0 for status in COUNTED_STATUSES}
    counts["other"] = 0

    if not isinstance(report, list):
        raise ValueError("results.json must contain a list of features")

    for feature in report:
        if not isinstance(feature, dict):
            raise ValueError("results.json feature entries must be objects")
        for element in feature.get("elements") or []:
            if not isinstance(element, dict):
                raise ValueError("results.json element entries must be objects")
            if element.get("type") != "scenario":
                continue
            status = element.get("status", "")
            if status in counts and status != "other":
                counts[status] += 1
            else:
                counts["other"] += 1

    return counts


def format_breakdown(counts: dict[str, int]) -> str:
    return (
        "KDE suite breakdown: "
        f"passed={counts['passed']} failed={counts['failed']} "
        f"skipped={counts['skipped']} undefined={counts['undefined']} "
        f"untested={counts['untested']} other={counts['other']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_json",
        nargs="?",
        default=DEFAULT_RESULTS,
        type=Path,
        help="Path to behave JSON output (default: results/results.json)",
    )
    args = parser.parse_args(argv)

    if not args.results_json.is_file():
        print(f"::error::No results.json found after KDE suite run: {args.results_json}")
        return 1

    try:
        with args.results_json.open(encoding="utf-8") as file_obj:
            report = json.load(file_obj)
    except (ValueError, OSError) as error:
        print(f"::error::Could not parse {args.results_json}: {error}")
        return 1

    try:
        counts = count_statuses(report)
    except ValueError as error:
        print(f"::error::Could not parse {args.results_json}: {error}")
        return 1

    print(format_breakdown(counts))

    if counts["passed"] <= 0:
        print(
            "::error::KDE suite reported 0 passing scenarios — the suite "
            "silently self-disabled. Check webdriver connectivity and "
            "AT-SPI bus availability."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
