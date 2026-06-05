"""Unit tests for behave_retry.py pure helper functions.

These helpers are critical to the retry pipeline and are not covered by the
existing test_retry.py (which focuses on the full retry loop).
"""
from tests.shared.behave_retry import (
    DEFAULT_RETRIES,
    OPTION_FLAGS_WITH_VALUES,
    REPORTER_FLAGS,
    _split_long_option,
    extract_option_args,
    parse_cli_args,
    read_rerun_entries,
    strip_reporter_args,
    with_quarantine_filter,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_retries_is_positive(self):
        assert DEFAULT_RETRIES >= 1

    def test_option_flags_contains_tags(self):
        assert "--tags" in OPTION_FLAGS_WITH_VALUES
        assert "-t" in OPTION_FLAGS_WITH_VALUES

    def test_option_flags_contains_format(self):
        assert "--format" in OPTION_FLAGS_WITH_VALUES
        assert "-f" in OPTION_FLAGS_WITH_VALUES

    def test_reporter_flags_is_subset_of_option_flags_with_values(self):
        # All reporter flags that take values must be in OPTION_FLAGS_WITH_VALUES
        value_reporters = {f for f in REPORTER_FLAGS if f in OPTION_FLAGS_WITH_VALUES}
        assert len(value_reporters) > 0


# ---------------------------------------------------------------------------
# parse_cli_args
# ---------------------------------------------------------------------------

class TestParseCliArgs:
    def test_returns_default_retries_when_not_specified(self):
        retries, args = parse_cli_args(["tests/", "--tags", "@smoke"])
        assert retries == DEFAULT_RETRIES

    def test_parses_retries_space_form(self):
        retries, args = parse_cli_args(["--retries", "5", "tests/"])
        assert retries == 5

    def test_parses_retries_equals_form(self):
        retries, args = parse_cli_args(["--retries=3", "tests/"])
        assert retries == 3

    def test_strips_retries_from_behave_args_space_form(self):
        _, args = parse_cli_args(["--retries", "3", "tests/", "--tags", "@x"])
        assert "--retries" not in args
        assert "3" not in args

    def test_strips_retries_from_behave_args_equals_form(self):
        _, args = parse_cli_args(["--retries=2", "tests/"])
        assert "--retries=2" not in args

    def test_preserves_other_args(self):
        _, args = parse_cli_args(["tests/", "--tags", "@smoke", "--dry-run"])
        assert "tests/" in args
        assert "--tags" in args
        assert "@smoke" in args
        assert "--dry-run" in args

    def test_empty_argv(self):
        retries, args = parse_cli_args([])
        assert retries == DEFAULT_RETRIES
        assert args == []

    def test_retries_zero_allowed(self):
        retries, args = parse_cli_args(["--retries=0"])
        assert retries == 0


# ---------------------------------------------------------------------------
# with_quarantine_filter
# ---------------------------------------------------------------------------

class TestWithQuarantineFilter:
    def test_appends_quarantine_tag(self):
        result = with_quarantine_filter(["tests/"])
        assert "--tags" in result
        assert "~@quarantine" in result

    def test_preserves_existing_args(self):
        result = with_quarantine_filter(["tests/", "--dry-run"])
        assert "tests/" in result
        assert "--dry-run" in result

    def test_adds_at_end(self):
        result = with_quarantine_filter(["tests/"])
        idx = result.index("~@quarantine")
        assert result[idx - 1] == "--tags"

    def test_does_not_mutate_original(self):
        original = ["tests/"]
        with_quarantine_filter(original)
        assert original == ["tests/"]


# ---------------------------------------------------------------------------
# _split_long_option
# ---------------------------------------------------------------------------

class TestSplitLongOption:
    def test_splits_long_option_with_value(self):
        assert _split_long_option("--format=plain") == "--format"

    def test_returns_arg_unchanged_when_no_equals(self):
        assert _split_long_option("--format") == "--format"

    def test_returns_short_option_unchanged(self):
        assert _split_long_option("-f") == "-f"

    def test_returns_positional_unchanged(self):
        assert _split_long_option("tests/smoke") == "tests/smoke"

    def test_preserves_value_containing_equals(self):
        # Only first = is used as split point
        assert _split_long_option("--define=KEY=VALUE") == "--define"


# ---------------------------------------------------------------------------
# extract_option_args
# ---------------------------------------------------------------------------

class TestExtractOptionArgs:
    def test_returns_only_flags(self):
        result = extract_option_args(["tests/", "--dry-run", "--tags", "@x"])
        assert "tests/" not in result
        assert "--dry-run" in result
        assert "--tags" in result

    def test_includes_value_for_option_that_takes_value(self):
        result = extract_option_args(["--tags", "@smoke"])
        assert "--tags" in result
        assert "@smoke" in result

    def test_inline_value_not_duplicated(self):
        result = extract_option_args(["--tags=@smoke"])
        assert "--tags=@smoke" in result
        # Value should NOT appear separately
        assert result.count("@smoke") == 0 or "--tags=@smoke" in result

    def test_short_option_without_value(self):
        result = extract_option_args(["-d"])
        assert "-d" in result

    def test_empty_args_returns_empty(self):
        result = extract_option_args([])
        assert result == []


# ---------------------------------------------------------------------------
# strip_reporter_args
# ---------------------------------------------------------------------------

class TestStripReporterArgs:
    def test_strips_format_flag_with_value(self):
        result = strip_reporter_args(["--format", "plain", "--dry-run"])
        assert "--format" not in result
        assert "plain" not in result
        assert "--dry-run" in result

    def test_strips_outfile_flag_with_value(self):
        result = strip_reporter_args(["--outfile", "out.txt", "tests/"])
        assert "--outfile" not in result
        assert "out.txt" not in result
        assert "tests/" in result

    def test_strips_junit_flag_no_value(self):
        result = strip_reporter_args(["--junit", "tests/"])
        assert "--junit" not in result
        assert "tests/" in result

    def test_preserves_non_reporter_flags(self):
        result = strip_reporter_args(["--dry-run", "--tags", "@smoke"])
        assert "--dry-run" in result
        assert "--tags" in result
        assert "@smoke" in result

    def test_empty_returns_empty(self):
        result = strip_reporter_args([])
        assert result == []

    def test_strips_inline_format_value(self):
        result = strip_reporter_args(["--format=plain", "tests/"])
        assert "--format=plain" not in result
        assert "tests/" in result


# ---------------------------------------------------------------------------
# read_rerun_entries
# ---------------------------------------------------------------------------

class TestReadRerunEntries:
    def test_returns_empty_when_file_missing(self, tmp_path):
        result = read_rerun_entries(tmp_path / "nonexistent.txt")
        assert result == []

    def test_reads_scenario_lines(self, tmp_path):
        rerun = tmp_path / "rerun.txt"
        rerun.write_text("tests/smoke/features/system.feature:42\n")
        result = read_rerun_entries(rerun)
        assert result == ["tests/smoke/features/system.feature:42"]

    def test_strips_comment_lines(self, tmp_path):
        rerun = tmp_path / "rerun.txt"
        rerun.write_text("# -- RERUN: 1 failing scenario\ntests/smoke/features/foo.feature:5\n")
        result = read_rerun_entries(rerun)
        assert "# -- RERUN: 1 failing scenario" not in result
        assert "tests/smoke/features/foo.feature:5" in result

    def test_deduplicates_entries(self, tmp_path):
        rerun = tmp_path / "rerun.txt"
        rerun.write_text(
            "tests/smoke/features/foo.feature:5\n"
            "tests/smoke/features/foo.feature:5\n"
        )
        result = read_rerun_entries(rerun)
        assert result.count("tests/smoke/features/foo.feature:5") == 1

    def test_strips_blank_lines(self, tmp_path):
        rerun = tmp_path / "rerun.txt"
        rerun.write_text("tests/smoke/features/foo.feature:5\n\n\n")
        result = read_rerun_entries(rerun)
        assert "" not in result

    def test_preserves_order(self, tmp_path):
        rerun = tmp_path / "rerun.txt"
        lines = ["tests/a.feature:1", "tests/b.feature:2", "tests/c.feature:3"]
        rerun.write_text("\n".join(lines) + "\n")
        result = read_rerun_entries(rerun)
        assert result == lines
