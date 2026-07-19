"""Orca screen-reader smoke-test steps.

The smoke suite runs inside the VM via qecore-headless, so these steps use the
local subprocess helper `_run_host()` from `steps.py` rather than SSH.
"""

import time

from behave import step

from steps.steps import _run_host

_SCREEN_READER_SCHEMA = "org.gnome.desktop.a11y.applications"
_SCREEN_READER_KEY = "screen-reader-enabled"
_ORCA_START_STOP_TIMEOUT = 15


def _set_screen_reader(enabled: bool) -> None:
    """Toggle the GNOME screen-reader gsettings key."""
    value = "true" if enabled else "false"
    _run_host(
        f"gsettings set {_SCREEN_READER_SCHEMA} {_SCREEN_READER_KEY} {value}",
        timeout=10,
    )


def _orca_is_running() -> bool:
    """Return True if an orca process is present."""
    stdout, rc, _ = _run_host("pgrep -x orca", timeout=10)
    return rc == 0 and stdout.strip() != ""


def _wait_for_orca(running: bool, timeout: int = _ORCA_START_STOP_TIMEOUT) -> None:
    """Poll until the Orca process state matches ``running``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _orca_is_running() == running:
            return
        time.sleep(0.2)
    state = "start" if running else "stop"
    raise AssertionError(f"Orca did not {state} within {timeout} seconds")


@step('Screen reader enabled state toggles Orca on and off')
def step_screen_reader_toggles_orca(context) -> None:  # noqa: ARG001
    """Enable the screen reader, assert Orca starts, then disable and stop it.

    The screen-reader key is always restored to ``false`` even if an assertion
    fails, so subsequent scenarios are not left with Orca running.
    """
    start_error = None
    stop_error = None

    try:
        # Start from a known-off state so the "on" transition is real.
        _set_screen_reader(False)
        _wait_for_orca(running=False)

        _set_screen_reader(True)
        _wait_for_orca(running=True)
    except AssertionError as exc:
        start_error = exc
    finally:
        try:
            _set_screen_reader(False)
            _wait_for_orca(running=False)
        except AssertionError as exc:
            stop_error = exc

    if start_error:
        raise start_error
    if stop_error:
        raise AssertionError(f"Orca did not stop after disabling screen reader: {stop_error}")
