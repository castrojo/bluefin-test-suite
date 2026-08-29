"""Unit tests for tests/smoke/features/steps/offline_boot_steps.py.

The module talks to a live VM over SSH (or the local shell when run outside a
container), so ``behave``, ``tests.shared.ssh_steps`` and ``subprocess`` are
stubbed. Coverage targets the container-vs-local dispatch in ``_run_host`` and
every accept/reject branch of the offline-boot steps.
"""
import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_offline_boot_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    ssh_stub = types.ModuleType("tests.shared.ssh_steps")
    ssh_stub.run_ssh = MagicMock()
    sys.modules["tests.shared.ssh_steps"] = ssh_stub

    sys.modules.pop("tests.smoke.features.steps.offline_boot_steps", None)

    import tests.smoke.features.steps.offline_boot_steps as m  # noqa: PLC0415
    return m


@pytest.fixture
def mod():
    return _import_offline_boot_steps()


def _completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(
        args="cmd", returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestRunHost:
    def test_forwards_over_ssh_when_in_container(self, mod, monkeypatch):
        monkeypatch.setenv("SSH_KEY", "/keys/id")
        monkeypatch.setenv("VM_IP", "10.0.0.5")
        monkeypatch.setenv("VM_USER", "tester")
        monkeypatch.setenv("SSH_PORT", "2222")

        with (
            patch.object(mod, "_IN_CONTAINER", True),
            patch.object(
                mod.subprocess, "run", return_value=_completed(" out \n", 0, " err ")
            ) as run,
        ):
            assert mod._run_host("uptime", timeout=9) == ("out", 0, "err")

        argv = run.call_args[0][0]
        assert argv[:3] == ["ssh", "-i", "/keys/id"]
        assert argv[-3:] == ["2222", "tester@10.0.0.5", "uptime"]
        assert run.call_args.kwargs["timeout"] == 9
        assert "shell" not in run.call_args.kwargs

    def test_uses_ssh_defaults_when_env_unset(self, mod, monkeypatch):
        for var in ("SSH_KEY", "VM_IP", "VM_USER", "SSH_PORT"):
            monkeypatch.delenv(var, raising=False)

        with (
            patch.object(mod, "_IN_CONTAINER", True),
            patch.object(mod.subprocess, "run", return_value=_completed()) as run,
        ):
            mod._run_host("uptime")

        argv = run.call_args[0][0]
        assert "/home/bluefin-test/.ssh/id_ed25519" in argv
        assert "bluefin-test@127.0.0.1" in argv
        assert run.call_args.kwargs["timeout"] == 30

    def test_runs_through_shell_when_not_in_container(self, mod):
        with (
            patch.object(mod, "_IN_CONTAINER", False),
            patch.object(
                mod.subprocess, "run", return_value=_completed("hi", 3, "bad")
            ) as run,
        ):
            assert mod._run_host("uptime") == ("hi", 3, "bad")

        assert run.call_args[0][0] == "uptime"
        assert run.call_args.kwargs["shell"] is True


class TestNmWaitOnlineNotBeforeGraphical:
    def test_returns_early_when_unit_is_masked(self, mod):
        with patch.object(
            mod, "_run_host", return_value=("UnitFileState=masked", 0, "")
        ) as run:
            mod.nm_wait_online_not_before_graphical(MagicMock())

        assert run.call_count == 1

    def test_returns_early_when_unit_not_found(self, mod):
        with patch.object(
            mod, "_run_host", return_value=("LoadState=not-found", 0, "")
        ) as run:
            mod.nm_wait_online_not_before_graphical(MagicMock())

        assert run.call_count == 1

    def test_passes_when_graphical_target_has_no_dependency(self, mod):
        with patch.object(
            mod,
            "_run_host",
            side_effect=[
                ("UnitFileState=enabled\nLoadState=loaded", 0, ""),
                ("Wants=gdm.service\nRequires=multi-user.target", 0, ""),
            ],
        ):
            mod.nm_wait_online_not_before_graphical(MagicMock())

    def test_passes_when_dependency_exists_but_unit_disabled(self, mod):
        with patch.object(
            mod,
            "_run_host",
            side_effect=[
                ("UnitFileState=disabled\nLoadState=loaded", 0, ""),
                ("Requires=NetworkManager-wait-online.service", 0, ""),
            ],
        ):
            mod.nm_wait_online_not_before_graphical(MagicMock())

    def test_fails_when_enabled_unit_is_required_by_graphical_target(self, mod):
        with patch.object(
            mod,
            "_run_host",
            side_effect=[
                ("UnitFileState=enabled\nLoadState=loaded", 0, ""),
                ("Requires=NetworkManager-wait-online.service", 0, ""),
            ],
        ):
            with pytest.raises(AssertionError, match="blocks offline boot"):
                mod.nm_wait_online_not_before_graphical(MagicMock())


class TestUupdTimerEnabledOrAbsent:
    @pytest.mark.parametrize("state", ["enabled", "static"])
    def test_accepts_enabled_and_static(self, mod, state):
        with patch.object(mod, "_run_host", return_value=(state, 0, "")):
            mod.uupd_timer_enabled_or_absent(MagicMock())

    @pytest.mark.parametrize("state", ["not-found", "No such file or directory"])
    def test_accepts_absent_timer(self, mod, state):
        with patch.object(mod, "_run_host", return_value=(state, 1, "")):
            mod.uupd_timer_enabled_or_absent(MagicMock())

    @pytest.mark.parametrize("state", ["disabled", "failed", "masked"])
    def test_rejects_unexpected_states(self, mod, state):
        with patch.object(mod, "_run_host", return_value=(state, 0, "")):
            with pytest.raises(AssertionError, match="unexpected state"):
                mod.uupd_timer_enabled_or_absent(MagicMock())


class TestNoUupdErrorJournalEntries:
    def test_passes_when_journal_is_empty(self, mod):
        with patch.object(mod, "_run_host", return_value=("   \n", 0, "")):
            mod.no_uupd_error_journal_entries(MagicMock())

    def test_fails_when_error_entries_present(self, mod):
        with patch.object(
            mod, "_run_host", return_value=("uupd: network unreachable", 0, "")
        ):
            with pytest.raises(AssertionError, match="error-level journal entries"):
                mod.no_uupd_error_journal_entries(MagicMock())


class TestDropDefaultRoute:
    def test_records_route_and_deletes_it(self, mod):
        context = MagicMock()
        with (
            patch.object(
                mod,
                "_run_host",
                side_effect=[("default via 10.0.2.2 dev eth0 ", 0, ""), ("", 0, "")],
            ) as run,
            patch.object(mod.time, "sleep") as sleep,
        ):
            mod.drop_default_route(context)

        assert context.offline_default_route == "default via 10.0.2.2 dev eth0"
        assert "ip route del default" in run.call_args_list[1][0][0]
        sleep.assert_called_once_with(1)

    def test_records_none_when_route_lookup_fails(self, mod):
        context = MagicMock()
        with (
            patch.object(mod, "_run_host", side_effect=[("", 2, "err"), ("", 0, "")]),
            patch.object(mod.time, "sleep"),
        ):
            mod.drop_default_route(context)

        assert context.offline_default_route is None


class TestRestoreDefaultRoute:
    def test_restores_recorded_route(self, mod):
        context = MagicMock()
        context.offline_default_route = "default via 10.0.2.2 dev eth0"
        with (
            patch.object(mod, "_run_host", return_value=("", 0, "")) as run,
            patch.object(mod.time, "sleep") as sleep,
        ):
            mod.restore_default_route(context)

        assert "ip route add default via 10.0.2.2 dev eth0" in run.call_args[0][0]
        sleep.assert_called_once_with(2)

    def test_falls_back_to_nmcli_when_no_route_recorded(self, mod):
        context = MagicMock()
        context.offline_default_route = None
        with (
            patch.object(mod, "_run_host", return_value=("", 0, "")) as run,
            patch.object(mod.time, "sleep"),
        ):
            mod.restore_default_route(context)

        assert "nmcli device connect" in run.call_args[0][0]


class TestBootWithInterfacesDown:
    def test_skips_the_pending_scenario(self, mod):
        context = MagicMock()

        mod.boot_with_interfaces_down(context)

        context.scenario.skip.assert_called_once()
        assert "Blocked" in context.scenario.skip.call_args[0][0]
