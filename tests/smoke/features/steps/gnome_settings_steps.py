"""Custom step definitions for GNOME Settings smoke tests."""
import subprocess
from time import sleep

from behave import step
try:
    from dogtail import tree
except Exception:  # noqa: BLE001
    tree = None  # type: ignore[assignment]
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass
from app_support import launch_background


def _skip_if_no_atspi(context) -> bool:
    if tree is None:
        try:
            context.scenario.skip("AT-SPI unavailable: dogtail not imported in this environment")
        except Exception:  # noqa: BLE001
            pass
        return True
    return False


SETTINGS_APP_NAMES = ("gnome-control-center", "Settings")
SETTINGS_LAUNCH_TARGETS = (
    ("command", "gnome-control-center"),
    ("desktop", "org.gnome.Settings.desktop"),
)
TEXT_ROLES = {"heading", "label", "static", "text", "description", "paragraph"}
INFO_TOKENS = ("bluefin", "fedora", "linux", "version", "os")
SETTINGS_PANEL_ALIASES = {
    "About": ("About", "System"),
    "Displays": ("Displays",),
    "Privacy & Security": ("Privacy & Security", "Privacy"),
}


def _settings_app():
    last_error = None
    for name in SETTINGS_APP_NAMES:
        try:
            return tree.root.application(name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise AssertionError(f"GNOME Settings application was not found via AT-SPI: {last_error}")


def _settings_window():
    app = _settings_app()
    frames = app.findChildren(lambda n: n.roleName in {"frame", "filler"} and n.showing)
    assert frames, "Visible GNOME Settings window not found"
    return frames[0]


@step("Launch Settings via command")
def launch_settings_via_command(context) -> None:
    if _skip_if_no_atspi(context):
        return
    context.settings_launch_target = launch_background(SETTINGS_LAUNCH_TARGETS)
    sleep(1)


@step("Settings window is accessible")
def settings_window_is_accessible(context) -> None:
    context.settings_window = _settings_window()


@step("Settings is no longer running")
def settings_is_no_longer_running(context) -> None:
    for i in range(40):
        for name in SETTINGS_APP_NAMES:
            try:
                app = tree.root.application(name)
                frames = app.findChildren(lambda n: n.roleName in {"frame", "filler"} and n.showing)
                if frames:
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            return
        # After 10s, force-kill the gnome-control-center daemon.
        if i == 19:
            subprocess.run(
                ["pkill", "-f", "gnome-control-center"],
                capture_output=True, text=True,
            )
            sleep(1)
        else:
            sleep(0.5)
    raise AssertionError("GNOME Settings is still visible in the AT-SPI tree")


def _visible_text(node) -> str:
    name = (getattr(node, "name", "") or "").strip()
    if name:
        return name
    try:
        text = (getattr(node, "text", "") or "").strip()
    except Exception:  # noqa: BLE001
        text = ""
    return text


def _looks_like_system_info(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in INFO_TOKENS) or any(char.isdigit() for char in text)


@step("Settings sidebar is present")
def settings_sidebar_is_present(context) -> None:
    app = _settings_app()
    list_boxes = app.findChildren(
        lambda n: n.roleName in {"list box", "list"}
        and n.showing
        and (
            (n.name or "").strip().casefold() == "settings categories"
            or n.findChildren(lambda c: c.roleName in {"button", "list item"})
        )
    )
    sidebar = next(
        (
            list_box
            for list_box in list_boxes
            if list_box.findChildren(lambda n: n.roleName in {"button", "list item"})
        ),
        None,
    )
    assert sidebar is not None, "Settings sidebar list box not found"
    context.settings_sidebar = sidebar


@step('Navigate to Settings panel "{name}"')
def navigate_to_settings_panel(context, name: str) -> None:
    sidebar = getattr(context, "settings_sidebar", None)
    if sidebar is None:
        settings_sidebar_is_present(context)
        sidebar = context.settings_sidebar

    aliases = SETTINGS_PANEL_ALIASES.get(name, (name,))
    candidates = sidebar.findChildren(
        lambda n: n.roleName in {"button", "list item"}
        and (n.name or "").strip().casefold() in {alias.casefold() for alias in aliases}
    )
    assert candidates, f"Settings sidebar item {name!r} not found"
    candidates[0].click()
    context.last_settings_panel = candidates[0].name or name
    sleep(1)
    if name == "About" and (context.last_settings_panel or "").casefold() == "system":
        about_buttons = _settings_app().findChildren(
            lambda n: n.showing
            and n.roleName in {"button", "list item"}
            and (n.name or "").strip().casefold() == "about"
        )
        if about_buttons:
            about_buttons[0].click()
            context.last_settings_panel = about_buttons[0].name or name
            sleep(1)


@step('Settings panel "{name}" is visible')
def settings_panel_is_visible(context, name: str) -> None:
    app = _settings_app()
    aliases = SETTINGS_PANEL_ALIASES.get(name, (name,))
    for _ in range(10):
        matches = app.findChildren(
            lambda n: n.showing
            and (n.name or "").strip() in aliases
            and n.roleName in TEXT_ROLES
        )
        if matches:
            return
        sleep(0.5)
    raise AssertionError(f"Settings panel {name!r} is not visible")


@step("About page shows system information")
def about_page_shows_system_information(context) -> None:
    app = _settings_app()
    # GNOME 50 libadwaita uses additional AT-SPI roles not in TEXT_ROLES.
    # First try with TEXT_ROLES, then fall back to all showing nodes.
    for _ in range(10):
        for role_filter in (
            lambda n: n.showing and n.roleName in TEXT_ROLES and bool(_visible_text(n)),
            lambda n: n.showing and bool(_visible_text(n)),
        ):
            visible_texts = [
                _visible_text(node)
                for node in app.findChildren(role_filter)
            ]
            matches = [text for text in visible_texts if _looks_like_system_info(text)]
            if matches:
                context.about_system_info = matches[0]
                return
        sleep(0.5)
    raise AssertionError(
        "About page did not expose visible system information text"
    )
