"""
Custom step definitions for developer suite tests.

common_steps covers: Start/Close application, Item found/not found,
Key combo, Press key, Type text, Run and save command output.

Custom steps here:
  - Make sure window is focused for wayland testing (port from GNOMETerminalAutomation)
  - Terminal output in ptyxis contains <text>
  - Ptyxis has N tabs
  - No Flatpak missing-runtime error
"""
import subprocess
from time import monotonic, sleep

from behave import step
from qecore.common_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import *  # noqa: F401,F403


UI_TIMEOUT_SECONDS = 15


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


@step("Ptyxis window is accessible")
def ptyxis_window_is_accessible(context) -> None:
    _wait_until(
        "Ptyxis window/frame was not accessible in the AT-SPI tree",
        lambda: _showing_nodes(context, {"frame", "window", "terminal"}),
    )


@step('Terminal output in ptyxis contains "{text}"')
def terminal_output_contains(context, text) -> None:
    # Ptyxis terminal widget uses roleName "terminal" (VTE-backed)
    terminal_widget = context.ptyxis.instance.child(roleName="terminal")
    _wait_until(
        f"Terminal output does not contain '{text}'",
        lambda: text in terminal_widget.text,
    )


@step('Ptyxis has "{number}" tabs')
def ptyxis_has_n_tabs(context, number) -> None:
    expected_tabs = int(number)

    def _tab_count_matches():
        results = _showing_nodes(context, {"page tab list"})
        if not results:
            return False
        tabs = results[0].findChildren(lambda n: n.roleName == "page tab")
        return len(tabs) == expected_tabs

    _wait_until(
        f"Expected {number} tabs in Ptyxis",
        _tab_count_matches,
    )


@step('No Flatpak missing-runtime error for "{flatpak_id}"')
def no_flatpak_missing_runtime_error(context, flatpak_id) -> None:
    # Checks journalctl for Flatpak runtime-missing errors (regression: dakota#430)
    result = subprocess.run(
        ["journalctl", "-b", "--no-pager", "-g", f"{flatpak_id}.*runtime.*missing"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0 or result.stdout.strip() == "", (
        f"Flatpak runtime-missing error found for {flatpak_id}:\n{result.stdout}"
    )

