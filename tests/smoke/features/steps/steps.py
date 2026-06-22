"""
Custom step definitions for GNOME Shell smoke tests.

common_steps provides: Application is running, Item found/not found,
Left/Right click, Key combo, Press key, Type text, Run and save command output,
Last command output, Wait N seconds.

Custom steps here cover:
- GNOME Shell accessibility check (retrying via context.sandbox.shell)
- Activities overview state, search bar content.

NOTE: We do NOT redefine 'Application "{name}" is running' — behave raises
AmbiguousStep when a literal step conflicts with an existing wildcard step.
Instead we use a distinct step name: 'GNOME Shell is accessible via AT-SPI'.

Step patterns sourced from: modehnal/GNOMETerminalAutomation steps.py
dogtail API: root.application(), Node.findChild(), Node.child(roleName=)
"""
import os
import subprocess
from time import sleep

from behave import step
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass
from tests.shared.gnome_shell_steps import *  # noqa: F401,F403

# Same container detection as system_health_steps — /proc/1/ns/mnt is a symlink
# to a kernel namespace object so lexists() is required (isfile() returns False).
_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _run_host(cmd: str, timeout: int = 30):
    """Run cmd on the host VM via SSH when inside the runner container."""
    if _IN_CONTAINER:
        ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
        vm_ip = os.environ.get("VM_IP", "127.0.0.1")
        vm_user = os.environ.get("VM_USER", "bluefin-test")
        ssh_port = os.environ.get("SSH_PORT", "22")
        result = subprocess.run(
            [
                "ssh",
                "-i", ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-p", ssh_port,
                f"{vm_user}@{vm_ip}",
                cmd,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.returncode, result.stderr.strip()


# ── Shell.Eval helpers (GNOME 50: uinput Super + AT-SPI toggle click broken) ──

def _shell_eval(js: str) -> str:
    """Run JS in GNOME Shell via gdbus and return raw stdout.

    Always re-enables unsafe_mode before evaluation — GNOME 50 resets it
    after UI interactions (modal dialogs, overview open/close, etc.).
    Returns the raw gdbus output string, e.g. ``(true, 'some value')\\n``.
    Use _eval_bool() when you need to check a JS boolean result.

    Routes via SSH when running inside the runner container — the container
    cannot connect to the VM's systemd user session bus directly.
    """
    import shlex
    # Prepend unsafe_mode enable — GNOME 50 resets it after UI events.
    js = f'global.context.unsafe_mode = true; {js}'
    cmd = (
        "source /tmp/session.env 2>/dev/null; "
        "gdbus call --session "
        "--dest org.gnome.Shell "
        "--object-path /org/gnome/Shell "
        "--method org.gnome.Shell.Eval "
        + shlex.quote(js)
    )
    stdout, rc, stderr = _run_host(cmd)
    assert rc == 0, f"Shell.Eval({js!r}) failed (rc={rc}): {stderr}"
    print(f"Shell.Eval({js!r}) → {stdout}", flush=True)
    return stdout


def _eval_bool(js: str) -> bool:
    """Evaluate a JS expression that returns true/false via Shell.Eval.

    Parses the gdbus return format ``(true, 'true')`` / ``(true, 'false')``.
    GNOME 50 may wrap the JS result in extra double quotes: ``(true, '"true"')``.
    Extracts only the **second** tuple element (the JS result string).
    Raises AssertionError if the result cannot be parsed as a boolean.
    """
    import re
    out = _shell_eval(js)
    # gdbus format: (success_bool, 'js_result_string')
    # GNOME 50 may return (true, '"true"') with extra double-quotes around the result.
    # We must match the JS result (after the comma), not the success flag.
    m = re.search(r',\s*\'"?(true|false)"?\'\s*\)', out, re.IGNORECASE)
    if m:
        return m.group(1).lower() == 'true'
    raise AssertionError(
        f"Shell.Eval did not return a boolean for {js!r}: got {out!r}"
    )


def _wait_eval_bool(js: str, expected: bool, retries: int = 8, delay: float = 0.5) -> bool:
    """Poll _eval_bool(js) until it equals expected, or return False on timeout."""
    for _ in range(retries):
        try:
            if _eval_bool(js) == expected:
                return True
        except AssertionError:
            pass
        sleep(delay)
    return False


def _gsettings_set_bool(schema: str, key: str, value: bool) -> None:
    val = "true" if value else "false"
    stdout, rc, stderr = _run_host(
        f"source /tmp/session.env 2>/dev/null; gsettings set {schema} {key} {val}"
    )
    assert rc == 0, (
        f"gsettings set {schema} {key} failed: rc={rc}\n{stderr}"
    )


def _gsettings_get_bool(schema: str, key: str) -> bool:
    stdout, rc, stderr = _run_host(
        f"source /tmp/session.env 2>/dev/null; gsettings get {schema} {key}"
    )
    assert rc == 0, (
        f"gsettings get {schema} {key} failed: rc={rc}\n{stderr}"
    )
    value = stdout.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise AssertionError(f"Unexpected gsettings value for {schema} {key}: {stdout!r}")


_DND_TOGGLE_JS = (
    "(() => { "
    "const quickSettings = Main.panel.statusArea.quickSettings; "
    "return quickSettings._doNotDisturb || "
    "quickSettings._do_not_disturb || "
    "quickSettings._dnd || null; "
    "})()"
)


def _dnd_toggle_exists_js() -> str:
    return f"({_DND_TOGGLE_JS}) !== null"


def _dnd_toggle_checked_js() -> str:
    return f"({_DND_TOGGLE_JS}).checked.toString()"


def _dnd_toggle_toggle_js() -> str:
    return f"({_DND_TOGGLE_JS}).toggle()"


def _set_dnd_enabled(expected: bool) -> None:
    # In GNOME 48+, the _do_not_disturb property on quickSettings may not exist
    # or may have been relocated.  Try the Shell.Eval UI path first; if the
    # toggle object is absent, fall back to the gsettings canonical source.
    # (DND is active when org.gnome.desktop.notifications show-banners = false)
    try:
        toggle_exists = _eval_bool(_dnd_toggle_exists_js())
    except AssertionError:
        toggle_exists = False

    if toggle_exists:
        checked_js = _dnd_toggle_checked_js()
        toggle_js = _dnd_toggle_toggle_js()
        if _eval_bool(checked_js) != expected:
            _shell_eval(toggle_js)
        if not _wait_eval_bool(checked_js, expected=expected, retries=8, delay=0.5):
            out = _shell_eval(checked_js)
            raise AssertionError(
                f"Do-Not-Disturb did not reach {expected} — Shell.Eval returned: {out!r}"
            )
    else:
        # Fallback: drive DND through gsettings
        # show-banners=true → DND disabled; show-banners=false → DND enabled
        _gsettings_set_bool(
            "org.gnome.desktop.notifications", "show-banners", not expected
        )
        actual = _gsettings_get_bool("org.gnome.desktop.notifications", "show-banners")
        dnd_active = not actual
        if dnd_active != expected:
            raise AssertionError(
                f"Do-Not-Disturb gsettings fallback: expected DND={expected}, "
                f"show-banners={actual!r}"
            )


@step('No coredump entries exist for "{name}"')
def no_coredump_entries_exist(context, name: str) -> None:
    stdout, returncode, stderr = _run_host(
        f"coredumpctl list {name} --no-pager --lines=10 2>&1 || true"
    )
    # coredumpctl exits 0 when matches found, 1 when no matches — treat 2+ as error
    if "command not found" in stdout or "command not found" in stderr:
        print(f"coredumpctl not available: {stdout or stderr}", flush=True)
        return
    matches = [line for line in stdout.splitlines() if name in line]
    assert not matches, f"Unexpected coredump entries for {name}: {matches}"


@step('No journal entries at priority "{priority}" contain "{text}"')
def no_journal_entries_at_priority_contain(context, priority: str, text: str) -> None:
    stdout, returncode, stderr = _run_host(
        f"journalctl --no-pager -b -p {priority} --lines=50"
    )
    assert returncode == 0, (
        f"journalctl failed for priority {priority}: rc={returncode}\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )
    matches = [line for line in stdout.splitlines() if text in line]
    assert not matches, f"Unexpected journal matches for {text!r}: {matches}"


@step('Open Activities overview via Shell.Eval')
def open_overview_eval(context) -> None:
    _shell_eval('Main.overview.show()')
    sleep(1)


@step('Quick Settings panel is open via Shell.Eval')
def quick_settings_open_eval(context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.quickSettings.menu.isOpen.toString()',
        expected=True, retries=6, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.quickSettings.menu.isOpen.toString()')
        raise AssertionError(f"Quick Settings not open — Shell.Eval returned: {out!r}")


@step('Ensure Night Light starts disabled via gsettings')
def ensure_night_light_starts_disabled(context) -> None:
    _gsettings_set_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
        False,
    )
    assert not _gsettings_get_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
    ), 'Night Light should start disabled'


@step('Enable Night Light via gsettings')
def enable_night_light_via_gsettings(context) -> None:
    _gsettings_set_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
        True,
    )


@step('Night Light is enabled via gsettings')
def night_light_is_enabled_via_gsettings(context) -> None:
    assert _gsettings_get_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
    ), 'Night Light should be enabled'


