"""Custom Homebrew step definitions for homebrew suite terminal tests.

"Make sure window is focused for wayland testing" is duplicated here (ported
from tests/developer/features/steps/steps.py) rather than imported across
suites: each suite loads only its own steps/*.py files (cross-suite step
isolation, see docs/skills/test-authoring/behave/SKILL.md), and both
brew.feature and bctl.feature need it in their Background.
"""
import re
import uuid
from time import monotonic, sleep

from behave import step
from dogtail.rawinput import pressKey, typeText
from qecore.common_steps import *  # noqa: F401,F403


COMMAND_TIMEOUT_SECONDS = 120
UI_TIMEOUT_SECONDS = 15


def _terminal_widget(context):
    return context.ptyxis.instance.child(roleName="terminal")


def _wait_until(description, predicate, timeout=UI_TIMEOUT_SECONDS):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        value = predicate()
        if value:
            return value
        sleep(1)
    raise AssertionError(description)


def _showing_nodes(context, role_names):
    return context.ptyxis.instance.findChildren(
        lambda n: n.roleName in role_names and n.showing
    )


@step("Make sure window is focused for wayland testing")
def make_sure_window_is_focused(context) -> None:
    # Pattern from GNOMETerminalAutomation steps.py — prevents input race on Wayland
    sleep(2)
    if context.sandbox.session_type == "wayland":
        node = _wait_until(
            "Timed out waiting for a showing Ptyxis widget to focus",
            lambda: next(
                iter(
                    _showing_nodes(
                        context,
                        {"terminal", "frame", "window", "panel", "filler"},
                    )
                ),
                None,
            ),
        )
        node.click()


def _terminal_delta(previous_text: str, current_text: str) -> str:
    if current_text.startswith(previous_text):
        return current_text[len(previous_text):]
    return current_text


def _wait_for_command_result(context, marker: str, previous_text: str) -> tuple[str, int]:
    deadline = monotonic() + COMMAND_TIMEOUT_SECONDS
    while monotonic() < deadline:
        current_text = _terminal_widget(context).text
        delta = _terminal_delta(previous_text, current_text)
        match = re.search(rf"{re.escape(marker)}:(\d+)", delta)
        if match:
            output = delta[:match.start()].strip()
            return output, int(match.group(1))
        sleep(1)
    raise AssertionError(f"Timed out waiting for terminal output marker {marker}")


@step('Run brew command in ptyxis and capture result: "{cmd}"')
def run_brew_command_in_ptyxis(context, cmd) -> None:
    marker = f"__BREW_EXIT_{uuid.uuid4().hex[:8]}__"
    previous_text = _terminal_widget(context).text
    typeText(f'{cmd}; printf "\\n{marker}:%s\\n" $?')
    pressKey("Return")
    output, exit_code = _wait_for_command_result(context, marker, previous_text)
    context.brew_command = cmd
    context.brew_output = output
    context.brew_exit_code = exit_code


@step("brew command prints a Homebrew version")
def brew_command_prints_a_homebrew_version(context) -> None:
    assert re.search(r"Homebrew\s+\d+\.\d+\.\d+", context.brew_output), (
        f"Expected Homebrew version string in output for '{context.brew_command}':\n"
        f"{context.brew_output}"
    )


@step('brew command output includes "{text}"')
def brew_command_output_includes(context, text) -> None:
    assert text in context.brew_output, (
        f"Expected '{text}' in output for '{context.brew_command}':\n"
        f"{context.brew_output}"
    )


@step("brew command exits with status 0")
def brew_command_exits_with_status_zero(context) -> None:
    assert context.brew_exit_code == 0, (
        f"Expected exit code 0 for '{context.brew_command}', got {context.brew_exit_code}:\n"
        f"{context.brew_output}"
    )


@step("brew doctor exits cleanly or only reports warnings")
def brew_doctor_exits_cleanly_or_only_reports_warnings(context) -> None:
    assert context.brew_exit_code in (0, 1), (
        f"Expected brew doctor exit code 0 or 1, got {context.brew_exit_code}:\n"
        f"{context.brew_output}"
    )
    if context.brew_exit_code == 1:
        lowered_output = context.brew_output.lower()
        assert "warning" in lowered_output or "warnings" in lowered_output, (
            "brew doctor returned 1 without warning text:\n"
            f"{context.brew_output}"
        )
