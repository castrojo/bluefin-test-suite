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
import time

from behave import step
from dogtail import tree
from dogtail.predicate import GenericPredicate
from qecore.common_steps import *  # noqa: F401,F403


def _shell_eval(js: str, timeout: int = 5) -> str:
    """Run JS in GNOME Shell via gdbus and return raw stdout."""
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell',
         '--method', 'org.gnome.Shell.Eval', js],
        capture_output=True, text=True, timeout=timeout,
    )
    assert result.returncode == 0, f"Shell.Eval failed: {result.stderr.strip()}"
    return result.stdout.strip()


def _eval_bool(js: str) -> bool:
    """Return True/False from a Shell.Eval JS expression.

    GNOME 50 wraps the result in extra double-quotes: (true, '"true"').
    Both single-quoted and double-quoted variants are handled here.
    """
    import re
    out = _shell_eval(js)
    m = re.search(r',\s*\'"?(true|false)"?\'\s*\)', out, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "true"
    raise AssertionError(f"Could not parse boolean from Shell.Eval output: {out}")


def _wait_eval_bool(js: str, expected: bool, retries: int = 8, delay: float = 0.5) -> bool:
    """Poll Shell.Eval until the JS expression matches *expected* or retries are exhausted.

    Mirrors the same helper in tests/shared/gnome_shell_steps.py.
    Required for animated UI state (overview open/close, Quick Settings) where
    a single-shot check races against GNOME's CSS animation.
    """
    for _ in range(retries):
        try:
            if _eval_bool(js) == expected:
                return True
        except AssertionError:
            pass
        time.sleep(delay)
    return False


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
    _shell_eval("Main.overview.show()")


@step('Close Activities overview via Shell.Eval')
def close_activities_overview(context) -> None:
    _shell_eval("Main.overview.hide()")


@step('Overview is open')
def overview_is_open(context) -> None:
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=True, retries=8):
        raise AssertionError("Activities overview did not open after 4s")


@step('Overview is closed')
def overview_is_closed(context) -> None:
    if not _wait_eval_bool('Main.overview.visible.toString()', expected=False, retries=8):
        raise AssertionError("Activities overview is still showing after 4s")


# ── Quick Settings ────────────────────────────────────────────────────────────

@step('Open Quick Settings via Shell.Eval')
def open_quick_settings(context) -> None:
    _shell_eval("Main.panel.statusArea.quickSettings.menu.open(true)")


@step('Quick Settings panel is open via Shell.Eval')
def quick_settings_is_open(context) -> None:
    if not _wait_eval_bool(
        'Main.panel.statusArea.quickSettings.menu.isOpen.toString()',
        expected=True, retries=8,
    ):
        raise AssertionError("Quick Settings panel did not open after 4s")



def _extension_state(context, uuid: str) -> str:
    """Return the extension state integer as a string.

    Uses the stable org.gnome.Shell.Extensions.GetExtensionInfo D-Bus method
    instead of Shell.Eval, which requires unsafe_mode and is unreliable on
    GNOME 50 (bazzite/gnomeos).

    State values: 1=ENABLED, 2=DISABLED, 3=ERROR, 4=OUT_OF_DATE,
                  5=DOWNLOADING, 6=INITIALIZED, 7=DISABLING, 8=ENABLING,
                  99=UNINSTALLED/unknown
    """
    import re
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell/Extensions',
         '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
         f"'{uuid}'"],  # GVariant string literal — bare UUID fails gdbus parser
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return "99"
    # Output: ({'state': <uint32 1>, 'path': ..., ...},)
    m = re.search(r"'state':\s*<uint32\s+(\d+)>", result.stdout)
    return m.group(1) if m else "99"


@step('Extension "{uuid}" is enabled')
def extension_is_enabled(context, uuid: str) -> None:
    # State 6 (INITIALIZED) is transient — poll until ENABLED(1) or timeout.
    # Bazzite ships 11 extensions; GNOME Shell can take >90s post-boot to fully
    # enable all of them, so use a generous timeout here.
    deadline = time.monotonic() + 90
    state = "6"
    while time.monotonic() < deadline:
        state = _extension_state(context, uuid)
        if state == "1":
            return
        if state not in ("6", "8"):  # 6=INITIALIZED, 8=ENABLING are transient
            break  # non-transient bad state, stop polling early
        time.sleep(2)
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
    _shell_eval("global.context.unsafe_mode = true")
    assert _eval_bool(
        "(() => { "
        "const logo = Main.panel.statusArea['LogoMenu']; "
        "if (!logo) return false; "
        "return Boolean(logo.container?.visible ?? logo.visible ?? logo.actor?.visible ?? false); "
        "})().toString()"
    ), "Logo Menu button is not present in GNOME Shell statusArea"


@step('Activities button is absent from panel')
def activities_button_absent(context) -> None:
    _shell_eval("global.context.unsafe_mode = true")
    assert _eval_bool(
        "(() => { "
        "const activities = Main.panel.statusArea['activities']; "
        "if (!activities) return true; "
        "return (!Boolean(activities.container?.visible ?? activities.visible ?? activities.actor?.visible ?? false)); "
        "})().toString()"
    ), (
        "Activities button is still visible in GNOME Shell statusArea — "
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
    try:
        result = subprocess.run(
            ["coredumpctl", "list", "--no-pager", "-q", "gnome-shell"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        print("coredumpctl not found in runner — skipping coredump check", flush=True)
        return
    entries = [
        line for line in result.stdout.splitlines()
        if "gnome-shell" in line
    ]
    assert not entries, (
        "gnome-shell coredumps found with extensions loaded:\n"
        + "\n".join(entries)
    )