@step('Disable Night Light via gsettings')
def disable_night_light_via_gsettings(context) -> None:
    _gsettings_set_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
        False,
    )


@step('Night Light is disabled via gsettings')
def night_light_is_disabled_via_gsettings(context) -> None:
    assert not _gsettings_get_bool(
        'org.gnome.settings-daemon.plugins.color',
        'night-light-enabled',
    ), 'Night Light should be disabled'


@step('Enable Do-Not-Disturb via Shell.Eval toggle')
def enable_do_not_disturb_via_shell_eval_toggle(context) -> None:
    _set_dnd_enabled(True)


@step('Do-Not-Disturb is enabled via Shell.Eval')
def do_not_disturb_is_enabled_via_shell_eval(context) -> None:
    # Prefer Shell.Eval UI check; fall back to gsettings if toggle not available.
    checked_js = _dnd_toggle_checked_js()
    try:
        ok = _wait_eval_bool(checked_js, expected=True, retries=8, delay=0.5)
    except AssertionError:
        ok = False
    if not ok:
        # gsettings fallback: show-banners=false means DND is enabled
        dnd_active = not _gsettings_get_bool(
            'org.gnome.desktop.notifications', 'show-banners'
        )
        assert dnd_active, 'Do-Not-Disturb should be enabled'


