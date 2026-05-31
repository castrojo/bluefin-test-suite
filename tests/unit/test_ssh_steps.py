"""Unit tests for tests/shared/ssh_steps.py.

Tests run_ssh command construction (prefix injection, port handling,
context attribute setting) using subprocess mocks. No live SSH required.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper — build a minimal behave context mock
# ---------------------------------------------------------------------------

def _make_context(*, ssh_key="/tmp/test.key", ssh_user="bluefin-test",
                  vm_ip="192.168.1.5", ssh_port=None, ssh_command_prefix=""):
    ctx = MagicMock()
    ctx.ssh_key = ssh_key
    ctx.ssh_user = ssh_user
    ctx.vm_ip = vm_ip
    ctx.ssh_port = ssh_port
    ctx.ssh_command_prefix = ssh_command_prefix
    ctx.command_stdout = ""
    ctx.last_command_output = ""
    ctx.ssh_rc = None
    ctx.last_ssh_result = None
    return ctx


def _make_proc(stdout="", returncode=0):
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# Import helper (avoids behave decorator side effects)
# ---------------------------------------------------------------------------

def _import_ssh_steps():
    import sys
    behave_stub = MagicMock()
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules.setdefault("behave", behave_stub)
    sys.modules.setdefault("behave.runner", MagicMock())

    if "tests.shared.ssh_steps" in sys.modules:
        del sys.modules["tests.shared.ssh_steps"]

    import tests.shared.ssh_steps as m
    return m


# ---------------------------------------------------------------------------
# run_ssh — basic functionality
# ---------------------------------------------------------------------------

class TestRunSsh:
    def setup_method(self):
        self.mod = _import_ssh_steps()

    def test_returns_stdout_and_returncode(self):
        ctx = _make_context()
        proc = _make_proc(stdout="hello\n", returncode=0)
        with patch("subprocess.run", return_value=proc):
            stdout, rc = self.mod.run_ssh(ctx, "echo hello")
        assert stdout == "hello"   # .strip() applied
        assert rc == 0

    def test_sets_context_attributes(self):
        ctx = _make_context()
        proc = _make_proc(stdout="output\n", returncode=0)
        with patch("subprocess.run", return_value=proc):
            self.mod.run_ssh(ctx, "somecommand")
        assert ctx.command_stdout == "output"
        assert ctx.last_command_output == "output"
        assert ctx.ssh_rc == 0
        assert ctx.last_ssh_result is proc

    def test_includes_ssh_key_in_command(self):
        ctx = _make_context(ssh_key="/home/user/.ssh/id_rsa")
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo ok")
        call_args = mock_run.call_args[0][0]
        assert "/home/user/.ssh/id_rsa" in call_args

    def test_no_prefix_passes_command_directly(self):
        ctx = _make_context(ssh_command_prefix="")
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo direct")
        call_args = mock_run.call_args[0][0]
        # The raw command should be the last element
        assert call_args[-1] == "echo direct"

    def test_prefix_wraps_in_bash_lc(self):
        ctx = _make_context(ssh_command_prefix="export VAR=1")
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo wrapped")
        call_args = mock_run.call_args[0][0]
        # The prefix+command is embedded in the final SSH argument as "bash -lc '...'"
        last_arg = call_args[-1]
        assert "bash" in last_arg
        assert "-lc" in last_arg
        assert "export VAR=1" in last_arg
        assert "echo wrapped" in last_arg

    def test_ssh_port_included_when_set(self):
        ctx = _make_context(ssh_port=2222)
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo ok")
        call_args = mock_run.call_args[0][0]
        assert "-p" in call_args
        assert "2222" in call_args

    def test_no_port_flag_when_ssh_port_is_none(self):
        ctx = _make_context(ssh_port=None)
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo ok")
        call_args = mock_run.call_args[0][0]
        assert "-p" not in call_args

    def test_target_host_in_command(self):
        ctx = _make_context(ssh_user="testuser", vm_ip="10.0.0.5")
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo ok")
        call_args = mock_run.call_args[0][0]
        assert "testuser@10.0.0.5" in call_args

    def test_strict_host_checking_disabled(self):
        ctx = _make_context()
        proc = _make_proc(stdout="ok\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod.run_ssh(ctx, "echo ok")
        call_args = mock_run.call_args[0][0]
        assert "StrictHostKeyChecking=no" in call_args

    def test_nonzero_returncode_stored_on_context(self):
        ctx = _make_context()
        proc = _make_proc(stdout="", returncode=1)
        with patch("subprocess.run", return_value=proc):
            _, rc = self.mod.run_ssh(ctx, "false")
        assert rc == 1
        assert ctx.ssh_rc == 1


# ---------------------------------------------------------------------------
# vm_reachable_over_ssh — retry behaviour
# ---------------------------------------------------------------------------

class TestVmReachableOverSsh:
    def setup_method(self):
        self.mod = _import_ssh_steps()

    def test_succeeds_immediately_when_ssh_works(self):
        ctx = _make_context()
        with patch.object(self.mod, "run_ssh", return_value=("ok", 0)):
            with patch("time.sleep"):
                # Should not raise
                self.mod.vm_reachable_over_ssh(ctx)

    def test_retries_then_succeeds(self):
        ctx = _make_context()
        side_effects = [
            ("", 1),
            ("", 1),
            ("ok", 0),
        ]
        call_count = {"n": 0}

        def _mock_run_ssh(context, cmd, timeout=20):
            val = side_effects[call_count["n"]]
            call_count["n"] += 1
            return val

        with patch.object(self.mod, "run_ssh", side_effect=_mock_run_ssh):
            with patch("time.sleep"):
                self.mod.vm_reachable_over_ssh(ctx)
        assert call_count["n"] == 3

    def test_raises_after_all_retries_fail(self):
        ctx = _make_context()
        with patch.object(self.mod, "run_ssh", return_value=("", 1)):
            with patch("time.sleep"):
                with pytest.raises(Exception):
                    self.mod.vm_reachable_over_ssh(ctx)
