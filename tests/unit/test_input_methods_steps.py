"""Unit tests for tests/smoke/features/steps/input_methods_steps.py.

The module shells out to ``gsettings``/``busctl``/``localectl`` inside the VM
session, so these tests stub ``behave`` and ``app_support`` and cover only pure
logic: command construction and the container-vs-local dispatch in
``_run_in_vm``, the idempotent restore helper, and each step's assertion
branches.
"""
import shlex
import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_input_methods_steps():
    """Import input_methods_steps.py with behave and app_support stubbed out."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    app_support_stub = types.ModuleType("app_support")
    app_support_stub._IN_CONTAINER = False
    app_support_stub._ssh_run = MagicMock()
    sys.modules["app_support"] = app_support_stub

    for key in list(sys.modules):
        if "input_methods_steps" in key:
            del sys.modules[key]

    import tests.smoke.features.steps.input_methods_steps as m  # noqa: PLC0415
    return m


@pytest.fixture
def ims():
    return _import_input_methods_steps()


def _completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args="cmd", returncode=returncode, stdout=stdout, stderr="")


class TestRunInVm:
    def test_forwards_over_ssh_when_in_container(self, ims):
        with (
            patch.object(ims, "_IN_CONTAINER", True),
            patch.object(ims, "_ssh_run", return_value=_completed()) as ssh_run,
        ):
            ims._run_in_vm("gsettings get a b", timeout=7)

        ssh_run.assert_called_once_with(
            "source /tmp/session.env 2>/dev/null; gsettings get a b", timeout=7
        )

    def test_runs_locally_when_not_in_container(self, ims):
        with (
            patch.object(ims, "_IN_CONTAINER", False),
            patch.object(ims.subprocess, "run", return_value=_completed()) as run,
        ):
            ims._run_in_vm("localectl status")

        run.assert_called_once_with(
            "source /tmp/session.env 2>/dev/null; localectl status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_always_sources_the_session_environment(self, ims):
        with (
            patch.object(ims, "_IN_CONTAINER", True),
            patch.object(ims, "_ssh_run", return_value=_completed()) as ssh_run,
        ):
            ims._run_in_vm("pgrep -x ibus-daemon")

        assert ssh_run.call_args[0][0].startswith("source /tmp/session.env 2>/dev/null; ")


class TestRunInVmChecked:
    def test_strips_stdout_and_returns_return_code(self, ims):
        with patch.object(ims, "_run_in_vm", return_value=_completed("  value \n", 0)):
            assert ims._run_in_vm_checked("cmd") == ("value", 0)

    def test_propagates_nonzero_return_code(self, ims):
        with patch.object(ims, "_run_in_vm", return_value=_completed("", 2)):
            assert ims._run_in_vm_checked("cmd") == ("", 2)

    def test_passes_timeout_through(self, ims):
        with patch.object(ims, "_run_in_vm", return_value=_completed()) as run_in_vm:
            ims._run_in_vm_checked("cmd", timeout=5)

        run_in_vm.assert_called_once_with("cmd", timeout=5)


class TestRestoreInputSources:
    def test_no_op_when_nothing_was_saved(self, ims):
        context = MagicMock(spec=[])
        with patch.object(ims, "_run_in_vm_checked") as run_in_vm:
            ims._restore_input_sources(context)

        run_in_vm.assert_not_called()

    def test_no_op_when_already_restored(self, ims):
        context = MagicMock()
        context._input_methods_original_state = {
            "sources": "[('xkb', 'us')]",
            "current": "uint32 0",
            "_restored": True,
        }
        with patch.object(ims, "_run_in_vm_checked") as run_in_vm:
            ims._restore_input_sources(context)

        run_in_vm.assert_not_called()

    def test_restores_sources_and_current_with_quoting(self, ims):
        context = MagicMock()
        context._input_methods_original_state = {
            "sources": "[('xkb', 'us')]",
            "current": "uint32 0",
            "_restored": False,
        }
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as run_in_vm:
            ims._restore_input_sources(context)

        commands = [call.args[0] for call in run_in_vm.call_args_list]
        assert commands == [
            "gsettings set org.gnome.desktop.input-sources sources "
            + shlex.quote("[('xkb', 'us')]"),
            "gsettings set org.gnome.desktop.input-sources current "
            + shlex.quote("uint32 0"),
        ]
        # The saved gsettings value contains single quotes, so shell-quoting is
        # required for the restore command to round-trip it correctly.
        assert commands[0].endswith("'[('\"'\"'xkb'\"'\"', '\"'\"'us'\"'\"')]'")

    def test_marks_state_restored_so_it_runs_once(self, ims):
        context = MagicMock()
        state = {"sources": "s", "current": "c", "_restored": False}
        context._input_methods_original_state = state
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as run_in_vm:
            ims._restore_input_sources(context)
            ims._restore_input_sources(context)

        assert state["_restored"] is True
        assert run_in_vm.call_count == 2

    def test_skips_empty_captured_values(self, ims):
        context = MagicMock()
        context._input_methods_original_state = {
            "sources": "",
            "current": "uint32 1",
            "_restored": False,
        }
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as run_in_vm:
            ims._restore_input_sources(context)

        assert run_in_vm.call_count == 1
        assert "current" in run_in_vm.call_args[0][0]

    def test_failed_restore_raises_and_leaves_state_unrestored(self, ims):
        """A failed `gsettings set` must not mark the state restored.

        Otherwise the behave cleanup hook becomes a no-op and the mutated
        input sources leak into every later scenario.
        """
        context = MagicMock()
        state = {"sources": "[('xkb', 'us')]", "current": "uint32 0", "_restored": False}
        context._input_methods_original_state = state
        with patch.object(ims, "_run_in_vm_checked", return_value=("boom", 1)):
            with pytest.raises(AssertionError, match="Failed to restore original input sources"):
                ims._restore_input_sources(context)

        assert state["_restored"] is False

    def test_cleanup_can_retry_after_a_failed_restore(self, ims):
        context = MagicMock()
        state = {"sources": "[('xkb', 'us')]", "current": "uint32 0", "_restored": False}
        context._input_methods_original_state = state
        with patch.object(ims, "_run_in_vm_checked", return_value=("boom", 1)):
            with pytest.raises(AssertionError):
                ims._restore_input_sources(context)

        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as run_in_vm:
            ims._restore_input_sources(context)

        assert run_in_vm.call_count == 2
        assert state["_restored"] is True

    def test_partial_failure_is_reported_and_not_marked_restored(self, ims):
        context = MagicMock()
        state = {"sources": "[('xkb', 'us')]", "current": "uint32 0", "_restored": False}
        context._input_methods_original_state = state
        results = [("", 0), ("nope", 1)]
        with patch.object(ims, "_run_in_vm_checked", side_effect=results):
            with pytest.raises(AssertionError, match="current="):
                ims._restore_input_sources(context)

        assert state["_restored"] is False


class TestPresenceSteps:
    def test_ibus_daemon_present_passes_on_zero_return_code(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("123", 0)):
            ims.ibus_daemon_process_is_present(MagicMock())

    def test_ibus_daemon_missing_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 1)):
            with pytest.raises(AssertionError, match="ibus-daemon is not running"):
                ims.ibus_daemon_process_is_present(MagicMock())

    def test_ibus_bus_name_present_passes(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as checked:
            ims.ibus_owns_session_bus_name(MagicMock())

        assert "org.freedesktop.IBus" in checked.call_args[0][0]

    def test_ibus_bus_name_missing_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 1)):
            with pytest.raises(AssertionError, match="not found on the VM session bus"):
                ims.ibus_owns_session_bus_name(MagicMock())


class TestInputSourceAssertions:
    def test_sources_list_requires_xkb_entry(self, ims):
        with patch.object(
            ims, "_run_in_vm_checked", return_value=("[('xkb', 'us')]", 0)
        ):
            ims.input_sources_list_contains_keyboard_layout(MagicMock())

    def test_sources_list_without_xkb_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("@a(ss) []", 0)):
            with pytest.raises(AssertionError, match="No xkb layout in input sources"):
                ims.input_sources_list_contains_keyboard_layout(MagicMock())

    def test_sources_list_read_failure_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("boom", 1)):
            with pytest.raises(AssertionError, match="Failed to read input sources"):
                ims.input_sources_list_contains_keyboard_layout(MagicMock())

    def test_second_layout_present_passes(self, ims):
        with patch.object(
            ims, "_run_in_vm_checked", return_value=("[('xkb', 'us'), ('xkb', 'de')]", 0)
        ):
            ims.input_sources_list_contains_second_layout(MagicMock())

    def test_second_layout_absent_fails(self, ims):
        with patch.object(
            ims, "_run_in_vm_checked", return_value=("[('xkb', 'us')]", 0)
        ):
            with pytest.raises(AssertionError, match="German layout not in sources"):
                ims.input_sources_list_contains_second_layout(MagicMock())

    def test_current_index_one_passes(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("uint32 1", 0)):
            ims.current_input_source_index_is_1(MagicMock())

    def test_current_index_other_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("uint32 0", 0)):
            with pytest.raises(AssertionError, match="Current input source is not 1"):
                ims.current_input_source_index_is_1(MagicMock())

    @pytest.mark.parametrize("value", ["uint32 10", "uint32 11", "uint32 21", "uint32 100"])
    def test_current_index_rejects_indexes_merely_containing_one(self, ims, value):
        """`uint32 10` must not satisfy an assertion for index 1.

        A substring test for "1" passed for every index whose decimal
        representation happens to contain the digit, so a failed layout switch
        looked like a success.
        """
        with patch.object(ims, "_run_in_vm_checked", return_value=(value, 0)):
            with pytest.raises(AssertionError, match="Current input source is not 1"):
                ims.current_input_source_index_is_1(MagicMock())

    def test_current_index_rejects_unparseable_value(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("nothing here", 0)):
            with pytest.raises(AssertionError, match="Current input source is not 1"):
                ims.current_input_source_index_is_1(MagicMock())

    @pytest.mark.parametrize("value", ["uint32 1", "1", " uint32 1 "])
    def test_parse_index_reads_gvariant_payload(self, ims, value):
        assert ims._parse_index(value) == 1

    @pytest.mark.parametrize("value", ["", "uint32", "uint32 1 2", "abc"])
    def test_parse_index_returns_none_for_garbage(self, ims, value):
        assert ims._parse_index(value) is None


class TestSaveAndMutateSteps:
    def test_save_captures_state_and_registers_cleanup(self, ims):
        context = MagicMock()
        with patch.object(
            ims,
            "_run_in_vm_checked",
            side_effect=[("[('xkb', 'us')]", 0), ("uint32 0", 0)],
        ):
            ims.current_input_sources_are_saved(context)

        assert context._input_methods_original_state == {
            "sources": "[('xkb', 'us')]",
            "current": "uint32 0",
            "_restored": False,
        }
        context.add_cleanup.assert_called_once()

    def test_save_fails_when_sources_cannot_be_read(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("boom", 1)):
            with pytest.raises(AssertionError, match="Failed to read input sources"):
                ims.current_input_sources_are_saved(MagicMock())

    def test_save_fails_when_current_cannot_be_read(self, ims):
        with patch.object(
            ims, "_run_in_vm_checked", side_effect=[("[]", 0), ("boom", 1)]
        ):
            with pytest.raises(AssertionError, match="Failed to read current input source"):
                ims.current_input_sources_are_saved(MagicMock())

    def test_set_second_layout_issues_expected_gsettings_write(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as checked:
            ims.input_sources_set_to_include_second_layout(MagicMock())

        assert checked.call_args[0][0] == (
            "gsettings set org.gnome.desktop.input-sources sources "
            "\"[('xkb', 'us'), ('xkb', 'de')]\""
        )

    def test_set_second_layout_failure_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 1)):
            with pytest.raises(AssertionError, match="Failed to add second keyboard layout"):
                ims.input_sources_set_to_include_second_layout(MagicMock())

    def test_switch_current_issues_expected_gsettings_write(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 0)) as checked:
            ims.current_input_source_switched_to_index_1(MagicMock())

        assert checked.call_args[0][0] == (
            "gsettings set org.gnome.desktop.input-sources current 1"
        )

    def test_switch_current_failure_fails(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("", 1)):
            with pytest.raises(AssertionError, match="Failed to switch current input source"):
                ims.current_input_source_switched_to_index_1(MagicMock())

    def test_explicit_restore_step_delegates_to_helper(self, ims):
        context = MagicMock()
        with patch.object(ims, "_restore_input_sources") as restore:
            ims.original_input_sources_are_restored(context)

        restore.assert_called_once_with(context)


class TestLocalectlStatus:
    def test_passes_when_vc_keymap_reported(self, ims):
        with patch.object(
            ims, "_run_in_vm_checked", return_value=("VC Keymap: us", 0)
        ):
            ims.localectl_status_reports_keymap(MagicMock())

    def test_fails_when_keymap_missing(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("X11 Layout: us", 0)):
            with pytest.raises(AssertionError, match="No VC Keymap in localectl status"):
                ims.localectl_status_reports_keymap(MagicMock())

    def test_fails_when_localectl_errors(self, ims):
        with patch.object(ims, "_run_in_vm_checked", return_value=("nope", 1)):
            with pytest.raises(AssertionError, match="localectl failed"):
                ims.localectl_status_reports_keymap(MagicMock())
