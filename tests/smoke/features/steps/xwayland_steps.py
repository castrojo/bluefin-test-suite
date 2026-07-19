"""Custom step definitions for XWayland smoke tests."""
import os
import subprocess
import time

from behave import step
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass

from app_support import _ssh_args, launch_background, launch_target_available


_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")

GLXGEARS_LAUNCH_TARGETS = (
    ("command", "glxgears"),
)


def _run_host(cmd: str, timeout: int = 30):
    """Run cmd on the host VM via SSH when inside the runner container."""
    if _IN_CONTAINER:
        result = subprocess.run(
            _ssh_args() + [cmd],
            capture_output=True, text=True, timeout=timeout,
        )
    else:
        # qecore-headless replaces os.environ with the gnome-session environment,
        # so DISPLAY/WAYLAND_DISPLAY are already present for local runs.
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=os.environ,
        )
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _run_host_session(cmd: str, timeout: int = 30):
    """Run cmd with the GNOME session environment sourced."""
    return _run_host(f"source /tmp/session.env 2>/dev/null; {cmd}", timeout=timeout)


@step("X11 client glxgears is available")
def x11_client_glxgears_is_available(context) -> None:
    if not launch_target_available(GLXGEARS_LAUNCH_TARGETS):
        try:
            context.scenario.skip("glxgears is not installed on this image")
        except Exception:  # noqa: BLE001
            pass


def _xwayland_display_env() -> dict[str, str]:
    """Return DISPLAY and XAUTHORITY for the running XWayland server."""
    stdout, rc, _ = _run_host("pgrep -a -x Xwayland || true")
    assert rc == 0 and stdout.strip(), "XWayland is not running"
    line = stdout.splitlines()[0]
    display = ":0"
    auth = None
    parts = line.split()
    for i, part in enumerate(parts):
        if part == "-auth" and i + 1 < len(parts):
            auth = parts[i + 1]
    for part in parts:
        if part.startswith(":") and part[1:].isdigit():
            display = part
            break
    env = {"DISPLAY": display}
    if auth:
        env["XAUTHORITY"] = auth
    return env


@step("Launch glxgears via command")
def launch_glxgears_via_command(context) -> None:
    context.glxgears_launch_target = launch_background(GLXGEARS_LAUNCH_TARGETS)


@step("XWayland process appears within {timeout:d} seconds")
def xwayland_process_appears_within_seconds(context, timeout: int) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        stdout, rc, _ = _run_host("pgrep -a -x Xwayland || true")
        if rc == 0 and "/usr/bin/Xwayland" in stdout:
            return
        time.sleep(0.5)
    raise AssertionError(f"XWayland /usr/bin/Xwayland process did not appear within {timeout}s")


@step("xprop can query the X root window")
def xprop_can_query_x_root_window(context) -> None:
    xenv = _xwayland_display_env()
    env_exports = " ".join(f'export {k}="{v}";' for k, v in xenv.items())
    stdout, rc, stderr = _run_host_session(
        f"{env_exports} xprop -root >/dev/null 2>&1; echo $?"
    )
    assert rc == 0 and stdout.strip() == "0", (
        f"xprop -root failed (rc={rc}, exit={stdout.strip()}): {stderr}"
    )


@step("Terminate glxgears")
def terminate_glxgears(context) -> None:
    _run_host("pkill -x glxgears 2>/dev/null || true")
    # Brief settle so XWayland has released the client before the next step polls.
    time.sleep(0.5)


@step("Terminate any running glxgears")
def terminate_any_running_glxgears(context) -> None:
    _run_host("pkill -x glxgears 2>/dev/null || true")


@step("Wait {seconds:d} seconds")
def wait_seconds(context, seconds: int) -> None:
    time.sleep(seconds)
