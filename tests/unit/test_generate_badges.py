"""Unit tests for scripts/generate_badges.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.generate_badges import (  # noqa: E402
    SuiteCounts,
    badge_color,
    count_scenarios,
    parse_feature_scenarios,
    suite_badge_payload,
    total_badge_payload,
    write_badges,
)


# ── parse_feature_scenarios ───────────────────────────────────────────────────


def test_parse_feature_inherits_feature_tags():
    content = """\
@smoke_suite @quarantine
Feature: Feature-level quarantine

  @active
  Scenario: Active scenario still inherits quarantine
    * step one

  Scenario: Untagged scenario inherits quarantine
    * step two
"""
    scenarios = parse_feature_scenarios(content)
    assert len(scenarios) == 2
    assert scenarios[0][1] == {"smoke_suite", "quarantine", "active"}
    assert scenarios[1][1] == {"smoke_suite", "quarantine"}


def test_parse_feature_scenario_level_tags():
    content = """\
Feature: Scenario-level tags

  @future
  Scenario: A stub
    * step one

  @quarantine @slow
  Scenario: A quarantined scenario
    * step two

  @smoke
  Scenario: Active scenario
    * step three
"""
    scenarios = parse_feature_scenarios(content)
    assert scenarios[0][1] == {"future"}
    assert scenarios[1][1] == {"quarantine", "slow"}
    assert scenarios[2][1] == {"smoke"}


def test_parse_feature_ignores_comments_and_background():
    content = """\
@feature_tag
Feature: With background

  Background:
    Given shared setup

  # This is a comment
  @scenario_tag
  Scenario: Real scenario
    * step one
"""
    scenarios = parse_feature_scenarios(content)
    assert len(scenarios) == 1
    assert scenarios[0][1] == {"feature_tag", "scenario_tag"}


def test_parse_feature_ignores_rule_block_tags():
    content = """\
Feature: Rule block

  @rule_tag
  Rule: Some rule

    @scenario_tag
    Scenario: Inside rule
      * step
"""
    scenarios = parse_feature_scenarios(content)
    assert len(scenarios) == 1
    assert scenarios[0][1] == {"scenario_tag"}


# ── count_scenarios ───────────────────────────────────────────────────────────


def test_count_scenarios_buckets_by_suite(tmp_path):
    tests = tmp_path / "tests"
    (tests / "smoke" / "features").mkdir(parents=True)
    (tests / "common" / "features").mkdir(parents=True)

    (tests / "smoke" / "features" / "a.feature").write_text(
        "@smoke_suite\nFeature: Smoke A\n\n"
        "  @active\n  Scenario: Active smoke\n    * step\n\n"
        "  @quarantine\n  Scenario: Quarantined smoke\n    * step\n",
        encoding="utf-8",
    )
    (tests / "common" / "features" / "a.feature").write_text(
        "@common_suite\nFeature: Common A\n\n"
        "  @future\n  Scenario: Future common\n    * step\n\n"
        "  @pending\n  Scenario: Pending common\n    * step\n\n"
        "  Scenario: Active common\n    * step\n",
        encoding="utf-8",
    )

    suites = count_scenarios(tmp_path)
    assert set(suites) == {"smoke", "common"}
    assert suites["smoke"].active == 1
    assert suites["smoke"].quarantined == 1
    assert suites["smoke"].future == 0
    assert suites["common"].active == 1
    assert suites["common"].quarantined == 0
    assert suites["common"].future == 2


def test_count_scenarios_no_feature_files(tmp_path):
    suites = count_scenarios(tmp_path)
    assert suites == {}


# ── badge_color / payloads ────────────────────────────────────────────────────


def test_badge_color_green_when_no_quarantined():
    counts = SuiteCounts(name="x", active=10, quarantined=0, future=2)
    assert badge_color(counts) == "green"


def test_badge_color_yellow_at_low_ratio():
    counts = SuiteCounts(name="x", active=99, quarantined=10, future=0)
    assert badge_color(counts) == "yellow"


def test_badge_color_yellow_at_exact_threshold():
    counts = SuiteCounts(name="x", active=90, quarantined=10, future=0)
    assert badge_color(counts) == "yellow"


def test_badge_color_red_above_threshold():
    counts = SuiteCounts(name="x", active=89, quarantined=11, future=0)
    assert badge_color(counts) == "red"


def test_suite_badge_payload_schema():
    counts = SuiteCounts(name="smoke", active=50, quarantined=3, future=1)
    payload = suite_badge_payload(counts)
    assert payload == {
        "schemaVersion": 1,
        "label": "smoke",
        "message": "50 active / 3 quarantined",
        "color": "yellow",
    }


def test_total_badge_payload_aggregates():
    suites = [
        SuiteCounts(name="a", active=10, quarantined=2, future=1),
        SuiteCounts(name="b", active=20, quarantined=0, future=0),
    ]
    payload = total_badge_payload(suites)
    assert payload["label"] == "total coverage"
    assert payload["message"] == "30 active / 2 quarantined"
    assert payload["color"] == "yellow"


def test_total_badge_payload_red_when_quarantine_high():
    suites = [SuiteCounts(name="a", active=8, quarantined=2, future=0)]
    payload = total_badge_payload(suites)
    assert payload["color"] == "red"


# ── write_badges ──────────────────────────────────────────────────────────────


def test_write_badges_creates_expected_files(tmp_path):
    suites = {
        "smoke": SuiteCounts(name="smoke", active=50, quarantined=3, future=0),
        "common": SuiteCounts(name="common", active=30, quarantined=0, future=2),
    }
    written = write_badges(suites, tmp_path)

    expected = {
        tmp_path / "smoke.json",
        tmp_path / "smoke-stubs.json",
        tmp_path / "common.json",
        tmp_path / "common-stubs.json",
        tmp_path / "total.json",
        tmp_path / "stubs.json",
    }
    assert set(written) == expected

    smoke = json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))
    assert smoke["schemaVersion"] == 1
    assert smoke["label"] == "smoke"
    assert smoke["message"] == "50 active / 3 quarantined"

    smoke_stubs = json.loads(
        (tmp_path / "smoke-stubs.json").read_text(encoding="utf-8")
    )
    assert smoke_stubs["label"] == "smoke stubs"
    assert smoke_stubs["message"] == "0 pending"

    total = json.loads((tmp_path / "total.json").read_text(encoding="utf-8"))
    assert total["message"] == "80 active / 3 quarantined"

    stubs = json.loads((tmp_path / "stubs.json").read_text(encoding="utf-8"))
    assert stubs["message"] == "2 pending"


# ── CLI smoke test ────────────────────────────────────────────────────────────


def test_script_runs_against_repo(tmp_path):
    """Run the script as a subprocess against a synthetic repo."""
    tests = tmp_path / "tests" / "smoke" / "features"
    tests.mkdir(parents=True)
    (tests / "demo.feature").write_text(
        "@smoke_suite\nFeature: Demo\n\n"
        "  Scenario: One\n    * step\n\n"
        "  @quarantine\n  Scenario: Two\n    * step\n",
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_badges.py"
    result = __import__("subprocess").run(
        [sys.executable, str(script), "--repo-root", str(tmp_path), "--output-dir", str(tmp_path / "badges")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    badge = json.loads((tmp_path / "badges" / "smoke.json").read_text(encoding="utf-8"))
    assert badge["message"] == "1 active / 1 quarantined"
