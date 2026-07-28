"""KDE session preconditions for SSH-driven test runs.

Helpers that configure a DUT into a deterministic, automatable KDE/Plasma
desktop state.  Every helper operates over the shared SSH runner and returns a
structured ``KDEResult`` so callers can skip (not fail) when KDE is absent or
incomplete — the Tast ``SoftwareDeps`` model.

Operations are split into two lifecycle phases:

**Disk-prep** (before first boot): autologin drop-in, determinism environment
drop-in, and home seeding.  These write to ``/etc`` and ``/home`` and only take
effect after a reboot.  Entry point: ``apply_disk_prep()``.

**Runtime** (after boot, with a live Plasma session): wait for Plasma readiness,
verify AT-SPI, suppress welcome wizards.  Entry point:
``apply_kde_session_preconditions()`` (kept as the public API for callers that
already use it, e.g. ``tests/kde-smoke/features/environment.py``).
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


# ---------------------------------------------------------------------------
# Session & display-manager constants
# ---------------------------------------------------------------------------

# The Plasma 6 Wayland session desktop file.
# IMPORTANT: ``plasmawayland.desktop`` lives in ``/usr/share/wayland-sessions/``
# and is the WAYLAND session.  ``plasma.desktop`` in ``/usr/share/xsessions/``
# is the X11 session — using it would silently start an X11 session instead.
KDE_WAYLAND_SESSION = "plasmawayland.desktop"

# Drop-in filename for the autologin configuration.  Written under whichever
# display-manager conf.d directory is active (SDDM or PLM).
# Prefix ``99-`` ensures this drop-in wins over any lower-numbered defaults
# (e.g. ``00-ci-autologin.conf`` from the e2e workflow).  The high precedence
# is intentional: the testsuite's autologin must be the final word.
AUTOLOGIN_DROPIN_FILENAME = "99-testsuite-autologin.conf"


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


# ---------------------------------------------------------------------------
# Capability probes
# ---------------------------------------------------------------------------

def is_kde_session(context) -> bool:
    """Probe whether the DUT is currently running a KDE/Plasma session."""
    return _ssh_ok(context, "pgrep -x kwin_wayland >/dev/null")


def is_kde_image(image_ref: str) -> bool:
    """Return True when ``image_ref`` names a KDE/Plasma variant.

    Recognises Aurora, Kinoite, Bazzite, and generic kde/plasma tokens.
    This is a pure string check — no SSH required.
    """
    if not image_ref:
        return False
    name = image_ref.lower().split("/")[-1].split(":")[0].split("@")[0]
    return any(
        token in name
        for token in ("aurora", "kinoite", "bazzite", "kde", "plasma")
    )


def has_sddm(context) -> bool:
    """Probe whether SDDM is the active display manager."""
    return _ssh_ok(
        context,
        "test -L /etc/systemd/system/display-manager.service && "
        "readlink /etc/systemd/system/display-manager.service | grep -q sddm",
    )


def has_plm(context) -> bool:
    """Probe whether Plasma Login Manager (PLM) is the active display manager.

    PLM replaces SDDM starting with Fedora 44 / Plasma 6.7.  We check the
    display-manager.service symlink for ``plasma-login-manager`` — the same
    approach used by ``has_sddm()``, which is the most reliable indicator
    because it reflects what systemd will actually start, regardless of which
    packages are installed.
    """
    return _ssh_ok(
        context,
        "test -L /etc/systemd/system/display-manager.service && "
        "readlink /etc/systemd/system/display-manager.service | grep -q plasma-login-manager",
    )


def detect_display_manager(context) -> str:
    """Detect which KDE-compatible display manager is active on the DUT.

    Returns ``"sddm"``, ``"plm"``, or ``"unknown"``.  The check reads the
    ``display-manager.service`` symlink, which reflects what systemd will
    actually start — more robust than checking installed packages or config
    directory existence.
    """
    if has_sddm(context):
        return "sddm"
    if has_plm(context):
        return "plm"
    return "unknown"


def _dm_conf_dir(dm: str) -> str:
    """Return the drop-in config directory for the given display manager."""
    if dm == "sddm":
        return "/etc/sddm.conf.d"
    if dm == "plm":
        return "/etc/plasmalogin.conf.d"
    raise ValueError(f"no config directory for unknown display manager {dm!r}")


def has_kwriteconfig6(context) -> bool:
    """Probe whether ``kwriteconfig6`` is available on the DUT."""
    return _ssh_ok(context, "command -v kwriteconfig6 >/dev/null")


def has_plasma_wayland_session(context) -> bool:
    """Probe whether the Plasma Wayland session desktop file exists."""
    return _ssh_ok(context, "test -f /usr/share/wayland-sessions/plasmawayland.desktop")


# ---------------------------------------------------------------------------
# Disk-prep helpers (run BEFORE first boot)
# ---------------------------------------------------------------------------

def configure_autologin(
    context,
    username: str = "bluefin-test",
    session: Optional[str] = None,
) -> KDEResult:
    """Configure the display manager to auto-login ``username`` into Plasma Wayland.

    Detects whether the DUT uses SDDM or PLM and writes the autologin drop-in
    to the correct config directory.  If neither DM is detected, returns a clear
    failure — never silently pretends success.

    The ``[Autologin]`` INI syntax is identical for both SDDM and PLM.
    """
    dm = detect_display_manager(context)
    if dm == "unknown":
        return KDEResult(
            ok=False,
            reason=(
                "Neither SDDM nor PLM detected as display manager; "
                "cannot configure autologin. Check display-manager.service symlink."
            ),
        )

    if session is None:
        if has_plasma_wayland_session(context):
            session = KDE_WAYLAND_SESSION
        else:
            return KDEResult(
                ok=False,
                reason="Plasma Wayland session desktop file not found",
            )

    conf_dir = _dm_conf_dir(dm)
    lines = ["[Autologin]", f"User={username}", f"Session={session}"]
    content = "\n".join(lines) + "\n"
    dropin = f"{conf_dir}/{AUTOLOGIN_DROPIN_FILENAME}"
    cmd = (
        f"sudo -n mkdir -p {conf_dir} && "
        f"printf '%s' {shlex.quote(content)} | sudo -n tee {dropin} >/dev/null && "
        f"sudo -n chmod 644 {dropin}"
    )
    if _ssh_ok(context, cmd):
        return KDEResult(ok=True, reason=f"{dm.upper()} autologin configured in {dropin}")

    return KDEResult(
        ok=False,
        reason=f"Failed to write {dm.upper()} autologin drop-in (rc={getattr(context, 'ssh_rc', -1)})",
    )


def configure_sddm_autologin(
    context,
    username: str = "bluefin-test",
    session: Optional[str] = None,
) -> KDEResult:
    """Configure SDDM to auto-login ``username`` into a Plasma Wayland session.

    .. deprecated::
        Use :func:`configure_autologin` which handles both SDDM and PLM.
        This wrapper is kept for backwards compatibility; it delegates to
        ``configure_autologin`` and maps "unknown DM" → skip (preserving the
        old "skip when SDDM absent" behaviour).
    """
    result = configure_autologin(context, username=username, session=session)
    # Old callers expect a skip when SDDM is absent, not a hard failure.
    if not result.ok and "Neither SDDM nor PLM" in result.reason:
        return KDEResult(
            ok=True,
            skipped=True,
            reason="Neither SDDM nor PLM is the display manager",
        )
    return result


def emit_determinism_dropin(context) -> KDEResult:
    """Write the systemd user-environment drop-in with deterministic KDE vars.

    The drop-in is read by ``systemd --user`` and propagated to graphical
    session units on systems where the display manager starts the user session
    via systemd.  It is paired with ``KWIN_NO_ANIMATIONS`` / ``QT_NO_ANIMATIONS``
    for processes that start outside the user manager.

    This is a **disk-prep** operation: the drop-in only takes effect on the
    NEXT boot when ``systemd --user`` re-reads ``/etc/environment.d/``.
    """
    lines = [f"{key}={value}" for key, value in DETERMINISM_ENV.items()]
    content = "\n".join(lines) + "\n"
    dropin = "/etc/environment.d/99-testsuite-kde.conf"
    # /etc is not writable by the unprivileged SSH user on immutable
    # bootc/ostree images; use non-interactive sudo.
    cmd = (
        "sudo -n mkdir -p /etc/environment.d && "
        f"printf '%s' {shlex.quote(content)} | sudo -n tee {dropin} >/dev/null && "
        f"sudo -n chmod 644 {dropin}"
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


def apply_disk_prep(
    context,
    username: str = "bluefin-test",
) -> KDEResult:
    """Apply all disk-prep preconditions (before first boot).

    This writes autologin config, the determinism environment drop-in, seeds
    the home directory, and suppresses the welcome wizard.  All of these modify
    on-disk state and take effect on the next boot.

    Must be called BEFORE the first boot when the session is NOT yet running.
    On an immutable bootc/ostree image, ``sudo -n`` is required for ``/etc``
    writes.
    """
    steps = [
        ("autologin", lambda: configure_autologin(context, username=username)),
        ("determinism drop-in", lambda: emit_determinism_dropin(context)),
        ("seed home", lambda: seed_home(context, username=username)),
        ("welcome wizard suppression", lambda: suppress_welcome_wizard(context, username=username)),
    ]
    notes: list[str] = []
    for name, step in steps:
        result = step()
        if result.ok:
            if result.skipped:
                notes.append(f"{name} skipped: {result.reason}")
            continue
        return KDEResult(ok=False, reason=f"disk-prep {name} failed: {result.reason}")

    reason = "Disk-prep preconditions applied"
    if notes:
        reason = f"{reason} ({'; '.join(notes)})"
    return KDEResult(ok=True, reason=reason)


# ---------------------------------------------------------------------------
# Runtime helpers (run AFTER boot, with a live Plasma session)
# ---------------------------------------------------------------------------

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


def ensure_kde_session(context, username: str = "bluefin-test") -> KDEResult:
    """Runtime entry point: wait for Plasma and apply runtime-only preconditions.

    This is the counterpart to :func:`apply_disk_prep`.  It assumes disk-prep
    has already been done (by the e2e workflow or :func:`apply_disk_prep`) and
    only performs operations that are valid/useful against a live session:

    1. Wait for the Plasma session to be ready (kwin_wayland, plasmashell, AT-SPI).
    2. Suppress the welcome wizard (writes to ``$HOME``, not ``/etc``).

    Callers (e.g. ``tests/kde-smoke/features/environment.py``) import this as
    the runtime phase entry point.
    """
    ready = wait_for_plasma_session(context)
    if not ready.ok:
        return KDEResult(
            ok=False,
            reason=f"session readiness failed: {ready.reason}",
        )

    wizard = suppress_welcome_wizard(context, username=username)
    if not wizard.ok and not wizard.skipped:
        return KDEResult(
            ok=False,
            reason=f"welcome wizard suppression failed: {wizard.reason}",
        )

    return KDEResult(ok=True, reason="KDE session ready and configured")


def apply_kde_session_preconditions(
    context,
    username: str = "bluefin-test",
) -> KDEResult:
    """Orchestrate runtime KDE session preconditions.

    Returns a skip result when the DUT is not a KDE/Plasma session.

    This is the **runtime** phase — it runs AFTER boot with a live session.
    Disk-prep operations (autologin, determinism drop-in) are NOT attempted
    here; they belong in :func:`apply_disk_prep` or the e2e workflow's
    disk-prep step.  Re-applying next-boot-only operations at runtime is
    pointless work that can only fail on immutable images.

    The pipeline:
    1. ``seed_home`` — non-fatal; deliberately refuses when a session is live.
    2. ``suppress_welcome_wizard`` — writes to ``$HOME``, safe at runtime.
    3. ``wait_for_plasma_session`` — polls for kwin_wayland + plasmashell + AT-SPI.
    """
    if not is_kde_session(context):
        return KDEResult(
            ok=True,
            skipped=True,
            reason="DUT is not running a KDE/Plasma session",
        )

    # Seed home is deliberately non-fatal: it is a pre-session operation.
    # This function runs once a Plasma session is already live, so seed_home()
    # will refuse rather than wipe .config out from under a running session.
    notes: list[str] = []
    seed_result = seed_home(context, username=username)
    if not seed_result.ok:
        notes.append(f"seed home skipped: {seed_result.reason}")

    wizard_result = suppress_welcome_wizard(context, username=username)
    if not wizard_result.ok and not wizard_result.skipped:
        notes.append(f"welcome wizard skipped: {wizard_result.reason}")

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
