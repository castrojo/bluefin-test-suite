"""Shared screenshot helpers for behave GNOME GUI suites."""

import json
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Any

# Detect when behave runs inside the runner container (not on the host VM).
# Screenshots must be triggered via SSH so GNOME Shell (on the VM) can write
# to the file — containerized gdbus calls are rejected by Shell's D-Bus policy.
_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _results_dir(context: Any | None = None) -> str:
    """Resolve output dir: userdata > env var > default /tmp/results."""
    if context is not None:
        config = getattr(context, "config", None)
        if config and hasattr(config, "userdata"):
            value = config.userdata.get("results_dir")
            if value:
                return value
    return os.environ.get("TESTSUITE_RESULTS_DIR", "/tmp/results")

# Seconds to wait after launching an app before screenshotting
_APP_LAUNCH_WAIT = int(os.environ.get("SCREENSHOT_APP_WAIT", "4"))
_CAPTURE_WAIT_SECONDS = float(os.environ.get("SCREENSHOT_CAPTURE_WAIT", "5"))

_CURRENT_CONTEXT: Any | None = None
_CURRENT_SUITE = "unknown"
_CURRENT_SCENARIO = "end_of_run"


def configure_screenshot_context(
    context: Any,
    suite_name: str,
    scenario_name: str | None = None,
) -> None:
    """Bind the active behave context so shared helpers can capture screenshots."""
    global _CURRENT_CONTEXT, _CURRENT_SCENARIO, _CURRENT_SUITE
    _CURRENT_CONTEXT = context
    _CURRENT_SUITE = suite_name
    if scenario_name is not None:
        _CURRENT_SCENARIO = scenario_name


