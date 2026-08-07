"""Unit tests for tests/smoke/features/steps/orca_steps.py.

The module runs inside a booted VM and shells out via ``_run_host``. These
tests stub ``behave`` and the ``steps.steps`` helper module, then exercise only
pure logic: context bookkeeping, assertion messages, gsettings command
construction, process-state polling, and the toggle step's restore semantics.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_orca_steps():
    """Import orca_steps.py with behave and steps.steps stubbed out."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    # orca_steps does `from steps.steps import _run_host`; the smoke steps
    # directory is only on sys.path inside a behave run, so provide a package
    # stub with a __path__ so the submodule import resolves.
    steps_pkg_stub = types.ModuleType("steps")
    steps_pkg_stub.__path__ = []
    steps_mod_stub = types.ModuleType("steps.steps")
    steps_mod_stub._run_host = lambda cmd, timeout=30: ("", 0, "")
    steps_pkg_stub.steps = steps_mod_stub
    sys.modules["steps"] = steps_pkg_stub
    sys.modules["steps.steps"] = steps_mod_stub

    for key in list(sys.modules):
        if "orca_steps" in key:
            del sys.modules[key]

    import tests.smoke.features.steps.orca_steps as m  # noqa: PLC0415
    return m


@pytest.fixture
def orca():
    return _import_orca_steps()


def _ctx(**attrs):
    ctx = MagicMock()
    for key, value in attrs.items():
        setattr(ctx, key, value)
    return ctx


class TestRunCommandOnVm:
    def test_stores_stdout_rc_and_stderr_on_context(self, orca):
        context = _ctx()
        with patch.object(
            orca, "_run_host", return_value=("out", 3, "err")
        ) as run_host:
            orca.step_run_command_on_vm(context, "echo hi")

        assert context.vm_command_stdout == "out"
        assert context.vm_command_rc == 3
        assert context.vm_command_stderr == "err"
        run_host.assert_called_once_with("echo hi", timeout=30)


class TestVmCommandReturnCode:
    def test_passes_when_return_code_matches(self, orca):
        context = _ctx(vm_command_rc=0, vm_command_stderr="")
        orca.step_vm_command_return_code(context, "0")

    def test_compares_expected_as_integer(self, orca):
        context = _ctx(vm_command_rc=127, vm_command_stderr="")
        orca.step_vm_command_return_code(context, "127")

    def test_fails_when_return_code_differs(self, orca):
        context = _ctx(vm_command_rc=1, vm_command_stderr="boom")
        with pytest.raises(AssertionError, match="return code was 1, expected 0"):
            orca.step_vm_command_return_code(context, "0")

    def test_failure_message_includes_stderr(self, orca):
        context = _ctx(vm_command_rc=1, vm_command_stderr="boom")
        with pytest.raises(AssertionError, match="boom"):
            orca.step_vm_command_return_code(context, "0")

    def test_fails_when_no_command_has_run(self, orca):
        context = MagicMock(spec=[])
        with pytest.raises(AssertionError, match="No VM command has been run"):
            orca.step_vm_command_return_code(context, "0")


class TestVmCommandOutputContains:
    def test_passes_on_substring_match(self, orca):
        orca.step_vm_command_output_contains(_ctx(vm_command_stdout="orca 47.0"), "orca")

    def test_fails_when_substring_absent(self, orca):
        context = _ctx(vm_command_stdout="nothing here")
        with pytest.raises(AssertionError, match="did not contain 'orca'"):
            orca.step_vm_command_output_contains(context, "orca")

    def test_missing_attribute_is_treated_as_empty_output(self, orca):
        context = MagicMock(spec=[])
        with pytest.raises(AssertionError):
            orca.step_vm_command_output_contains(context, "orca")


class TestSetScreenReader:
    def test_enable_sets_key_true(self, orca):
        with patch.object(orca, "_run_host", return_value=("", 0, "")) as run_host:
            orca._set_screen_reader(True)

        run_host.assert_called_once_with(
            "gsettings set org.gnome.desktop.a11y.applications "
            "screen-reader-enabled true",
            timeout=10,
        )

    def test_disable_sets_key_false(self, orca):
        with patch.object(orca, "_run_host", return_value=("", 0, "")) as run_host:
            orca._set_screen_reader(False)

        assert run_host.call_args[0][0].endswith("screen-reader-enabled false")


