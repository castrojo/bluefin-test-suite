"""Unit tests for tests/smoke/features/steps/printing_steps.py.

Tests focus on pure helpers that do not need a live CUPS scheduler:
- _parse_job_id(): lp stdout parsing
- _run_host(): container vs direct routing
- _IN_CONTAINER: detection constant
"""
import os
import sys
import types
from unittest.mock import MagicMock, patch


def _import_steps(in_container: bool = False):
    """Import printing_steps.py with all GNOME dependencies stubbed out."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    for key in list(sys.modules):
        if "printing_steps" in key:
            del sys.modules[key]

    with patch.dict(os.environ, {}, clear=False):
        with patch("os.path.lexists", return_value=in_container), \
             patch("os.path.isfile", return_value=not in_container):
            import tests.smoke.features.steps.printing_steps as m  # noqa: PLC0415
    return m


class TestInContainer:
    def test_false_outside_container(self):
        m = _import_steps(in_container=False)
        assert m._IN_CONTAINER is False

    def test_true_inside_container(self):
        m = _import_steps(in_container=True)
        assert m._IN_CONTAINER is True


class TestParseJobId:
    def test_standard_request_id_format(self):
        m = _import_steps()
        assert m._parse_job_id("request id is smokeprint-1 (1 file(s))") == "smokeprint-1"

    def test_name_hyphen_number_fallback(self):
        m = _import_steps()
        assert m._parse_job_id("queued job printer-42") == "printer-42"

    def test_returns_none_when_no_id_present(self):
        m = _import_steps()
        assert m._parse_job_id("scheduler is running") is None

    def test_empty_string_returns_none(self):
        m = _import_steps()
        assert m._parse_job_id("") is None


class TestRunHost:
    def test_uses_ssh_when_in_container(self):
        m = _import_steps(in_container=True)
        m._IN_CONTAINER = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="output\n", returncode=0, stderr="")
            stdout, rc, stderr = m._run_host("echo hi")
        call_args = mock_run.call_args[0][0]
        assert "ssh" in call_args[0]
        assert stdout == "output"
        assert rc == 0
        assert stderr == ""

    def test_uses_shell_when_not_in_container(self):
        m = _import_steps(in_container=False)
        m._IN_CONTAINER = False
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="hello\n", returncode=0, stderr="")
            stdout, rc, stderr = m._run_host("echo hi")
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("shell") is True
        assert stdout == "hello"
        assert rc == 0
        assert stderr == ""
