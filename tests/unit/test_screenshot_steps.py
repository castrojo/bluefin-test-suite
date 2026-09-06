"""Unit tests for tests/shared/screenshot_steps.py.

screenshot_steps.py registers two behave @step handlers that wrap
take_screenshot / take_app_screenshot and assert the returned path is
not None.  These tests verify both the happy path and the assertion
failure path without requiring a live display or VM.
"""

from unittest.mock import MagicMock, patch

import pytest

import tests.shared.screenshot_steps as _mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# step_take_screenshot_labeled
# ---------------------------------------------------------------------------

def test_take_screenshot_labeled_success():
    """Step succeeds when take_screenshot returns a path."""
    with patch.object(_mod, "take_screenshot", return_value="/tmp/shot.png"):
        _mod.step_take_screenshot_labeled(_ctx(), "my-label")


def test_take_screenshot_labeled_passes_label():
    """Step forwards the label argument to take_screenshot."""
    with patch.object(_mod, "take_screenshot", return_value="/tmp/shot.png") as mock_ts:
        _mod.step_take_screenshot_labeled(_ctx(), "smoke")
        mock_ts.assert_called_once_with("smoke")


def test_take_screenshot_labeled_raises_on_none():
    """Step raises AssertionError when take_screenshot returns None."""
    with patch.object(_mod, "take_screenshot", return_value=None):
        with pytest.raises(AssertionError, match="Screenshot failed for label 'fail-label'"):
            _mod.step_take_screenshot_labeled(_ctx(), "fail-label")


# ---------------------------------------------------------------------------
# step_launch_and_screenshot
# ---------------------------------------------------------------------------

def test_launch_and_screenshot_success():
    """Step succeeds when take_app_screenshot returns a path."""
    with patch.object(_mod, "take_app_screenshot", return_value="/tmp/app.png"):
        _mod.step_launch_and_screenshot(_ctx(), "org.gnome.Calculator")


def test_launch_and_screenshot_passes_app_id():
    """Step forwards the app_id argument to take_app_screenshot."""
    with patch.object(_mod, "take_app_screenshot", return_value="/tmp/app.png") as mock_tas:
        _mod.step_launch_and_screenshot(_ctx(), "org.gnome.Clocks")
        mock_tas.assert_called_once_with("org.gnome.Clocks")


def test_launch_and_screenshot_raises_on_none():
    """Step raises AssertionError when take_app_screenshot returns None."""
    with patch.object(_mod, "take_app_screenshot", return_value=None):
        with pytest.raises(AssertionError, match="Screenshot failed for app 'org.gnome.BadApp'"):
            _mod.step_launch_and_screenshot(_ctx(), "org.gnome.BadApp")
