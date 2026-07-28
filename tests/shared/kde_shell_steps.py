"""Shared KDE Plasma D-Bus control plane helpers.

These functions provide read-only diagnostics, state inspection, layout dumps,
and between-scenario session reset for KDE Plasma desktops. They are the
structural analogue of :mod:`tests.shared.gnome_shell_steps` for KDE.

CRITICAL SCOPE RULE
-------------------
``org.kde.PlasmaShell.evaluateScript`` and KWin scripting are for **diagnostics,
state inspection, layout dumps, and between-scenario session reset ONLY**.

Real users do not drive Plasma through ``evaluateScript`` or KWin scripts. A
test that opens Kickoff or changes a setting through these APIs validates a
debugging path that ships to nobody and would pass while the real UI is broken.
Actual user interaction must go through AT-SPI/WebDriver or app-specific CLI /
D-Bus entry points (``kcmshell6``, KRunner, desktop-file activation) that mirror
what a user actually triggers.

Do not expand this module to perform primary user-facing interactions.
"""

from __future__ import annotations

import os
import base64
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from tests.shared.ssh_steps import run_ssh

# When behave runs inside the runner container the host VM's session bus socket
# is inaccessible (systemd user bus rejects cgroup-external connections).
# Route gdbus calls to the VM via SSH instead.
_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")

# Substrings emitted when PlasmaShell scripting is disabled by policy or by
# the desktop being system-immutable ("widgets locked"). Kept generic enough
# to catch both the KAuthorized refusal and the immutability refusal.
_JOURNAL_MAX_LINES = 2000
_JOURNAL_MAX_BYTES = 262144

_PLASMA_SCRIPTING_DISABLED_HINTS = (
    "widgets are locked",
    "widget are locked",
    "forbidden",
    "kauthorized",
    "scripting_console",
    "not authorized",
)


class PlasmaScriptingDisabledError(RuntimeError):
    """Raised when PlasmaShell scripting is refused by policy or immutability."""


class DbusCapabilityError(RuntimeError):
    """Raised when the requested KDE D-Bus service or object is not available."""


def _dbus_command(
    service: str,
    path: str,
    interface: str,
    method: str,
    args: tuple[str, ...] = (),
) -> list[str]:
    """Build the argv for a gdbus call."""
    return [
        "gdbus",
        "call",
        "--session",
        "--dest",
        service,
        "--object-path",
        path,
        "--method",
        f"{interface}.{method}",
        *args,
    ]


def _dbus_call(
    context,
    service: str,
    path: str,
    interface: str,
    method: str,
    args: tuple[str, ...] = (),
    timeout: int = 30,
) -> tuple[str, int]:
    """Invoke a D-Bus method and return ``(stdout, returncode)``.

    Uses SSH when running inside the runner container so the call reaches the
    VM's session bus; otherwise calls gdbus locally.
    """
    argv = _dbus_command(service, path, interface, method, args)

    if _IN_CONTAINER:
        quoted = [shlex.quote(str(arg)) for arg in argv]
        cmd = f"source /tmp/session.env 2>/dev/null; {' '.join(quoted)}"
        stdout, rc = run_ssh(context, cmd, timeout=timeout)
        return stdout, rc

    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    # Merge stderr into the returned payload: gdbus reports the KAuthorized /
    # widgets-locked refusal on stderr, and dropping it made local runs
    # misclassify a policy refusal as a generic D-Bus failure, so callers could
    # not turn it into a clean skip.
    combined = result.stdout if not result.stderr else f"{result.stdout}\n{result.stderr}"
    return combined, result.returncode


def _raise_if_disabled(service: str, stderr: str, stdout: str) -> None:
    """Detect PlasmaShell scripting refusal and raise a capability error."""
    combined = f"{stderr}\n{stdout}".lower()
    if any(hint in combined for hint in _PLASMA_SCRIPTING_DISABLED_HINTS):
        raise PlasmaScriptingDisabledError(
            "PlasmaShell scripting is disabled on this desktop "
            "(widgets locked or KAuthorized policy refuses plasma-desktop/scripting_console)."
        )


def _service_present(context, service: str, path: str, timeout: int = 5) -> bool:
    """Return whether ``service``/``path`` is introspectable on the session bus."""
    stdout, rc = _dbus_call(
        context,
        service,
        path,
        "org.freedesktop.DBus.Introspectable",
        "Introspect",
        timeout=timeout,
    )
    return rc == 0 and "<interface" in stdout


