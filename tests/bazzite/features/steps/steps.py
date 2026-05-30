"""
Bazzite-specific step definitions.

Covers:
  - Extension presence checks (via Shell.Eval extensionManager)
  - Logo Menu replacing Activities button
  - Caffeine toggle
  - Restart To in power menu
  - AppIndicator / system tray
  - GSConnect indicator

common_steps from qecore provides standard AT-SPI steps.
Shell.Eval patterns: docs/skills/gnome.md
"""
import subprocess

from behave import step
from dogtail import tree
from dogtail.predicate import GenericPredicate
from qecore.common_steps import *  # noqa: F401,F403


# ── AT-SPI connectivity ───────────────────────────────────────────────────────

@step('GNOME Shell is accessible via AT-SPI')
def shell_accessible_via_atspi(context) -> None:
    shell = tree.root.application("gnome-shell")
    assert shell, "gnome-shell application not found in AT-SPI tree"


@step('Dump panel children to log')
def dump_panel_children(context) -> None:
    shell = tree.root.application("gnome-shell")
    panels = shell.findChildren(GenericPredicate(roleName="panel"))
    if panels:
        for child in panels[0].findChildren(lambda n: True):
            print(f"  [{child.roleName}] {child.name!r} showing={child.showing}")
    else:
        print("  No panel found in AT-SPI tree")


@step('Panel is present in AT-SPI tree')
def panel_is_present(context) -> None:
    shell = tree.root.application("gnome-shell")
    panels = shell.findChildren(GenericPredicate(roleName="panel"))
    assert panels, "No panel found in gnome-shell AT-SPI tree"


# ── Activities overview ───────────────────────────────────────────────────────

@step('Open Activities overview via Shell.Eval')
def open_activities_overview(context) -> None:
    context.sandbox.shell.eval_js("Main.overview.show()")


@step('Close Activities overview via Shell.Eval')
def close_activities_overview(context) -> None:
    context.sandbox.shell.eval_js("Main.overview.hide()")


@step('Overview is open')
def overview_is_open(context) -> None:
    result = context.sandbox.shell.eval_js("Main.overview.visible")
    visible = str(result).strip().lower()
    assert "true" in visible, f"Overview is not open (visible={visible!r})"


@step('Overview is closed')
def overview_is_closed(context) -> None:
    result = context.sandbox.shell.eval_js("Main.overview.visible")
    visible = str(result).strip().lower()
    assert "false" in visible or "true" not in visible, (
        f"Overview is still open (visible={visible!r})"
    )


# ── Quick Settings ────────────────────────────────────────────────────────────

@step('Open Quick Settings via Shell.Eval')
def open_quick_settings(context) -> None:
    context.sandbox.shell.eval_js(
        "Main.panel.statusArea.quickSettings.menu.open(true)"
    )


@step('Quick Settings panel is open via Shell.Eval')
def quick_settings_is_open(context) -> None:
    result = context.sandbox.shell.eval_js(
        "Main.panel.statusArea.quickSettings.menu.isOpen"
    )
    is_open = str(result).strip().lower()
    assert "true" in is_open, (
        f"Quick Settings panel is not open (isOpen={is_open!r})"
    )



def _extension_state(context, uuid: str) -> str:
    """Return the extension state integer as a string via Shell.Eval.
    State values: 1=ENABLED, 2=DISABLED, 3=ERROR, 4=OUT_OF_DATE,
                  5=DOWNLOADING, 6=INITIALIZED, 99=UNINSTALLED
    """
    js = f"Main.extensionManager.lookup('{uuid}')?.state ?? 99"
    result = context.sandbox.shell.eval_js(js)
    # eval_js returns a string like "(true, '1')" — extract the value
    if isinstance(result, tuple):
        return str(result[1]).strip().strip("'\"")
    return str(result).strip().strip("'\"")


@step('Extension "{uuid}" is enabled')
def extension_is_enabled(context, uuid: str) -> None:
    state = _extension_state(context, uuid)
    assert state == "1", (
        f"Extension {uuid!r} is not enabled (state={state}). "
        "Expected state=1 (ENABLED)."
    )


@step('Extension "{uuid}" is installed')
def extension_is_installed(context, uuid: str) -> None:
    state = _extension_state(context, uuid)
    assert state != "99", (
        f"Extension {uuid!r} is not installed (state={state})."
    )


# ── Logo Menu ─────────────────────────────────────────────────────────────────

@step('Logo Menu button is present in panel')
def logo_menu_button_present(context) -> None:
    shell = tree.root.application("gnome-shell")
    panels = shell.findChildren(GenericPredicate(roleName="panel"))
    assert panels, "No panel found in gnome-shell AT-SPI tree"
    # Logo Menu adds a button; its exact name varies by distro logo config.
    # We check for a push button or menu button in the panel that is NOT
    # the Activities toggle — Logo Menu replaces Activities entirely.
    buttons = panels[0].findChildren(
        lambda n: n.roleName in ("push button", "menu button") and n.showing
    )
    assert buttons, "No Logo Menu button found in panel"


@step('Activities button is absent from panel')
def activities_button_absent(context) -> None:
    shell = tree.root.application("gnome-shell")
    panels = shell.findChildren(GenericPredicate(roleName="panel"))
    assert panels, "No panel found in gnome-shell AT-SPI tree"
    activities = panels[0].findChildren(
        lambda n: n.roleName == "toggle button" and n.name == "Activities"
    )
    assert not activities, (
        "Activities toggle button is still present — "
        "Logo Menu should have replaced it"
    )


# ── Caffeine ──────────────────────────────────────────────────────────────────

@step('Caffeine indicator is visible in panel')
def caffeine_indicator_visible(context) -> None:
    """Caffeine adds a system-tray-style indicator when active."""
    shell = tree.root.application("gnome-shell")
    # AppIndicator support exposes tray icons; Caffeine may show as a toggle
    # or inside the system menu area. Accept any node with 'caffeine' in name.
    nodes = shell.findChildren(
        lambda n: "caffeine" in (n.name or "").lower() and n.showing
    )
    assert nodes, "Caffeine indicator not found in AT-SPI tree"


# ── No coredump ───────────────────────────────────────────────────────────────

@step('No gnome-shell coredump with extensions loaded')
def no_coredump_with_extensions(context) -> None:
    result = subprocess.run(
        ["coredumpctl", "list", "--no-pager", "-q", "gnome-shell"],
        capture_output=True, text=True, timeout=10,
    )
    entries = [
        line for line in result.stdout.splitlines()
        if "gnome-shell" in line
    ]
    assert not entries, (
        "gnome-shell coredumps found with extensions loaded:\n"
        + "\n".join(entries)
    )
