"""Unit tests for tests/shared/wait_for_shell.py."""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


MODULE_NAME = "tests.shared.wait_for_shell"


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


def test_wait_for_shell_returns_true_when_ready():
    mod = _import_wait_for_shell()
    _ready_shell(mod)

    with patch.object(mod.subprocess, "run", return_value=_proc(stdout="(true, 'true')")) as run_mock:
        with patch.object(mod.time, "sleep") as sleep_mock:
            assert mod.wait_for_shell(attempts=1, sleep_time=0) is True

    run_mock.assert_called_once()
    sleep_mock.assert_not_called()


def test_wait_for_shell_retries_on_shell_eval_failure():
    mod = _import_wait_for_shell()
    _ready_shell(mod)
    run_results = [
        _proc(returncode=1, stderr="shell not ready"),
        _proc(stdout="(true, 'true')"),
    ]

    with patch.object(mod.subprocess, "run", side_effect=run_results) as run_mock:
        with patch.object(mod.time, "sleep") as sleep_mock:
            assert mod.wait_for_shell(attempts=2, sleep_time=0) is True

    assert run_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_wait_for_shell_retries_when_eval_tuple_is_unsuccessful():
    """Exit code 0 is not enough — gdbus returns 0 for a failed Shell.Eval."""
    mod = _import_wait_for_shell()
    _ready_shell(mod)
    run_results = [
        _proc(returncode=0, stdout="(false, '')"),
        _proc(returncode=0, stdout="(true, 'true')"),
    ]

    with patch.object(mod.subprocess, "run", side_effect=run_results) as run_mock:
        with patch.object(mod.time, "sleep") as sleep_mock:
            assert mod.wait_for_shell(attempts=2, sleep_time=0) is True

    assert run_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_wait_for_shell_fails_when_eval_tuple_never_succeeds(capsys):
    """A permanently unsuccessful Shell.Eval must not be reported as ready."""
    mod = _import_wait_for_shell()
    _ready_shell(mod)

    with patch.object(mod.subprocess, "run", return_value=_proc(returncode=0, stdout="(false, '')")):
        with patch.object(mod.time, "sleep"):
            assert mod.wait_for_shell(attempts=2, sleep_time=0) is False

    assert "Shell.Eval not ready" in capsys.readouterr().out


def test_wait_for_shell_retries_when_panel_not_visible():
    mod = _import_wait_for_shell()
    shell = MagicMock()
    panel = MagicMock()
    panel.findChildren.return_value = [
        SimpleNamespace(name="Show Apps", roleName="toggle button"),
    ]
    shell.findChildren.side_effect = [[], [panel]]
    mod.dtree.root.application.return_value = shell

    with patch.object(mod.subprocess, "run", return_value=_proc(stdout="(true, 'true')")) as run_mock:
        with patch.object(mod.time, "sleep") as sleep_mock:
            assert mod.wait_for_shell(attempts=2, sleep_time=0) is True

    assert run_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_wait_for_shell_retries_on_exception_then_succeeds():
    mod = _import_wait_for_shell()
    shell = _ready_shell(mod)
    mod.dtree.root.application.side_effect = [RuntimeError("boom"), shell]

    with patch.object(mod.subprocess, "run", return_value=_proc(stdout="(true, 'true')")) as run_mock:
        with patch.object(mod.time, "sleep") as sleep_mock:
            assert mod.wait_for_shell(attempts=2, sleep_time=0) is True

    assert run_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_wait_for_shell_returns_false_after_retries_exhausted(capsys):
    mod = _import_wait_for_shell()

    with patch.object(mod.subprocess, "run", return_value=_proc(returncode=1, stderr="no shell")):
        with patch.object(mod.time, "sleep"):
            assert mod.wait_for_shell(attempts=1, sleep_time=0) is False

    captured = capsys.readouterr()
    assert "ERROR: GNOME Shell AT-SPI readiness failed after 1 attempts" in captured.err
