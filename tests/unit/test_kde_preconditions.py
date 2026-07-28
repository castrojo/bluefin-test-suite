"""Unit tests for tests/shared/kde_preconditions.py.

All SSH interactions are mocked; no live VM is required.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.shared import kde_preconditions
import subprocess
import sys
from unittest import mock


# ---------------------------------------------------------------------------
# Minimal behave context mock
# ---------------------------------------------------------------------------

def _make_context(ssh_rc=0, command_stdout="", ssh_stderr=""):
    ctx = MagicMock()
    ctx.ssh_key = "/tmp/test.key"
    ctx.ssh_user = "bluefin-test"
    ctx.vm_ip = "192.168.1.5"
    ctx.ssh_port = None
    ctx.ssh_command_prefix = ""
    ctx.command_stdout = command_stdout
    ctx.last_command_output = command_stdout
    ctx.ssh_rc = ssh_rc
    ctx.last_ssh_result = MagicMock()
    ctx.last_ssh_result.stderr = ssh_stderr
    ctx.last_ssh_result.returncode = ssh_rc
    return ctx


def _mock_ssh_ok(ctx):
    """Patch _ssh so it only records ssh_rc=0 on context."""
    def _fake_ssh(context, cmd, timeout=60):
        context.ssh_rc = 0
        context.command_stdout = ""
        context.last_ssh_result = MagicMock()
        context.last_ssh_result.stderr = ""
        context.last_ssh_result.returncode = 0

    return patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh)


def _mock_ssh_fail(ctx, rc=1, stderr=""):
    def _fake_ssh(context, cmd, timeout=60):
        context.ssh_rc = rc
        context.command_stdout = ""
        context.last_ssh_result = MagicMock()
        context.last_ssh_result.stderr = stderr
        context.last_ssh_result.returncode = rc

    return patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh)


# ---------------------------------------------------------------------------
# Capability probes
# ---------------------------------------------------------------------------

class TestIsKdeSession:
    def test_true_when_kwin_wayland_runs(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.is_kde_session(ctx) is True

    def test_false_when_kwin_wayland_absent(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.is_kde_session(ctx) is False


class TestHasSddm:
    def test_true_when_display_manager_is_sddm(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.has_sddm(ctx) is True

    def test_false_when_display_manager_is_gdm(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.has_sddm(ctx) is False


class TestHasKwriteconfig6:
    def test_true_when_binary_exists(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.has_kwriteconfig6(ctx) is True

    def test_false_when_binary_missing(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.has_kwriteconfig6(ctx) is False


class TestHasPlasmaWaylandSession:
    def test_true_when_desktop_file_exists(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.has_plasma_wayland_session(ctx) is True

    def test_false_when_desktop_file_missing(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.has_plasma_wayland_session(ctx) is False


# ---------------------------------------------------------------------------
# SDDM autologin
# ---------------------------------------------------------------------------

class TestConfigureSddmAutologin:
    def test_skips_when_sddm_not_display_manager(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=False):
            result = kde_preconditions.configure_sddm_autologin(ctx)
        assert result.skipped is True
        assert result.ok is True
        assert "SDDM is not the display manager" in result.reason

    def test_writes_dropin_for_plasma_wayland(self):
        ctx = _make_context()
        commands = []

        def _fake_ssh(context, cmd, timeout=60):
            commands.append(cmd)
            context.ssh_rc = 0
            context.command_stdout = ""

        with patch.object(kde_preconditions, "has_sddm", return_value=True):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
                    result = kde_preconditions.configure_sddm_autologin(ctx, username="kde-test")

        assert result.ok is True
        assert result.skipped is False
        assert any("99-testsuite-autologin.conf" in c for c in commands)
        assert any("Session=plasmawayland.desktop" in c for c in commands)
        assert any("User=kde-test" in c for c in commands)

    def test_fails_when_plasma_wayland_session_missing(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=True):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=False):
                result = kde_preconditions.configure_sddm_autologin(ctx)
        assert result.ok is False
        assert "Plasma Wayland session desktop file not found" in result.reason

    def test_fails_when_ssh_write_fails(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=True):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_fail(ctx, rc=1, stderr="permission denied"):
                    result = kde_preconditions.configure_sddm_autologin(ctx)
        assert result.ok is False
        assert "Failed to write" in result.reason


# ---------------------------------------------------------------------------
# Welcome wizard suppression
# ---------------------------------------------------------------------------

class TestSuppressWelcomeWizard:
    def test_skips_when_kwriteconfig6_missing(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_kwriteconfig6", return_value=False):
            result = kde_preconditions.suppress_welcome_wizard(ctx)
        assert result.skipped is True
        assert result.ok is True
        assert "kwriteconfig6 not available" in result.reason

    def test_disables_welcome_and_animations(self):
        ctx = _make_context()
        commands = []

        def _fake_ssh(context, cmd, timeout=60):
            commands.append(cmd)
            context.ssh_rc = 0

        with patch.object(kde_preconditions, "has_kwriteconfig6", return_value=True):
            with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
                result = kde_preconditions.suppress_welcome_wizard(ctx, username="kde-test")

        assert result.ok is True
        joined = " && ".join(commands)
        assert "ShowOnStartup false" in joined
        assert "AnimationDurationFactor 0" in joined
        assert "/home/kde-test/.config" in joined
        assert "chown -R kde-test:kde-test" in joined

    def test_fails_when_ssh_command_fails(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_kwriteconfig6", return_value=True):
            with _mock_ssh_fail(ctx, rc=127):
                result = kde_preconditions.suppress_welcome_wizard(ctx)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Determinism drop-in
# ---------------------------------------------------------------------------

class TestEmitDeterminismDropin:
    def test_writes_expected_env_vars(self):
        ctx = _make_context()
        commands = []

        def _fake_ssh(context, cmd, timeout=60):
            commands.append(cmd)
            context.ssh_rc = 0

        with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
            result = kde_preconditions.emit_determinism_dropin(ctx)

        assert result.ok is True
        cmd = commands[0]
        assert "/etc/environment.d/99-testsuite-kde.conf" in cmd
        for key in kde_preconditions.DETERMINISM_ENV:
            assert f"{key}=" in cmd

    def test_fails_when_write_fails(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            result = kde_preconditions.emit_determinism_dropin(ctx)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Home seeding
# ---------------------------------------------------------------------------

class TestSeedHome:
    def test_cleans_and_recreates_home_dirs(self):
        ctx = _make_context()
        commands = []

        def _fake_ssh(context, cmd, timeout=60):
            commands.append(cmd)
            context.ssh_rc = 0

        # Seeding is a pre-session operation; assert it under "no live session".
        with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
            with patch.object(kde_preconditions, "is_kde_session", return_value=False):
                result = kde_preconditions.seed_home(ctx, username="kde-test")

        assert result.ok is True
        cmd = commands[0]
        assert "rm -rf" in cmd
        assert "/home/kde-test/.config" in cmd
        assert "/home/kde-test/.local/share" in cmd
        assert "chown -R" in cmd

    def test_fails_when_ssh_fails(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            result = kde_preconditions.seed_home(ctx)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Readiness waiter
# ---------------------------------------------------------------------------

class TestWaitForPlasmaSession:
    def test_succeeds_immediately_when_all_signals_present(self):
        ctx = _make_context()

        def _fake_ssh(context, cmd, timeout=10):
            context.ssh_rc = 0
            context.command_stdout = ""

        with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
            with patch.object(kde_preconditions.time, "sleep"):
                # Success path returns immediately; still guard against sleeps.
                result = kde_preconditions.wait_for_plasma_session(ctx, timeout=5)

        assert result.ok is True
        assert "ready after" in result.reason

    def test_polls_with_backoff_and_times_out(self):
        ctx = _make_context()
        call_count = {"n": 0}
        sleep_delays = []

        def _fake_ssh(context, cmd, timeout=10):
            call_count["n"] += 1
            context.ssh_rc = 1
            context.command_stdout = ""
            context.last_ssh_result = MagicMock()
            context.last_ssh_result.stderr = ""

        def _fake_sleep(delay):
            sleep_delays.append(delay)

        with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
            with patch.object(kde_preconditions.time, "monotonic", side_effect=[0, 0.5, 1.5, 3.5, 10]):
                with patch.object(kde_preconditions.time, "sleep", side_effect=_fake_sleep):
                    result = kde_preconditions.wait_for_plasma_session(ctx, timeout=5)

        assert result.ok is False
        assert "not ready after 5s" in result.reason
        assert call_count["n"] >= 2
        # Backoff should grow then cap.
        assert sleep_delays[0] == pytest.approx(0.2)
        assert all(d <= 2.0 for d in sleep_delays)

    def test_includes_session_env_source(self):
        ctx = _make_context()
        commands = []

        def _fake_ssh(context, cmd, timeout=10):
            commands.append(cmd)
            context.ssh_rc = 0

        with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
            kde_preconditions.wait_for_plasma_session(ctx, timeout=1)

        assert any("source /tmp/session.env" in c for c in commands)
        assert any("org.a11y.Bus" in c for c in commands)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestApplyKdeSessionPreconditions:
    def test_skips_when_not_kde_session(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "is_kde_session", return_value=False):
            result = kde_preconditions.apply_kde_session_preconditions(ctx)
        assert result.skipped is True
        assert result.ok is True
        assert "not running a KDE/Plasma session" in result.reason

    def test_runs_all_steps_and_waits(self):
        ctx = _make_context()

        def _fake_ssh(context, cmd, timeout=60):
            context.ssh_rc = 0

        with patch.object(kde_preconditions, "is_kde_session", return_value=True):
            with patch.object(kde_preconditions, "_ssh", side_effect=_fake_ssh):
                with patch.object(kde_preconditions, "has_sddm", return_value=True):
                    with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                        with patch.object(kde_preconditions, "has_kwriteconfig6", return_value=True):
                            result = kde_preconditions.apply_kde_session_preconditions(ctx)

        assert result.ok is True
        assert result.skipped is False

    def test_fails_when_a_step_fails(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "is_kde_session", return_value=True):
            with patch.object(kde_preconditions, "seed_home", return_value=kde_preconditions.KDEResult(ok=False, reason="disk full")):
                result = kde_preconditions.apply_kde_session_preconditions(ctx)
        assert result.ok is False
        assert "determinism drop-in failed" in result.reason


class TestReviewFixes:
    """Regression tests for issues found in code review of PR #641."""

    @pytest.mark.parametrize("bad", ["../../etc", "a/b", "root/../x", "", "-x", "A" * 40])
    def test_seed_home_rejects_unsafe_usernames(self, bad):
        """Quoting stops injection but not traversal; seed_home must refuse."""
        ctx = mock.Mock()
        with mock.patch.object(kde_preconditions, "is_kde_session", return_value=False):
            result = kde_preconditions.seed_home(ctx, username=bad, force=True)
        assert result.ok is False
        assert "unsafe" in result.reason.lower()

    def test_seed_home_refuses_while_session_live(self):
        """Wiping .config under a running Plasma session destroys user state."""
        ctx = mock.Mock()
        with mock.patch.object(kde_preconditions, "is_kde_session", return_value=True):
            result = kde_preconditions.seed_home(ctx, username="bluefin-test")
        assert result.ok is False
        assert "refusing to seed home" in result.reason

    def test_ssh_timeout_does_not_escape(self):
        """A timeout must become a failed probe, not an exception out of a hook."""
        ctx = mock.Mock()
        stub = mock.Mock()
        stub.run_ssh.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=1)
        with mock.patch.dict(sys.modules, {"tests.shared.ssh_steps": stub}):
            kde_preconditions._ssh(ctx, "true", timeout=1)
        assert ctx.ssh_rc == -1

    def test_autologin_write_uses_sudo(self):
        """/etc/sddm.conf.d is not writable by the unprivileged SSH user."""
        sent = {}

        def fake_ok(context, cmd, timeout=60):
            sent.setdefault("cmds", []).append(cmd)
            return True

        ctx = mock.Mock()
        with mock.patch.object(kde_preconditions, "_ssh_ok", fake_ok):
            kde_preconditions.configure_sddm_autologin(ctx, username="bluefin-test")
        assert any("sudo -n" in c for c in sent["cmds"]), sent