class TestOrcaIsRunning:
    def test_true_when_pgrep_succeeds_with_output(self, orca):
        with patch.object(orca, "_run_host", return_value=("1234\n", 0, "")):
            assert orca._orca_is_running() is True

    def test_false_when_pgrep_returns_nonzero(self, orca):
        with patch.object(orca, "_run_host", return_value=("", 1, "")):
            assert orca._orca_is_running() is False

    def test_false_when_pgrep_succeeds_with_blank_output(self, orca):
        with patch.object(orca, "_run_host", return_value=("   \n", 0, "")):
            assert orca._orca_is_running() is False


class TestWaitForOrca:
    def test_returns_immediately_when_state_already_matches(self, orca):
        with (
            patch.object(orca, "_orca_is_running", return_value=True) as is_running,
            patch.object(orca.time, "sleep") as sleep,
        ):
            orca._wait_for_orca(running=True)

        assert is_running.call_count == 1
        sleep.assert_not_called()

    def test_polls_until_state_matches(self, orca):
        with (
            patch.object(
                orca, "_orca_is_running", side_effect=[False, False, True]
            ) as is_running,
            patch.object(orca.time, "sleep"),
        ):
            orca._wait_for_orca(running=True)

        assert is_running.call_count == 3

    def test_timeout_message_says_start_when_waiting_for_running(self, orca):
        with (
            patch.object(orca, "_orca_is_running", return_value=False),
            patch.object(orca.time, "sleep"),
            patch.object(orca.time, "monotonic", side_effect=[0, 1, 99]),
        ):
            with pytest.raises(AssertionError, match="Orca did not start within 15"):
                orca._wait_for_orca(running=True)

    def test_timeout_message_says_stop_when_waiting_for_stopped(self, orca):
        with (
            patch.object(orca, "_orca_is_running", return_value=True),
            patch.object(orca.time, "sleep"),
            patch.object(orca.time, "monotonic", side_effect=[0, 1, 99]),
        ):
            with pytest.raises(AssertionError, match="Orca did not stop within 5"):
                orca._wait_for_orca(running=False, timeout=5)


class TestScreenReaderTogglesOrca:
    def test_happy_path_toggles_off_on_then_off_again(self, orca):
        with (
            patch.object(orca, "_set_screen_reader") as set_reader,
            patch.object(orca, "_wait_for_orca") as wait,
        ):
            orca.step_screen_reader_toggles_orca(_ctx())

        assert [call.args[0] for call in set_reader.call_args_list] == [
            False,
            True,
            False,
        ]
        assert [call.kwargs["running"] for call in wait.call_args_list] == [
            False,
            True,
            False,
        ]

    def test_start_failure_still_restores_screen_reader_to_false(self, orca):
        with (
            patch.object(orca, "_set_screen_reader") as set_reader,
            patch.object(
                orca,
                "_wait_for_orca",
                side_effect=[None, AssertionError("no start"), None],
            ),
        ):
            with pytest.raises(AssertionError, match="no start"):
                orca.step_screen_reader_toggles_orca(_ctx())

        assert set_reader.call_args_list[-1].args[0] is False

    def test_start_failure_is_reported_in_preference_to_stop_failure(self, orca):
        with (
            patch.object(orca, "_set_screen_reader"),
            patch.object(
                orca,
                "_wait_for_orca",
                side_effect=[
                    None,
                    AssertionError("no start"),
                    AssertionError("no stop"),
                ],
            ),
        ):
            with pytest.raises(AssertionError, match="no start"):
                orca.step_screen_reader_toggles_orca(_ctx())

    def test_stop_failure_is_wrapped_with_context(self, orca):
        with (
            patch.object(orca, "_set_screen_reader"),
            patch.object(
                orca,
                "_wait_for_orca",
                side_effect=[None, None, AssertionError("still there")],
            ),
        ):
            with pytest.raises(
                AssertionError,
                match="Orca did not stop after disabling screen reader: still there",
            ):
                orca.step_screen_reader_toggles_orca(_ctx())

    def test_non_assertion_errors_are_not_swallowed(self, orca):
        with (
            patch.object(orca, "_set_screen_reader"),
            patch.object(orca, "_wait_for_orca", side_effect=RuntimeError("boom")),
        ):
            with pytest.raises(RuntimeError, match="boom"):
                orca.step_screen_reader_toggles_orca(_ctx())
