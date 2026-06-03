"""Custom step definitions for GNOME app launch smoke tests."""
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


def _skip_if_no_atspi(context) -> bool:
    """Skip the current scenario if AT-SPI (dogtail) is unavailable. Returns True if skipped."""
    if tree is None:
        try:
            context.scenario.skip("AT-SPI unavailable: dogtail not imported in this environment")
        except Exception:  # noqa: BLE001
            pass
        return True
    return False


FRAME_ROLES = {"frame", "filler"}
PTYXIS_APP_NAMES = ("ptyxis", "Ptyxis")
# GNOME 50 changed the Ptyxis window title from "Ptyxis" to "Terminal"
PTYXIS_WINDOW_NAMES: set[str] = {"Ptyxis", "Terminal", ""}
FILES_APP_NAMES = ("nautilus", "org.gnome.Nautilus", "Files")

# Map app name fragments → WM class substrings for Shell.Eval force-close.
# GNOME 50 apps (Ptyxis, Settings, Files) run as background daemons and
# don't terminate on Alt+F4 — we must force-delete via mutter.
_APP_WM_CLASS_HINTS: dict[str, str] = {
    "ptyxis": "ptyxis",
    "nautilus": "nautilus",
    "gnome.nautilus": "nautilus",
    "gnome-control-center": "gnome-control-center",
    "org.gnome.settings": "gnome-control-center",
}


def _shell_eval_force_close(app_names: tuple[str, ...]) -> None:
    """Force-close via mutter any windows matching app_names WM class fragments."""
    wm_hints: set[str] = set()
    for name in app_names:
        for key, hint in _APP_WM_CLASS_HINTS.items():
            if key in name.lower():
                wm_hints.add(hint)
    if not wm_hints:
        return
    checks = " || ".join(f"wc.includes('{h}')" for h in wm_hints)
    js = (
        "global.get_window_actors().forEach(a => {"
        "  try {"
        f"    const wc = (a.meta_window.get_wm_class() || '').toLowerCase();"
        f"    if ({checks}) a.meta_window.delete(global.get_current_time());"
        "  } catch(e) {}"
        "});"
    )
    subprocess.run(
        ["gdbus", "call", "--session",
         "--dest", "org.gnome.Shell",
         "--object-path", "/org/gnome/Shell",
         "--method", "org.gnome.Shell.Eval",
         js],
        capture_output=True, text=True, timeout=5,
    )
    sleep(1)


def _launch_app(app_id: str) -> None:
    """Launch a GNOME app by ID, trying multiple invocation methods.

    GNOME 50 / GLib 2.82+ changed ``gio launch`` to require an absolute path
    to the ``.desktop`` file rather than resolving by application ID via
    XDG_DATA_DIRS.  We try the absolute /usr/share path first, then fall back
    to older invocation styles.
    """
    attempts = [
        ["gio", "launch", f"/usr/share/applications/{app_id}.desktop"],
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
    for _ in range(40):
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
    # GNOME 50 apps (Ptyxis, Files, Settings) run as background daemons and
    # don't quit on Alt+F4.  Force-delete the window via mutter so the test
    # environment is clean for subsequent scenarios.
    _shell_eval_force_close(app_names)
    # Nautilus also needs --quit to stop its background service process.
    if "nautilus" in app_id.lower() or any("nautilus" in n.lower() for n in app_names):
        subprocess.run(
            ["nautilus", "--quit"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        sleep(1)
    _wait_for_app_to_close(app_names, label)


@step("the Ptyxis terminal launches successfully")
def ptyxis_terminal_launches_successfully(context) -> None:
    if _skip_if_no_atspi(context):
        return
    _launch_assert_and_close(
        context,
        "org.gnome.Ptyxis",
        PTYXIS_APP_NAMES,
        PTYXIS_WINDOW_NAMES,
        "Ptyxis",
    )


@step("the Files file manager launches successfully")
def files_file_manager_launches_successfully(context) -> None:
    if _skip_if_no_atspi(context):
        return
    _launch_assert_and_close(
        context,
        "org.gnome.Nautilus",
        FILES_APP_NAMES,
        {"Files", "Home"},
        "Files",
    )
