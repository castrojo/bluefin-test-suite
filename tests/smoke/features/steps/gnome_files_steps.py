"""Custom step definitions for GNOME Files (Nautilus) smoke tests."""
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403


def _nautilus_window(timeout: int = 10):
    """Return the visible Files frame, retrying briefly while Nautilus settles."""
    app = tree.root.application("nautilus")
    last_children = []
    for _ in range(timeout * 2):
        frames = app.findChildren(
            lambda n: n.roleName == "frame" and n.name == "Files" and n.showing
        )
        if frames:
            return frames[0]
        last_children = [(child.roleName, child.name) for child in app.children[:10]]
        sleep(0.5)
    raise AssertionError(
        f"Visible Files window not found in nautilus app. Top-level children: {last_children}"
    )


@step("Home folder is in the sidebar")
def home_folder_is_in_the_sidebar(context) -> None:
    window = _nautilus_window()
    trees = window.findChildren(lambda n: n.roleName == "tree" and n.showing)
    assert trees, "Sidebar tree not found in Files window"

    home_items = []
    for sidebar in trees:
        home_items.extend(
            sidebar.findChildren(
                lambda n: n.roleName == "list item"
                and n.showing
                and bool(n.name)
                and "Home" in n.name
            )
        )

    assert home_items, "Home list item not found in Nautilus sidebar"


@step("Navigating to home folder shows file listing")
def navigating_to_home_folder_shows_file_listing(context) -> None:
    window = _nautilus_window()
    for _ in range(10):
        content_lists = window.findChildren(
            lambda n: n.roleName == "list" and n.showing and len(n.children) > 0
        )
        if content_lists:
            return
        sleep(0.5)
    raise AssertionError("Visible file listing with children not found after navigating home")


@step("New folder dialog is open")
def new_folder_dialog_is_open(context) -> None:
    app = tree.root.application("nautilus")
    for _ in range(10):
        dialogs = app.findChildren(lambda n: n.roleName == "dialog" and n.showing)
        for dialog in dialogs:
            entries = dialog.findChildren(
                lambda n: n.roleName in {"text", "entry"}
                and n.showing
                and getattr(n, "focusable", True)
            )
            if entries:
                return

        focused_entries = app.findChildren(
            lambda n: n.roleName in {"text", "entry"}
            and n.showing
            and getattr(n, "focused", False)
        )
        if focused_entries:
            return
        sleep(0.5)

    raise AssertionError("New folder dialog entry was not found in Nautilus")