def _safe_fragment(value: str | None, fallback: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", (value or fallback).lower()).strip("_")
    return safe[:60] or fallback


def _scenario_name() -> str:
    scenario = getattr(getattr(_CURRENT_CONTEXT, "scenario", None), "name", None)
    return scenario or _CURRENT_SCENARIO or "end_of_run"


def _screenshot_path(label: str, context: Any | None = None) -> str:
    suite = _safe_fragment(_CURRENT_SUITE, "suite")
    safe_label = _safe_fragment(label, "capture")
    scenario = _safe_fragment(_scenario_name(), "scenario")
    return os.path.join(_results_dir(context), f"screenshot_{suite}_{safe_label}_{scenario}.png")


def _ssh_run(cmd: str, timeout: int = 15) -> "subprocess.CompletedProcess[str]":
    """Run a shell command on the VM via SSH (used when inside the runner container)."""
    ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
    vm_ip = os.environ.get("VM_IP", "127.0.0.1")
    vm_user = os.environ.get("VM_USER", "bluefin-test")
    ssh_port = os.environ.get("SSH_PORT", "22")
    return subprocess.run(
        [
            "ssh", "-i", ssh_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", ssh_port,
            f"{vm_user}@{vm_ip}",
            cmd,
        ],
        capture_output=True, text=True, timeout=timeout,
    )


def _take_screenshot_via_ssh(path: str) -> bool:
    """Take a screenshot on the VM using the best available method.

    Tries in order:
    1. grim  — Wayland screencopy; bypasses GNOME Shell permission check entirely.
    2. gnome-screenshot — fallback for older GNOME versions.
    3. org.gnome.Shell.Screenshot D-Bus — last resort; requires unsafe_mode=true.

    All methods run on the VM (via SSH) since screencapture tools must have
    access to the Wayland/X11 display, not the container's namespaced environment.
    """
    # session.env provides WAYLAND_DISPLAY, XDG_RUNTIME_DIR, DBUS_SESSION_BUS_ADDRESS
    env_prefix = "source /tmp/session.env && "

    # --- 1. grim (wlr-screencopy, no GNOME Shell involvement) ---
    grim_cmd = f"{env_prefix}grim {shlex.quote(path)}"
    r = _ssh_run(grim_cmd)
    if r.returncode == 0:
        print(f"Screenshot via grim: {path}", flush=True)
        return True
    if "command not found" not in r.stderr and "No such file" not in r.stderr:
        print(f"grim failed (rc={r.returncode}): {r.stderr.strip()!r}", flush=True)

    # --- 2. gnome-screenshot CLI ---
    gnome_ss_cmd = f"{env_prefix}gnome-screenshot -f {shlex.quote(path)}"
    r = _ssh_run(gnome_ss_cmd)
    if r.returncode == 0:
        print(f"Screenshot via gnome-screenshot: {path}", flush=True)
        return True
    if "command not found" not in r.stderr and "No such file" not in r.stderr:
        print(f"gnome-screenshot failed (rc={r.returncode}): {r.stderr.strip()!r}", flush=True)

    # --- 3. gdbus org.gnome.Shell.Screenshot (requires unsafe_mode=true) ---
    # Try SetUnsafeMode (GNOME 43+, polkit-gated) then Shell.Eval as fallback.
    # The workflow pre-installs a polkit rule so SetUnsafeMode succeeds without
    # interactive auth.
    for _unsafe_cmd in [
        (f"{env_prefix}gdbus call --session --dest org.gnome.Shell "
         "--object-path /org/gnome/Shell "
         "--method org.gnome.Shell.SetUnsafeMode true"),
        (f"{env_prefix}gdbus call --session --dest org.gnome.Shell "
         "--object-path /org/gnome/Shell "
         "--method org.gnome.Shell.Eval "
         "'global.context.unsafe_mode = true'"),
    ]:
        if _ssh_run(_unsafe_cmd).returncode == 0:
            break
    gvariant_path = json.dumps(path)
    gdbus_cmd = (
        f"{env_prefix}"
        "gdbus call --session "
        "--dest org.gnome.Shell "
        "--object-path /org/gnome/Shell/Screenshot "
        "--method org.gnome.Shell.Screenshot.Screenshot "
        f"true false '{gvariant_path}'"
    )
    r = _ssh_run(gdbus_cmd)
    if r.returncode == 0:
        print(f"Screenshot via gdbus Shell.Screenshot: {path}", flush=True)
        return True
    print(
        f"All screenshot methods failed. gdbus: rc={r.returncode} "
        f"stderr={r.stderr.strip()!r}",
        flush=True,
    )
    return False


def _gdbus_screenshot(path: str) -> bool:
    """Take a screenshot, routing to the right host depending on environment."""
    if _IN_CONTAINER:
        return _take_screenshot_via_ssh(path)

    # Running directly on the VM — use subprocess list form (no shell quoting needed)
    gvariant_path = json.dumps(path)
    result = subprocess.run(
        [
            'gdbus', 'call', '--session',
            '--dest', 'org.gnome.Shell',
            '--object-path', '/org/gnome/Shell/Screenshot',
            '--method', 'org.gnome.Shell.Screenshot.Screenshot',
            'true', 'false', gvariant_path,
        ],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        print(
            f"Screenshot gdbus failed (rc={result.returncode}): "
            f"stderr={result.stderr.strip()!r}",
            flush=True,
        )
    return result.returncode == 0


def take_screenshot(label: str, context: Any | None = None) -> str | None:
    """Capture a PNG via the org.gnome.Shell.Screenshot D-Bus interface.

    Uses the native Screenshot DBus method (not Shell.Eval which is restricted
    in GNOME 48+). The screenshot is written synchronously by GNOME Shell.
    """
    context = context or _CURRENT_CONTEXT
    results_dir = _results_dir(context)
    path = _screenshot_path(label, context)
    os.makedirs(results_dir, exist_ok=True)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

    if not _gdbus_screenshot(path):
        return None

    deadline = time.monotonic() + _CAPTURE_WAIT_SECONDS
    while time.monotonic() < deadline:
        if os.path.exists(path):
            print(f"Screenshot saved: {path}", flush=True)
            return path
        time.sleep(0.2)

    print(f"Screenshot did not materialize: {path}", flush=True)
    return None


def take_app_screenshot(
    app_id: str,
    label: str | None = None,
    wait: int = _APP_LAUNCH_WAIT,
    context: Any | None = None,
) -> str | None:
    """Launch an app, screenshot it, then close it again."""
    proc = None
    target_label = label or app_id

    if '.' in app_id and _flatpak_installed(app_id):
        cmd = ['flatpak', 'run', app_id]
    elif shutil.which(app_id):
        cmd = [app_id]
    else:
        desktop_stem = app_id.removesuffix('.desktop')
        cmd = ['gtk-launch', desktop_stem]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(wait)
        return take_screenshot(target_label, context)
    except Exception as exc:  # noqa: BLE001
        print(f"App screenshot ({app_id}): {exc}", flush=True)
        return None
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                pass


def _flatpak_installed(app_id: str) -> bool:
    return subprocess.run(
        ['flatpak', 'info', app_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def take_fastfetch_screenshot(context: Any | None = None) -> str | None:
    """Open a terminal, run fastfetch, screenshot it, then close."""
    candidates = [
        ('ptyxis', ['ptyxis', '--', 'bash', '-c', 'fastfetch; sleep 10']),
        ('kgx', ['kgx', '--', 'bash', '-c', 'fastfetch; sleep 10']),
        ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', 'fastfetch; sleep 10']),
    ]

    attempted = False
    for term, cmd in candidates:
        if not shutil.which(term):
            continue
        attempted = True
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(4)
            path = take_screenshot('fastfetch', context)
            if path is not None:
                return path
            print(f"Fastfetch screenshot ({term}): capture returned no file", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Fastfetch screenshot ({term}): {exc}", flush=True)
        finally:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:  # noqa: BLE001
                    pass

    if not attempted:
        # No terminal emulator in PATH (e.g. inside the runner container which uses
        # fedora-minimal). Fall back to a plain desktop screenshot so the Promote
        # step still finds a screenshot_*fastfetch*.png artifact.
        print('Fastfetch screenshot: no terminal emulator — taking plain desktop screenshot', flush=True)
        return take_screenshot('fastfetch', context)
    print('Fastfetch screenshot: all terminal attempts failed', flush=True)
    return None
