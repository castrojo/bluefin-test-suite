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
import subprocess
from time import sleep

from behave import step
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass
from tests.shared.gnome_shell_steps import *  # noqa: F401,F403


# ── Shell.Eval helpers (GNOME 50: uinput Super + AT-SPI toggle click broken) ──

def _shell_eval(js: str) -> str:
    """Run JS in GNOME Shell via gdbus and return raw stdout.

    Requires unsafe_mode=true (set in before_all).  Returns the raw gdbus
    output string, e.g. ``(true, 'some value')\\n``.  Use _eval_bool() when
    you need to check a JS boolean result — do NOT use ``'true' in out`` on
    the raw string because gdbus always includes the success flag ``true`` as
    the first tuple element even when the JS result is ``false``.
    """
    import subprocess
    r = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell',
         '--method', 'org.gnome.Shell.Eval',
         js],
        capture_output=True, text=True, timeout=5,
    )
    print(f"Shell.Eval({js!r}) → {r.stdout.strip()}", flush=True)
    return r.stdout


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
    result = subprocess.run(
        ["gsettings", "set", schema, key, "true" if value else "false"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"gsettings set {schema} {key} failed: rc={result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def _gsettings_get_bool(schema: str, key: str) -> bool:
    result = subprocess.run(
        ["gsettings", "get", schema, key],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"gsettings get {schema} {key} failed: rc={result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    value = result.stdout.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise AssertionError(f"Unexpected gsettings value for {schema} {key}: {result.stdout!r}")


def _set_dnd_enabled(expected: bool) -> None:
    # In GNOME 48+, the _do_not_disturb property on quickSettings may not exist
    # or may have been relocated.  Try the Shell.Eval UI path first; if the
    # toggle object is absent, fall back to the gsettings canonical source.
    # (DND is active when org.gnome.desktop.notifications show-banners = false)
    exists_js = (
        "Main.panel.statusArea.quickSettings._do_not_disturb !== null && "
        "Main.panel.statusArea.quickSettings._do_not_disturb !== undefined"
    )
    try:
        toggle_exists = _eval_bool(exists_js)
    except AssertionError:
        toggle_exists = False

    if toggle_exists:
        checked_js = "Main.panel.statusArea.quickSettings._do_not_disturb.checked.toString()"
        toggle_js = "Main.panel.statusArea.quickSettings._do_not_disturb.toggle()"
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
    result = subprocess.run(
        ["coredumpctl", "list", name, "--no-pager", "--lines=10"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode not in (0, 1):
        raise AssertionError(
            f"coredumpctl list failed for {name}: rc={result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    matches = [line for line in result.stdout.splitlines() if name in line]
    assert not matches, f"Unexpected coredump entries for {name}: {matches}"


@step('No journal entries at priority "{priority}" contain "{text}"')
def no_journal_entries_at_priority_contain(context, priority: str, text: str) -> None:
    result = subprocess.run(
        ["journalctl", "--no-pager", "-b", "-p", priority, "--lines=50"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"journalctl failed for priority {priority}: rc={result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    matches = [line for line in result.stdout.splitlines() if text in line]
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
    checked_js = 'Main.panel.statusArea.quickSettings._do_not_disturb.checked.toString()'
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
    checked_js = 'Main.panel.statusArea.quickSettings._do_not_disturb.checked.toString()'
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
    """Lock the GNOME session via gdbus ScreenSaver D-Bus call."""
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.ScreenSaver",
            "--object-path", "/org/gnome/ScreenSaver",
            "--method", "org.gnome.ScreenSaver.Lock",
        ],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, (
        f"gdbus ScreenSaver.Lock failed: {result.stderr.strip()}"
    )


@step("Session is locked")
def session_is_locked(context) -> None:
    """Assert the current session is in a locked state via loginctl."""
    import os

    session_id = os.environ.get("XDG_SESSION_ID", "")
    if not session_id:
        result = subprocess.run(
            ["loginctl", "list-sessions", "--no-legend"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert lines, "No active loginctl sessions found"
        session_id = lines[0].split()[0]

    for _ in range(10):
        result = subprocess.run(
            ["loginctl", "show-session", session_id, "--property=LockedHint"],
            capture_output=True, text=True, timeout=10,
        )
        if "LockedHint=yes" in result.stdout:
            return
        sleep(1)
    raise AssertionError(
        f"Session {session_id} is not locked after 10s: {result.stdout.strip()}"
    )


@step("Unlock screen via Shell.Eval")
def unlock_screen_via_shell_eval(context) -> None:
    """Unlock the GNOME session via gdbus ScreenSaver SetActive(false)."""
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.ScreenSaver",
            "--object-path", "/org/gnome/ScreenSaver",
            "--method", "org.gnome.ScreenSaver.SetActive",
            "false",
        ],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, (
        f"gdbus ScreenSaver.SetActive(false) failed: {result.stderr.strip()}"
    )

    import os

    session_id = os.environ.get("XDG_SESSION_ID", "")
    if not session_id:
        session_result = subprocess.run(
            ["loginctl", "list-sessions", "--no-legend"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [line.strip() for line in session_result.stdout.splitlines() if line.strip()]
        assert lines, "No active loginctl sessions found while unlocking"
        session_id = lines[0].split()[0]

    for _ in range(10):
        locked_hint = subprocess.run(
            ["loginctl", "show-session", session_id, "--property=LockedHint"],
            capture_output=True, text=True, timeout=10,
        )
        if "LockedHint=no" in locked_hint.stdout:
            return
        sleep(1)

    raise AssertionError(
        f"Session {session_id} is still locked after unlock attempt: {locked_hint.stdout.strip()}"
    )


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
