"""Custom step definitions for GNOME Files (Nautilus) smoke tests."""
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403
from app_support import launch_background


FILES_APP_NAMES = ("nautilus", "org.gnome.Nautilus", "Files")
FILES_LAUNCH_TARGETS = (
    ("command", "nautilus"),
    ("desktop", "org.gnome.Nautilus.desktop"),
)


def _nautilus_app():
    last_error = None
    for name in FILES_APP_NAMES:
        try:
            return tree.root.application(name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise AssertionError(f"GNOME Files application was not found via AT-SPI: {last_error}")


@step("Launch Files via command")
def launch_files_via_command(context) -> None:
    context.files_launch_target = launch_background(FILES_LAUNCH_TARGETS)
    sleep(1)


def _nautilus_window(timeout: int = 10):
    """Return the visible Files frame, retrying briefly while Nautilus settles."""
    app = _nautilus_app()
    last_children = []
    for _ in range(timeout * 2):
        frames = app.findChildren(
            lambda n: n.roleName in {"frame", "filler"}
            and n.showing
            and (n.name or "").strip() in {"Files", "Home"}
        )
        if frames:
            return frames[0]
        last_children = [(child.roleName, child.name) for child in app.children[:10]]
        sleep(0.5)
    raise AssertionError(
        f"Visible Files window not found in nautilus app. Top-level children: {last_children}"
    )


@step("Files window is accessible")
def files_window_is_accessible(context) -> None:
    context.files_window = _nautilus_window()


@step("Files is no longer running")
def files_is_no_longer_running(context) -> None:
    for _ in range(20):
        for name in FILES_APP_NAMES:
            try:
                app = tree.root.application(name)
                frames = app.findChildren(lambda n: n.roleName in {"frame", "filler"} and n.showing)
                if frames:
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            return
        sleep(0.5)
    raise AssertionError("GNOME Files is still visible in the AT-SPI tree")


@step("Home folder is in the sidebar")
def home_folder_is_in_the_sidebar(context) -> None:
    window = _nautilus_window()
    trees = window.findChildren(
        lambda n: n.roleName in {"tree", "list"}
        and n.showing
        and ((n.name or "").strip() in {"Sidebar", ""})
    )
    assert trees, "Sidebar tree not found in Files window"

    home_items = []
    for sidebar in trees:
        home_items.extend(
            sidebar.findChildren(
                lambda n: n.roleName == "list item"
                and n.showing
                and bool(n.name)
                and ("Home" in n.name or "Personal Folder" in n.name)
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


@step("File search bar is open in Files")
def file_search_bar_is_open_in_files(context) -> None:
    """Assert the Ctrl+F search bar is visible in Nautilus."""
    app = _nautilus_app()
    for _ in range(20):
        # Nautilus search bar: a visible text/entry widget in the header area
        search_entries = app.findChildren(
            lambda n: n.showing
            and n.roleName in {"text", "entry"}
            and getattr(n, "focusable", True)
        )
        if search_entries:
            context.search_bar = search_entries[0]
            return
        sleep(0.5)
    raise AssertionError("File search bar was not found in Nautilus after Ctrl+F")
