"""Custom step definitions for GNOME Settings smoke tests."""
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403


TEXT_ROLES = {"heading", "label", "static", "text"}
INFO_TOKENS = ("bluefin", "fedora", "linux", "version", "os")


def _settings_app():
    return tree.root.application("gnome-control-center")


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
    list_boxes = app.findChildren(lambda n: n.roleName == "list box" and n.showing)
    sidebar = next(
        (
            list_box
            for list_box in list_boxes
            if list_box.findChildren(lambda n: n.roleName == "list item")
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

    candidates = sidebar.findChildren(
        lambda n: n.roleName == "list item" and (n.name or "").strip().casefold() == name.casefold()
    )
    assert candidates, f"Settings sidebar item {name!r} not found"
    candidates[0].click()
    context.last_settings_panel = name


@step('Settings panel "{name}" is visible')
def settings_panel_is_visible(context, name: str) -> None:
    app = _settings_app()
    for _ in range(10):
        matches = app.findChildren(
            lambda n: n.showing
            and (n.name or "").strip() == name
            and n.roleName in TEXT_ROLES
        )
        if matches:
            return
        sleep(0.5)
    raise AssertionError(f"Settings panel {name!r} is not visible")


@step("About page shows system information")
def about_page_shows_system_information(context) -> None:
    app = _settings_app()
    for _ in range(10):
        visible_texts = [
            _visible_text(node)
            for node in app.findChildren(
                lambda n: n.showing and n.roleName in TEXT_ROLES and bool(_visible_text(n))
            )
        ]
        matches = [text for text in visible_texts if _looks_like_system_info(text)]
        if matches:
            context.about_system_info = matches[0]
            return
        sleep(0.5)
    raise AssertionError(
        "About page did not expose visible system information text"
    )