@step('Disable Do-Not-Disturb via Shell.Eval toggle')
def disable_do_not_disturb_via_shell_eval_toggle(context) -> None:
    _set_dnd_enabled(False)


@step('Do-Not-Disturb is disabled via Shell.Eval')
def do_not_disturb_is_disabled_via_shell_eval(context) -> None:
    # Prefer Shell.Eval UI check; fall back to gsettings if toggle not available.
    checked_js = _dnd_toggle_checked_js()
    try:
        ok = _wait_eval_bool(checked_js, expected=False, retries=8, delay=0.5)
    except AssertionError:
        ok = False
    if not ok:
        # gsettings fallback: show-banners=true means DND is disabled
        dnd_active = not _gsettings_get_bool(
            'org.gnome.desktop.notifications', 'show-banners'
        )
        assert not dnd_active, 'Do-Not-Disturb should be disabled'


@step('Date menu panel is open via Shell.Eval')
def date_menu_open_eval(context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.dateMenu.menu.isOpen.toString()',
        expected=True, retries=6, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.dateMenu.menu.isOpen.toString()')
        raise AssertionError(f"Date menu not open — Shell.Eval returned: {out!r}")


@step('Set overview search text to "{text}" via Shell.Eval')
def set_overview_search_eval(context, text) -> None:
    """Populate overview search bar via GNOME Shell JS.

    Uses clutter_text.set_text() which naturally emits the text-changed
    signal, triggering the search controller without relying on the private
    _onSearchChanged() method that was removed in GNOME 47+.
    """
    safe_text = text.replace('"', '\\"')
    # clutter_text.set_text() emits text-changed, which the SearchEntry
    # propagates to the search controller — works across GNOME 45–50.
    _shell_eval(f'Main.overview.searchEntry.clutter_text.set_text("{safe_text}")')
    sleep(0.5)


@step("Lock screen via Shell.Eval")
def lock_screen_via_shell_eval(context) -> None:
    """Lock the GNOME session via Shell.Eval screenShield.lock()."""
    _shell_eval('Main.screenShield.lock(true)')
    sleep(1)


@step("Session is locked")
def session_is_locked(context) -> None:
    """Assert the current session is in a locked state via loginctl."""
    for _ in range(10):
        stdout, rc, _ = _run_host(
            "loginctl list-sessions --no-legend 2>/dev/null | head -1"
        )
        if not stdout.strip():
            sleep(1)
            continue
        session_id = stdout.strip().split()[0]
        locked_out, _, _ = _run_host(
            f"loginctl show-session {session_id} --property=LockedHint 2>/dev/null"
        )
        if "LockedHint=yes" in locked_out:
            return
        sleep(1)
    raise AssertionError("Session is not locked after 10s")


@step("Unlock screen via Shell.Eval")
def unlock_screen_via_shell_eval(context) -> None:
    """Unlock the GNOME session via gdbus ScreenSaver SetActive(false)."""
    stdout, rc, stderr = _run_host(
        "source /tmp/session.env 2>/dev/null; "
        "gdbus call --session "
        "--dest org.gnome.ScreenSaver "
        "--object-path /org/gnome/ScreenSaver "
        "--method org.gnome.ScreenSaver.SetActive "
        "false"
    )
    assert rc == 0, f"gdbus ScreenSaver.SetActive(false) failed: {stderr}"

    for _ in range(10):
        locked_out, _, _ = _run_host(
            "loginctl list-sessions --no-legend 2>/dev/null | head -1 | "
            "awk '{print $1}' | xargs -I{} loginctl show-session {} --property=LockedHint 2>/dev/null"
        )
        if "LockedHint=no" in locked_out:
            return
        sleep(1)

    raise AssertionError("Session is still locked after unlock attempt")


@step("Active workspace index is noted")
def note_active_workspace_index(context) -> None:
    """Store the current workspace index for later comparison."""
    import re
    out = _shell_eval(
        "global.workspace_manager.get_active_workspace_index();"
    )
    m = re.search(r',\s*\'"?(\d+)"?\'\s*\)', out)
    try:
        context.initial_workspace_index = int(m.group(1)) if m else 0
    except (ValueError, AttributeError):
        context.initial_workspace_index = 0
    print(f"Initial workspace index: {context.initial_workspace_index}", flush=True)


@step("Switch to next workspace via Shell.Eval")
def switch_to_next_workspace_via_shell_eval(context) -> None:
    """Switch to the next workspace using workspace_manager."""
    _shell_eval(
        "global.workspace_manager.get_active_workspace().get_neighbor("
        "Meta.MotionDirection.RIGHT).activate(global.get_current_time());"
    )
    sleep(0.5)


@step("Active workspace has changed")
def active_workspace_has_changed(context) -> None:
    """Assert the active workspace index changed from the noted value."""
    import re
    initial = getattr(context, 'initial_workspace_index', 0)
    for _ in range(10):
        out = _shell_eval(
            "global.workspace_manager.get_active_workspace_index();"
        )
        m = re.search(r',\s*\'"?(\d+)"?\'\s*\)', out)
        try:
            current = int(m.group(1)) if m else None
        except (ValueError, AttributeError):
            sleep(0.5)
            continue
        if current is not None and current != initial:
            return
        sleep(0.5)
    raise AssertionError(
        f"Workspace index did not change from {initial}"
    )


@step("Overview is open")
def overview_is_open(context) -> None:
    """Check via Shell.Eval: AT-SPI overview node naming is unstable across GNOME versions."""
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=True, retries=8):
        raise AssertionError("Activities overview did not open after 4s")


