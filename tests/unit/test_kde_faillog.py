"""Unit tests for tests/shared/kde_faillog.py.

All SSH and host-side collectors are fully mocked. No live VM is required.
"""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import helper — stub behave before loading ssh_steps via kde_faillog
# ---------------------------------------------------------------------------

def _import_faillog():
    import sys

    behave_stub = MagicMock()
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules.setdefault("behave", behave_stub)
    sys.modules.setdefault("behave.runner", MagicMock())

    if "tests.shared.kde_faillog" in sys.modules:
        del sys.modules["tests.shared.kde_faillog"]
    if "tests.shared.ssh_steps" in sys.modules:
        del sys.modules["tests.shared.ssh_steps"]

    import tests.shared.kde_faillog as m
    return m


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_context(results_dir):
    return SimpleNamespace(
        config=SimpleNamespace(userdata={"results_dir": str(results_dir)}),
    )


def _make_scenario(name="Test scenario", status="failed", feature="KDE Smoke"):
    return SimpleNamespace(
        name=name,
        status=SimpleNamespace(name=status),
        feature=SimpleNamespace(name=feature),
    )


# ---------------------------------------------------------------------------
# Status gating
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["failed", "error", "hook_error"])
def test_collect_on_failure_collects_on_failure_statuses(tmp_path, status):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status=status)

    with patch.object(mod, "collect_journalctl", return_value={"rc": 0, "lines": 1}) as journal:
        with patch.object(mod, "collect_at_spi_tree", return_value={"rc": 0, "lines": 1}):
            with patch.object(mod, "collect_kwin_support_info", return_value={"rc": 0, "lines": 1}):
                with patch.object(mod, "collect_plasma_layout", return_value={"rc": 0, "lines": 1}):
                    with patch.object(mod, "collect_coredumpctl", return_value={"rc": 0, "lines": 1}):
                        with patch.object(mod, "collect_qemu_screendump", return_value={"rc": 0}):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is not None
    assert os.path.isdir(bundle_dir)
    journal.assert_called_once()


@pytest.mark.parametrize("status", ["passed", "skipped", "untested"])
def test_collect_on_failure_skips_non_failure_statuses(tmp_path, status):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status=status)

    with patch.object(mod, "collect_journalctl") as journal:
        bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is None
    journal.assert_not_called()


# ---------------------------------------------------------------------------
# Collector fault isolation
# ---------------------------------------------------------------------------

def test_one_collector_failing_others_still_run(tmp_path):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status="failed")

    def _failing_collector(*args, **kwargs):
        raise RuntimeError("boom")

    with patch.object(mod, "collect_at_spi_tree", side_effect=_failing_collector):
        with patch.object(mod, "collect_journalctl", return_value={"rc": 0, "lines": 5}) as journal:
            with patch.object(mod, "collect_kwin_support_info", return_value={"rc": 0, "lines": 1}):
                with patch.object(mod, "collect_plasma_layout", return_value={"rc": 0, "lines": 1}):
                    with patch.object(mod, "collect_coredumpctl", return_value={"rc": 0, "lines": 1}):
                        with patch.object(mod, "collect_qemu_screendump", return_value={"rc": 0}):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is not None
    journal.assert_called_once()
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert "collect_at_spi_tree" in [e["collector"] for e in manifest["errors"]]
    assert "collect_journalctl" in manifest["collectors"]


def test_all_collectors_failing_still_produces_bundle_with_manifest(tmp_path):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status="failed")

    def _always_fail(*args, **kwargs):
        raise RuntimeError("everything is on fire")

    with patch.object(mod, "collect_at_spi_tree", side_effect=_always_fail):
        with patch.object(mod, "collect_journalctl", side_effect=_always_fail):
            with patch.object(mod, "collect_kwin_support_info", side_effect=_always_fail):
                with patch.object(mod, "collect_plasma_layout", side_effect=_always_fail):
                    with patch.object(mod, "collect_coredumpctl", side_effect=_always_fail):
                        with patch.object(mod, "collect_qemu_screendump", side_effect=_always_fail):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is not None
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert len(manifest["errors"]) == 6
    assert manifest["collectors"] == {}
    assert manifest["scenario"] == scenario.name
    assert manifest["status"] == "failed"


def test_ssh_timeout_is_recorded_as_collector_error(tmp_path):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status="failed")

    def _timeout_on_journal(*args, **kwargs):
        if "journalctl" in args[1]:
            raise subprocess.TimeoutExpired("ssh", 30)
        return ("ok", 0)

    with patch.object(mod, "run_ssh", side_effect=_timeout_on_journal):
        bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is not None
    manifest = json.loads(Path(bundle_dir, "manifest.json").read_text(encoding="utf-8"))
    journal_errors = [e for e in manifest["errors"] if e["collector"] == "collect_journalctl"]
    assert len(journal_errors) == 1
    assert "timed out" in journal_errors[0]["error"].lower()


