import os
import shutil
import subprocess


# When behave runs inside the runner container the host VM filesystem is not
# visible: /usr/share/applications, flatpak, etc. are absent from the image.
# Detect container context so desktop/flatpak lookups and app launches can be
# forwarded to the VM via SSH instead.
_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")

DESKTOP_DIRS = (
    "/usr/share/applications",
    "/var/lib/flatpak/exports/share/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
)


def _ssh_args() -> list[str]:
    return [
        "ssh",
        "-i", os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519"),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-p", os.environ.get("SSH_PORT", "22"),
        f"{os.environ.get('VM_USER', 'bluefin-test')}@{os.environ.get('VM_IP', '127.0.0.1')}",
    ]


def _ssh_run(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        _ssh_args() + [cmd],
        capture_output=True, text=True, timeout=timeout,
    )


def _desktop_path(desktop_id: str) -> str | None:
    if _IN_CONTAINER:
        for d in DESKTOP_DIRS:
            r = _ssh_run(f"test -f {d}/{desktop_id} && echo {d}/{desktop_id}")
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        return None
    for directory in DESKTOP_DIRS:
        path = os.path.join(directory, desktop_id)
        if os.path.exists(path):
            return path
    return None


def _flatpak_available(app_id: str) -> bool:
    if _IN_CONTAINER:
        return _ssh_run(f"flatpak info {app_id} 2>/dev/null").returncode == 0
    return subprocess.run(
        ["flatpak", "info", app_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _ssh_launch(cmd: str) -> None:
    """Launch an app on the VM via SSH; returns immediately (fire-and-forget)."""
    # Source session.env to get DBUS_SESSION_BUS_ADDRESS + WAYLAND_DISPLAY,
    # then run the launch command detached so SSH disconnect doesn't kill it.
    full = f"source /tmp/session.env 2>/dev/null; nohup {cmd} </dev/null &>/dev/null & disown"
    subprocess.run(_ssh_args() + [full], capture_output=True, text=True, timeout=15)


def launch_target_available(targets: tuple[tuple[str, str], ...]) -> bool:
    for kind, value in targets:
        if kind == "command":
            if _IN_CONTAINER:
                if _ssh_run(f"command -v {value}").returncode == 0:
                    return True
            elif shutil.which(value):
                return True
        if kind == "desktop" and _desktop_path(value):
            return True
        if kind == "flatpak" and _flatpak_available(value):
            return True
    return False


def launch_background(targets: tuple[tuple[str, str], ...]) -> str:
    for kind, value in targets:
        if kind == "command":
            if _IN_CONTAINER:
                if _ssh_run(f"command -v {value}").returncode == 0:
                    _ssh_launch(value)
                    return f"command:{value}"
            elif shutil.which(value):
                subprocess.Popen(
                    [value],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"command:{value}"
        if kind == "desktop":
            dp = _desktop_path(value)
            if dp:
                if _IN_CONTAINER:
                    _ssh_launch(f"gio launch {dp}")
                else:
                    subprocess.Popen(
                        ["gtk-launch", value],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                return f"desktop:{value}"
        if kind == "flatpak" and _flatpak_available(value):
            if _IN_CONTAINER:
                _ssh_launch(f"flatpak run {value}")
            else:
                subprocess.Popen(
                    ["flatpak", "run", value],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return f"flatpak:{value}"
    raise AssertionError(f"No launch candidate available from {targets!r}")


# AT-SPI action names that represent a primary click in order of preference.
_ATSPI_CLICK_ACTIONS = ("click", "press", "activate")


def atspi_click(node) -> None:
    """Activate a widget via AT-SPI action API (no ponytail / Wayland injection).

    Tries "click", "press", and "activate" actions in order. Falls back to the
    coordinate-based node.click() when no matching action is found — this may
    fail on Wayland without ponytail but keeps compatibility with X11 / local runs.
    """
    try:
        available = node.actions or {}
    except Exception:  # noqa: BLE001
        available = {}
    for action in _ATSPI_CLICK_ACTIONS:
        if action in available:
            try:
                node.do_action_named(action)
                return
            except Exception:  # noqa: BLE001
                pass
    node.click()