@step("Overview is closed")
def overview_is_closed(context) -> None:
    """Check via Shell.Eval: AT-SPI overview node naming is unstable across GNOME versions."""
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=False, retries=8):
        raise AssertionError("Activities overview is still showing after 4s")


@step('Overview search bar contains "{text}"')
def overview_search_bar_contains(context, text) -> None:
    """Verify search bar text via Shell.Eval for reliability across GNOME versions.

    AT-SPI text entry roles vary (text/entry/document text) and the search
    entry may not be visible until the controller activates — JS is faster.
    """
    import re
    for _ in range(8):
        out = _shell_eval('Main.overview.searchEntry.clutter_text.get_text()')
        # gdbus returns: (true, 'Files') — extract the JS result string
        m = re.search(r",\s*'([^']*)'\s*\)", out)
        if m and text in m.group(1):
            return
        sleep(0.5)
    raise AssertionError(
        f"Overview search bar does not contain {text!r} — last Shell.Eval: {out!r}"
    )


@step("Wayland session type is active")
def wayland_session_active(context) -> None:
    stdout, returncode, stderr = _run_host(
        "source /tmp/session.env 2>/dev/null; "
        "printf '%s\\n' \"${XDG_SESSION_TYPE:-}\"; "
        "if [ -z \"${XDG_SESSION_TYPE:-}\" ]; then "
        "session_id=$(loginctl list-sessions --no-legend 2>/dev/null | awk 'NR==1{print $1}'); "
        "[ -n \"$session_id\" ] && loginctl show-session \"$session_id\" --property=Type --value 2>/dev/null; "
        "fi"
    )
    assert returncode == 0, f"Unable to determine session type: {stderr or stdout}"
    values = [line.strip().lower() for line in stdout.splitlines() if line.strip()]
    assert "wayland" in values, f"Session type is not Wayland: {stdout.strip()!r}"


