"""KDE session preconditions for SSH-driven test runs.

Helpers that configure a DUT into a deterministic, automatable KDE/Plasma
desktop state.  Every helper operates over the shared SSH runner and returns a
structured ``KDEResult`` so callers can skip (not fail) when KDE is absent or
incomplete — the Tast ``SoftwareDeps`` model.
"""

from __future__ import annotations

import dataclasses
import posixpath
import re
import subprocess
import shlex
import time
from typing import Optional


@dataclasses.dataclass(frozen=True)
class KDEResult:
    """Outcome of a KDE precondition helper.

    Attributes:
        ok: True when the desired state was reached or the step was skipped.
        skipped: True when the DUT lacks the required capability; scenario
            callers should treat this as a skip, not a failure.
        reason: Human-readable description of the outcome.
    """

    ok: bool = False
    skipped: bool = False
    reason: str = ""


# Environment variables applied to the graphical session.  These keep KWin
# permissive for automation, force software rendering, disable animations, and
# pin a deterministic locale.
DETERMINISM_ENV = {
    "KWIN_WAYLAND_NO_PERMISSION_CHECKS": "1",
    "KWIN_SCREENSHOT_NO_PERMISSION_CHECKS": "1",
    "QT_ACCESSIBILITY": "1",
    "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1",
    "QT_QPA_PLATFORM": "wayland",
    "LIBGL_ALWAYS_SOFTWARE": "1",
    "KWIN_NO_ANIMATIONS": "1",
    "QT_NO_ANIMATIONS": "1",
    "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe",
    "LANG": "C.UTF-8",
}


_VALID_USERNAME = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def _validate_username(username: str) -> str:
    """Reject anything that is not a plain POSIX account name.

    shlex.quote() prevents shell injection but NOT path traversal: a value like
    ``../../etc`` still yields a path under /etc despite the ``/home/`` prefix,
    and seed_home() would then rm -rf it.
    """
    if not _VALID_USERNAME.match(username or ""):
        raise ValueError(
            f"refusing to operate on unsafe username {username!r}; "
            "expected a plain POSIX account name"
        )
    return username


def _home_for(username: str) -> str:
    """Return the validated home directory for ``username``."""
    home = posixpath.normpath(f"/home/{_validate_username(username)}")
    if not home.startswith("/home/") or home.count("/") != 2:
        raise ValueError(f"refusing to operate on unsafe home path {home!r}")
    return home


