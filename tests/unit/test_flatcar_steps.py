"""Unit tests for tests/flatcar/features/steps/steps.py."""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_flatcar_steps(run_ssh_return=None):
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")
    if run_ssh_return is not None:
        ssh_steps_stub.run_ssh = MagicMock(return_value=run_ssh_return)
    else:
        ssh_steps_stub.run_ssh = MagicMock(return_value=("ok", 0))

    def _ssh_output_is(context, expected):
        actual = getattr(context, "command_stdout", "").strip()
        assert actual == expected, f"Expected {expected!r}, got {actual!r}"

    def _ssh_return_code_is(context, expected):
        actual = getattr(context, "ssh_rc", 0)
        assert str(actual) == str(expected), f"Expected rc {expected}, got {actual}"

    ssh_steps_stub.ssh_output_is = _ssh_output_is
    ssh_steps_stub.ssh_return_code_is = _ssh_return_code_is

    sys.modules["tests"] = sys.modules.get("tests", types.ModuleType("tests"))
    sys.modules["tests.shared"] = sys.modules.get("tests.shared", types.ModuleType("tests.shared"))
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    for key in list(sys.modules):
        if "flatcar.features.steps.steps" in key:
            del sys.modules[key]

    import tests.flatcar.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**attrs):
    ctx = MagicMock()
    ctx.command_stdout = ""
    ctx.ssh_rc = 0
    ctx.last_ssh_result = None
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# flatcar_vm_is_reachable
# ---------------------------------------------------------------------------

class TestFlatcarVmIsReachable:
    def test_passes_when_ssh_returns_ok(self):
        m = _import_flatcar_steps(run_ssh_return=("ok", 0))
        ctx = _ctx(vm_ip="192.168.1.10")
        m.flatcar_vm_is_reachable(ctx)

    def test_raises_after_retries_exhausted(self):
        m = _import_flatcar_steps()
        m.run_ssh = MagicMock(return_value=("", 1))
        ctx = _ctx(vm_ip="192.168.1.10")
        with patch("tests.flatcar.features.steps.steps.run_ssh", return_value=("", 1)):
            with patch("tests.flatcar.features.steps.steps.time.sleep"):
                with pytest.raises(AssertionError, match="Cannot reach Flatcar VM"):
                    m.flatcar_vm_is_reachable(ctx)


# ---------------------------------------------------------------------------
# flatcar_target_disk_has_partitions
# ---------------------------------------------------------------------------

class TestFlatcarTargetDiskHasPartitions:
    def test_passes_when_partitions_exist(self):
        m = _import_flatcar_steps(run_ssh_return=("2", 0))
        ctx = _ctx(command_stdout="2", ssh_rc=0)
        # run_ssh sets command_stdout via side_effect
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            mock_run.return_value = ("2", 0)

            def set_stdout(context, cmd, timeout=60):
                context.command_stdout = "2"
                return "2", 0

            mock_run.side_effect = set_stdout
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                m.flatcar_target_disk_has_partitions(ctx)

    def test_raises_when_zero_partitions(self):
        m = _import_flatcar_steps()
        ctx = _ctx(command_stdout="0", ssh_rc=0)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            def set_stdout(context, cmd, timeout=60):
                context.command_stdout = "0"
                return "0", 0

            mock_run.side_effect = set_stdout
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                with pytest.raises(AssertionError, match="at least one partition"):
                    m.flatcar_target_disk_has_partitions(ctx)


# ---------------------------------------------------------------------------
# flatcar_update_channel_is_configured
# ---------------------------------------------------------------------------

class TestFlatcarUpdateChannelIsConfigured:
    def test_passes_when_group_set(self):
        m = _import_flatcar_steps()
        ctx = _ctx(command_stdout="GROUP=stable", ssh_rc=0)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            def set_stdout(context, cmd, timeout=60):
                context.command_stdout = "GROUP=stable"
                return "GROUP=stable", 0

            mock_run.side_effect = set_stdout
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                m.flatcar_update_channel_is_configured(ctx)

    def test_raises_when_group_empty(self):
        m = _import_flatcar_steps()
        ctx = _ctx(command_stdout="", ssh_rc=0)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            def set_stdout(context, cmd, timeout=60):
                context.command_stdout = ""
                return "", 0

            mock_run.side_effect = set_stdout
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                with pytest.raises(AssertionError, match="non-empty GROUP setting"):
                    m.flatcar_update_channel_is_configured(ctx)


# ---------------------------------------------------------------------------
# ignition_hostname_is
# ---------------------------------------------------------------------------