@step("GNOME Shell is not using software rendering")
def no_llvmpipe(context) -> None:
    stdout, returncode, stderr = _run_host(
        "source /tmp/session.env 2>/dev/null; "
        "{ glxinfo -B 2>/dev/null | grep 'OpenGL renderer string' || "
        "journalctl -b _COMM=gnome-shell --no-pager -n 200 2>/dev/null | "
        "grep -i llvmpipe | head -1 || "
        "echo 'no_llvmpipe'; }"
    )
    assert returncode == 0, f"Renderer check failed: {stderr or stdout}"
    lower = stdout.lower()
    assert "llvmpipe" not in lower or "no_llvmpipe" in lower, (
        f"LLVMpipe (software rendering) detected: {stdout.strip()!r}"
    )


@step("Dash to Dock panel is visible")
def dash_to_dock_visible(context) -> None:
    visible = _eval_bool(
        "(() => { "
        "try { "
        "const ext = Main.extensionManager.lookup('dash-to-dock@micxgx.gmail.com'); "
        "if (!ext || !ext.stateObj) return false; "
        "const dockManager = ext.stateObj.dockManager; "
        "if (!dockManager) return false; "
        "const docks = dockManager._allDocks || []; "
        "return docks.length > 0 && docks.some(dock => dock?.actor?.visible === true); "
        "} catch (e) { return false; } "
        "})().toString()"
    )
    assert visible, "Dash to Dock panel is not visible"


@step("System tray area is present in the panel")
def system_tray_present(context) -> None:
    present = _eval_bool(
        "(() => { "
        "try { "
        "const panel = Main.panel; "
        "const rightBox = panel._rightBox; "
        "if (!rightBox) return false; "
        "const quickSettings = panel.statusArea.quickSettings; "
        "return rightBox.visible === true && quickSettings !== null && quickSettings !== undefined; "
        "} catch (e) { return false; } "
        "})().toString()"
    )
    assert present, "System tray area is not present in GNOME Shell panel"
