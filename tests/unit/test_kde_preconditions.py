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


def _mock_ssh_capture(commands_list):
    """Patch _ssh to record commands and report success."""
    def _fake_ssh(context, cmd, timeout=60):
        commands_list.append(cmd)
        context.ssh_rc = 0
        context.command_stdout = ""

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


class TestIsKdeImage:
    @pytest.mark.parametrize("ref", [
        "ghcr.io/ublue-os/aurora:latest",
        "ghcr.io/ublue-os/kinoite:40",
        "ghcr.io/ublue-os/bazzite:stable",
        "registry.example.com/kde-desktop:v1",
        "plasma-custom:test",
    ])
    def test_recognises_kde_variants(self, ref):
        assert kde_preconditions.is_kde_image(ref) is True

    @pytest.mark.parametrize("ref", [
        "ghcr.io/ublue-os/bluefin:latest",
        "ghcr.io/fedora/silverblue:40",
        "",
    ])
    def test_rejects_non_kde_variants(self, ref):
        assert kde_preconditions.is_kde_image(ref) is False


class TestHasSddm:
    def test_true_when_display_manager_is_sddm(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.has_sddm(ctx) is True

    def test_false_when_display_manager_is_gdm(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.has_sddm(ctx) is False


class TestHasPlm:
    def test_true_when_display_manager_is_plm(self):
        ctx = _make_context()
        with _mock_ssh_ok(ctx):
            assert kde_preconditions.has_plm(ctx) is True

    def test_false_when_display_manager_is_not_plm(self):
        ctx = _make_context()
        with _mock_ssh_fail(ctx, rc=1):
            assert kde_preconditions.has_plm(ctx) is False


class TestDetectDisplayManager:
    def test_detects_sddm(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=True):
            assert kde_preconditions.detect_display_manager(ctx) == "sddm"

    def test_detects_plm(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=False):
            with patch.object(kde_preconditions, "has_plm", return_value=True):
                assert kde_preconditions.detect_display_manager(ctx) == "plm"

    def test_returns_unknown_when_neither(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=False):
            with patch.object(kde_preconditions, "has_plm", return_value=False):
                assert kde_preconditions.detect_display_manager(ctx) == "unknown"

    def test_sddm_takes_precedence_over_plm(self):
        """If both somehow match, SDDM wins (checked first)."""
        ctx = _make_context()
        with patch.object(kde_preconditions, "has_sddm", return_value=True):
            with patch.object(kde_preconditions, "has_plm", return_value=True):
                assert kde_preconditions.detect_display_manager(ctx) == "sddm"


class TestDmConfDir:
    def test_sddm_dir(self):
        assert kde_preconditions._dm_conf_dir("sddm") == "/etc/sddm.conf.d"

    def test_plm_dir(self):
        assert kde_preconditions._dm_conf_dir("plm") == "/etc/plasmalogin.conf.d"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown display manager"):
            kde_preconditions._dm_conf_dir("unknown")


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
# Autologin (DM-aware)
# ---------------------------------------------------------------------------

class TestConfigureAutologin:
    def test_sddm_writes_to_sddm_conf_d(self):
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    result = kde_preconditions.configure_autologin(ctx)

        assert result.ok is True
        cmd = commands[0]
        assert "/etc/sddm.conf.d/99-testsuite-autologin.conf" in cmd
        assert f"Session={kde_preconditions.KDE_WAYLAND_SESSION}" in cmd

    def test_plm_writes_to_plasmalogin_conf_d(self):
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="plm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    result = kde_preconditions.configure_autologin(ctx)

        assert result.ok is True
        cmd = commands[0]
        assert "/etc/plasmalogin.conf.d/99-testsuite-autologin.conf" in cmd
        assert f"Session={kde_preconditions.KDE_WAYLAND_SESSION}" in cmd

    def test_unknown_dm_fails_clearly(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "detect_display_manager", return_value="unknown"):
            result = kde_preconditions.configure_autologin(ctx)

        assert result.ok is False
        assert result.skipped is False
        assert "Neither SDDM nor PLM" in result.reason

    def test_session_value_is_plasmawayland_desktop(self):
        """The session must be plasmawayland.desktop (Wayland), NOT plasma.desktop (X11)."""
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    kde_preconditions.configure_autologin(ctx)

        assert any("Session=plasmawayland.desktop" in c for c in commands)
        assert not any("Session=plasma.desktop" in c for c in commands)

    def test_uses_sudo(self):
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    kde_preconditions.configure_autologin(ctx)

        assert any("sudo -n" in c for c in commands)

    def test_custom_username(self):
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="plm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    kde_preconditions.configure_autologin(ctx, username="testuser")

        assert any("User=testuser" in c for c in commands)

    def test_fails_when_plasma_wayland_session_missing(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=False):
                result = kde_preconditions.configure_autologin(ctx)
        assert result.ok is False
        assert "Plasma Wayland session desktop file not found" in result.reason

    def test_fails_when_ssh_write_fails(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_fail(ctx, rc=1, stderr="permission denied"):
                    result = kde_preconditions.configure_autologin(ctx)
        assert result.ok is False
        assert "Failed to write" in result.reason


class TestConfigureSddmAutologinCompat:
    """Backwards-compatibility wrapper tests."""

    def test_skips_when_no_dm_detected(self):
        """Old callers expect a skip, not hard failure, when SDDM is absent."""
        ctx = _make_context()
        with patch.object(kde_preconditions, "detect_display_manager", return_value="unknown"):
            result = kde_preconditions.configure_sddm_autologin(ctx)
        assert result.ok is True
        assert result.skipped is True

    def test_delegates_to_configure_autologin(self):
        ctx = _make_context()
        commands = []

        with patch.object(kde_preconditions, "detect_display_manager", return_value="sddm"):
            with patch.object(kde_preconditions, "has_plasma_wayland_session", return_value=True):
                with _mock_ssh_capture(commands):
                    result = kde_preconditions.configure_sddm_autologin(ctx, username="kde-test")

        assert result.ok is True
        assert any("99-testsuite-autologin.conf" in c for c in commands)
        assert any("Session=plasmawayland.desktop" in c for c in commands)
        assert any("User=kde-test" in c for c in commands)


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

    def test_uses_sudo(self):
        """Defect 1: /etc is not writable without sudo on immutable images."""
        ctx = _make_context()
        commands = []

        with _mock_ssh_capture(commands):
            kde_preconditions.emit_determinism_dropin(ctx)

        cmd = commands[0]
        assert "sudo -n" in cmd

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
# Disk-prep orchestrator
# ---------------------------------------------------------------------------

class TestApplyDiskPrep:
    def test_runs_autologin_and_determinism_and_seed(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "configure_autologin",
                          return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
            with patch.object(kde_preconditions, "emit_determinism_dropin",
                              return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                with patch.object(kde_preconditions, "seed_home",
                                  return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                    with patch.object(kde_preconditions, "suppress_welcome_wizard",
                                      return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                        result = kde_preconditions.apply_disk_prep(ctx)
        assert result.ok is True

    def test_fails_when_autologin_fails(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "configure_autologin",
                          return_value=kde_preconditions.KDEResult(ok=False, reason="no DM")):
            result = kde_preconditions.apply_disk_prep(ctx)
        assert result.ok is False
        assert "autologin failed" in result.reason

    def test_reports_skipped_steps(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "configure_autologin",
                          return_value=kde_preconditions.KDEResult(ok=True, skipped=True, reason="no DM")):
            with patch.object(kde_preconditions, "emit_determinism_dropin",
                              return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                with patch.object(kde_preconditions, "seed_home",
                                  return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                    with patch.object(kde_preconditions, "suppress_welcome_wizard",
                                      return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                        result = kde_preconditions.apply_disk_prep(ctx)
        assert result.ok is True
        assert "autologin skipped" in result.reason


# ---------------------------------------------------------------------------
# ensure_kde_session (runtime entry point for kde-smoke)
# ---------------------------------------------------------------------------

class TestEnsureKdeSession:
    def test_waits_for_plasma_then_suppresses_wizard(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "wait_for_plasma_session",
                          return_value=kde_preconditions.KDEResult(ok=True, reason="ready")):
            with patch.object(kde_preconditions, "suppress_welcome_wizard",
                              return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                result = kde_preconditions.ensure_kde_session(ctx)
        assert result.ok is True

    def test_fails_when_session_not_ready(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "wait_for_plasma_session",
                          return_value=kde_preconditions.KDEResult(ok=False, reason="timeout")):
            result = kde_preconditions.ensure_kde_session(ctx)
        assert result.ok is False
        assert "session readiness failed" in result.reason

    def test_tolerates_wizard_skip(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "wait_for_plasma_session",
                          return_value=kde_preconditions.KDEResult(ok=True, reason="ready")):
            with patch.object(kde_preconditions, "suppress_welcome_wizard",
                              return_value=kde_preconditions.KDEResult(ok=True, skipped=True, reason="no kwriteconfig6")):
                result = kde_preconditions.ensure_kde_session(ctx)
        assert result.ok is True


# ---------------------------------------------------------------------------
# Runtime orchestrator (apply_kde_session_preconditions)
# ---------------------------------------------------------------------------

class TestApplyKdeSessionPreconditions:
    def test_skips_when_not_kde_session(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "is_kde_session", return_value=False):
            result = kde_preconditions.apply_kde_session_preconditions(ctx)
        assert result.skipped is True
        assert result.ok is True
        assert "not running a KDE/Plasma session" in result.reason

    def test_does_not_attempt_disk_prep_operations(self):
        """Runtime must NOT attempt autologin or determinism drop-in writes."""
        ctx = _make_context()

        with patch.object(kde_preconditions, "is_kde_session", return_value=True):
            with patch.object(kde_preconditions, "seed_home",
                              return_value=kde_preconditions.KDEResult(ok=False, reason="session running")):
                with patch.object(kde_preconditions, "suppress_welcome_wizard",
                                  return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                    with patch.object(kde_preconditions, "wait_for_plasma_session",
                                      return_value=kde_preconditions.KDEResult(ok=True, reason="ready")):
                        with patch.object(kde_preconditions, "configure_autologin") as mock_autologin:
                            with patch.object(kde_preconditions, "emit_determinism_dropin") as mock_dropin:
                                result = kde_preconditions.apply_kde_session_preconditions(ctx)

        assert result.ok is True
        mock_autologin.assert_not_called()
        mock_dropin.assert_not_called()

    def test_seed_home_failure_is_non_fatal(self):
        """Seeding is a pre-session operation: refusal must not abort the run."""
        ctx = _make_context()
        refusal = kde_preconditions.KDEResult(ok=False, reason="session is running")
        with patch.object(kde_preconditions, "is_kde_session", return_value=True):
            with patch.object(kde_preconditions, "seed_home", return_value=refusal):
                with patch.object(kde_preconditions, "suppress_welcome_wizard",
                                  return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                    with patch.object(kde_preconditions, "wait_for_plasma_session",
                                      return_value=kde_preconditions.KDEResult(ok=True, reason="ready")):
                        result = kde_preconditions.apply_kde_session_preconditions(ctx)
        assert result.ok is True
        assert "seed home skipped" in result.reason

    def test_fails_when_session_not_ready(self):
        ctx = _make_context()
        with patch.object(kde_preconditions, "is_kde_session", return_value=True):
            with patch.object(kde_preconditions, "seed_home",
                              return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                with patch.object(kde_preconditions, "suppress_welcome_wizard",
                                  return_value=kde_preconditions.KDEResult(ok=True, reason="ok")):
                    with patch.object(kde_preconditions, "wait_for_plasma_session",
                                      return_value=kde_preconditions.KDEResult(ok=False, reason="timeout")):
                        result = kde_preconditions.apply_kde_session_preconditions(ctx)
        assert result.ok is False
        assert "session readiness failed" in result.reason


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_kde_wayland_session_is_wayland_not_x11(self):
        """Guard against the plasmawayland.desktop vs plasma.desktop trap."""
        assert kde_preconditions.KDE_WAYLAND_SESSION == "plasmawayland.desktop"
        assert "plasma.desktop" != kde_preconditions.KDE_WAYLAND_SESSION

    def test_autologin_dropin_filename_has_99_prefix(self):
        assert kde_preconditions.AUTOLOGIN_DROPIN_FILENAME.startswith("99-")


# ---------------------------------------------------------------------------
# Regression tests from PR #641
# ---------------------------------------------------------------------------

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
