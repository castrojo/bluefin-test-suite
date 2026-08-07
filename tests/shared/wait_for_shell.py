"""Wait for GNOME Shell to become ready, tolerating a GDM restart.

``qecore-headless`` restarts GDM as part of session setup. During that restart
the previous session's D-Bus socket (``$XDG_RUNTIME_DIR/bus``) is destroyed and
a brand new autologin session publishes a new one. Two distinct failures are
therefore expected *while the shell is still coming up*, and both are
retryable:

* ``ServiceUnknown`` — the bus is alive but ``org.gnome.Shell`` has no owner yet.
* ``Could not connect: No such file or directory`` — the bus socket itself is
  gone because GDM is mid-restart. It will reappear for the replacement session.

Because the socket is replaced, the session bus address must be **re-resolved
on every attempt**; a connection (or address) cached before the restart points
at a destroyed socket and can never recover.

Readiness is also required to be *stable* across consecutive checks so we do
not latch onto the outgoing session microseconds before GDM tears it down.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

from dogtail import tree as dtree

# A full GDM restart cycle (teardown + autologin + shell + AT-SPI registration)
# comfortably exceeds a minute on the KubeVirt lab VMs.
DEFAULT_TIMEOUT = 300.0
DEFAULT_INTERVAL = 2.0
DEFAULT_STABLE_CHECKS = 2

ERR_SERVICE_UNKNOWN = "service-unknown"
ERR_BUS_UNAVAILABLE = "bus-unavailable"
ERR_SHELL_NOT_READY = "shell-not-ready"
ERR_ATSPI_NOT_READY = "atspi-not-ready"
ERR_OTHER = "other"

_SERVICE_UNKNOWN_MARKERS = (
    "serviceunknown",
    "was not provided by any .service files",
    "name org.gnome.shell was not provided",
)

_BUS_UNAVAILABLE_MARKERS = (
    "could not connect",
    "no such file or directory",
    "enoent",
    "connection refused",
    "failed to connect to socket",
    "cannot autolaunch d-bus",
    "the connection is closed",
    "connection reset by peer",
    "unable to autolaunch",
    "autolaunch",
    "dbus-launch",
    "error connecting",
)


def classify_error(message: str) -> str:
    """Bucket a gdbus/AT-SPI failure into a retryable error class."""
    text = (message or "").lower()
    if any(marker in text for marker in _SERVICE_UNKNOWN_MARKERS):
        return ERR_SERVICE_UNKNOWN
    if any(marker in text for marker in _BUS_UNAVAILABLE_MARKERS):
        return ERR_BUS_UNAVAILABLE
    return ERR_OTHER


def _address_socket_path(address: str) -> str | None:
    """Return the filesystem path of a ``unix:path=`` bus address, if any."""
    for part in (address or "").split(","):
        part = part.strip()
        if part.startswith("unix:path="):
            return part[len("unix:path="):]
        if part.startswith("path="):
            return part[len("path="):]
    return None


def resolve_session_bus_env(base_env=None) -> dict:
    """Re-resolve the session bus address from the *current* environment.

    Never cache the result: GDM restarts replace the socket, so a stale address
    is unrecoverable. Falls back to ``$XDG_RUNTIME_DIR/bus`` and then to
    ``/run/user/<uid>/bus`` when the inherited address points at a socket that
    no longer exists.

    The address is *always* set, even while no socket exists. Unsetting it makes
    ``gdbus`` fall back to ``dbus-launch --autolaunch``, which either fails
    opaquely or spawns a private bus that the real session never joins; keeping
    the canonical path means the very next attempt connects as soon as the
    replacement session creates it.
    """
    env = dict(os.environ if base_env is None else base_env)

    uid = os.getuid()
    default_runtime_dir = f"/run/user/{uid}"
    runtime_dir = env.get("XDG_RUNTIME_DIR") or default_runtime_dir
    if not os.path.isdir(runtime_dir) and os.path.isdir(default_runtime_dir):
        runtime_dir = default_runtime_dir
    env["XDG_RUNTIME_DIR"] = runtime_dir

    address = env.get("DBUS_SESSION_BUS_ADDRESS", "")
    socket_path = _address_socket_path(address)
    address_usable = bool(address) and (socket_path is None or os.path.exists(socket_path))

    if not address_usable:
        candidates = [os.path.join(runtime_dir, "bus"), os.path.join(default_runtime_dir, "bus")]
        for candidate in candidates:
            if os.path.exists(candidate):
                env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={candidate}"
                break
        else:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={candidates[0]}"
    return env


def _shell_eval_ready(env: dict, timeout: float = 5.0) -> tuple[bool, str, str]:
    """Run the Shell.Eval readiness probe. Returns (ready, error_class, detail)."""
    try:
        result = subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.gnome.Shell",
                "--object-path",
                "/org/gnome/Shell",
                "--method",
                "org.gnome.Shell.Eval",
                "global.context.unsafe_mode = true; Main.panel ? true : false",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, ERR_SHELL_NOT_READY, "gdbus call timed out"
    except OSError as exc:
        return False, classify_error(str(exc)), str(exc)

    if result.returncode != 0 or "(true," not in (result.stdout or ""):
        detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "unknown gdbus failure"
        error_class = classify_error(detail)
        if error_class == ERR_OTHER:
            error_class = ERR_SHELL_NOT_READY
        return False, error_class, f"Shell.Eval not ready: {detail[:200]}"
    return True, "", ""


def _atspi_panel_ready() -> tuple[bool, str, str]:
    """Check the gnome-shell top panel is exposed and populated over AT-SPI."""
    try:
        shell = dtree.root.application("gnome-shell")
        panels = shell.findChildren(lambda n: n.roleName == "panel")
        if not panels:
            return False, ERR_ATSPI_NOT_READY, "gnome-shell panel not exposed in AT-SPI yet"

        # On GNOME Shell 50 the clock button has an empty AT-SPI name.
        # Readiness: panel exists + Shell.Eval confirms Main.panel is live.
        # Require 'Activities' or 'Show Apps' to confirm panel is populated.
        toggles = panels[0].findChildren(lambda n: n.roleName == "toggle button")
        named = [t.name for t in toggles if t.name]
        if any(name in ("Activities", "Show Apps") for name in named):
            return True, "", ""
        return False, ERR_ATSPI_NOT_READY, f"panel not yet populated (toggles: {named})"
    except Exception as exc:  # noqa: BLE001 - AT-SPI raises many bus-level errors
        detail = str(exc)
        error_class = classify_error(detail)
        if error_class == ERR_OTHER:
            error_class = ERR_ATSPI_NOT_READY
        return False, error_class, detail


def wait_for_shell(
    timeout: float = DEFAULT_TIMEOUT,
    interval: float = DEFAULT_INTERVAL,
    stable_checks: int = DEFAULT_STABLE_CHECKS,
) -> bool:
    """Poll until GNOME Shell is stably ready, or the deadline expires.

    Bounded by a wall-clock deadline rather than a fixed attempt count so that a
    full GDM restart cycle fits inside the budget. Every attempt re-resolves the
    session bus address, so the socket disappearing and reappearing is survived.
    """
    started = time.monotonic()
    deadline = started + timeout
    error_counts: dict[str, int] = {}
    last_error = "unknown"
    consecutive_ok = 0
    attempt = 0

    while True:
        attempt += 1
        env = resolve_session_bus_env()

        ready, error_class, detail = _shell_eval_ready(env)
        if ready:
            ready, error_class, detail = _atspi_panel_ready()

        if ready:
            consecutive_ok += 1
            if consecutive_ok >= stable_checks:
                print(
                    f"GNOME Shell ready (attempt {attempt}, "
                    f"{consecutive_ok} consecutive checks, "
                    f"{time.monotonic() - started:.1f}s)",
                    flush=True,
                )
                return True
            print(
                f"Readiness attempt {attempt}: ready ({consecutive_ok}/{stable_checks} "
                "consecutive checks), confirming stability",
                flush=True,
            )
        else:
            if consecutive_ok:
                print(
                    f"Readiness attempt {attempt}: shell went away after "
                    f"{consecutive_ok} good check(s) — session likely restarted",
                    flush=True,
                )
            consecutive_ok = 0
            error_counts[error_class] = error_counts.get(error_class, 0) + 1
            last_error = detail
            print(f"Readiness attempt {attempt} [{error_class}]: {detail}", flush=True)

        if time.monotonic() >= deadline:
            break
        time.sleep(interval)

    breakdown = ", ".join(f"{name}={count}" for name, count in sorted(error_counts.items())) or "none"
    print(
        f"ERROR: GNOME Shell readiness failed after {attempt} attempts / "
        f"{time.monotonic() - started:.1f}s (budget {timeout:.0f}s). "
        f"Error classes: {breakdown}. Last error: {last_error}. "
        f"'{ERR_BUS_UNAVAILABLE}' means the session bus socket vanished — GDM was "
        "restarted (qecore-headless does this) and the replacement session never "
        f"came up; '{ERR_SERVICE_UNKNOWN}' means the bus is up but org.gnome.Shell "
        "never took its name.",
        file=sys.stderr,
        flush=True,
    )
    return False


if __name__ == "__main__":
    if not wait_for_shell():
        sys.exit(1)
