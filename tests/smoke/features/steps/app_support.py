import os
import shutil
import subprocess


DESKTOP_DIRS = (
    "/usr/share/applications",
    "/var/lib/flatpak/exports/share/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
)


def _desktop_path(desktop_id: str) -> str | None:
    for directory in DESKTOP_DIRS:
        path = os.path.join(directory, desktop_id)
        if os.path.exists(path):
            return path
    return None


def _flatpak_available(app_id: str) -> bool:
    return subprocess.run(
        ["flatpak", "info", app_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def launch_target_available(targets: tuple[tuple[str, str], ...]) -> bool:
    for kind, value in targets:
        if kind == "command" and shutil.which(value):
            return True
        if kind == "desktop" and _desktop_path(value):
            return True
        if kind == "flatpak" and _flatpak_available(value):
            return True
    return False


def launch_background(targets: tuple[tuple[str, str], ...]) -> str:
    for kind, value in targets:
        if kind == "command" and shutil.which(value):
            subprocess.Popen(
                [value],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"command:{value}"
        if kind == "desktop" and _desktop_path(value):
            subprocess.Popen(
                ["gtk-launch", value],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"desktop:{value}"
        if kind == "flatpak" and _flatpak_available(value):
            subprocess.Popen(
                ["flatpak", "run", value],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"flatpak:{value}"
    raise AssertionError(f"No launch candidate available from {targets!r}")
