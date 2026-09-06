"""Unit tests for tests/developer/features/steps/bctl_steps.py.

The module drives ptyxis through dogtail inside a live desktop session, so
``behave``, ``dogtail.rawinput`` and ``qecore.common_steps`` are stubbed.
Coverage targets the terminal-delta computation, the marker polling loop
(match, mid-buffer match, timeout) and every bctl assertion step.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_bctl_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    dogtail_stub = types.ModuleType("dogtail")
    rawinput_stub = types.ModuleType("dogtail.rawinput")
    rawinput_stub.pressKey = MagicMock()
    rawinput_stub.typeText = MagicMock()
    dogtail_stub.rawinput = rawinput_stub
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.rawinput"] = rawinput_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    sys.modules.pop("tests.developer.features.steps.bctl_steps", None)

    import tests.developer.features.steps.bctl_steps as m  # noqa: PLC0415
    return m


@pytest.fixture
def mod():
    return _import_bctl_steps()


def _context_with_terminal(text=""):
    terminal = MagicMock()
    terminal.text = text
    context = MagicMock()
    context.ptyxis.instance.child.return_value = terminal
    return context, terminal


class TestTerminalWidget:
    def test_selects_the_terminal_role_child(self, mod):
        context, terminal = _context_with_terminal("hello")

        assert mod._terminal_widget(context) is terminal
        context.ptyxis.instance.child.assert_called_once_with(roleName="terminal")


class TestTerminalDelta:
    def test_returns_suffix_when_current_extends_previous(self, mod):
        assert mod._terminal_delta("$ ", "$ bctl --help\n") == "bctl --help\n"

    def test_returns_full_text_when_buffer_scrolled(self, mod):
        assert mod._terminal_delta("old prompt", "scrolled") == "scrolled"

    def test_returns_empty_when_unchanged(self, mod):
        assert mod._terminal_delta("same", "same") == ""


class TestWaitForCommandResult:
    def test_returns_output_and_exit_code_on_first_poll(self, mod):
        context, _ = _context_with_terminal("$ bctl version\nbctl 1.2.3\n__M__:0\n")

        with patch.object(mod, "monotonic", side_effect=[0, 1]):
            assert mod._wait_for_command_result(context, "__M__", "$ ") == (
                "bctl version\nbctl 1.2.3",
                0,
            )

    def test_polls_until_marker_appears(self, mod):
        terminal = MagicMock()
        type(terminal).text = property(
            lambda self: next(self._texts)  # noqa: SLF001
        )
        terminal._texts = iter(["$ ", "$ out\n", "$ out\n__M__:1\n"])
        context = MagicMock()
        context.ptyxis.instance.child.return_value = terminal

        with (
            patch.object(mod, "monotonic", side_effect=[0, 1, 2, 3]),
            patch.object(mod, "sleep") as sleep,
        ):
            assert mod._wait_for_command_result(context, "__M__", "$ ") == ("out", 1)

        assert sleep.call_count == 2

    def test_escapes_regex_metacharacters_in_marker(self, mod):
        context, _ = _context_with_terminal("$ x.y:7\n")

        with patch.object(mod, "monotonic", side_effect=[0, 1]):
            assert mod._wait_for_command_result(context, "x.y", "$ ") == ("", 7)

    def test_raises_after_timeout(self, mod):
        context, _ = _context_with_terminal("$ no marker here")

        with (
            patch.object(mod, "monotonic", side_effect=[0, 1, mod.COMMAND_TIMEOUT_SECONDS + 1]),
            patch.object(mod, "sleep"),
        ):
            with pytest.raises(AssertionError, match="Timed out waiting for terminal output"):
                mod._wait_for_command_result(context, "__M__", "$ ")


class TestRunBctlCommandInPtyxis:
    def test_types_command_with_marker_and_records_result(self, mod):
        context, _ = _context_with_terminal("$ ")

        with (
            patch.object(mod, "_wait_for_command_result", return_value=("out", 3)) as wait,
            patch.object(mod, "typeText") as type_text,
            patch.object(mod, "pressKey") as press_key,
        ):
            mod.run_bctl_command_in_ptyxis(context, "bctl status")

        typed = type_text.call_args[0][0]
        assert typed.startswith("bctl status; printf ")
        assert "__BCTL_EXIT_" in typed
        press_key.assert_called_once_with("Return")

        marker = wait.call_args[0][1]
        assert marker in typed
        assert wait.call_args[0][2] == "$ "

        assert context.bctl_command == "bctl status"
        assert context.bctl_output == "out"
        assert context.bctl_exit_code == 3

    def test_uses_a_unique_marker_per_invocation(self, mod):
        context, _ = _context_with_terminal("$ ")
        markers = []

        with (
            patch.object(
                mod, "_wait_for_command_result", side_effect=lambda c, m, p: (markers.append(m), ("", 0))[1]
            ),
            patch.object(mod, "typeText"),
            patch.object(mod, "pressKey"),
        ):
            mod.run_bctl_command_in_ptyxis(context, "bctl status")
            mod.run_bctl_command_in_ptyxis(context, "bctl status")

        assert markers[0] != markers[1]


class TestBctlOutputIncludes:
    def test_passes_when_substring_present(self, mod):
        context = MagicMock(bctl_output="bluefinctl 1.0", bctl_command="bctl --version")

        mod.bctl_command_output_includes(context, "bluefinctl")

    def test_fails_when_substring_absent(self, mod):
        context = MagicMock(bctl_output="command not found", bctl_command="bctl --version")

        with pytest.raises(AssertionError, match="Expected 'bluefinctl' in output"):
            mod.bctl_command_output_includes(context, "bluefinctl")


class TestBctlExitStatusAssertions:
    def test_status_zero_passes(self, mod):
        mod.bctl_command_exits_with_status_zero(
            MagicMock(bctl_exit_code=0, bctl_output="", bctl_command="bctl status")
        )

    def test_status_zero_fails_on_nonzero(self, mod):
        context = MagicMock(bctl_exit_code=2, bctl_output="boom", bctl_command="bctl status")

        with pytest.raises(AssertionError, match="Expected exit code 0"):
            mod.bctl_command_exits_with_status_zero(context)

    @pytest.mark.parametrize("code", [0, 1])
    def test_update_check_accepts_zero_and_one(self, mod, code):
        mod.bctl_update_check_exits_with_status_zero_or_one(
            MagicMock(bctl_exit_code=code, bctl_output="", bctl_command="bctl update --check")
        )

    @pytest.mark.parametrize("code", [2, 127])
    def test_update_check_rejects_other_codes(self, mod, code):
        context = MagicMock(
            bctl_exit_code=code, bctl_output="boom", bctl_command="bctl update --check"
        )

        with pytest.raises(AssertionError, match=r"Expected exit code 0 \(up to date\)"):
            mod.bctl_update_check_exits_with_status_zero_or_one(context)
