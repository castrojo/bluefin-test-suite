"""Unit tests for shared screenshot helpers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.shared import screenshot


def test_safe_fragment_replaces_spaces_and_special_chars():
    fragment = screenshot._safe_fragment("Hello World!!!", "fallback")

    assert fragment == "hello_world"
    assert " " not in fragment
    assert fragment.replace("_", "").isalnum()


def test_safe_fragment_uses_fallback_for_empty_value():
    assert screenshot._safe_fragment("", "fallback") == "fallback"


def test_screenshot_path_uses_png_suffix_and_label(tmp_path, monkeypatch):
    monkeypatch.setenv("TESTSUITE_RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(screenshot, "_CURRENT_CONTEXT", None)
    monkeypatch.setattr(screenshot, "_CURRENT_SUITE", "Software")
    monkeypatch.setattr(screenshot, "_CURRENT_SCENARIO", "Launch App")

    path = Path(screenshot._screenshot_path("Capture Label"))

    assert path.parent == tmp_path
    assert path.suffix == ".png"
    assert "capture_label" in path.name


@pytest.mark.parametrize(("returncode", "expected"), [(0, True), (1, False)])
def test_flatpak_installed_uses_subprocess_return_code(returncode, expected):
    with patch(
        "tests.shared.screenshot.subprocess.run",
        return_value=SimpleNamespace(returncode=returncode),
    ) as run_mock:
        assert screenshot._flatpak_installed("org.gnome.Foo") is expected

    run_mock.assert_called_once_with(
        ["flatpak", "info", "org.gnome.Foo"],
        stdout=screenshot.subprocess.DEVNULL,
        stderr=screenshot.subprocess.DEVNULL,
        check=False,
    )


# ── screenshot_steps.py ───────────────────────────────────────────────────────


from tests.shared import screenshot_steps  # noqa: E402


class _FakeContext:
    pass


def test_step_take_screenshot_labeled_passes_when_path_returned():
    """Step succeeds when take_screenshot returns a non-None path."""
    with patch(
        "tests.shared.screenshot_steps.take_screenshot",
        return_value="/tmp/results/foo.png",
    ):
        # Should not raise
        screenshot_steps.step_take_screenshot_labeled(_FakeContext(), "my-label")


def test_step_take_screenshot_labeled_asserts_on_none():
    """Step raises AssertionError when take_screenshot returns None."""
    with patch(
        "tests.shared.screenshot_steps.take_screenshot",
        return_value=None,
    ):
        with pytest.raises(AssertionError, match="Screenshot failed"):
            screenshot_steps.step_take_screenshot_labeled(_FakeContext(), "my-label")


def test_step_launch_and_screenshot_passes_when_path_returned():
    """Step succeeds when take_app_screenshot returns a non-None path."""
    with patch(
        "tests.shared.screenshot_steps.take_app_screenshot",
        return_value="/tmp/results/app.png",
    ):
        screenshot_steps.step_launch_and_screenshot(_FakeContext(), "org.gnome.Foo")


def test_step_launch_and_screenshot_asserts_on_none():
    """Step raises AssertionError when take_app_screenshot returns None."""
    with patch(
        "tests.shared.screenshot_steps.take_app_screenshot",
        return_value=None,
    ):
        with pytest.raises(AssertionError, match="Screenshot failed"):
            screenshot_steps.step_launch_and_screenshot(_FakeContext(), "org.gnome.Foo")
