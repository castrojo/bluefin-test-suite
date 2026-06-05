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
