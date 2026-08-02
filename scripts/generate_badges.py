#!/usr/bin/env python3
"""Generate shields.io endpoint JSON files for per-suite coverage badges.

Counts scenarios by parsing .feature files under tests/*/features/ at publish
time. A scenario is quarantined when tagged @quarantine at feature or scenario
level; @future and @pending scenarios are counted separately as stubs. No
counts are hardcoded, so the badges always reflect the current test content.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class SuiteCounts:
    """Coverage counters for a single test suite."""

    name: str
    active: int
    quarantined: int
    future: int

    @property
    def total(self) -> int:
        """Total scenarios including stubs."""
        return self.active + self.quarantined + self.future

    @property
    def runnable(self) -> int:
        """Scenarios that are active or quarantined (i.e. not stubs)."""
        return self.active + self.quarantined

    @property
    def quarantine_ratio(self) -> float:
        """Quarantined share of runnable scenarios."""
        return self.quarantined / self.runnable if self.runnable else 0.0


def parse_feature_scenarios(content: str) -> list[tuple[str, set[str]]]:
    """Return (scenario_name, effective_tags) for each scenario in a feature.

    Feature-level tags are inherited by every scenario. Tags applying to
    ``Rule:`` or ``Examples:`` blocks are ignored for simplicity because the
    test suite does not use them for quarantine/future tagging.
    """
    feature_tags: tuple[str, ...] = ()
    pending_tags: list[str] = []
    scenarios: list[tuple[str, set[str]]] = []

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("@"):
            pending_tags.extend(
                token[1:] for token in stripped.split() if token.startswith("@")
            )
            continue

        if stripped.startswith("Feature:"):
            feature_tags = tuple(pending_tags)
            pending_tags = []
            continue

        if stripped.startswith(("Scenario:", "Scenario Outline:")):
            _, scenario_name = stripped.split(":", 1)
            scenarios.append(
                (scenario_name.strip(), set(feature_tags) | set(pending_tags))
            )
            pending_tags = []
            continue

        if stripped.startswith(("Rule:", "Background:", "Examples:")):
            pending_tags = []

    return scenarios


def iter_feature_files(repo_root: Path) -> Iterable[Path]:
    """Yield all .feature files under tests/*/features."""
    tests_root = repo_root / "tests"
    if tests_root.exists():
        yield from sorted(tests_root.rglob("*.feature"))


def count_scenarios(repo_root: Path) -> dict[str, SuiteCounts]:
    """Count active/quarantined/future scenarios per suite."""
    suites: dict[str, SuiteCounts] = {}

    for feature_file in iter_feature_files(repo_root):
        suite = feature_file.relative_to(repo_root / "tests").parts[0]
        content = feature_file.read_text(encoding="utf-8")
        for _name, tags in parse_feature_scenarios(content):
            if suite not in suites:
                suites[suite] = SuiteCounts(
                    name=suite, active=0, quarantined=0, future=0
                )

            if "future" in tags or "pending" in tags:
                suites[suite].future += 1
            elif "quarantine" in tags:
                suites[suite].quarantined += 1
            else:
                suites[suite].active += 1

    return suites


def badge_color(counts: SuiteCounts) -> str:
    """Pick a shields.io color based on the quarantine ratio.

    Thresholds:
      - green:  no quarantined scenarios
      - yellow: up to 10% of runnable scenarios quarantined
      - red:    more than 10% quarantined
    """
    if counts.quarantined == 0:
        return "green"
    if counts.quarantine_ratio <= 0.10:
        return "yellow"
    return "red"


def suite_badge_payload(counts: SuiteCounts) -> dict[str, object]:
    """shields.io endpoint payload for the active/quarantined badge."""
    return {
        "schemaVersion": 1,
        "label": counts.name,
        "message": f"{counts.active} active / {counts.quarantined} quarantined",
        "color": badge_color(counts),
    }


def stubs_badge_payload(counts: SuiteCounts) -> dict[str, object]:
    """shields.io endpoint payload for the future-stub badge."""
    return {
        "schemaVersion": 1,
        "label": f"{counts.name} stubs",
        "message": f"{counts.future} pending",
        "color": "lightgrey",
    }


def total_badge_payload(counts: Iterable[SuiteCounts]) -> dict[str, object]:
    """Aggregate active/quarantined payload across all suites."""
    active = sum(c.active for c in counts)
    quarantined = sum(c.quarantined for c in counts)
    runnable = active + quarantined
    ratio = quarantined / runnable if runnable else 0.0

    if quarantined == 0:
        color = "green"
    elif ratio <= 0.10:
        color = "yellow"
    else:
        color = "red"

    return {
        "schemaVersion": 1,
        "label": "total coverage",
        "message": f"{active} active / {quarantined} quarantined",
        "color": color,
    }


def total_stubs_payload(counts: Iterable[SuiteCounts]) -> dict[str, object]:
    """Aggregate future-stub payload across all suites."""
    future = sum(c.future for c in counts)
    return {
        "schemaVersion": 1,
        "label": "stubs",
        "message": f"{future} pending",
        "color": "lightgrey",
    }


def write_badges(suites: dict[str, SuiteCounts], output_dir: Path) -> list[Path]:
    """Write all badge JSON files and return the written paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for suite in sorted(suites):
        counts = suites[suite]

        suite_path = output_dir / f"{suite}.json"
        suite_path.write_text(
            json.dumps(suite_badge_payload(counts), indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(suite_path)

        stubs_path = output_dir / f"{suite}-stubs.json"
        stubs_path.write_text(
            json.dumps(stubs_badge_payload(counts), indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(stubs_path)

    total_path = output_dir / "total.json"
    total_path.write_text(
        json.dumps(total_badge_payload(suites.values()), indent=2) + "\n",
        encoding="utf-8",
    )
    written.append(total_path)

    stubs_total_path = output_dir / "stubs.json"
    stubs_total_path.write_text(
        json.dumps(total_stubs_payload(suites.values()), indent=2) + "\n",
        encoding="utf-8",
    )
    written.append(stubs_total_path)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate per-suite coverage badge JSON files."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to scan (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: <repo-root>/badges)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else repo_root / "badges"

    suites = count_scenarios(repo_root)
    if not suites:
        print("No feature files found under tests/*/features/")
        return 1

    written = write_badges(suites, output_dir)
    for path in written:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
