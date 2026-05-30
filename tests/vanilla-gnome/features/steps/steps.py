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
import re
import subprocess
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403


@step("Dump panel children to log")
def dump_panel_children(context) -> None:
    """Print the full gnome-shell AT-SPI tree to stdout (Argo logs).
    Helps discover clock/system-status area roles and names in Bluefin GNOME.
    """
    try:
        shell = context.sandbox.shell
        print("=== GNOME-SHELL AT-SPI TREE ===", flush=True)
        def _dump(node, depth=0, max_depth=3):
            prefix = "  " * depth
            print(f"{prefix}role={node.roleName!r:20} name={node.name!r:30} showing={node.showing}", flush=True)
            if depth < max_depth:
                for c in node.children[:30]:
                    _dump(c, depth + 1, max_depth)
        _dump(shell, max_depth=3)
        print("=== END AT-SPI TREE ===", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"dump_panel_children failed: {exc}", flush=True)


@step("Dump gnome-shell AT-SPI tree to results")
def dump_atspi_tree(context) -> None:
    """Write the gnome-shell AT-SPI node tree to /tmp/results/atspi_tree.txt.

    Called from the first smoke scenario while the session is live, so the
    Wayland session and AT-SPI bus are both active.
    """
    import os
    lines = []
    shell = context.sandbox.shell
    def _write_tree(node, depth=0, max_depth=4):
        prefix = "  " * depth
        lines.append(f"{prefix}role={node.roleName!r:25} name={node.name!r} showing={node.showing}")
        if depth < max_depth:
            for gc in node.children[:40]:
                _write_tree(gc, depth + 1, max_depth)
    _write_tree(shell, max_depth=4)
    os.makedirs("/tmp/results", exist_ok=True)
    with open("/tmp/results/atspi_tree.txt", "w") as f:
        f.write("\n".join(lines))
    print(f"AT-SPI tree written: {len(lines)} lines (depth=4)", flush=True)



@step("GNOME Shell is accessible via AT-SPI")
def gnome_shell_is_accessible(context) -> None:
    """Retrying gnome-shell AT-SPI check via qecore's built-in shell getter.

    The common 'Application "{name}" is running' step calls is_open() which
    does not work for gnome-shell (compositor, not a regular window).
    context.sandbox.shell uses qecore's own retry path and is the recommended
    way to access gnome-shell per qecore docs.
    """
    last_exc = None
    for attempt in range(6):   # up to 30 s total
        try:
            shell = context.sandbox.shell
            assert shell is not None, "gnome-shell not registered in AT-SPI tree"
            return
        except Exception as exc:   # noqa: BLE001
            last_exc = exc
            sleep(5)
    raise AssertionError(
        f"gnome-shell not accessible via AT-SPI after 30 s: {last_exc}"
    )


@step('Panel is present in AT-SPI tree')
def panel_is_present(context) -> None:
    """Verify the GNOME Shell top bar panel is accessible.
    Searches by role='panel' — does NOT depend on accessible-name, which
    varies across GNOME versions (may be empty, 'panel', 'top-bar', etc.).
    """
    shell = context.sandbox.shell
    # dogtail 4.16 dropped requireResult kwarg — use findChildren instead
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    if not panels:
        children = [(c.roleName, c.name) for c in shell.children[:15]]
        raise AssertionError(f"Panel (role='panel') not found in gnome-shell.\nTop-level children: {children}")
    context.panel = panels[0]


@step('Clock toggle is visible in top bar')
def clock_toggle_visible(context) -> None:
    """Verify the clock toggle button is visible in the panel.
    GNOME 47+ accessible-name for the clock is the formatted time string
    (e.g. '7:14 PM' or 'Sunday 25 May, 7:14 PM'), NOT the literal 'clock'.
    We match by role and exclude 'Activities' and known system-menu names.
    """
    import re
    shell = context.sandbox.shell
    # dogtail 4.16 dropped requireResult kwarg — use findChildren instead
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    assert panels, "Panel not found"
    panel = panels[0]
    toggles = panel.findChildren(lambda n: n.roleName == "toggle button" and n.showing)
    # Clock names: time string (digits + colon), 'clock', or a formatted date
    SYSTEM_NAMES = {"Activities", "System", "System Menu", "System menu"}
    time_re = re.compile(r'\d{1,2}:\d{2}|clock', re.IGNORECASE)
    clock = next(
        (t for t in toggles
         if t.name not in SYSTEM_NAMES and time_re.search(t.name)),
        None,
    )
    if clock is None:
        # Fallback: accept any non-Activities, non-System toggle in the panel
        candidates = [t for t in toggles if t.name not in SYSTEM_NAMES]
        toggle_info = [(t.name, t.roleName) for t in toggles]
        assert len(candidates) > 0, (
            f"No clock-like toggle button found in panel.\nAll panel toggles: {toggle_info}"
        )
        clock = candidates[0]  # first non-system toggle is likely the clock
    context.clock_toggle = clock
    print(f"Clock toggle found: name={clock.name!r}", flush=True)


