"""Input-method and keyboard-layout smoke steps.

The behave runner for the smoke suite executes inside the runner container,
not inside the VM session. Commands that need the VM's session bus, gsettings,
or system binaries must be forwarded via SSH when `_IN_CONTAINER` is true.
"""
import shlex
import subprocess

from behave import step
from app_support import _IN_CONTAINER, _ssh_run


def _run_in_vm(cmd: str, timeout: int = 30):
    """Run ``cmd`` inside the VM session.

    In the runner container the command is forwarded over SSH and the VM's
    `/tmp/session.env` is sourced first so commands like ``gsettings`` and
    ``busctl --user`` can reach the GNOME session bus. When running locally
    (inside the VM) the command is executed directly.
    """
    full = f"source /tmp/session.env 2>/dev/null; {cmd}"
    if _IN_CONTAINER:
        return _ssh_run(full, timeout=timeout)
    return subprocess.run(
        full,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_in_vm_checked(cmd: str, timeout: int = 30) -> tuple[str, int]:
    """Run ``cmd`` inside the VM session and return (stdout, returncode)."""
    result = _run_in_vm(cmd, timeout=timeout)
    return result.stdout.strip(), result.returncode


def _restore_input_sources(context) -> None:
    """Restore the input sources/current values captured by the save step.

    Registered as a behave cleanup task so restoration happens even if a
    scenario fails mid-way. Idempotent so the explicit restore step and the
    automatic cleanup do not fight.
    """
    state = getattr(context, "_input_methods_original_state", None)
    if not state or state.get("_restored"):
        return

    sources = state.get("sources", "")
    current = state.get("current", "")
    if sources:
        _run_in_vm(
            "gsettings set org.gnome.desktop.input-sources sources "
            f"{shlex.quote(sources)}"
        )
    if current:
        _run_in_vm(
            "gsettings set org.gnome.desktop.input-sources current "
            f"{shlex.quote(current)}"
        )
    state["_restored"] = True


@step("IBus daemon process is present")
def ibus_daemon_process_is_present(context) -> None:
    """Verify ibus-daemon is running in the VM session."""
    _, returncode = _run_in_vm_checked("pgrep -x ibus-daemon")
    assert returncode == 0, "ibus-daemon is not running in the VM session"


@step("IBus owns org.freedesktop.IBus on the session bus")
def ibus_owns_session_bus_name(context) -> None:
    """Verify the IBus D-Bus name is registered on the VM session bus."""
    _, returncode = _run_in_vm_checked(
        "busctl --user list | grep -q org.freedesktop.IBus"
    )
    assert returncode == 0, "org.freedesktop.IBus not found on the VM session bus"


@step("Input sources list contains a keyboard layout")
def input_sources_list_contains_keyboard_layout(context) -> None:
    """Assert the default input sources include an xkb keyboard layout."""
    output, returncode = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources sources"
    )
    assert returncode == 0, f"Failed to read input sources: {output}"
    assert "xkb" in output, f"No xkb layout in input sources: {output}"


@step("Current input sources are saved")
def current_input_sources_are_saved(context) -> None:
    """Capture current sources/current and register a cleanup to restore them."""
    sources, src_rc = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources sources"
    )
    assert src_rc == 0, f"Failed to read input sources: {sources}"

    current, cur_rc = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources current"
    )
    assert cur_rc == 0, f"Failed to read current input source: {current}"

    context._input_methods_original_state = {
        "sources": sources,
        "current": current,
        "_restored": False,
    }
    context.add_cleanup(lambda: _restore_input_sources(context))


@step("Input sources are set to include a second layout")
def input_sources_set_to_include_second_layout(context) -> None:
    """Add a German keyboard layout alongside the US layout."""
    _, returncode = _run_in_vm_checked(
        "gsettings set org.gnome.desktop.input-sources sources "
        "\"[('xkb', 'us'), ('xkb', 'de')]\""
    )
    assert returncode == 0, "Failed to add second keyboard layout"


@step("Current input source is switched to index 1")
def current_input_source_switched_to_index_1(context) -> None:
    """Set the active input source to the newly added German layout."""
    _, returncode = _run_in_vm_checked(
        "gsettings set org.gnome.desktop.input-sources current 1"
    )
    assert returncode == 0, "Failed to switch current input source"


@step("Input sources list contains the second layout")
def input_sources_list_contains_second_layout(context) -> None:
    """Assert sources now includes the German layout."""
    output, returncode = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources sources"
    )
    assert returncode == 0, f"Failed to read input sources: {output}"
    assert "('xkb', 'de')" in output, f"German layout not in sources: {output}"


@step("Current input source index is 1")
def current_input_source_index_is_1(context) -> None:
    """Assert the active input source index is 1."""
    output, returncode = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources current"
    )
    assert returncode == 0, f"Failed to read current input source: {output}"
    assert "1" in output, f"Current input source is not 1: {output}"


@step("MRU sources contain the second layout")
def mru_sources_contain_second_layout(context) -> None:
    """Assert the most-recently-used sources include the German layout."""
    output, returncode = _run_in_vm_checked(
        "gsettings get org.gnome.desktop.input-sources mru-sources"
    )
    assert returncode == 0, f"Failed to read MRU sources: {output}"
    assert "('xkb', 'de')" in output, f"German layout not in MRU sources: {output}"


@step("Original input sources are restored")
def original_input_sources_are_restored(context) -> None:
    """Explicit restore step at the end of the layout-switching scenario."""
    _restore_input_sources(context)


@step("localectl status reports a keymap")
def localectl_status_reports_keymap(context) -> None:
    """Assert localectl reports a virtual console keymap from the VM."""
    output, returncode = _run_in_vm_checked("localectl status")
    assert returncode == 0, f"localectl failed: {output}"
    assert "VC Keymap" in output, f"No VC Keymap in localectl status: {output}"