def _ssh(context, cmd: str, timeout: int = 60) -> None:
    """Run ``cmd`` on the DUT over SSH via the shared helper.

    The import is deferred so unit tests can avoid pulling in behave.
    """
    from tests.shared.ssh_steps import run_ssh

    try:
        run_ssh(context, cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        # run_ssh re-raises on timeout. Letting that escape would blow up a
        # capability probe (and the calling behave hook) instead of yielding a
        # clean skip, so record it as a failed command and carry on.
        context.ssh_rc = -1
        context.command_stdout = ""
        context.last_command_output = ""
    except OSError as exc:  # transport failure (host unreachable, key missing)
        context.ssh_rc = -1
        context.command_stdout = ""
        context.last_command_output = str(exc)


def _ssh_ok(context, cmd: str, timeout: int = 60) -> bool:
    """Run a command over SSH and return True iff it exits 0."""
    _ssh(context, cmd, timeout=timeout)
    return getattr(context, "ssh_rc", -1) == 0


def is_kde_session(context) -> bool:
    """Probe whether the DUT is currently running a KDE/Plasma session."""
    return _ssh_ok(context, "pgrep -x kwin_wayland >/dev/null")


def has_sddm(context) -> bool:
    """Probe whether SDDM is the active display manager."""
    return _ssh_ok(
        context,
        "test -L /etc/systemd/system/display-manager.service && "
        "readlink /etc/systemd/system/display-manager.service | grep -q sddm",
    )


def has_kwriteconfig6(context) -> bool:
    """Probe whether ``kwriteconfig6`` is available on the DUT."""
    return _ssh_ok(context, "command -v kwriteconfig6 >/dev/null")


def has_plasma_wayland_session(context) -> bool:
    """Probe whether the Plasma Wayland session desktop file exists."""
    return _ssh_ok(context, "test -f /usr/share/wayland-sessions/plasmawayland.desktop")


def _dropin_path(filename: str) -> str:
    return f"/etc/sddm.conf.d/{filename}"


def configure_sddm_autologin(
    context,
    username: str = "bluefin-test",
    session: Optional[str] = None,
) -> KDEResult:
    """Configure SDDM to auto-login ``username`` into a Plasma Wayland session.

    If SDDM is not the active display manager the step is skipped cleanly.
    The session name defaults to the upstream Plasma Wayland desktop file.
    """
    if not has_sddm(context):
        return KDEResult(
            ok=True,
            skipped=True,
            reason="SDDM is not the display manager",
        )

    if session is None:
        if has_plasma_wayland_session(context):
            session = "plasmawayland.desktop"
        else:
            return KDEResult(
                ok=False,
                reason="Plasma Wayland session desktop file not found",
            )

    lines = ["[Autologin]", f"User={username}", f"Session={session}"]
    content = "\n".join(lines) + "\n"
    dropin = _dropin_path("99-testsuite-autologin.conf")
    # /etc is not writable by the unprivileged SSH user; use non-interactive
    # sudo and surface a clear reason when privilege is unavailable.
    cmd = (
        "sudo -n mkdir -p /etc/sddm.conf.d && "
        f"printf '%s' {shlex.quote(content)} | sudo -n tee {dropin} >/dev/null && "
        f"sudo -n chmod 644 {dropin}"
    )
    if _ssh_ok(context, cmd):
        return KDEResult(ok=True, reason=f"SDDM autologin configured in {dropin}")

    return KDEResult(
        ok=False,
        reason=f"Failed to write SDDM autologin drop-in (rc={getattr(context, 'ssh_rc', -1)})",
    )


def suppress_welcome_wizard(context, username: str = "bluefin-test") -> KDEResult:
    """Suppress Plasma Welcome Center and distro first-run wizards.

    Also disables Plasma animations via ``kwriteconfig6``.  Skipped cleanly when
    ``kwriteconfig6`` is not installed.
    """
    if not has_kwriteconfig6(context):
        return KDEResult(
            ok=True,
            skipped=True,
            reason="kwriteconfig6 not available",
        )

    home = f"/home/{username}"
    config_dir = f"{home}/.config"
    commands = [
        f"mkdir -p {shlex.quote(config_dir)}",
        # Plasma Welcome Center
        "kwriteconfig6 --file plasma-welcomerc --group General --key ShowOnStartup false",
        # Global animation duration factor (instant / no animation)
        "kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0",
    ]

    # Sentinel files for known distro first-run wizards.  Add more as variants
    # are discovered; touching a missing sentinel is harmless.
    sentinel_files = [
        f"{config_dir}/plasma-welcome-done",
        f"{config_dir}/kde-neon-welcome",
        f"{config_dir}/aurora-welcome",
        f"{config_dir}/bazzite-welcome",
    ]
    for sentinel in sentinel_files:
        commands.append(f"touch {shlex.quote(sentinel)}")

    # Ensure the seeded home owns the files we just created.
    commands.append(f"chown -R {shlex.quote(username)}:{shlex.quote(username)} {shlex.quote(config_dir)}")

    if _ssh_ok(context, " && ".join(commands)):
        return KDEResult(
            ok=True,
            reason="Welcome wizard suppressed and animations disabled",
        )

    return KDEResult(
        ok=False,
        reason="Failed to suppress welcome wizard",
    )


def emit_determinism_dropin(context) -> KDEResult:
    """Write the systemd user-environment drop-in with deterministic KDE vars.

    The drop-in is read by ``systemd --user`` and propagated to graphical
    session units on systems where the display manager starts the user session
    via systemd.  It is paired with ``KWIN_NO_ANIMATIONS`` / ``QT_NO_ANIMATIONS``
    for processes that start outside the user manager.
    """
    lines = [f"{key}={value}" for key, value in DETERMINISM_ENV.items()]
    content = "\n".join(lines) + "\n"
    dropin = "/etc/environment.d/99-testsuite-kde.conf"
    cmd = (
        "mkdir -p /etc/environment.d && "
        f"printf '%s' {shlex.quote(content)} > {dropin} && "
        f"chmod 644 {dropin}"
    )
    if _ssh_ok(context, cmd):
        return KDEResult(ok=True, reason=f"Determinism drop-in written to {dropin}")

    return KDEResult(
        ok=False,
        reason=f"Failed to write determinism drop-in (rc={getattr(context, 'ssh_rc', -1)})",
    )


def seed_home(context, username: str = "bluefin-test", force: bool = False) -> KDEResult:
    """Reset the test user's home directory to a deterministic seed state.

    Refuses to run while a Plasma session is live unless ``force`` is set:
    deleting .config/.local/.cache under a running session leaves Plasma with
    stale in-memory state and destroys user data.
    """
    try:
        home = _home_for(username)
    except ValueError as exc:
        return KDEResult(ok=False, reason=str(exc))

    if not force and is_kde_session(context):
        return KDEResult(
            ok=False,
            reason=(
                "refusing to seed home while a Plasma session is running; "
                "seed before session start or pass force=True"
            ),
        )
    cmd = (
        f"rm -rf {shlex.quote(home)}/.cache "
        f"{shlex.quote(home)}/.config "
        f"{shlex.quote(home)}/.local && "
        f"mkdir -p {shlex.quote(home)}/.config "
        f"{shlex.quote(home)}/.local/share && "
        f"chown -R {shlex.quote(username)}:{shlex.quote(username)} {shlex.quote(home)}"
    )
    if _ssh_ok(context, cmd):
        return KDEResult(ok=True, reason=f"Seeded {home}")

    return KDEResult(ok=False, reason=f"Failed to seed {home}")


def wait_for_plasma_session(context, timeout: int = 120) -> KDEResult:
    """Poll until ``kwin_wayland``, ``plasmashell``, and AT-SPI are reachable.

    Uses exponential backoff capped at two seconds.  Callers should gate on
    ``is_kde_session()`` (or equivalent variant detection) before invoking this
    waiter so non-KDE DUTs can skip instead of timing out.
    """
    # One-shot SSH command that checks all three readiness signals.
    check_cmd = (
        "source /tmp/session.env 2>/dev/null; "
        "pgrep -x kwin_wayland >/dev/null && "
        "pgrep -x plasmashell >/dev/null && "
        "gdbus call --session --dest org.a11y.Bus "
        "--object-path /org/a11y/bus "
        "--method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1"
    )

    deadline = time.monotonic() + timeout
    attempt = 0
    last_reason = "no attempt made"

    while time.monotonic() < deadline:
        attempt += 1
        _ssh(context, check_cmd, timeout=10)
        if getattr(context, "ssh_rc", -1) == 0:
            return KDEResult(
                ok=True,
                reason=f"Plasma session ready after {attempt} attempt(s)",
            )

        stdout = getattr(context, "command_stdout", "")
        stderr = ""
        last_result = getattr(context, "last_ssh_result", None)
        if last_result is not None:
            stderr = getattr(last_result, "stderr", "") or ""
        last_reason = f"rc={getattr(context, 'ssh_rc', -1)} stdout={stdout!r} stderr={stderr[:200]!r}"

        # Exponential backoff: 0.2, 0.4, 0.8, ... capped at 2s.
        delay = min(2.0, 0.2 * (2 ** (attempt - 1)))
        time.sleep(delay)

    return KDEResult(
        ok=False,
        reason=f"Plasma session not ready after {timeout}s: {last_reason}",
    )


def apply_kde_session_preconditions(
    context,
    username: str = "bluefin-test",
) -> KDEResult:
    """Orchestrate the full KDE session precondition pipeline.

    Returns a skip result when the DUT is not a KDE/Plasma session.  Individual
    capabilities (SDDM, kwriteconfig6) skip their own steps cleanly rather than
    failing.
    """
    if not is_kde_session(context):
        return KDEResult(
            ok=True,
            skipped=True,
            reason="DUT is not running a KDE/Plasma session",
        )

    # (name, step, fatal). Home seeding is deliberately NON-fatal: it is a
    # pre-session operation. This function only runs once a Plasma session is
    # already live, so seed_home() will refuse rather than wipe .config out from
    # under a running session. Seeding must happen at disk-prep time instead.
    steps = [
        ("seed home", lambda: seed_home(context, username=username), False),
        ("determinism drop-in", lambda: emit_determinism_dropin(context), True),
        ("SDDM autologin", lambda: configure_sddm_autologin(context, username=username), True),
        ("welcome wizard suppression", lambda: suppress_welcome_wizard(context, username=username), True),
    ]
    notes: list[str] = []
    for name, step, fatal in steps:
        result = step()
        if result.ok:
            continue
        if fatal:
            return KDEResult(ok=False, reason=f"{name} failed: {result.reason}")
        notes.append(f"{name} skipped: {result.reason}")

    ready = wait_for_plasma_session(context)
    if not ready.ok:
        return KDEResult(
            ok=False,
            reason=f"session readiness failed: {ready.reason}",
        )

    reason = "KDE session preconditions applied"
    if notes:
        reason = f"{reason} ({'; '.join(notes)})"
    return KDEResult(ok=True, reason=reason)
