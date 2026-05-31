"""Custom step definitions for GNOME app launch smoke tests."""
import subprocess
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403


FRAME_ROLES = {"frame", "filler"}
PTYXIS_APP_NAMES = ("ptyxis", "Ptyxis")
# GNOME 50 changed the Ptyxis window title from "Ptyxis" to "Terminal"
PTYXIS_WINDOW_NAMES: set[str] = {"Ptyxis", "Terminal", ""}
FILES_APP_NAMES = ("nautilus", "org.gnome.Nautilus", "Files")


def _launch_app(app_id: str) -> None:
    """Launch a GNOME app by ID, trying multiple invocation methods.

    ``gio launch`` requires the full ``.desktop`` file ID (e.g.
    ``org.gnome.Ptyxis.desktop``).  Older callers may pass the bare app ID
    without the suffix, so we try several variants before giving up.
    """
    attempts = [
        ["gtk-launch", app_id],
        ["gio", "launch", f"{app_id}.desktop"],
        ["gio", "launch", app_id],
    ]
    last_cmd: list[str] = []
    last_err = ""
    for cmd in attempts:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        last_cmd = cmd
        last_err = result.stderr.strip() or result.stdout.strip()
        if result.returncode == 0:
            sleep(1)
            return
    raise AssertionError(
        f"Failed to launch {app_id!r}: last command {last_cmd!r} rc=1 — {last_err}"
    )


def _app(app_names: tuple[str, ...], label: str):
    last_error = None
    for name in app_names:
        try:
            return tree.root.application(name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise AssertionError(f"{label} application was not found via AT-SPI: {last_error}")


def _wait_for_window(
    app_names: tuple[str, ...],
    window_names: set[str],
    label: str,
    timeout: int = 15,
):
    last_frames = []
    for _ in range(timeout * 2):
        try:
            app = _app(app_names, label)
        except Exception:  # noqa: BLE001
            sleep(0.5)
            continue

        frames = app.findChildren(
            lambda n: n.roleName in FRAME_ROLES
            and n.showing
            and (not window_names or (n.name or "").strip() in window_names)
        )
        if frames:
            return frames[0]

        last_frames = [
            ((frame.name or "").strip(), frame.roleName)
            for frame in app.findChildren(lambda n: n.roleName in FRAME_ROLES and n.showing)
        ]
        sleep(0.5)

    raise AssertionError(
        f"Visible {label} window not found. Visible frames: {last_frames}"
    )


def _wait_for_app_to_close(app_names: tuple[str, ...], label: str) -> None:
    for _ in range(20):
        for name in app_names:
            try:
                app = tree.root.application(name)
                frames = app.findChildren(
                    lambda n: n.roleName in FRAME_ROLES and n.showing
                )
                if frames:
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            return
        sleep(0.5)
    raise AssertionError(f"{label} is still visible in the AT-SPI tree")


def _launch_assert_and_close(
    context,
    app_id: str,
    app_names: tuple[str, ...],
    window_names: set[str],
    label: str,
) -> None:
    _launch_app(app_id)
    window = _wait_for_window(app_names, window_names, label)
    context.last_launched_app_window = window
    try:
        window.click()
    except Exception:  # noqa: BLE001
        pass
    context.execute_steps('* Key combo: "<Alt><F4>" with uinput')
    # Nautilus (and some other GNOME 50 apps) persist as background daemons
    # even after all windows close.  Force-quit to ensure a clean state.
    if "nautilus" in app_id.lower() or any("nautilus" in n.lower() for n in app_names):
        subprocess.run(
            ["nautilus", "--quit"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    _wait_for_app_to_close(app_names, label)


@step("the Ptyxis terminal launches successfully")
def ptyxis_terminal_launches_successfully(context) -> None:
    _launch_assert_and_close(
        context,
        "org.gnome.Ptyxis",
        PTYXIS_APP_NAMES,
        PTYXIS_WINDOW_NAMES,
        "Ptyxis",
    )


@step("the Files file manager launches successfully")
def files_file_manager_launches_successfully(context) -> None:
    _launch_assert_and_close(
        context,
        "org.gnome.Nautilus",
        FILES_APP_NAMES,
        {"Files", "Home"},
        "Files",
    )
