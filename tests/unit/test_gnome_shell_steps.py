"""Unit tests for tests/shared/gnome_shell_steps.py.

Tests _eval_bool, _wait_eval_bool, and _shell_eval using subprocess mocks.
These functions parse Shell.Eval output and drive boolean assertions in
the smoke and vanilla-gnome suites.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to avoid importing the full behave/dogtail stack
# ---------------------------------------------------------------------------

def _import_gnome_shell_steps():
    """Import the module under test, skipping behave decorator registration."""
    import importlib
    import sys

    # Stub out behave.step so @step decorators don't explode without a running
    # behave context.
    behave_stub = MagicMock()
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules.setdefault("behave", behave_stub)
    sys.modules.setdefault("behave.runner", MagicMock())

    # Force reimport from the real path
    if "tests.shared.gnome_shell_steps" in sys.modules:
        del sys.modules["tests.shared.gnome_shell_steps"]

    import tests.shared.gnome_shell_steps as m
    return m


# ---------------------------------------------------------------------------
# _shell_eval
# ---------------------------------------------------------------------------

class TestShellEval:
    def setup_method(self):
        self.mod = _import_gnome_shell_steps()

    def _make_completed(self, stdout="", stderr="", returncode=0):
        proc = MagicMock()
        proc.stdout = stdout
        proc.stderr = stderr
        proc.returncode = returncode
        return proc

    def test_returns_stdout_on_success(self):
        proc = self._make_completed(stdout="(true, 'true')\n")
        with patch("subprocess.run", return_value=proc):
            result = self.mod._shell_eval("Main.overview.visible")
        assert result == "(true, 'true')\n"

    def test_raises_on_nonzero_returncode(self):
        proc = self._make_completed(returncode=1, stderr="DBus error")
        with patch("subprocess.run", return_value=proc):
            with pytest.raises(AssertionError, match="Shell.Eval failed"):
                self.mod._shell_eval("bad.js")

    def test_passes_js_to_subprocess(self):
        proc = self._make_completed(stdout="(true, 'true')\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod._shell_eval("Main.overview.visible")
        call_args = mock_run.call_args[0][0]
        assert "Main.overview.visible" in call_args

    def test_uses_gdbus_call(self):
        proc = self._make_completed(stdout="(true, 'true')\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            self.mod._shell_eval("x")
        call_args = mock_run.call_args[0][0]
        assert "gdbus" in call_args[0]
        assert "org.gnome.Shell" in call_args


# ---------------------------------------------------------------------------
# _eval_bool
# ---------------------------------------------------------------------------

class TestEvalBool:
    def setup_method(self):
        self.mod = _import_gnome_shell_steps()

    def _patch_shell_eval(self, stdout):
        return patch.object(self.mod, "_shell_eval", return_value=stdout)

    def test_true_quoted(self):
        with self._patch_shell_eval("(true, 'true')\n"):
            assert self.mod._eval_bool("x") is True

    def test_false_quoted(self):
        with self._patch_shell_eval("(true, 'false')\n"):
            assert self.mod._eval_bool("x") is False

    def test_case_insensitive_true(self):
        with self._patch_shell_eval("(true, 'True')\n"):
            assert self.mod._eval_bool("x") is True

    def test_raises_on_unparseable_output(self):
        with self._patch_shell_eval("unexpected garbage\n"):
            with pytest.raises(AssertionError, match="Could not parse boolean"):
                self.mod._eval_bool("x")

    def test_raises_on_empty_output(self):
        with self._patch_shell_eval(""):
            with pytest.raises(AssertionError, match="Could not parse boolean"):
                self.mod._eval_bool("x")


# ---------------------------------------------------------------------------
# _wait_eval_bool
# ---------------------------------------------------------------------------

class TestWaitEvalBool:
    def setup_method(self):
        self.mod = _import_gnome_shell_steps()

    def test_returns_true_immediately_when_value_matches(self):
        with patch.object(self.mod, "_eval_bool", return_value=True):
            with patch("time.sleep"):
                assert self.mod._wait_eval_bool("x", True, retries=3) is True

    def test_retries_until_match(self):
        side_effects = [False, False, True]
        call_count = {"n": 0}

        def _mock_eval_bool(js):
            val = side_effects[call_count["n"]]
            call_count["n"] += 1
            return val

        with patch.object(self.mod, "_eval_bool", side_effect=_mock_eval_bool):
            with patch("time.sleep"):
                result = self.mod._wait_eval_bool("x", True, retries=5)
        assert result is True
        assert call_count["n"] == 3

    def test_returns_false_when_retries_exhausted(self):
        with patch.object(self.mod, "_eval_bool", return_value=False):
            with patch("time.sleep"):
                assert self.mod._wait_eval_bool("x", True, retries=3) is False

    def test_tolerates_assertion_errors_during_retries(self):
        side_effects = [AssertionError("parse error"), AssertionError("parse error"), True]

        def _mock_eval_bool(js):
            val = side_effects.pop(0)
            if isinstance(val, Exception):
                raise val
            return val

        with patch.object(self.mod, "_eval_bool", side_effect=_mock_eval_bool):
            with patch("time.sleep"):
                result = self.mod._wait_eval_bool("x", True, retries=5)
        assert result is True

    def test_matching_false_value(self):
        with patch.object(self.mod, "_eval_bool", return_value=False):
            with patch("time.sleep"):
                assert self.mod._wait_eval_bool("x", False, retries=3) is True
