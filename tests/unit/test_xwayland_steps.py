"""Unit tests for tests/smoke/features/steps/xwayland_steps.py.

The module drives a real XWayland server and an X11 client inside the VM, so
these tests stub ``behave``, ``qecore`` and ``app_support`` and cover only pure
logic: the container-vs-local dispatch in ``_run_host``, session-env prefixing,
``pgrep -a`` output parsing in ``_xwayland_display_env``, and the polling and
skip branches of the steps.
"""
import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_xwayland_steps():
    """Import xwayland_steps.py with behave, qecore and app_support stubbed."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    app_support_stub = types.ModuleType("app_support")
    app_support_stub._ssh_args = MagicMock(return_value=["ssh", "vm"])
    app_support_stub.launch_background = MagicMock(return_value="command")
    app_support_stub.launch_target_available = MagicMock(return_value=True)
    sys.modules["app_support"] = app_support_stub

    for key in list(sys.modules):
        if "xwayland_steps" in key:
            del sys.modules[key]

    import tests.smoke.features.steps.xwayland_steps as m  # noqa: PLC0415
    return m


@pytest.fixture
def xw():
    return _import_xwayland_steps()


def _completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(
        args="cmd", returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestRunHost:
    def test_forwards_over_ssh_when_in_container(self, xw):
        with (
            patch.object(xw, "_IN_CONTAINER", True),
            patch.object(xw, "_ssh_args", return_value=["ssh", "vm"]),
            patch.object(
                xw.subprocess, "run", return_value=_completed(" out \n", 0, " err ")
            ) as run,
        ):
            assert xw._run_host("pgrep -x Xwayland", timeout=9) == ("out", 0, "err")

        assert run.call_args[0][0] == ["ssh", "vm", "pgrep -x Xwayland"]
        assert run.call_args.kwargs["timeout"] == 9
        assert "shell" not in run.call_args.kwargs

    def test_runs_through_shell_when_not_in_container(self, xw):
        with (
            patch.object(xw, "_IN_CONTAINER", False),
            patch.object(xw.subprocess, "run", return_value=_completed()) as run,
        ):
            xw._run_host("xprop -root")

        assert run.call_args[0][0] == "xprop -root"
        assert run.call_args.kwargs["shell"] is True
        assert run.call_args.kwargs["env"] is xw.os.environ

    def test_strips_whitespace_from_stdout_and_stderr(self, xw):
        with (
            patch.object(xw, "_IN_CONTAINER", False),
            patch.object(
                xw.subprocess, "run", return_value=_completed("\na\n", 3, "\nb\n")
            ),
        ):
            assert xw._run_host("cmd") == ("a", 3, "b")


class TestRunHostSession:
    def test_prefixes_command_with_session_env(self, xw):
        with patch.object(xw, "_run_host", return_value=("", 0, "")) as run_host:
            xw._run_host_session("xprop -root", timeout=12)

        run_host.assert_called_once_with(
            "source /tmp/session.env 2>/dev/null; xprop -root", timeout=12
        )


class TestXwaylandDisplayEnv:
    def test_extracts_display_and_auth_file(self, xw):
        line = "1234 /usr/bin/Xwayland :1 -rootless -auth /run/user/1000/.mutter-Xwaylandauth.ABC"
        with patch.object(xw, "_run_host", return_value=(line, 0, "")):
            assert xw._xwayland_display_env() == {
                "DISPLAY": ":1",
                "XAUTHORITY": "/run/user/1000/.mutter-Xwaylandauth.ABC",
            }

    def test_defaults_to_display_zero_when_no_display_argument(self, xw):
        with patch.object(xw, "_run_host", return_value=("1234 /usr/bin/Xwayland", 0, "")):
            assert xw._xwayland_display_env() == {"DISPLAY": ":0"}

    def test_omits_xauthority_when_auth_flag_absent(self, xw):
        with patch.object(
            xw, "_run_host", return_value=("1234 /usr/bin/Xwayland :0", 0, "")
        ):
            assert "XAUTHORITY" not in xw._xwayland_display_env()

    def test_ignores_dangling_auth_flag_with_no_value(self, xw):
        with patch.object(
            xw, "_run_host", return_value=("1234 /usr/bin/Xwayland :0 -auth", 0, "")
        ):
            assert xw._xwayland_display_env() == {"DISPLAY": ":0"}

    def test_uses_first_process_line_only(self, xw):
        stdout = "1 /usr/bin/Xwayland :2\n2 /usr/bin/Xwayland :3"
        with patch.object(xw, "_run_host", return_value=(stdout, 0, "")):
            assert xw._xwayland_display_env()["DISPLAY"] == ":2"

    def test_non_numeric_colon_token_is_not_treated_as_display(self, xw):
        stdout = "1 /usr/bin/Xwayland :abc :4"
        with patch.object(xw, "_run_host", return_value=(stdout, 0, "")):
            assert xw._xwayland_display_env()["DISPLAY"] == ":4"

    def test_fails_when_no_xwayland_process_is_reported(self, xw):
        with patch.object(xw, "_run_host", return_value=("", 0, "")):
            with pytest.raises(AssertionError, match="XWayland is not running"):
                xw._xwayland_display_env()

    def test_fails_when_pgrep_command_itself_fails(self, xw):
        with patch.object(xw, "_run_host", return_value=("1 /usr/bin/Xwayland :0", 1, "")):
            with pytest.raises(AssertionError, match="XWayland is not running"):
                xw._xwayland_display_env()


class TestGlxgearsAvailability:
    def test_does_not_skip_when_launch_target_is_available(self, xw):
        context = MagicMock()
        with patch.object(xw, "launch_target_available", return_value=True):
            xw.x11_client_glxgears_is_available(context)

        context.scenario.skip.assert_not_called()

    def test_skips_scenario_when_glxgears_is_missing(self, xw):
        context = MagicMock()
        with patch.object(xw, "launch_target_available", return_value=False):
            xw.x11_client_glxgears_is_available(context)

        context.scenario.skip.assert_called_once_with(
            "glxgears is not installed on this image"
        )

    def test_swallows_errors_raised_by_scenario_skip(self, xw):
        context = MagicMock()
        context.scenario.skip.side_effect = RuntimeError("cannot skip here")
        with patch.object(xw, "launch_target_available", return_value=False):
            xw.x11_client_glxgears_is_available(context)


class TestLaunchGlxgears:
    def test_records_the_launch_target_on_context(self, xw):
        context = MagicMock()
        with patch.object(
            xw, "launch_background", return_value="command"
        ) as launch_background:
            xw.launch_glxgears_via_command(context)

        assert context.glxgears_launch_target == "command"
        launch_background.assert_called_once_with(xw.GLXGEARS_LAUNCH_TARGETS)


class TestXwaylandProcessAppears:
    def test_returns_as_soon_as_the_binary_path_is_seen(self, xw):
        with (
            patch.object(
                xw, "_run_host", return_value=("1234 /usr/bin/Xwayland :0", 0, "")
            ) as run_host,
            patch.object(xw.time, "sleep") as sleep,
        ):
            xw.xwayland_process_appears_within_seconds(MagicMock(), 10)

        assert run_host.call_count == 1
        sleep.assert_not_called()

    def test_keeps_polling_until_the_process_appears(self, xw):
        with (
            patch.object(
                xw,
                "_run_host",
                side_effect=[("", 0, ""), ("1234 /usr/bin/Xwayland :0", 0, "")],
            ) as run_host,
            patch.object(xw.time, "sleep"),
        ):
            xw.xwayland_process_appears_within_seconds(MagicMock(), 10)

        assert run_host.call_count == 2

    def test_raises_after_the_deadline(self, xw):
        with (
            patch.object(xw, "_run_host", return_value=("", 0, "")),
            patch.object(xw.time, "sleep"),
            patch.object(xw.time, "time", side_effect=[0, 1, 99]),
        ):
            with pytest.raises(
                AssertionError, match=r"did not appear within 5s"
            ):
                xw.xwayland_process_appears_within_seconds(MagicMock(), 5)


class TestXpropQueriesRootWindow:
    def test_exports_display_and_xauthority_before_running_xprop(self, xw):
        with (
            patch.object(
                xw,
                "_xwayland_display_env",
                return_value={"DISPLAY": ":0", "XAUTHORITY": "/run/auth"},
            ),
            patch.object(
                xw, "_run_host_session", return_value=("0", 0, "")
            ) as run_session,
        ):
            xw.xprop_can_query_x_root_window(MagicMock())

        command = run_session.call_args[0][0]
        assert command.startswith('export DISPLAY=":0"; export XAUTHORITY="/run/auth";')
        assert command.endswith("xprop -root >/dev/null 2>&1; echo $?")

    def test_fails_when_xprop_reports_a_nonzero_exit_code(self, xw):
        with (
            patch.object(xw, "_xwayland_display_env", return_value={"DISPLAY": ":0"}),
            patch.object(xw, "_run_host_session", return_value=("1", 0, "no display")),
        ):
            with pytest.raises(AssertionError, match=r"xprop -root failed"):
                xw.xprop_can_query_x_root_window(MagicMock())

    def test_fails_when_the_wrapper_command_itself_fails(self, xw):
        with (
            patch.object(xw, "_xwayland_display_env", return_value={"DISPLAY": ":0"}),
            patch.object(xw, "_run_host_session", return_value=("0", 255, "ssh error")),
        ):
            with pytest.raises(AssertionError, match="ssh error"):
                xw.xprop_can_query_x_root_window(MagicMock())


class TestTerminateAndWait:
    def test_terminate_glxgears_kills_and_settles(self, xw):
        with (
            patch.object(xw, "_run_host", return_value=("", 0, "")) as run_host,
            patch.object(xw.time, "sleep") as sleep,
        ):
            xw.terminate_glxgears(MagicMock())

        run_host.assert_called_once_with("pkill -x glxgears 2>/dev/null || true")
        sleep.assert_called_once_with(0.5)

    def test_terminate_any_running_glxgears_does_not_settle(self, xw):
        with (
            patch.object(xw, "_run_host", return_value=("", 0, "")) as run_host,
            patch.object(xw.time, "sleep") as sleep,
        ):
            xw.terminate_any_running_glxgears(MagicMock())

        run_host.assert_called_once_with("pkill -x glxgears 2>/dev/null || true")
        sleep.assert_not_called()

    def test_wait_seconds_sleeps_for_the_requested_duration(self, xw):
        with patch.object(xw.time, "sleep") as sleep:
            xw.wait_seconds(MagicMock(), 3)

        sleep.assert_called_once_with(3)
