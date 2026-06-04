"""Unit tests for tests/shared/screenshot_cli.py.

Tests the main() function logic — argument validation, per-app dispatch,
and exit-code accounting — using mocks for the GNOME screenshot helpers.
No live display or filesystem access required.
"""

from unittest.mock import patch

from tests.shared import screenshot_cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_take_screenshot(results: dict[str, str | None]):
    """Return a fake take_app_screenshot that maps app_id → path (or None)."""
    def _fake(app_id, *, context=None):
        return results.get(app_id)
    return _fake


# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------

def test_main_returns_1_with_no_args(capsys):
    rc = screenshot_cli.main([])

    assert rc == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.err


def test_main_returns_0_when_all_succeed(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    monkeypatch.setenv("SUITE", "gallery")
    take = _make_take_screenshot({
        "org.gnome.Calculator": "/tmp/results/screenshot_gallery_gnome_calculator_flatpak_gallery.png",
        "org.gnome.Clocks": "/tmp/results/screenshot_gallery_gnome_clocks_flatpak_gallery.png",
    })
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        rc = screenshot_cli.main(["org.gnome.Calculator", "org.gnome.Clocks"])

    assert rc == 0


def test_main_returns_1_when_all_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    take = _make_take_screenshot({})  # nothing matched → all return None
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        rc = screenshot_cli.main(["org.gnome.Calculator"])

    assert rc == 1


def test_main_returns_1_when_any_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    take = _make_take_screenshot({
        "org.gnome.Calculator": "/tmp/ok.png",
        "io.failing.App": None,
    })
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        rc = screenshot_cli.main(["org.gnome.Calculator", "io.failing.App"])

    assert rc == 1


def test_main_calls_take_screenshot_for_each_app(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    captured_ids = []

    def _record(app_id, *, context=None):
        captured_ids.append(app_id)
        return "/tmp/dummy.png"

    with patch.object(screenshot_cli, "take_app_screenshot", _record):
        screenshot_cli.main(["app.one", "app.two", "app.three"])

    assert captured_ids == ["app.one", "app.two", "app.three"]


def test_main_prints_ok_for_successful_screenshot(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    take = _make_take_screenshot({"org.gnome.Calculator": "/tmp/calc.png"})
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        screenshot_cli.main(["org.gnome.Calculator"])

    out = capsys.readouterr().out
    assert "OK" in out
    assert "org.gnome.Calculator" in out


def test_main_prints_fail_for_missing_screenshot(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    take = _make_take_screenshot({"org.gnome.Calculator": None})
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        screenshot_cli.main(["org.gnome.Calculator"])

    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "org.gnome.Calculator" in out


def test_main_summary_line_shows_counts(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    take = _make_take_screenshot({
        "org.gnome.Calculator": "/tmp/ok.png",
        "io.failing.App": None,
    })
    with patch.object(screenshot_cli, "take_app_screenshot", take):
        screenshot_cli.main(["org.gnome.Calculator", "io.failing.App"])

    out = capsys.readouterr().out
    assert "1 captured" in out
    assert "1 failed" in out


def test_main_uses_suite_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    monkeypatch.setenv("SUITE", "mysuite")
    configured = {}

    original_configure = screenshot_cli.configure_screenshot_context

    def _capture_configure(ctx, suite, label):
        configured["suite"] = suite
        return original_configure(ctx, suite, label)

    with patch.object(screenshot_cli, "configure_screenshot_context", _capture_configure):
        with patch.object(screenshot_cli, "take_app_screenshot", lambda *a, **kw: "/tmp/x.png"):
            screenshot_cli.main(["any.App"])

    assert configured.get("suite") == "mysuite"