class TestIgnitionHostnameIs:
    def test_delegates_to_ssh_output_is(self):
        m = _import_flatcar_steps()
        ctx = _ctx(command_stdout="flatcar-test", ssh_rc=0)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            mock_run.return_value = ("flatcar-test", 0)
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                with patch("tests.flatcar.features.steps.steps.ssh_output_is") as mock_out:
                    m.ignition_hostname_is(ctx, "flatcar-test")
                    mock_out.assert_called_once_with(ctx, "flatcar-test")


# ---------------------------------------------------------------------------
# afterburn_service_is_available
# ---------------------------------------------------------------------------

class TestAfterburns:
    def test_passes_when_afterburn_active(self):
        m = _import_flatcar_steps()
        ctx = _ctx(ssh_rc=0)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            mock_run.return_value = ("1", 0)
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                m.afterburn_service_is_available(ctx)


# ---------------------------------------------------------------------------
# parse_update_conf / automatic_updates_disabled
# ---------------------------------------------------------------------------

class TestParseUpdateConf:
    def test_parses_plain_assignments(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf("GROUP=stable\nSERVER=https://public.update.flatcar-linux.net/v1/update/") == {
            "GROUP": "stable",
            "SERVER": "https://public.update.flatcar-linux.net/v1/update/",
        }

    def test_strips_quotes_and_whitespace(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf('  REBOOT_STRATEGY="off"  \n') == {"REBOOT_STRATEGY": "off"}
        assert m.parse_update_conf("GROUP='beta'") == {"GROUP": "beta"}

    def test_ignores_comments_and_blank_lines(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf("# comment\n\n   \nGROUP=alpha\n") == {"GROUP": "alpha"}

    def test_ignores_lines_without_assignment(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf("not an assignment\nGROUP=stable") == {"GROUP": "stable"}

    def test_last_assignment_wins(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf("SERVER=a\nSERVER=disabled")["SERVER"] == "disabled"

    def test_handles_empty_input(self):
        m = _import_flatcar_steps()
        assert m.parse_update_conf("") == {}
        assert m.parse_update_conf(None) == {}


class TestAutomaticUpdatesDisabled:
    @pytest.mark.parametrize("conf", [
        "SERVER=disabled",
        'SERVER="disabled"',
        "GROUP=stable\nSERVER=disabled\n",
        "SERVER=DISABLED",
        "SERVER=off",
        "SERVER=",
    ])
    def test_true_for_disabled_server_values(self, conf):
        m = _import_flatcar_steps()
        assert m.automatic_updates_disabled(conf) is True

    @pytest.mark.parametrize("conf", [
        "",
        "GROUP=stable",
        "SERVER=https://public.update.flatcar-linux.net/v1/update/",
        "# SERVER=disabled",
        "REBOOT_STRATEGY=off",
    ])
    def test_false_when_updates_remain_enabled(self, conf):
        m = _import_flatcar_steps()
        assert m.automatic_updates_disabled(conf) is False


# ---------------------------------------------------------------------------
# ignition_first_boot_marker_is_cleared
# ---------------------------------------------------------------------------

class TestIgnitionFirstBootMarkerIsCleared:
    @staticmethod
    def _probe(stdout, rc):
        def _run(context, cmd, timeout=60):
            context.command_stdout = stdout
            context.ssh_rc = rc
            return stdout, rc
        return _run

    def test_passes_when_marker_absent(self):
        m = _import_flatcar_steps()
        ctx = _ctx()
        with patch("tests.flatcar.features.steps.steps.run_ssh",
                   side_effect=self._probe("absent", 0)):
            m.ignition_first_boot_marker_is_cleared(ctx)

    def test_raises_when_marker_still_present(self):
        m = _import_flatcar_steps()
        ctx = _ctx()
        with patch("tests.flatcar.features.steps.steps.run_ssh",
                   side_effect=self._probe("present", 0)):
            with pytest.raises(AssertionError, match="Ignition did not complete"):
                m.ignition_first_boot_marker_is_cleared(ctx)

    def test_ssh_transport_failure_is_not_read_as_marker_absent(self):
        """rc 255 means the connection failed, not that Ignition succeeded.

        The previous implementation treated *any* nonzero result as proof the
        marker was gone, so an unreachable VM produced a green Ignition check.
        """
        m = _import_flatcar_steps()
        ctx = _ctx()
        with patch("tests.flatcar.features.steps.steps.run_ssh",
                   side_effect=self._probe("", 255)):
            with pytest.raises(AssertionError):
                m.ignition_first_boot_marker_is_cleared(ctx)

    def test_shell_failure_without_recognisable_output_fails(self):
        m = _import_flatcar_steps()
        ctx = _ctx()
        with patch("tests.flatcar.features.steps.steps.run_ssh",
                   side_effect=self._probe("bash: no such thing", 0)):
            with pytest.raises(AssertionError, match="Could not determine"):
                m.ignition_first_boot_marker_is_cleared(ctx)

    def test_probe_always_reports_state_in_stdout(self):
        m = _import_flatcar_steps()
        ctx = _ctx()
        with patch("tests.flatcar.features.steps.steps.run_ssh",
                   side_effect=self._probe("absent", 0)) as mock_run:
            m.ignition_first_boot_marker_is_cleared(ctx)

        cmd = mock_run.call_args[0][1]
        assert "echo present" in cmd and "echo absent" in cmd


# ---------------------------------------------------------------------------
# flatcar_esp_is_mounted_at_boot
# ---------------------------------------------------------------------------

class TestFlatcarEspIsMountedAtBoot:
    def _run(self, fstype):
        m = _import_flatcar_steps()
        ctx = _ctx()

        def set_stdout(context, cmd, timeout=60):
            context.command_stdout = fstype
            return fstype, 0

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=set_stdout):
            with patch("tests.flatcar.features.steps.steps.ssh_return_code_is"):
                m.flatcar_esp_is_mounted_at_boot(ctx)

    def test_passes_for_vfat(self):
        self._run("vfat")

    def test_raises_for_non_esp_filesystem(self):
        with pytest.raises(AssertionError, match="EFI System Partition"):
            self._run("ext4")


# ---------------------------------------------------------------------------
# restore_update_conf
# ---------------------------------------------------------------------------

class TestRestoreUpdateConf:
    def test_no_op_when_no_backup_taken(self):
        m = _import_flatcar_steps()
        ctx = _ctx(update_conf_backed_up=False)
        with patch("tests.flatcar.features.steps.steps.run_ssh") as mock_run:
            m.restore_update_conf(ctx)
            mock_run.assert_not_called()

    def test_restores_and_clears_flag(self):
        m = _import_flatcar_steps()
        ctx = _ctx(update_conf_backed_up=True)

        def _run(context, cmd, timeout=60):
            context.command_stdout = "GROUP=stable\nSERVER=https://public.update.flatcar-linux.net/v1/update/"
            context.ssh_rc = 0
            return context.command_stdout, 0

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=_run) as mock_run:
            m.restore_update_conf(ctx)

        commands = [call[0][1] for call in mock_run.call_args_list]
        assert m.UPDATE_CONF_BACKUP in commands[0]
        assert commands[-1] == f"cat {m.UPDATE_CONF}"
        assert ctx.update_conf_backed_up is False

    def test_failed_restore_command_keeps_flag_set_for_retry(self):
        """A failed restore must leave the flag set so after_scenario retries.

        Clearing it first left the VM with automatic updates disabled and no
        way to recover for the rest of the run.
        """
        m = _import_flatcar_steps()
        ctx = _ctx(update_conf_backed_up=True)

        def _run(context, cmd, timeout=60):
            context.command_stdout = ""
            context.ssh_rc = 1
            return "", 1

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=_run):
            with pytest.raises(AssertionError):
                m.restore_update_conf(ctx)

        assert ctx.update_conf_backed_up is True

    def test_unverified_restore_keeps_flag_set(self):
        """The move can succeed while the file still disables updates."""
        m = _import_flatcar_steps()
        ctx = _ctx(update_conf_backed_up=True)

        def _run(context, cmd, timeout=60):
            context.command_stdout = "GROUP=stable\nSERVER=disabled"
            context.ssh_rc = 0
            return context.command_stdout, 0

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=_run):
            with pytest.raises(AssertionError, match="still disables automatic updates"):
                m.restore_update_conf(ctx)

        assert ctx.update_conf_backed_up is True

    def test_cleanup_can_retry_after_a_failed_restore(self):
        m = _import_flatcar_steps()
        ctx = _ctx(update_conf_backed_up=True)

        def _fail(context, cmd, timeout=60):
            context.command_stdout = ""
            context.ssh_rc = 1
            return "", 1

        def _ok(context, cmd, timeout=60):
            context.command_stdout = "GROUP=stable\nSERVER=https://public.update.flatcar-linux.net/v1/update/"
            context.ssh_rc = 0
            return context.command_stdout, 0

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=_fail):
            with pytest.raises(AssertionError):
                m.restore_update_conf(ctx)

        with patch("tests.flatcar.features.steps.steps.run_ssh", side_effect=_ok):
            m.restore_update_conf(ctx)

        assert ctx.update_conf_backed_up is False