# ---------------------------------------------------------------------------
# Journal truncation
# ---------------------------------------------------------------------------

def test_collect_journalctl_honors_line_cap(tmp_path, monkeypatch):
    mod = _import_faillog()
    monkeypatch.setenv("KDE_FAILLOG_JOURNAL_LINES", "5")
    bundle_dir = str(tmp_path / "bundle")
    os.makedirs(bundle_dir)

    long_output = "\n".join(f"line {i}" for i in range(100))
    with patch.object(mod, "_run_ssh_collector", return_value=(long_output, 0)):
        info = mod.collect_journalctl(None, bundle_dir)

    assert info["capped_at"] == 5
    written = Path(bundle_dir, "journalctl.log").read_text(encoding="utf-8")
    # Previously asserted `written == long_output`, i.e. it verified that a
    # 5-line cap wrote all 100 lines unchanged — the test encoded the bug.
    # The remote `journalctl -n` cap does not bound what we write locally.
    assert written != long_output
    assert len([ln for ln in written.splitlines() if ln.startswith("line ")]) == 5
    assert "truncated 95 more line(s)" in written


# ---------------------------------------------------------------------------
# Results directory handling
# ---------------------------------------------------------------------------

def test_collect_on_failure_creates_missing_results_dir(tmp_path):
    mod = _import_faillog()
    results_dir = tmp_path / "missing" / "nested"
    context = _make_context(results_dir)
    scenario = _make_scenario(status="failed")

    with patch.object(mod, "collect_journalctl", return_value={"rc": 0}):
        with patch.object(mod, "collect_at_spi_tree", return_value={"rc": 0}):
            with patch.object(mod, "collect_kwin_support_info", return_value={"rc": 0}):
                with patch.object(mod, "collect_plasma_layout", return_value={"rc": 0}):
                    with patch.object(mod, "collect_coredumpctl", return_value={"rc": 0}):
                        with patch.object(mod, "collect_qemu_screendump", return_value={"rc": 0}):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    assert bundle_dir is not None
    assert os.path.isdir(results_dir)


def test_collect_on_failure_returns_none_when_results_dir_not_writable(tmp_path):
    mod = _import_faillog()
    results_dir = tmp_path / "readonly"
    results_dir.mkdir()
    results_dir.chmod(0o555)
    context = _make_context(results_dir)
    scenario = _make_scenario(status="failed")

    try:
        with patch.object(mod, "collect_journalctl") as journal:
            bundle_dir = mod.collect_on_failure(context, scenario)
        assert bundle_dir is None
        journal.assert_not_called()
    finally:
        results_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# QEMU screendump collector
# ---------------------------------------------------------------------------

def test_collect_qemu_screendump_runs_helper_script(tmp_path, monkeypatch):
    mod = _import_faillog()
    bundle_dir = str(tmp_path / "bundle")
    os.makedirs(bundle_dir)

    def _fake_run(cmd, *args, **kwargs):
        # cmd is [sys.executable, script_path, png_path]
        png_path = cmd[2]
        Path(png_path).write_text("png", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    info = mod.collect_qemu_screendump(bundle_dir, timeout=10)

    assert info["rc"] == 0
    assert os.path.exists(os.path.join(bundle_dir, "qemu_screendump.png"))


def test_collect_qemu_screendump_records_error_on_failure(tmp_path):
    mod = _import_faillog()
    bundle_dir = str(tmp_path / "bundle")
    os.makedirs(bundle_dir)

    with patch.object(mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 10)):
        with pytest.raises(TimeoutError):
            mod.collect_qemu_screendump(bundle_dir, timeout=10)


# ---------------------------------------------------------------------------
# Manifest and tarball
# ---------------------------------------------------------------------------