def wait_until(predicate, timeout: float = 30.0, interval: float = 0.5):
    """Poll ``predicate`` until it returns a truthy value or time expires.

    Uses mild exponential backoff capped at two seconds. This is the module
    every other KDE helper uses for synchronization; do not use bare
    ``time.sleep()`` as a readiness mechanism.

    Returns the truthy result from ``predicate`` on success.
    Raises :exc:`TimeoutError` if the predicate never returns truthy.
    """
    deadline = time.monotonic() + timeout
    sleep_for = interval
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"predicate did not become true within {timeout:.1f}s"
            )
        time.sleep(sleep_for)
        sleep_for = min(sleep_for * 1.5, 2.0)


def plasma_available(context) -> bool:
    """Return ``True`` if the PlasmaShell D-Bus service is reachable."""
    return _service_present(context, "org.kde.plasmashell", "/PlasmaShell")


def kwin_available(context) -> bool:
    """Return ``True`` if the KWin D-Bus service is reachable."""
    return _service_present(context, "org.kde.KWin", "/KWin")


def plasma_eval(context, script: str, timeout: int = 30) -> str:
    """Evaluate ``script`` in plasmashell via ``org.kde.PlasmaShell.evaluateScript``.

    Raises :exc:`PlasmaScriptingDisabledError` when the desktop refuses
    scripting because widgets are locked or KAuthorized policy denies it.
    Callers can turn this into a scenario skip.

    Raises :exc:`DbusCapabilityError` when the PlasmaShell service is not
    present or the call otherwise fails.
    """
    stdout, rc = _dbus_call(
        context,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell",
        "evaluateScript",
        args=(script,),
        timeout=timeout,
    )
    if rc != 0:
        # gdbus writes errors to stderr; when routed through SSH that stderr is
        # attached to the CompletedProcess returned by run_ssh but not echoed in
        # stdout. Look at the last SSH result for the raw service error.
        last = getattr(context, "last_ssh_result", None)
        stderr = last.stderr if last is not None else ""
        _raise_if_disabled("org.kde.plasmashell", stderr, stdout)
        raise DbusCapabilityError(
            f"plasma_eval failed (rc={rc}): {stdout.strip() or stderr.strip() or 'no output'}"
        )
    return stdout


def dump_layout_js(context, timeout: int = 30) -> str:
    """Return the output of ``org.kde.PlasmaShell.dumpCurrentLayoutJS()``.

    This is a diagnostic golden-snapshot source for the live panel/widget
    layout. It is read-only and never drives user interaction.
    """
    stdout, rc = _dbus_call(
        context,
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell",
        "dumpCurrentLayoutJS",
        timeout=timeout,
    )
    if rc != 0:
        last = getattr(context, "last_ssh_result", None)
        stderr = last.stderr if last is not None else ""
        _raise_if_disabled("org.kde.plasmashell", stderr, stdout)
        raise DbusCapabilityError(
            f"dumpCurrentLayoutJS failed (rc={rc}): {stdout.strip() or stderr.strip() or 'no output'}"
        )
    return stdout


def kwin_support_info(context, timeout: int = 30) -> str:
    """Return ``org.kde.KWin.supportInformation()`` text for failure diagnostics."""
    stdout, rc = _dbus_call(
        context,
        "org.kde.KWin",
        "/KWin",
        "org.kde.KWin",
        "supportInformation",
        timeout=timeout,
    )
    if rc != 0:
        last = getattr(context, "last_ssh_result", None)
        stderr = last.stderr if last is not None else ""
        raise DbusCapabilityError(
            f"kwin_support_info failed (rc={rc}): {stdout.strip() or stderr.strip() or 'no output'}"
        )
    return stdout


def _write_target_file(context, path: str, contents: str) -> None:
    """Write ``contents`` to ``path`` on the local machine or the SSH target."""
    if _IN_CONTAINER:
        # Transfer base64-encoded rather than via a heredoc: a script containing
        # a line equal to the heredoc delimiter would terminate it early and let
        # the following lines execute as shell commands on the target.
        payload = base64.b64encode(contents.encode("utf-8")).decode("ascii")
        run_ssh(
            context,
            f"printf %s {shlex.quote(payload)} | base64 -d > {shlex.quote(path)}",
        )
    else:
        Path(path).write_text(contents)


