"""Unit tests for tests/shared/self.mod.py.

Mocks SSH and subprocess so no live KDE VM is required. Covers happy paths,
capability failures, D-Bus errors, malformed output, and polling behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
import base64
import subprocess
from unittest import mock


# ---------------------------------------------------------------------------
# Helpers to avoid importing the full behave stack
# ---------------------------------------------------------------------------


def _import_kde_shell_steps():
    """Import the module under test, stubbing behave for ssh_steps."""
    import sys

    # ssh_steps imports behave.step; stub it so import works without a runner.
    behave_stub = MagicMock()
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules.setdefault("behave", behave_stub)
    sys.modules.setdefault("behave.runner", MagicMock())

    if "tests.shared.kde_shell_steps" in sys.modules:
        del sys.modules["tests.shared.kde_shell_steps"]
    if "tests.shared.ssh_steps" in sys.modules:
        del sys.modules["tests.shared.ssh_steps"]

    import tests.shared.kde_shell_steps as m
    return m


def _make_context():
    """Return a behave-like context with SSH attributes."""
    context = MagicMock()
    context.ssh_key = "/key"
    context.ssh_user = "u"
    context.vm_ip = "1.2.3.4"
    context.ssh_port = "22"
    context.ssh_command_prefix = ""
    context.last_ssh_result = None
    return context


def _make_completed(stdout="", stderr="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ---------------------------------------------------------------------------
# _dbus_call dispatch
# ---------------------------------------------------------------------------


class TestDbusCall:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def test_uses_subprocess_locally(self):
        proc = _make_completed(stdout="ok\n", returncode=0)
        with patch.object(self.mod, "_IN_CONTAINER", False), \
             patch("subprocess.run", return_value=proc) as mock_run:
            stdout, rc = self.mod._dbus_call(
                self.context, "org.kde.KWin", "/KWin", "org.kde.KWin",
                "supportInformation"
            )
        assert stdout == "ok\n"
        assert rc == 0
        argv = mock_run.call_args[0][0]
        assert argv[0] == "gdbus"
        assert "org.kde.KWin" in argv

    def test_uses_ssh_in_container(self):
        with patch.object(self.mod, "_IN_CONTAINER", True), \
             patch.object(self.mod, "run_ssh", return_value=("ok\n", 0)) as mock_ssh:
            stdout, rc = self.mod._dbus_call(
                self.context, "org.kde.KWin", "/KWin", "org.kde.KWin",
                "supportInformation"
            )
        assert stdout == "ok\n"
        assert rc == 0
        cmd = mock_ssh.call_args[0][1]
        assert "gdbus" in cmd
        assert "source /tmp/session.env" in cmd


# ---------------------------------------------------------------------------
# wait_until
# ---------------------------------------------------------------------------


class TestWaitUntil:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()

    def test_returns_immediately_when_predicate_true(self):
        with patch("time.sleep"):
            assert self.mod.wait_until(lambda: "yes", timeout=1.0) == "yes"

    def test_succeeds_on_later_poll(self):
        calls = {"n": 0}

        def predicate():
            calls["n"] += 1
            return calls["n"] == 3

        with patch("time.sleep"):
            result = self.mod.wait_until(predicate, timeout=1.0, interval=0.1)
        assert result is True
        assert calls["n"] == 3

    def test_raises_timeout_when_exhausted(self):
        with patch("time.sleep"):
            with pytest.raises(TimeoutError, match="did not become true"):
                self.mod.wait_until(lambda: False, timeout=0.05, interval=0.01)

    def test_backoff_increases_interval(self):
        sleeps = []
        with patch("time.sleep", side_effect=sleeps.append):
            calls = {"n": 0}

            def predicate():
                calls["n"] += 1
                return calls["n"] == 4

            self.mod.wait_until(predicate, timeout=1.0, interval=0.5)
        # 0.5 -> 0.75 -> 1.125 before success.
        assert len(sleeps) == 3
        assert sleeps[0] == 0.5
        assert sleeps[1] == 0.75


# ---------------------------------------------------------------------------
# plasma_eval
# ---------------------------------------------------------------------------


class TestPlasmaEval:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def _patch_dbus_call(self, stdout="", rc=0, stderr=""):
        def _fake(context, service, path, interface, method, args=(), timeout=30):
            return stdout, rc

        patcher = patch.object(self.mod, "_dbus_call", side_effect=_fake)
        self.context.last_ssh_result = _make_completed(stderr=stderr, returncode=rc)
        return patcher

    def test_returns_stdout_on_success(self):
        with self._patch_dbus_call(stdout="(true, 'hello')\n", rc=0):
            assert self.mod.plasma_eval(self.context, "1+1") == "(true, 'hello')\n"

    def test_raises_plasma_scripting_disabled_for_widgets_locked(self):
        stderr = "Error: GDBus.Error:org.freedesktop.DBus.Error.AccessDenied: Widgets are locked"
        with self._patch_dbus_call(stdout="", rc=1, stderr=stderr):
            with pytest.raises(self.mod.PlasmaScriptingDisabledError):
                self.mod.plasma_eval(self.context, "1+1")

    def test_raises_plasma_scripting_disabled_for_kauthorized(self):
        stderr = "KAuthorized policy forbids plasma-desktop/scripting_console"
        with self._patch_dbus_call(stdout="", rc=1, stderr=stderr):
            with pytest.raises(self.mod.PlasmaScriptingDisabledError):
                self.mod.plasma_eval(self.context, "1+1")

    def test_raises_capability_error_for_missing_service(self):
        with self._patch_dbus_call(stdout="", rc=1, stderr="Service unknown"):
            with pytest.raises(self.mod.DbusCapabilityError, match="plasma_eval failed"):
                self.mod.plasma_eval(self.context, "1+1")

    def test_passes_script_as_argument(self):
        with self._patch_dbus_call(stdout="ok", rc=0) as mock_call:
            self.mod.plasma_eval(self.context, "dump()")
        kwargs = mock_call.call_args_list[0].kwargs
        assert kwargs["args"] == ("dump()",)


# ---------------------------------------------------------------------------
# dump_layout_js
# ---------------------------------------------------------------------------


class TestDumpLayoutJs:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def test_returns_layout_dump(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("var layout = {}", 0)
        ):
            assert self.mod.dump_layout_js(self.context) == "var layout = {}"

    def test_raises_on_failure(self):
        self.context.last_ssh_result = _make_completed(stderr="boom", returncode=1)
        with patch.object(
            self.mod, "_dbus_call", return_value=("", 1)
        ):
            with pytest.raises(self.mod.DbusCapabilityError, match="dumpCurrentLayoutJS failed"):
                self.mod.dump_layout_js(self.context)


# ---------------------------------------------------------------------------
# kwin_support_info
# ---------------------------------------------------------------------------


class TestKwinSupportInfo:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def test_returns_support_text(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("KWin support info", 0)
        ):
            assert self.mod.kwin_support_info(self.context) == "KWin support info"

    def test_raises_on_failure(self):
        self.context.last_ssh_result = _make_completed(stderr="no kwin", returncode=1)
        with patch.object(
            self.mod, "_dbus_call", return_value=("", 1)
        ):
            with pytest.raises(self.mod.DbusCapabilityError, match="kwin_support_info failed"):
                self.mod.kwin_support_info(self.context)


# ---------------------------------------------------------------------------
# plasma_available / kwin_available
# ---------------------------------------------------------------------------


class TestAvailabilityProbes:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def test_plasma_available_true(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("<interface name='org.kde.PlasmaShell'>", 0)
        ):
            assert self.mod.plasma_available(self.context) is True

    def test_plasma_available_false_when_no_service(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("", 1)
        ):
            assert self.mod.plasma_available(self.context) is False

    def test_plasma_available_false_when_no_interfaces(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("<node></node>", 0)
        ):
            assert self.mod.plasma_available(self.context) is False

    def test_kwin_available_true(self):
        with patch.object(
            self.mod, "_dbus_call", return_value=("<interface name='org.kde.KWin'>", 0)
        ):
            assert self.mod.kwin_available(self.context) is True


# ---------------------------------------------------------------------------
# kwin_script
# ---------------------------------------------------------------------------


class TestKwinScript:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()
        self.script_source = "print('hello')"

    def _mock_dbus_for_script(self, load_rc=0, start_rc=0, loaded_states=None):
        """Return a side_effect for _dbus_call that simulates a script run."""
        loaded_states = loaded_states or ["true", "false"]
        loaded_iter = iter(loaded_states)

        def _fake(context, service, path, interface, method, args=(), timeout=30):
            if method == "loadScript":
                return "(int32 1,)", load_rc
            if method == "start":
                return "", start_rc
            if method == "isScriptLoaded":
                return f"(boolean {next(loaded_iter)},)", 0
            if method == "unloadScript":
                return "", 0
            return "", 0

        return _fake

    def _patch_uuid(self):
        uuid_value = MagicMock()
        uuid_value.hex = "deadbeef"
        return patch.object(
            self.mod, "uuid", MagicMock(uuid4=MagicMock(return_value=uuid_value))
        )

    def test_happy_path_loads_starts_unloads_and_returns_output(self):
        with patch.object(self.mod, "_dbus_call", side_effect=self._mock_dbus_for_script()) as mock_call, \
             patch.object(self.mod, "_journal_output", return_value="hello") as mock_journal, \
             patch.object(self.mod, "_write_target_file") as mock_write, \
             patch.object(self.mod, "_remove_target_file") as mock_remove, \
             self._patch_uuid():
            result = self.mod.kwin_script(self.context, self.script_source)

        assert result == "hello"
        methods = [c.args[4] for c in mock_call.call_args_list]
        assert methods == ["loadScript", "start", "isScriptLoaded", "isScriptLoaded", "unloadScript"]
        mock_journal.assert_called_once_with(self.context, "testsuite_deadbeef")
        mock_remove.assert_called_once()
        mock_write.assert_called_once()

    def test_cleanup_runs_when_script_body_raises(self):
        with patch.object(self.mod, "_dbus_call", side_effect=RuntimeError("boom")), \
             patch.object(self.mod, "_write_target_file") as mock_write, \
             patch.object(self.mod, "_remove_target_file") as mock_remove, \
             pytest.raises(RuntimeError, match="boom"):
            self.mod.kwin_script(self.context, self.script_source)
        mock_remove.assert_called_once()
        mock_write.assert_called_once()

    def test_unload_attempted_even_when_remove_fails(self):
        with patch.object(self.mod, "_dbus_call", side_effect=self._mock_dbus_for_script()) as mock_call, \
             patch.object(self.mod, "_journal_output", return_value=""), \
             patch.object(self.mod, "_write_target_file"), \
             patch.object(self.mod, "_remove_target_file", side_effect=OSError("rm failed")):
            self.mod.kwin_script(self.context, self.script_source)

        methods = [c.args[4] for c in mock_call.call_args_list]
        assert "unloadScript" in methods

    def test_raises_when_loadscript_fails(self):
        with patch.object(
            self.mod, "_dbus_call", side_effect=self._mock_dbus_for_script(load_rc=1)
        ), \
             patch.object(self.mod, "_write_target_file"), \
             patch.object(self.mod, "_remove_target_file") as mock_remove, \
             pytest.raises(self.mod.DbusCapabilityError, match="loadScript failed"):
            self.mod.kwin_script(self.context, self.script_source)
        mock_remove.assert_called_once()

    def test_raises_when_start_fails(self):
        with patch.object(
            self.mod, "_dbus_call", side_effect=self._mock_dbus_for_script(start_rc=1)
        ), \
             patch.object(self.mod, "_write_target_file"), \
             patch.object(self.mod, "_remove_target_file") as mock_remove, \
             pytest.raises(self.mod.DbusCapabilityError, match="start failed"):
            self.mod.kwin_script(self.context, self.script_source)
        mock_remove.assert_called_once()

    def test_raises_when_script_never_finishes(self):
        with patch.object(
            self.mod,
            "_dbus_call",
            side_effect=self._mock_dbus_for_script(loaded_states=["true", "true", "true"]),
        ), \
             patch.object(self.mod, "_write_target_file"), \
             patch.object(self.mod, "_remove_target_file") as mock_remove, \
             pytest.raises(self.mod.DbusCapabilityError, match="did not finish"):
            self.mod.kwin_script(self.context, self.script_source, timeout=0.1)
        mock_remove.assert_called_once()


# ---------------------------------------------------------------------------
# _journal_output
# ---------------------------------------------------------------------------


class TestJournalOutput:
    def setup_method(self):
        self.mod = _import_kde_shell_steps()
        self.context = _make_context()

    def test_filters_script_print_output(self):
        journal = (
            "kwin_scripting: testsuite_abc: js: testsuite_abc: hello\n"
            "kwin_scripting: testsuite_abc: js: testsuite_abc: world\n"
            "kwin_scripting: other: js: other: ignored\n"
        )
        with patch.object(self.mod, "_IN_CONTAINER", True), \
             patch.object(self.mod, "run_ssh", return_value=(journal, 0)):
            result = self.mod._journal_output(self.context, "testsuite_abc")
        assert result == "hello\nworld"

    def test_returns_empty_when_no_js_lines(self):
        with patch.object(self.mod, "_IN_CONTAINER", False), \
             patch("subprocess.run", return_value=_make_completed(stdout="noise\n")):
            result = self.mod._journal_output(self.context, "testsuite_abc")
        assert result == ""

    def test_handles_local_subprocess(self):
        journal = "js: testsuite_xyz: result\n"
        with patch.object(self.mod, "_IN_CONTAINER", False), \
             patch("subprocess.run", return_value=_make_completed(stdout=journal)):
            result = self.mod._journal_output(self.context, "testsuite_xyz")
        assert result == "result"


class TestReviewFixes:
    """Regression tests for issues found in code review of PR #642."""

    @pytest.fixture(autouse=True)
    def _mod(self):
        self.mod = _import_kde_shell_steps()
        yield

    def test_local_dbus_call_preserves_stderr(self):
        """gdbus reports policy refusals on stderr; dropping it misclassified them."""
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Widgets are locked"
        )
        with mock.patch.object(self.mod, "_IN_CONTAINER", False):
            with mock.patch.object(subprocess, "run", return_value=completed):
                out, rc = self.mod._dbus_call(
                    None, "org.kde.plasmashell", "/PlasmaShell",
                    "org.kde.PlasmaShell", "evaluateScript", ["x"],
                )
        assert "Widgets are locked" in out
        assert rc == 1

    def test_script_containing_heredoc_delimiter_cannot_inject(self):
        """A script line equal to the old heredoc delimiter must not escape."""
        malicious = "print('a')\nEOF\nrm -rf /tmp/pwned\n"
        sent = {}

        def fake_run_ssh(context, cmd, **kwargs):
            sent["cmd"] = cmd
            return "", 0

        with mock.patch.object(self.mod, "_IN_CONTAINER", True):
            with mock.patch.object(self.mod, "run_ssh", fake_run_ssh):
                self.mod._write_target_file(None, "/tmp/s.js", malicious)

        cmd = sent["cmd"]
        assert "rm -rf" not in cmd, "raw script text must not reach the shell"
        assert "base64 -d" in cmd
        assert base64.b64encode(malicious.encode()).decode() in cmd

    def test_journal_read_is_bounded(self):
        sent = {}

        def fake_run_ssh(context, cmd, **kwargs):
            sent["cmd"] = cmd
            return "", 0

        with mock.patch.object(self.mod, "_IN_CONTAINER", True):
            with mock.patch.object(self.mod, "run_ssh", fake_run_ssh):
                self.mod._journal_output(None, "probe", timeout=5)

        assert f"-n {self.mod._JOURNAL_MAX_LINES}" in sent["cmd"]
        assert f"head -c {self.mod._JOURNAL_MAX_BYTES}" in sent["cmd"]
