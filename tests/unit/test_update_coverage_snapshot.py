"""Unit tests for scripts/update_coverage_snapshot.py.

Covers parse_scenarios tag inheritance, classify precedence, count_scenarios
aggregation, render_snapshot output and update_file in write and --check modes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import update_coverage_snapshot as ucs  # noqa: E402


def _write_feature(repo_root: Path, suite: str, name: str, content: str) -> Path:
    path = repo_root / "tests" / suite / "features" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def repo_root(tmp_path):
    (tmp_path / "tests").mkdir()
    return tmp_path


# ── parse_scenarios ───────────────────────────────────────────────────────────


class TestParseScenarios:
    def test_untagged_scenario_has_empty_tag_set(self):
        assert ucs.parse_scenarios("Feature: F\n\n  Scenario: one\n") == [set()]

    def test_scenario_tags_are_captured(self):
        content = "Feature: F\n\n  @pending\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"pending"}]

    def test_feature_tags_are_inherited_by_every_scenario(self):
        content = "@quarantine\nFeature: F\n\n  Scenario: one\n\n  Scenario: two\n"
        assert ucs.parse_scenarios(content) == [{"quarantine"}, {"quarantine"}]

    def test_feature_and_scenario_tags_are_unioned(self):
        content = "@nvidia\nFeature: F\n\n  @future\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"nvidia", "future"}]

    def test_scenario_tags_do_not_leak_to_the_next_scenario(self):
        content = "Feature: F\n\n  @pending\n  Scenario: one\n\n  Scenario: two\n"
        assert ucs.parse_scenarios(content) == [{"pending"}, set()]

    def test_multiple_tags_on_one_line(self):
        content = "Feature: F\n\n  @pending @hardware_blocked\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"pending", "hardware_blocked"}]

    def test_tags_accumulate_across_consecutive_tag_lines(self):
        content = "Feature: F\n\n  @pending\n  @future\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"pending", "future"}]

    def test_hyphenated_tags_are_captured_whole(self):
        content = "Feature: F\n\n  @vm-only\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"vm-only"}]

    def test_scenario_outline_counts_as_a_scenario(self):
        content = "Feature: F\n\n  @future\n  Scenario Outline: one\n    Examples:\n"
        assert ucs.parse_scenarios(content) == [{"future"}]

    def test_comment_lines_are_ignored(self):
        content = "Feature: F\n\n  # @quarantine is only mentioned here\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [set()]

    def test_step_lines_do_not_reset_or_add_tags(self):
        content = (
            "Feature: F\n\n  @pending\n  Scenario: one\n"
            "    Given a thing\n    Then it works\n\n  Scenario: two\n"
        )
        assert ucs.parse_scenarios(content) == [{"pending"}, set()]

    @pytest.mark.parametrize("keyword", ["Rule:", "Background:", "Examples:"])
    def test_structural_keywords_discard_pending_tags(self, keyword):
        content = f"Feature: F\n\n  @pending\n  {keyword}\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [set()]

    def test_tags_before_feature_do_not_double_apply_after_feature(self):
        content = "@smoke\nFeature: F\n\n  @pending\n  Scenario: one\n"
        assert ucs.parse_scenarios(content) == [{"smoke", "pending"}]

    def test_file_without_scenarios_returns_empty_list(self):
        assert ucs.parse_scenarios("@smoke\nFeature: F\n") == []


# ── classify ──────────────────────────────────────────────────────────────────


class TestClassify:
    def test_no_tags_is_active(self):
        assert ucs.classify(set()) == "active"

    def test_unrelated_tags_are_active(self):
        assert ucs.classify({"smoke", "dakota_only"}) == "active"

    @pytest.mark.parametrize("tag", ["hardware_blocked", "future", "pending"])
    def test_backlog_tags_are_pending(self, tag):
        assert ucs.classify({tag}) == "pending"

    def test_quarantine_is_quarantined(self):
        assert ucs.classify({"quarantine"}) == "quarantined"

    @pytest.mark.parametrize("tag", ["hardware_blocked", "future", "pending"])
    def test_quarantine_wins_over_backlog_tags(self, tag):
        assert ucs.classify({"quarantine", tag}) == "quarantined"


# ── SuiteCounts ───────────────────────────────────────────────────────────────


class TestSuiteCounts:
    def test_total_sums_all_buckets(self):
        counts = ucs.SuiteCounts(name="smoke", active=3, quarantined=2, pending=5)
        assert counts.total == 10

    def test_default_counts_are_zero(self):
        assert ucs.SuiteCounts(name="smoke").total == 0


# ── count_scenarios ───────────────────────────────────────────────────────────


class TestCountScenarios:
    def test_empty_tests_tree_yields_no_suites(self, repo_root):
        assert ucs.count_scenarios(repo_root) == {}

    def test_buckets_scenarios_by_classification(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", (
            "Feature: F\n\n"
            "  Scenario: active one\n\n"
            "  @pending\n  Scenario: backlog one\n\n"
            "  @quarantine\n  Scenario: broken one\n"
        ))
        counts = ucs.count_scenarios(repo_root)
        assert counts["smoke"].active == 1
        assert counts["smoke"].quarantined == 1
        assert counts["smoke"].pending == 1
        assert counts["smoke"].total == 3

    def test_suite_name_is_first_path_part_under_tests(self, repo_root):
        _write_feature(repo_root, "lifecycle", "a.feature", "Feature: F\n  Scenario: s\n")
        assert set(ucs.count_scenarios(repo_root)) == {"lifecycle"}

    def test_multiple_feature_files_aggregate_into_one_suite(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _write_feature(repo_root, "smoke", "b.feature", "Feature: G\n  Scenario: s\n")
        assert ucs.count_scenarios(repo_root)["smoke"].active == 2

    def test_suites_are_tracked_separately(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _write_feature(repo_root, "security", "a.feature",
                       "@quarantine\nFeature: G\n  Scenario: s\n")
        counts = ucs.count_scenarios(repo_root)
        assert counts["smoke"].active == 1
        assert counts["security"].quarantined == 1


# ── render_snapshot ───────────────────────────────────────────────────────────


class TestRenderSnapshot:
    def test_block_is_wrapped_in_markers(self, repo_root):
        block = ucs.render_snapshot(repo_root)
        assert block.startswith(ucs.MARKER_START)
        assert block.endswith(ucs.MARKER_END)

    def test_summary_line_reports_totals_and_file_count(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", (
            "Feature: F\n\n  Scenario: one\n\n  @future\n  Scenario: two\n"
        ))
        _write_feature(repo_root, "smoke", "b.feature",
                       "@quarantine\nFeature: G\n  Scenario: three\n")
        block = ucs.render_snapshot(repo_root)
        assert "3 scenarios across 2 feature files: 1 active, 1 quarantined, 1 " in block

    def test_suite_row_uses_hand_maintained_note(self, repo_root, monkeypatch):
        monkeypatch.setitem(ucs.SUITE_NOTES, "smoke", "hand written prose")
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        assert "| smoke | 1 | 1 | 0 | 0 | hand written prose |" in ucs.render_snapshot(repo_root)

    def test_suite_without_a_note_gets_an_empty_cell(self, repo_root):
        _write_feature(repo_root, "brand-new", "a.feature", "Feature: F\n  Scenario: s\n")
        assert "| brand-new | 1 | 1 | 0 | 0 |  |" in ucs.render_snapshot(repo_root)

    def test_suites_are_listed_in_sorted_order(self, repo_root):
        for suite in ("zebra", "alpha"):
            _write_feature(repo_root, suite, "a.feature", "Feature: F\n  Scenario: s\n")
        block = ucs.render_snapshot(repo_root)
        assert block.index("| alpha |") < block.index("| zebra |")

    def test_empty_tree_renders_zero_totals(self, repo_root):
        block = ucs.render_snapshot(repo_root)
        assert "0 scenarios across 0 feature files: 0 active, 0 quarantined, 0 " in block


# ── update_file ───────────────────────────────────────────────────────────────


def _write_suite_map(repo_root: Path, body: str) -> Path:
    path = repo_root / ucs.SUITE_MAP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _synced_suite_map(repo_root: Path) -> Path:
    return _write_suite_map(
        repo_root,
        f"# Suite map\n\nintro\n\n{ucs.render_snapshot(repo_root)}\n\noutro\n",
    )


class TestUpdateFile:
    def test_missing_markers_returns_2(self, repo_root, capsys):
        _write_suite_map(repo_root, "# Suite map\n\nno markers here\n")
        assert ucs.update_file(repo_root, check=False) == 2
        assert "markers not found" in capsys.readouterr().err

    def test_missing_end_marker_returns_2(self, repo_root):
        _write_suite_map(repo_root, f"# Suite map\n\n{ucs.MARKER_START}\n")
        assert ucs.update_file(repo_root, check=False) == 2

    def test_check_passes_when_snapshot_is_current(self, repo_root, capsys):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _synced_suite_map(repo_root)
        assert ucs.update_file(repo_root, check=True) == 0
        assert "OK:" in capsys.readouterr().out

    def test_check_fails_when_a_scenario_was_added(self, repo_root, capsys):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _synced_suite_map(repo_root)
        _write_feature(repo_root, "smoke", "b.feature", "Feature: G\n  Scenario: t\n")
        assert ucs.update_file(repo_root, check=True) == 1
        assert "STALE:" in capsys.readouterr().out

    def test_check_does_not_rewrite_the_file(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        path = _synced_suite_map(repo_root)
        _write_feature(repo_root, "smoke", "b.feature", "Feature: G\n  Scenario: t\n")
        before = path.read_text(encoding="utf-8")
        assert ucs.update_file(repo_root, check=True) == 1
        assert path.read_text(encoding="utf-8") == before

    def test_write_replaces_only_the_marked_block(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        path = _write_suite_map(
            repo_root,
            f"# Suite map\n\nintro\n\n{ucs.MARKER_START}\nstale\n{ucs.MARKER_END}\n\noutro\n",
        )
        assert ucs.update_file(repo_root, check=False) == 0
        text = path.read_text(encoding="utf-8")
        assert "stale" not in text
        assert text.startswith("# Suite map\n\nintro\n\n")
        assert text.endswith("\n\noutro\n")
        assert "| smoke | 1 | 1 | 0 | 0 |" in text

    def test_write_is_idempotent(self, repo_root, capsys):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _synced_suite_map(repo_root)
        assert ucs.update_file(repo_root, check=False) == 0
        assert "No change" in capsys.readouterr().out

    def test_write_then_check_is_clean(self, repo_root):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _write_suite_map(
            repo_root, f"# Suite map\n\n{ucs.MARKER_START}\nstale\n{ucs.MARKER_END}\n"
        )
        assert ucs.update_file(repo_root, check=False) == 0
        assert ucs.update_file(repo_root, check=True) == 0


# ── main ──────────────────────────────────────────────────────────────────────


class TestMain:
    def test_repo_root_flag_is_honoured(self, repo_root, monkeypatch):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _synced_suite_map(repo_root)
        monkeypatch.setattr(
            sys, "argv",
            ["update_coverage_snapshot.py", "--check", "--repo-root", str(repo_root)],
        )
        assert ucs.main() == 0

    def test_check_flag_reports_stale_repo(self, repo_root, monkeypatch):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        _write_suite_map(
            repo_root, f"# Suite map\n\n{ucs.MARKER_START}\nstale\n{ucs.MARKER_END}\n"
        )
        monkeypatch.setattr(
            sys, "argv",
            ["update_coverage_snapshot.py", "--check", "--repo-root", str(repo_root)],
        )
        assert ucs.main() == 1

    def test_without_check_the_file_is_written(self, repo_root, monkeypatch):
        _write_feature(repo_root, "smoke", "a.feature", "Feature: F\n  Scenario: s\n")
        path = _write_suite_map(
            repo_root, f"# Suite map\n\n{ucs.MARKER_START}\nstale\n{ucs.MARKER_END}\n"
        )
        monkeypatch.setattr(
            sys, "argv", ["update_coverage_snapshot.py", "--repo-root", str(repo_root)]
        )
        assert ucs.main() == 0
        assert "| smoke | 1 | 1 | 0 | 0 |" in path.read_text(encoding="utf-8")