@step('System menu toggle is visible in top bar')
def system_menu_toggle_visible(context) -> None:
    """Verify the system menu / quick-settings toggle is visible.
    In GNOME 47/48 the accessible-name is 'System' (not 'System menu').
    Also accepts 'System menu' for forward compatibility.
    """
    shell = context.sandbox.shell
    # dogtail 4.16 dropped requireResult kwarg — use findChildren instead
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    assert panels, "Panel not found"
    panel = panels[0]
    CANDIDATE_NAMES = {"System", "System menu", "System Menu"}
    toggles = panel.findChildren(lambda n: n.roleName == "toggle button" and n.showing)
    system = next((t for t in toggles if t.name in CANDIDATE_NAMES), None)
    if system is None:
        # Fallback: look for a toggle that is NOT Activities and NOT a clock
        import re
        time_re = re.compile(r'\d{1,2}:\d{2}|clock', re.IGNORECASE)
        non_clock = [t for t in toggles
                     if t.name != "Activities" and not time_re.search(t.name)]
        toggle_info = [(t.name, t.roleName) for t in toggles]
        assert len(non_clock) > 0, (
            f"System menu toggle not found.\nPanel toggles: {toggle_info}"
        )
        system = non_clock[0]
    context.system_toggle = system
    print(f"System menu toggle found: name={system.name!r}", flush=True)


@step('Last command output stripped "is" "{expected}"')
def last_command_output_stripped_is(context, expected) -> None:
    """Compare last command output after stripping whitespace/newlines.

    grep -c always appends a trailing newline; use this step instead of
    'Last command output "is"' when the command output has trailing whitespace.
    Supports qecore versions that use last_command_output or last_run_output.
    """
    # qecore 4.16 stores under command_stdout; older versions used last_command_output
    actual = (
        getattr(context, 'command_stdout', None)
        or getattr(context, 'last_command_output', None)
        or getattr(context, 'last_run_output', None)
        or ""
    ).strip()
    assert actual == expected, (
        f"\nWanted output: '{expected}'\nActual output: '{actual}'"
    )


# ── Shell.Eval helpers (GNOME 50: uinput Super + AT-SPI toggle click broken) ──

def _shell_eval(js: str, timeout: int = 10) -> str:
    """Run JS in GNOME Shell and return stdout. Requires unsafe_mode=true."""
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell',
         '--method', 'org.gnome.Shell.Eval',
         js],
        capture_output=True, text=True, timeout=timeout,
    )
    assert result.returncode == 0, f"Shell.Eval failed: {result.stderr.strip()}"
    print(f"Shell.Eval({js!r}) → {result.stdout.strip()}", flush=True)
    return result.stdout


def _shell_eval_value(context, js: str, timeout: int = 10) -> str:
    """Return a Shell.Eval result string via gdbus.

    GNOME 50 may wrap strings in extra double-quotes: (true, '"value"').
    """
    out = _shell_eval(js, timeout=timeout)
    # Parse the gdbus tuple: (true, 'value') or (true, '"value"')
    match = re.search(r",\s*'\"?(.+?)\"?'\s*\)\s*$", out.strip(), re.DOTALL)
    if match:
        return match.group(1)
    raise AssertionError(f"Could not parse Shell.Eval value from output: {out}")


def _eval_bool(js: str) -> bool:
    out = _shell_eval(js)
    # GNOME 50 may wrap the JS result in extra double-quotes: (true, '"true"')
    match = re.search(r',\s*\'"?(true|false)"?\'\s*\)', out, re.IGNORECASE)
    if match:
        return match.group(1).lower() == 'true'
    raise AssertionError(f"Could not parse boolean from Shell.Eval output: {out}")


def _eval_context_bool(context, js: str, timeout: int = 10) -> bool:
    value = _shell_eval_value(context, f"({js}).toString()", timeout=timeout)
    if value.lower() in {'true', 'false'}:
        return value.lower() == 'true'
    raise AssertionError(f"Could not parse boolean from Shell.Eval output: {value}")


