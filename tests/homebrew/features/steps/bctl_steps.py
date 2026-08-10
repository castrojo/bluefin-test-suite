"""bctl (bluefinctl) step definitions for homebrew suite terminal tests.

Mirrors brew_steps.py's marker-based terminal-capture pattern. Kept as a
separate module (rather than parameterizing brew_steps.py) to match this
suite's existing one-tool-per-file convention (see ptyxis, podman, brew).
"Make sure window is focused for wayland testing" is defined once, in
brew_steps.py, and shared by both feature files in this suite.
"""
import re
import uuid
from time import monotonic, sleep

from behave import step
from dogtail.rawinput import pressKey, typeText
from qecore.common_steps import *  # noqa: F401,F403


COMMAND_TIMEOUT_SECONDS = 120


def _terminal_widget(context):
    return context.ptyxis.instance.child(roleName="terminal")


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


@step('Run bctl command in ptyxis and capture result: "{cmd}"')
def run_bctl_command_in_ptyxis(context, cmd) -> None:
    marker = f"__BCTL_EXIT_{uuid.uuid4().hex[:8]}__"
    previous_text = _terminal_widget(context).text
    typeText(f'{cmd}; printf "\\n{marker}:%s\\n" $?')
    pressKey("Return")
    output, exit_code = _wait_for_command_result(context, marker, previous_text)
    context.bctl_command = cmd
    context.bctl_output = output
    context.bctl_exit_code = exit_code


@step('bctl command output includes "{text}"')
def bctl_command_output_includes(context, text) -> None:
    assert text in context.bctl_output, (
        f"Expected '{text}' in output for '{context.bctl_command}':\n"
        f"{context.bctl_output}"
    )


@step("bctl command exits with status 0")
def bctl_command_exits_with_status_zero(context) -> None:
    assert context.bctl_exit_code == 0, (
        f"Expected exit code 0 for '{context.bctl_command}', got {context.bctl_exit_code}:\n"
        f"{context.bctl_output}"
    )


@step("bctl update --check exits with status 0 or 1")
def bctl_update_check_exits_with_status_zero_or_one(context) -> None:
    assert context.bctl_exit_code in (0, 1), (
        f"Expected exit code 0 (up to date) or 1 (updates available) for "
        f"'{context.bctl_command}', got {context.bctl_exit_code}:\n"
        f"{context.bctl_output}"
    )
