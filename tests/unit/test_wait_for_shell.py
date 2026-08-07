"""Unit tests for tests/shared/wait_for_shell.py.

Two layers of coverage:

1. The original retry contract — Shell.Eval failures, AT-SPI panel not exposed
   yet, transient exceptions, and a bounded failure path.
2. The GDM-restart tolerance contract — ``ServiceUnknown`` and "bus socket
   vanished" errors are both retryable, the session bus address is re-resolved
   on every attempt (a cached address cannot survive a GDM restart), readiness
   must hold across consecutive checks, the deadline is bounded, and the
   timeout message names the error classes it saw.
"""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


MODULE_NAME = "tests.shared.wait_for_shell"

SERVICE_UNKNOWN = (
    "Error: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown: "
    "The name org.gnome.Shell was not provided by any .service files"
)
SOCKET_GONE = "Error: Could not connect: No such file or directory"
AUTOLAUNCH_FAILED = (
    "Error connecting: Error spawning command line "
    "\u201cdbus-launch --autolaunch=8041862c --binary-syntax --close-stderr\u201d: "
    "Child process exited with code 1"
)


def _import_wait_for_shell():
    """Import helper with dogtail stubbed out."""
    dogtail_stub = types.ModuleType("dogtail")
    tree_stub = types.ModuleType("dogtail.tree")
    tree_stub.root = MagicMock()
    dogtail_stub.tree = tree_stub
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.tree"] = tree_stub

    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def _proc(*, returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _ready_proc():
    return _proc(stdout="(true, 'true')")


def _ready_shell(mod):
    shell = MagicMock()
    panel = MagicMock()
    panel.findChildren.return_value = [
        SimpleNamespace(name="Activities", roleName="toggle button"),
        SimpleNamespace(name="", roleName="toggle button"),
    ]
    shell.findChildren.return_value = [panel]
    mod.dtree.root.application.return_value = shell
    return shell


@pytest.fixture
def mod():
    module = _import_wait_for_shell()
    _ready_shell(module)
    return module


@pytest.fixture
def quiet_mod(mod, monkeypatch):
    """``mod`` with the diagnostic snapshot stubbed out.

    Diagnostics shell out to ls/loginctl/systemctl; the polling tests patch
    ``subprocess.run`` wholesale, so leaving them live would consume the mocked
    call sequence. They have dedicated coverage in ``TestSessionDiagnostics``.
    """
    monkeypatch.setattr(mod, "collect_session_diagnostics", lambda env: "<diagnostics>")
    return mod


# ---------------------------------------------------------------------------
# Original retry contract
# ---------------------------------------------------------------------------

def test_wait_for_shell_returns_true_when_ready(quiet_mod):
    with patch.object(quiet_mod.subprocess, "run", return_value=_ready_proc()) as run_mock, \
         patch.object(quiet_mod.time, "sleep"), \
         patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
        assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True

    # Readiness must be confirmed on consecutive checks, never a single probe.
    assert run_mock.call_count == quiet_mod.DEFAULT_STABLE_CHECKS


def test_wait_for_shell_retries_on_shell_eval_failure(quiet_mod):
    run_results = [
        _proc(returncode=1, stderr="shell not ready"),
        _ready_proc(),
        _ready_proc(),
    ]

    with patch.object(quiet_mod.subprocess, "run", side_effect=run_results) as run_mock, \
         patch.object(quiet_mod.time, "sleep") as sleep_mock, \
         patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
        assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True

    assert run_mock.call_count == 3
    assert sleep_mock.call_count == 2


def test_wait_for_shell_retries_when_panel_not_visible(quiet_mod):
    shell = MagicMock()
    panel = MagicMock()
    panel.findChildren.return_value = [
        SimpleNamespace(name="Show Apps", roleName="toggle button"),
    ]
    shell.findChildren.side_effect = [[], [panel], [panel]]
    quiet_mod.dtree.root.application.return_value = shell

    with patch.object(quiet_mod.subprocess, "run", return_value=_ready_proc()) as run_mock, \
         patch.object(quiet_mod.time, "sleep") as sleep_mock, \
         patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
        assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True

    assert run_mock.call_count == 3
    assert sleep_mock.call_count == 2


def test_wait_for_shell_retries_on_exception_then_succeeds(quiet_mod):
    shell = _ready_shell(quiet_mod)
    quiet_mod.dtree.root.application.side_effect = [RuntimeError("boom"), shell, shell]

    with patch.object(quiet_mod.subprocess, "run", return_value=_ready_proc()) as run_mock, \
         patch.object(quiet_mod.time, "sleep") as sleep_mock, \
         patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
        assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True

    assert run_mock.call_count == 3
    assert sleep_mock.call_count == 2


def test_wait_for_shell_returns_false_after_budget_exhausted(quiet_mod, capsys):
    with patch.object(quiet_mod.subprocess, "run", return_value=_proc(returncode=1, stderr="no shell")), \
         patch.object(quiet_mod.time, "sleep"), \
         patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
        assert quiet_mod.wait_for_shell(timeout=0, interval=0) is False

    captured = capsys.readouterr()
    assert "ERROR: GNOME Shell readiness failed after 1 attempts" in captured.err


# ---------------------------------------------------------------------------
# classify_error
# ---------------------------------------------------------------------------

class TestClassifyError:
    def test_service_unknown(self, mod):
        assert mod.classify_error(SERVICE_UNKNOWN) == mod.ERR_SERVICE_UNKNOWN

    def test_socket_gone_is_bus_unavailable(self, mod):
        assert mod.classify_error(SOCKET_GONE) == mod.ERR_BUS_UNAVAILABLE

    def test_connection_refused_is_bus_unavailable(self, mod):
        assert mod.classify_error("Connection refused") == mod.ERR_BUS_UNAVAILABLE

    def test_enoent_is_bus_unavailable(self, mod):
        assert mod.classify_error("[Errno 2] ENOENT") == mod.ERR_BUS_UNAVAILABLE

    def test_autolaunch_failure_is_bus_unavailable(self, mod):
        """Observed in lab run testsuite-727 when no session bus socket exists."""
        assert mod.classify_error(AUTOLAUNCH_FAILED) == mod.ERR_BUS_UNAVAILABLE

    def test_unrelated_error_is_other(self, mod):
        assert mod.classify_error("kaboom") == mod.ERR_OTHER


# ---------------------------------------------------------------------------
# resolve_session_bus_env
# ---------------------------------------------------------------------------

class TestResolveSessionBusEnv:
    def test_keeps_address_when_socket_exists(self, mod):
        env = {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=True), \
             patch("os.getuid", return_value=1000):
            resolved = mod.resolve_session_bus_env(env)
        assert resolved["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/1000/bus"

    def test_rederives_address_when_socket_is_gone(self, mod):
        env = {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/stale-bus"}
        existing = {"/run/user/1000/bus"}
        with patch("os.path.exists", side_effect=lambda p: p in existing), \
             patch("os.path.isdir", return_value=True), \
             patch("os.getuid", return_value=1000):
            resolved = mod.resolve_session_bus_env(env)
        assert resolved["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/1000/bus"

    def test_keeps_canonical_path_when_no_socket_exists_yet(self, mod):
        """Never unset the address mid-restart.

        An unset ``DBUS_SESSION_BUS_ADDRESS`` makes gdbus fall back to
        ``dbus-launch --autolaunch``, which spawns/attempts a private bus the
        real session never joins (observed in lab run testsuite-727). Keeping
        the canonical socket path means the next attempt connects the moment the
        replacement session creates it.
        """
        env = {
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/stale-bus",
        }
        with patch("os.path.exists", return_value=False), \
             patch("os.path.isdir", return_value=True), \
             patch("os.getuid", return_value=1000):
            resolved = mod.resolve_session_bus_env(env)
        assert resolved["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/1000/bus"

    def test_empty_address_is_replaced_never_left_empty(self, mod):
        """An empty address is what sends GIO down the autolaunch path."""
        env = {"XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": ""}
        with patch("os.path.exists", return_value=False), \
             patch("os.path.isdir", return_value=True), \
             patch("os.getuid", return_value=1000):
            resolved = mod.resolve_session_bus_env(env)
        assert resolved["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/1000/bus"

    def test_defaults_runtime_dir_to_run_user_uid(self, mod):
        with patch("os.path.exists", return_value=False), \
             patch("os.path.isdir", return_value=True), \
             patch("os.getuid", return_value=1000):
            resolved = mod.resolve_session_bus_env({})
        assert resolved["XDG_RUNTIME_DIR"] == "/run/user/1000"


# ---------------------------------------------------------------------------
# GDM-restart tolerance
# ---------------------------------------------------------------------------

class TestGdmRestartTolerance:
    def test_retries_service_unknown_then_succeeds(self, quiet_mod):
        calls = {"n": 0}

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 5:
                return _proc(returncode=1, stderr=SERVICE_UNKNOWN)
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True
        assert calls["n"] == 7  # 5 failures + 2 stable confirmations

    def test_bus_unavailable_never_terminates_early(self, quiet_mod):
        """Socket-gone must be retryable, not fatal."""
        calls = {"n": 0}

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 10:
                return _proc(returncode=1, stderr=SOCKET_GONE)
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True
        assert calls["n"] == 12

    def test_socket_gone_recovers_after_bus_address_is_reresolved(self, quiet_mod):
        """The bus socket dies with GDM and a NEW one appears.

        Only a re-resolved address can reach the replacement session; an address
        cached before the restart names a destroyed socket forever.
        """
        state = {"resolves": 0, "current_socket": "/run/user/1000/bus-old"}
        existing_sockets = {"/run/user/1000/bus-new"}

        def fake_resolve(base_env=None):
            state["resolves"] += 1
            if state["resolves"] == 4:
                # GDM finished restarting: the new session publishes a new socket.
                state["current_socket"] = "/run/user/1000/bus-new"
            return {"DBUS_SESSION_BUS_ADDRESS": f"unix:path={state['current_socket']}"}

        def fake_run(*args, **kwargs):
            env = kwargs.get("env") or {}
            if env.get("DBUS_SESSION_BUS_ADDRESS") != "unix:path=/run/user/1000/bus-new":
                return _proc(returncode=1, stderr=SOCKET_GONE)
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch("os.path.exists", side_effect=lambda p: p in existing_sockets), \
             patch.object(quiet_mod, "resolve_session_bus_env", side_effect=fake_resolve):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True
        assert state["resolves"] >= 4

    def test_missing_socket_short_circuits_before_spawning_gdbus(self, quiet_mod):
        """No socket means no gdbus call — that is the autolaunch trapdoor.

        With no reachable address GIO falls back to
        ``dbus-launch --autolaunch``, which cannot work in the test container
        and hides its own failure behind ``--close-stderr``.
        """
        calls = {"n": 0}

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch("os.path.exists", return_value=False), \
             patch.object(
                 quiet_mod,
                 "resolve_session_bus_env",
                 return_value={"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
             ):
            assert quiet_mod.wait_for_shell(timeout=0, interval=0) is False

        assert calls["n"] == 0

    def test_requires_stable_consecutive_checks(self, quiet_mod):
        """A single good check must not win: the old session can vanish."""
        outcomes = [
            _ready_proc(),                                # old session, about to die
            _proc(returncode=1, stderr=SOCKET_GONE),      # GDM restart
            _proc(returncode=1, stderr=SERVICE_UNKNOWN),  # new session starting
            _ready_proc(),
            _ready_proc(),
        ]

        with patch.object(quiet_mod.subprocess, "run", side_effect=lambda *a, **k: outcomes.pop(0)), \
             patch.object(quiet_mod.time, "sleep"), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0, stable_checks=2) is True
        assert not outcomes

    def test_unsuccessful_shell_eval_tuple_is_not_ready(self, quiet_mod):
        """Return code 0 with a ``(false, ...)`` Shell.Eval tuple is NOT ready."""
        calls = {"n": 0}

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 3:
                return _proc(returncode=0, stdout="(false, '')")
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True
        assert calls["n"] == 5

    def test_oserror_from_subprocess_is_retryable(self, quiet_mod):
        calls = {"n": 0}

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise OSError(2, "No such file or directory")
            return _ready_proc()

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "sleep"), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=20, interval=0) is True

    def test_timeout_is_bounded_and_message_names_error_classes(self, quiet_mod, capsys):
        clock = {"t": 0.0}
        outcomes = []

        def fake_run(*args, **kwargs):
            outcomes.append(1)
            if len(outcomes) <= 14:
                return _proc(returncode=1, stderr=SERVICE_UNKNOWN)
            return _proc(returncode=1, stderr=SOCKET_GONE)

        with patch.object(quiet_mod.subprocess, "run", side_effect=fake_run), \
             patch.object(quiet_mod.time, "monotonic", side_effect=lambda: clock["t"]), \
             patch.object(quiet_mod.time, "sleep", side_effect=lambda s: clock.__setitem__("t", clock["t"] + max(s, 2.0))), \
             patch.object(quiet_mod, "resolve_session_bus_env", return_value={}):
            assert quiet_mod.wait_for_shell(timeout=60, interval=2) is False

        # Bounded deadline: 60s budget polled every 2s.
        assert clock["t"] <= 62
        assert len(outcomes) <= 32

        message = capsys.readouterr().err
        assert quiet_mod.ERR_SERVICE_UNKNOWN in message
        assert quiet_mod.ERR_BUS_UNAVAILABLE in message
        assert "=14" in message
        assert "Last error:" in message
        assert "No such file or directory" in message


# ---------------------------------------------------------------------------
# Session diagnostics
# ---------------------------------------------------------------------------

class TestSessionDiagnostics:
    ENV = {
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }

    def test_reports_socket_presence_and_probe_output(self, mod):
        def fake_run(argv, **kwargs):
            return _proc(stdout=f"output of {argv[0]}")

        with patch.object(mod.subprocess, "run", side_effect=fake_run), \
             patch("os.path.exists", return_value=True):
            report = mod.collect_session_diagnostics(self.ENV)

        assert "socket /run/user/1000/bus exists=True" in report
        assert "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" in report
        for probe in ("ls -la runtime dir", "loginctl list-sessions", "systemctl status gdm"):
            assert probe in report

    def test_reports_missing_socket(self, mod):
        with patch.object(mod.subprocess, "run", return_value=_proc(stdout="")), \
             patch("os.path.exists", return_value=False):
            report = mod.collect_session_diagnostics(self.ENV)
        assert "exists=False" in report

    def test_probe_failure_does_not_raise(self, mod):
        with patch.object(mod.subprocess, "run", side_effect=OSError("no loginctl")), \
             patch("os.path.exists", return_value=True):
            report = mod.collect_session_diagnostics(self.ENV)
        assert "probe failed" in report

    def test_diagnostics_emitted_on_first_failure_and_every_nth(self, mod, capsys):
        snapshots = []

        with patch.object(mod.subprocess, "run", return_value=_proc(returncode=1, stderr=SERVICE_UNKNOWN)), \
             patch.object(mod.time, "sleep"), \
             patch.object(mod, "collect_session_diagnostics", side_effect=lambda env: snapshots.append(env) or "<diag>"), \
             patch.object(mod, "resolve_session_bus_env", return_value={}):
            clock = {"t": 0.0}
            with patch.object(mod.time, "monotonic", side_effect=lambda: clock["t"]), \
                 patch.object(mod.time, "sleep", side_effect=lambda s: clock.__setitem__("t", clock["t"] + 2.0)):
                assert mod.wait_for_shell(timeout=20, interval=2, diagnostic_every=5) is False

        # 11 failing attempts over a 20s budget: snapshots on failures 1, 5 and
        # 10, plus the final one printed with the timeout summary.
        assert len(snapshots) == 4
        output = capsys.readouterr()
        assert "Session diagnostics (attempt 1)" in output.out
        assert "Final session diagnostics" in output.err
        assert "not a bug in this helper" in output.err

    def test_diagnostics_can_be_disabled(self, mod, capsys):
        with patch.object(mod.subprocess, "run", return_value=_proc(returncode=1, stderr=SERVICE_UNKNOWN)), \
             patch.object(mod.time, "sleep"), \
             patch.object(mod, "collect_session_diagnostics", return_value="<diag>") as diag, \
             patch.object(mod, "resolve_session_bus_env", return_value={}):
            assert mod.wait_for_shell(timeout=0, interval=0, diagnostic_every=0) is False

        # Only the final snapshot; no per-attempt noise.
        assert diag.call_count == 1
        assert "Session diagnostics (attempt" not in capsys.readouterr().out
