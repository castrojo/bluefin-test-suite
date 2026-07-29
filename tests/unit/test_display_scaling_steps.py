"""Unit tests for smoke display-scaling command and assertion helpers."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.smoke.features.steps import display_scaling_steps


def test_remote_session_commands_source_session_environment():
    with patch.object(display_scaling_steps, "_IN_CONTAINER", True):
        command = display_scaling_steps._with_session_env("gsettings get foo bar")

    assert command == "source /tmp/session.env 2>/dev/null; gsettings get foo bar"


def test_gsettings_get_sources_remote_session_environment():
    with (
        patch.object(display_scaling_steps, "_IN_CONTAINER", True),
        patch.object(
            display_scaling_steps,
            "_run_host",
            return_value=("@as ['scale-monitor-framebuffer']", 0, ""),
        ) as run_host,
    ):
        features, raw = display_scaling_steps._gsettings_get_features()

    assert features == ["scale-monitor-framebuffer"]
    assert raw == "@as ['scale-monitor-framebuffer']"
    run_host.assert_called_once_with(
        "source /tmp/session.env 2>/dev/null; "
        "gsettings get org.gnome.mutter experimental-features"
    )


def test_gsettings_set_sources_remote_session_environment():
    with (
        patch.object(display_scaling_steps, "_IN_CONTAINER", True),
        patch.object(
            display_scaling_steps, "_run_host", return_value=("", 0, "")
        ) as run_host,
    ):
        display_scaling_steps._gsettings_set_features("['feature']")

    run_host.assert_called_once_with(
        "source /tmp/session.env 2>/dev/null; "
        "gsettings set org.gnome.mutter experimental-features "
        "'['\"'\"'feature'\"'\"']'"
    )


def test_scale_assertion_checks_every_logical_monitor():
    context = SimpleNamespace(display_scale_target=1.5)
    with patch.object(
        display_scaling_steps, "_get_display_scales", return_value=[1.5, 1.5]
    ):
        display_scaling_steps.current_display_scale_matches_applied(context)


def test_scale_assertion_reports_mismatched_monitor():
    context = SimpleNamespace(display_scale_target=1.5)
    with patch.object(
        display_scaling_steps, "_get_display_scales", return_value=[1.5, 1.25]
    ):
        with pytest.raises(AssertionError, match="Expected scale 1.5"):
            display_scaling_steps.current_display_scale_matches_applied(context)
