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
from time import sleep

from behave import step
from qecore.common_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import *  # noqa: F401,F403


@step("Make sure window is focused for wayland testing")
def make_sure_window_is_focused(context) -> None:
    # Pattern from GNOMETerminalAutomation steps.py — prevents input race on Wayland
    sleep(2)
    if context.sandbox.session_type == "wayland":
        context.ptyxis.instance.children[0].click()


@step('Terminal output in ptyxis contains "{text}"')
def terminal_output_contains(context, text) -> None:
    # Ptyxis terminal widget uses roleName "terminal" (VTE-backed)
    terminal_widget = context.ptyxis.instance.child(roleName="terminal")
    assert text in terminal_widget.text, (
        f"Terminal output does not contain '{text}'"
    )


@step('Ptyxis has "{number}" tabs')
def ptyxis_has_n_tabs(context, number) -> None:
    # Tab bar uses roleName "page tab list"
    results = context.ptyxis.instance.findChildren(
        lambda n: n.roleName == "page tab list" and n.showing
    )
    assert results, "Ptyxis tab list (page tab list) not found"
    tab_list = results[0]
    tabs = tab_list.findChildren(lambda n: n.roleName == "page tab")
    assert len(tabs) == int(number), (
        f"Expected {number} tabs, found {len(tabs)}"
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

