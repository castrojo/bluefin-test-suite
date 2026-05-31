"""
Shared GNOME Shell step definitions reused by smoke and vanilla-gnome.
Includes common AT-SPI assertions plus Shell.Eval-based menu toggles that
both suites register via ``from tests.shared.gnome_shell_steps import *``.
"""

import subprocess
from time import sleep

from behave import step
from behave.runner import Context


def _shell_eval(js: str, timeout: int = 5) -> str:
    """Run JS in GNOME Shell via gdbus and return raw stdout."""
    result = subprocess.run(
        [
            'gdbus', 'call', '--session',
            '--dest', 'org.gnome.Shell',
            '--object-path', '/org/gnome/Shell',
            '--method', 'org.gnome.Shell.Eval',
            js,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, f"Shell.Eval failed: {result.stderr.strip()}"
    print(f"Shell.Eval({js!r}) → {result.stdout.strip()}", flush=True)
    return result.stdout


def _eval_bool(js: str) -> bool:
    import re

    out = _shell_eval(js)
    match = re.search(r',\s*\'"?(true|false)"?\'\s*\)', out, re.IGNORECASE)
    if match:
        return match.group(1).lower() == 'true'
    raise AssertionError(f"Could not parse boolean from Shell.Eval output: {out}")


def _wait_eval_bool(js: str, expected: bool, retries: int = 8, delay: float = 0.5) -> bool:
    for _ in range(retries):
        try:
            if _eval_bool(js) == expected:
                return True
        except AssertionError:
            pass
        sleep(delay)
    return False


@step("Dump panel children to log")
def dump_panel_children(context: Context) -> None:
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
def dump_atspi_tree(context: Context) -> None:
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
def gnome_shell_is_accessible(context: Context) -> None:
    """Retrying gnome-shell AT-SPI check via qecore's built-in shell getter.

    The common 'Application "{name}" is running' step calls is_open() which
    does not work for gnome-shell (compositor, not a regular window).
    context.sandbox.shell uses qecore's own retry path and is the recommended
    way to access gnome-shell per qecore docs.
    """
    last_exc = None
    for _ in range(6):
        try:
            shell = context.sandbox.shell
            assert shell is not None, "gnome-shell not registered in AT-SPI tree"
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            sleep(5)
    raise AssertionError(
        f"gnome-shell not accessible via AT-SPI after 30 s: {last_exc}"
    )


@step('Panel is present in AT-SPI tree')
def panel_is_present(context: Context) -> None:
    """Verify the GNOME Shell top bar panel is accessible.
    Searches by role='panel' — does NOT depend on accessible-name, which
    varies across GNOME versions (may be empty, 'panel', 'top-bar', etc.).
    """
    shell = context.sandbox.shell
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    if not panels:
        children = [(c.roleName, c.name) for c in shell.children[:15]]
        raise AssertionError(f"Panel (role='panel') not found in gnome-shell.\nTop-level children: {children}")
    context.panel = panels[0]


@step('Clock toggle is visible in top bar')
def clock_toggle_visible(context: Context) -> None:
    """Verify the clock toggle button is visible in the panel.
    GNOME 47+ accessible-name for the clock is the formatted time string
    (e.g. '7:14 PM' or 'Sunday 25 May, 7:14 PM'), NOT the literal 'clock'.
    We match by role and exclude 'Activities' and known system-menu names.
    """
    import re

    shell = context.sandbox.shell
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    assert panels, "Panel not found"
    panel = panels[0]
    toggles = panel.findChildren(lambda n: n.roleName == "toggle button" and n.showing)
    SYSTEM_NAMES = {"Activities", "System", "System Menu", "System menu"}
    time_re = re.compile(r'\d{1,2}:\d{2}|clock', re.IGNORECASE)
    clock = next(
        (t for t in toggles if t.name not in SYSTEM_NAMES and time_re.search(t.name)),
        None,
    )
    if clock is None:
        candidates = [t for t in toggles if t.name not in SYSTEM_NAMES]
        toggle_info = [(t.name, t.roleName) for t in toggles]
        assert len(candidates) > 0, (
            f"No clock-like toggle button found in panel.\nAll panel toggles: {toggle_info}"
        )
        clock = candidates[0]
    context.clock_toggle = clock
    print(f"Clock toggle found: name={clock.name!r}", flush=True)


@step('System menu toggle is visible in top bar')
def system_menu_toggle_visible(context: Context) -> None:
    """Verify the system menu / quick-settings toggle is visible.
    In GNOME 47/48 the accessible-name is 'System' (not 'System menu').
    Also accepts 'System menu' for forward compatibility.
    """
    shell = context.sandbox.shell
    panels = shell.findChildren(lambda n: n.roleName == "panel")
    assert panels, "Panel not found"
    panel = panels[0]
    candidate_names = {"System", "System menu", "System Menu"}
    toggles = panel.findChildren(lambda n: n.roleName == "toggle button" and n.showing)
    system = next((t for t in toggles if t.name in candidate_names), None)
    if system is None:
        import re

        time_re = re.compile(r'\d{1,2}:\d{2}|clock', re.IGNORECASE)
        non_clock = [t for t in toggles if t.name != "Activities" and not time_re.search(t.name)]
        toggle_info = [(t.name, t.roleName) for t in toggles]
        assert len(non_clock) > 0, (
            f"System menu toggle not found.\nPanel toggles: {toggle_info}"
        )
        system = non_clock[0]
    context.system_toggle = system
    print(f"System menu toggle found: name={system.name!r}", flush=True)


@step('Last command output stripped "is" "{expected}"')
def last_command_output_stripped_is(context: Context, expected: str) -> None:
    """Compare last command output after stripping whitespace/newlines.

    grep -c always appends a trailing newline; use this step instead of
    'Last command output "is"' when the command output has trailing whitespace.
    Supports qecore versions that use last_command_output or last_run_output.
    """
    actual = (
        getattr(context, 'command_stdout', None)
        or getattr(context, 'last_command_output', None)
        or getattr(context, 'last_run_output', None)
        or ""
    ).strip()
    assert actual == expected, (
        f"\nWanted output: '{expected}'\nActual output: '{actual}'"
    )


@step('Close Activities overview via Shell.Eval')
def close_overview_eval(context: Context) -> None:
    _shell_eval('Main.overview.hide()')
    sleep(0.5)


@step('Open Quick Settings via Shell.Eval')
def open_quick_settings_eval(context: Context) -> None:
    _shell_eval('Main.panel.statusArea.quickSettings.menu.toggle()')
    sleep(0.5)


@step('Quick Settings panel is closed via Shell.Eval')
def quick_settings_closed_eval(context: Context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.quickSettings.menu.isOpen.toString()',
        expected=False, retries=8, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.quickSettings.menu.isOpen.toString()')
        raise AssertionError(f"Quick Settings still open after 4s — Shell.Eval: {out!r}")


@step('Open date menu via Shell.Eval')
def open_date_menu_eval(context: Context) -> None:
    _shell_eval('Main.panel.statusArea.dateMenu.menu.toggle()')
    sleep(0.5)


@step('Close Quick Settings via Shell.Eval')
def close_quick_settings_eval(context: Context) -> None:
    _shell_eval('Main.panel.statusArea.quickSettings.menu.close(0)')
    sleep(0.5)


@step('Close date menu via Shell.Eval')
def close_date_menu_eval(context: Context) -> None:
    _shell_eval('Main.panel.statusArea.dateMenu.menu.close(0)')
    sleep(0.5)


@step('Date menu panel is closed via Shell.Eval')
def date_menu_closed_eval(context: Context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.dateMenu.menu.isOpen.toString()',
        expected=False, retries=8, delay=0.5,
    ):
        out = _shell_eval('Main.panel.statusArea.dateMenu.menu.isOpen.toString()')
        raise AssertionError(f"Date menu still open after 4s — Shell.Eval: {out!r}")