def _remove_target_file(context, path: str) -> None:
    """Remove ``path`` from the local machine or the SSH target."""
    if _IN_CONTAINER:
        run_ssh(context, f"rm -f {shlex.quote(path)}")
    else:
        Path(path).unlink(missing_ok=True)


def _journal_output(context, name: str, timeout: int = 10) -> str:
    """Collect ``print()`` output from a KWin script via the user journal.

    KWin scripts cannot write files directly, so scripts communicate results
    through ``print()`` calls that land in the systemd user journal tagged
    with ``js:``. This helper reads the last few seconds of journal output
    and filters for lines belonging to the named script.
    """
    # Bounded: a diagnostic script can emit unlimited output, so cap both the
    # number of journal lines read and the bytes returned.
    cmd = (
        "journalctl --user -u plasma-kwin_wayland.service --since '5 seconds ago' "
        f"-n {_JOURNAL_MAX_LINES} -o cat | grep -F 'js:' | head -c {_JOURNAL_MAX_BYTES} || true"
    )
    if _IN_CONTAINER:
        stdout, _rc = run_ssh(context, cmd, timeout=timeout)
    else:
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout
    # The KWin journal prefix is ``kwin_scripting: <name>: js: <message>``.
    prefix = f"{name}:"
    lines = []
    for line in stdout.splitlines():
        if "js:" not in line:
            continue
        # Strip the leading kwin_scripting prefix if present.
        js_part = line.split("js:", 1)[1].lstrip()
        if js_part.startswith(prefix):
            lines.append(js_part[len(prefix) :].lstrip())
        elif name in line:
            lines.append(js_part)
    return "\n".join(lines)


def kwin_script(context, script_source: str, timeout: int = 30) -> str:
    """Load, run, and unload a KWin script, returning captured ``print()`` output.

    A temporary file is written on the target, loaded with a unique plugin
    name, started, and cleaned up even if any step raises. Output produced by
    ``print()`` calls inside the script is captured from the user journal.

    This is intended for diagnostics and session reset only; see the module
    docstring for the scope rule.
    """
    name = f"testsuite_{uuid.uuid4().hex}"
    path = f"/tmp/kde_kwin_{name}.js"

    _write_target_file(context, path, script_source)

    try:
        stdout, rc = _dbus_call(
            context,
            "org.kde.KWin",
            "/Scripting",
            "org.kde.kwin.Scripting",
            "loadScript",
            args=(path, name),
            timeout=timeout,
        )
        if rc != 0:
            last = getattr(context, "last_ssh_result", None)
            stderr = last.stderr if last is not None else ""
            raise DbusCapabilityError(
                f"loadScript failed (rc={rc}): {stdout.strip() or stderr.strip() or 'no output'}"
            )

        stdout, rc = _dbus_call(
            context,
            "org.kde.KWin",
            "/Scripting",
            "org.kde.kwin.Scripting",
            "start",
            timeout=timeout,
        )
        if rc != 0:
            last = getattr(context, "last_ssh_result", None)
            stderr = last.stderr if last is not None else ""
            raise DbusCapabilityError(
                f"start failed (rc={rc}): {stdout.strip() or stderr.strip() or 'no output'}"
            )

        def _script_finished() -> bool:
            out, rc = _dbus_call(
                context,
                "org.kde.KWin",
                "/Scripting",
                "org.kde.kwin.Scripting",
                "isScriptLoaded",
                args=(name,),
                timeout=10,
            )
            return rc == 0 and "false" in out.lower()

        try:
            wait_until(_script_finished, timeout=timeout, interval=0.5)
        except TimeoutError as exc:
            raise DbusCapabilityError(
                f"KWin script '{name}' did not finish within {timeout}s"
            ) from exc

        return _journal_output(context, name)
    finally:
        # Always attempt unload and file cleanup; never let a failure in the
        # body leak a loaded script or temp file.
        try:
            _dbus_call(
                context,
                "org.kde.KWin",
                "/Scripting",
                "org.kde.kwin.Scripting",
                "unloadScript",
                args=(name,),
                timeout=10,
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            _remove_target_file(context, path)
        except Exception:  # noqa: BLE001
            pass