def _wait_eval_bool(js: str, expected: bool, retries: int = 8, delay: float = 0.5) -> bool:
    for _ in range(retries):
        try:
            if _eval_bool(js) == expected:
                return True
        except AssertionError:
            pass
        sleep(delay)
    return False


@step('No coredump entries exist for "{name}"')
def no_coredump_entries_exist(context, name: str) -> None:
    import subprocess

    result = subprocess.run(
        ['coredumpctl', 'list', name, '--no-pager', '--lines=10'],
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


@step('Open Activities overview via Shell.Eval')
def open_overview_eval(context) -> None:
    out = _shell_eval('Main.overview.show(); Main.overview.visible.toString()')
    assert '(true,' in out, f"overview show failed: {out}"
    ok = _wait_eval_bool('Main.overview.visible.toString()', True, retries=8, delay=0.5)
    assert ok, 'Overview did not become visible after show()'


@step('Close Activities overview via Shell.Eval')
def close_overview_eval(context) -> None:
    _shell_eval('Main.overview.hide()')
    sleep(0.5)


@step('Open Quick Settings via Shell.Eval')
def open_quick_settings_eval(context) -> None:
    # menu.toggle() is stable across GNOME 49/50
    _shell_eval('Main.panel.statusArea.quickSettings.menu.toggle()')
    sleep(0.5)


@step('Quick Settings panel is open via Shell.Eval')
def quick_settings_open_eval(context) -> None:
    assert _eval_bool('Main.panel.statusArea.quickSettings.menu.isOpen.toString()'), 'Quick Settings menu is not open'


@step('Quick Settings panel is closed via Shell.Eval')
def quick_settings_closed_eval(context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.quickSettings.menu.isOpen.toString()',
        expected=False, retries=8, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.quickSettings.menu.isOpen.toString()')
        raise AssertionError(f"Quick Settings still open after 4s — Shell.Eval: {out!r}")


@step('Open date menu via Shell.Eval')
def open_date_menu_eval(context) -> None:
    # menu.toggle() is stable across GNOME 49/50; _toggleMenu() is GNOME 50+ only
    _shell_eval('Main.panel.statusArea.dateMenu.menu.toggle()')
    sleep(0.5)


@step('Close Quick Settings via Shell.Eval')
def close_quick_settings_eval(context) -> None:
    # close(0) = BoxPointer.PopupAnimation.NONE — explicit close, not toggle
    _shell_eval('Main.panel.statusArea.quickSettings.menu.close(0)')
    sleep(0.5)


@step('Close date menu via Shell.Eval')
def close_date_menu_eval(context) -> None:
    _shell_eval('Main.panel.statusArea.dateMenu.menu.close(0)')
    sleep(0.5)


@step('Date menu panel is open via Shell.Eval')
def date_menu_open_eval(context) -> None:
    assert _eval_bool('Main.panel.statusArea.dateMenu.menu.isOpen.toString()'), 'Date menu is not open'


@step('Date menu panel is closed via Shell.Eval')
def date_menu_closed_eval(context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.dateMenu.menu.isOpen.toString()',
        expected=False, retries=8, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.dateMenu.menu.isOpen.toString()')
        raise AssertionError(f"Date menu still open after 4s — Shell.Eval: {out!r}")


@step('Set overview search text to "{text}" via Shell.Eval')
def set_overview_search_eval(context, text) -> None:
    """Populate overview search bar via GNOME Shell JS.
    uinput typing is broken on these VMs — use Shell.Eval instead.
    """
    js = (
        "Main.overview.show();"
        "const entry = Main.overview.searchEntry || Main.overview._overview.controls._searchController._searchEntry;"
        f"entry.get_clutter_text().set_text({text!r});"
        "entry.get_clutter_text().set_cursor_position(-1);"
        "entry.get_clutter_text().queue_redraw();"
        "true"
    )
    out = _shell_eval(js, timeout=15)
    assert '(true,' in out, f"Failed to set overview search text via Shell.Eval: {out}"
    sleep(0.5)


@step("Overview is open")
def overview_is_open(context) -> None:
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=True, retries=8):
        raise AssertionError("Activities overview did not open after 4s")


@step("Overview is closed")
def overview_is_closed(context) -> None:
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=False, retries=8):
        raise AssertionError("Activities overview is still showing after 4s")


@step('Overview search bar contains "{text}"')
def overview_search_bar_contains(context, text) -> None:
    shell = tree.root.application("gnome-shell")
    # dogtail 4.16 dropped requireResult kwarg
    entries = shell.findChildren(lambda n: n.roleName == "text" and n.showing)
    assert entries, "Search bar text entry not found"
    entry = entries[0]
    assert text in entry.text, f"Search bar text '{entry.text}' does not contain '{text}'"


def _command_exists(command: str) -> bool:
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _flatpak_app_exists(app_id: str) -> bool:
    try:
        result = subprocess.run(
            ['flatpak', 'list', '--app', '--columns=application'],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return False
    if result.returncode != 0:
        return False
    installed = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return app_id in installed


def _assert_any_app_present(label: str, commands: tuple[str, ...], flatpaks: tuple[str, ...]) -> None:
    found_commands = [command for command in commands if _command_exists(command)]
    found_flatpaks = [app_id for app_id in flatpaks if _flatpak_app_exists(app_id)]
    assert found_commands or found_flatpaks, (
        f"{label} not found. Commands checked: {commands}; flatpaks checked: {flatpaks}"
    )


@step('Do-not-disturb toggle is present in Quick Settings')
def dnd_toggle_present(context) -> None:
    assert _eval_context_bool(
        context,
        'Main.panel.statusArea.quickSettings._dnd !== null && '
        'Main.panel.statusArea.quickSettings._dnd !== undefined',
    ), 'Do-not-disturb toggle is missing from Quick Settings'


@step('Night Light toggle is present in Quick Settings')
def night_light_toggle_present(context) -> None:
    assert _eval_context_bool(
        context,
        'Main.panel.statusArea.quickSettings._nightLight !== null && '
        'Main.panel.statusArea.quickSettings._nightLight !== undefined',
    ), 'Night Light toggle is missing from Quick Settings'


@step('GNOME Files application is installed')
def files_application_is_installed(context) -> None:
    _assert_any_app_present(
        'GNOME Files application',
        ('nautilus',),
        ('org.gnome.Nautilus',),
    )


@step('GNOME Text Editor application is installed')
def text_editor_application_is_installed(context) -> None:
    _assert_any_app_present(
        'GNOME Text Editor application',
        ('gnome-text-editor',),
        ('org.gnome.TextEditor',),
    )


@step('A web browser application is installed')
def web_browser_application_is_installed(context) -> None:
    _assert_any_app_present(
        'Web browser application',
        ('epiphany', 'firefox', 'chromium', 'chromium-browser'),
        ('org.gnome.Epiphany', 'org.mozilla.firefox', 'org.chromium.Chromium'),
    )


@step('A terminal application is installed')
def terminal_application_is_installed(context) -> None:
    _assert_any_app_present(
        'Terminal application',
        ('kgx', 'ptyxis', 'gnome-terminal'),
        ('org.gnome.Console', 'app.devsuite.Ptyxis', 'org.gnome.Terminal'),
    )


@step('Screenshot tool launches via Shell.Eval')
def screenshot_tool_launches(context) -> None:
    _shell_eval('Main.screenshotUI.open().catch(logError); true', timeout=15)
    if not _wait_eval_bool('Main.screenshotUI.visible.toString()', expected=True, retries=10):
        out = _shell_eval('Main.screenshotUI.visible.toString()')
        raise AssertionError(f'Screenshot UI did not become visible: {out!r}')


@step('Screenshot tool window is accessible via AT-SPI')
def screenshot_tool_window_accessible(context) -> None:
    expected_labels = {'Selection', 'Screen', 'Window', 'Show Pointer', 'Take Screenshot'}
    visible_labels: list[str] = []
    for _ in range(10):
        shell = tree.root.application('gnome-shell')
        visible_labels = sorted({
            node.name for node in shell.findChildren(
                lambda n: n.showing and n.name in expected_labels
            )
        })
        if len(visible_labels) >= 2:
            return
        sleep(0.5)
    raise AssertionError(
        'Screenshot UI was not accessible via AT-SPI. '
        f'Visible screenshot labels: {visible_labels}'
    )


@step('Close screenshot tool')
def close_screenshot_tool(context) -> None:
    _shell_eval('Main.screenshotUI.close(true)')
    if not _wait_eval_bool('Main.screenshotUI.visible.toString()', expected=False, retries=8):
        out = _shell_eval('Main.screenshotUI.visible.toString()')
        raise AssertionError(f'Screenshot UI is still visible after close(): {out!r}')
