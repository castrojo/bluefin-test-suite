"""Custom step definitions for GNOME Extensions smoke tests."""
import os
import re
import subprocess
from time import sleep

from behave import step
from dogtail import tree
from qecore.common_steps import *  # noqa: F401,F403


EXTENSIONS_APP_NAMES = (
    "Extensions",
    "org.gnome.Extensions",
    "gnome-extensions-app",
    "gnome-extensions",
)
EXTENSIONS_WINDOW_ROLES = {"frame", "dialog", "filler"}
EXTENSIONS_DESKTOP_FILE = "/usr/share/applications/org.gnome.Extensions.desktop"


def _run(cmd: list[str]):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _extensions_app():
    last_error = None
    for name in EXTENSIONS_APP_NAMES:
        try:
            return tree.root.application(name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    for node in getattr(tree.root, "children", []):
        if node.roleName == "application" and "extension" in (node.name or "").casefold():
            return node

    raise AssertionError(
        f"GNOME Extensions application was not found via AT-SPI: {last_error}"
    )


def _extensions_window():
    app = _extensions_app()
    last_children = []
    for _ in range(40):  # 20s — extensions-app can be slow to present its window
        windows = app.findChildren(
            lambda n: n.roleName in EXTENSIONS_WINDOW_ROLES and n.showing
        )
        if windows:
            return windows[0]
        last_children = [(child.roleName, child.name) for child in app.children[:10]]
        sleep(0.5)
    raise AssertionError(
        "Visible GNOME Extensions window not found in AT-SPI tree. "
        f"Top-level children: {last_children}"
    )


@step("At least one GNOME extension is installed")
def at_least_one_gnome_extension_is_installed(context) -> None:
    output, returncode, stderr = _run(["gnome-extensions", "list"])
    assert returncode == 0, f"gnome-extensions list failed: {stderr or output}"

    extensions = [line.strip() for line in output.splitlines() if line.strip()]
    assert extensions, "gnome-extensions list returned no installed extensions"
    context.installed_extensions = extensions


@step("At least one GNOME extension is enabled")
def at_least_one_gnome_extension_is_enabled(context) -> None:
    output, returncode, stderr = _run(["gnome-extensions", "list", "--enabled"])
    assert returncode == 0, f"gnome-extensions list --enabled failed: {stderr or output}"

    enabled_extensions = [line.strip() for line in output.splitlines() if line.strip()]
    assert enabled_extensions, "gnome-extensions list --enabled returned no enabled extensions"
    context.enabled_extensions = enabled_extensions


@step("Launch Extensions preferences via command")
def launch_extensions_preferences_via_command(context) -> None:
    launch_attempts = [["gnome-extensions", "--launch-preferences"]]
    if os.path.exists(EXTENSIONS_DESKTOP_FILE):
        launch_attempts.append(["gio", "launch", EXTENSIONS_DESKTOP_FILE])

    last_error = "no launch attempts were executed"
    for cmd in launch_attempts:
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            last_error = str(exc)
            continue

        context.extensions_launch_target = " ".join(cmd)
        for _ in range(6):
            try:
                context.extensions_window = _extensions_window()
                return
            except AssertionError as exc:
                last_error = str(exc)
                sleep(0.5)

    raise AssertionError(f"Unable to launch GNOME Extensions preferences: {last_error}")


@step("Extensions window is accessible")
def extensions_window_is_accessible(context) -> None:
    last_error = None
    for _ in range(20):
        try:
            context.extensions_window = _extensions_window()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            sleep(0.5)
    raise AssertionError(f"GNOME Extensions window was not accessible: {last_error}")


@step("Extensions is no longer running")
def extensions_is_no_longer_running(context) -> None:
    for _ in range(20):
        try:
            app = _extensions_app()
        except AssertionError:
            return

        windows = app.findChildren(
            lambda n: n.roleName in EXTENSIONS_WINDOW_ROLES and n.showing
        )
        if not windows:
            return
        sleep(0.5)

    raise AssertionError("GNOME Extensions is still visible in the AT-SPI tree")


@step("No gnome-shell extension load journal errors exist")
def no_gnome_shell_extension_load_journal_errors_exist(context) -> None:
    output, returncode, stderr = _run(
        ["journalctl", "--no-pager", "-b", "-p", "err..emerg", "--lines=200", "-q"]
    )
    assert returncode == 0, f"journalctl failed: {stderr or output}"

    pattern = re.compile(r"gnome-shell.*extension", re.IGNORECASE)
    matches = [line for line in output.splitlines() if pattern.search(line)]
    assert not matches, (
        "Unexpected gnome-shell extension journal errors found:\n"
        + "\n".join(matches)
    )