def test_manifest_records_collector_results_and_errors(tmp_path):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status="failed", name="Manifest test", feature="KDE Feature")

    with patch.object(mod, "collect_at_spi_tree", side_effect=RuntimeError("atspi broken")):
        with patch.object(mod, "collect_journalctl", return_value={"rc": 0, "lines": 42}) as journal:
            with patch.object(mod, "collect_kwin_support_info", return_value={"rc": 0, "lines": 1}):
                with patch.object(mod, "collect_plasma_layout", return_value={"rc": 0, "lines": 1}):
                    with patch.object(mod, "collect_coredumpctl", return_value={"rc": 0, "lines": 1}):
                        with patch.object(mod, "collect_qemu_screendump", return_value={"rc": 0}):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    manifest = json.loads(Path(bundle_dir, "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenario"] == "Manifest test"
    assert manifest["feature"] == "KDE Feature"
    assert manifest["status"] == "failed"
    assert manifest["collectors"]["collect_journalctl"]["lines"] == 42
    assert manifest["collectors"]["collect_journalctl"]["rc"] == 0
    assert len(manifest["errors"]) == 1
    assert manifest["errors"][0]["collector"] == "collect_at_spi_tree"
    journal.assert_called_once()


def test_tarball_created_next_to_bundle(tmp_path):
    mod = _import_faillog()
    context = _make_context(tmp_path)
    scenario = _make_scenario(status="failed")

    with patch.object(mod, "collect_at_spi_tree", return_value={"rc": 0}):
        with patch.object(mod, "collect_journalctl", return_value={"rc": 0}):
            with patch.object(mod, "collect_kwin_support_info", return_value={"rc": 0}):
                with patch.object(mod, "collect_plasma_layout", return_value={"rc": 0}):
                    with patch.object(mod, "collect_coredumpctl", return_value={"rc": 0}):
                        with patch.object(mod, "collect_qemu_screendump", return_value={"rc": 0}):
                            bundle_dir = mod.collect_on_failure(context, scenario)

    tar_path = bundle_dir + ".tar.gz"
    assert os.path.exists(tar_path)
    import tarfile

    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
    assert any("manifest.json" in name for name in names)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def test_safe_fragment_normalizes_strings():
    mod = _import_faillog()
    assert mod._safe_fragment("Hello World!!!", "fallback") == "hello_world"
    assert mod._safe_fragment("", "fallback") == "fallback"
    assert mod._safe_fragment("a" * 100, "fallback") == "a" * 60


def test_results_dir_prefers_userdata_then_env_then_default(tmp_path, monkeypatch):
    mod = _import_faillog()
    context = SimpleNamespace(config=SimpleNamespace(userdata={"results_dir": str(tmp_path / "user")}))
    assert mod._results_dir(context) == str(tmp_path / "user")

    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path / "env"))
    assert mod._results_dir(SimpleNamespace(config=SimpleNamespace(userdata={}))) == str(tmp_path / "env")
    assert mod._results_dir(None) == str(tmp_path / "env")

    monkeypatch.delenv("TESTSUITE_RESULTS_DIR")
    assert mod._results_dir(None) == "/tmp/results"


def test_ssh_collector_catches_timeout_exception():
    mod = _import_faillog()
    with patch.object(mod, "run_ssh", side_effect=subprocess.TimeoutExpired("ssh", 10)):
        stdout, rc = mod._run_ssh_collector(None, "cmd", 10)
    assert stdout == ""
    assert rc == -1


def test_ssh_collector_catches_unexpected_exception():
    mod = _import_faillog()
    with patch.object(mod, "run_ssh", side_effect=ValueError("unexpected")):
        stdout, rc = mod._run_ssh_collector(None, "cmd", 10)
    assert stdout == ""
    assert rc == -2


# ---------------------------------------------------------------------------
# Bounding and collision regressions (code review of PR #644)
# ---------------------------------------------------------------------------

def test_write_text_enforces_absolute_byte_cap(tmp_path):
    mod = _import_faillog()
    bundle_dir = str(tmp_path / "b")
    os.makedirs(bundle_dir)
    huge = "x" * (mod.MAX_ARTIFACT_BYTES + 10_000)

    mod._write_text(bundle_dir, "huge.txt", huge)

    written = Path(bundle_dir, "huge.txt").read_text(encoding="utf-8")
    assert len(written.encode()) <= mod.MAX_ARTIFACT_BYTES + 200
    assert "truncated" in written


@pytest.mark.parametrize("raw", ["-1", "0", "not-a-number", None, "999999999"])
def test_clamp_lines_rejects_unsafe_configuration(raw):
    """A negative, zero, junk or absurd env value must not disable bounding."""
    mod = _import_faillog()
    value = mod._clamp_lines(raw, 2000)
    assert 0 < value <= mod.MAX_CONFIGURABLE_LINES


def test_bundle_dirs_do_not_collide_within_one_second():
    mod = _import_faillog()
    scenario = SimpleNamespace(
        name="same scenario", status=SimpleNamespace(name="failed"),
        feature=SimpleNamespace(name="f"),
    )
    first = mod._bundle_dir("/tmp/results", scenario)
    second = mod._bundle_dir("/tmp/results", scenario)
    assert first != second
