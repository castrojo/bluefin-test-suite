"""Failure-artifact bundle for KDE/Plasma scenarios, modelled on ChromeOS Tast faillog.

Triggered from after_scenario whenever a scenario ends with status failed, error, or
hook_error. Collectors run over SSH (or locally for QEMU screendump) and each collector
is fault-isolated: a failure in one collector does not stop the others and is recorded
in the bundle manifest.
"""

import json
import os
import re
import subprocess
import sys
import tarfile
import time
from typing import Any

from tests.shared import qemu_screendump
from tests.shared.ssh_steps import run_ssh


# Status values that trigger artifact collection.
FAILURE_STATUSES = frozenset({"failed", "error", "hook_error"})

# Default bounds for captured artifacts. These are intentionally conservative so the
# bundle stays small enough to upload as a CI artifact.
DEFAULT_JOURNAL_LINES = 2000
DEFAULT_COREDUMP_LINES = 100

# AT-SPI tree dump script executed on the VM via SSH. It imports pyatspi and walks the
# accessibility tree. Every node access is wrapped so a transient failure in one branch
# does not abort the whole dump.
_AT_SPI_DUMP_SCRIPT = r'''import sys
try:
    import pyatspi
except Exception as exc:
    print(f"Cannot import pyatspi: {exc}", file=sys.stderr)
    sys.exit(1)


def _state_names(node):
    try:
        return [str(s) for s in node.getState().getStates()]
    except Exception:
        return []


def _dump_node(node, depth=0):
    try:
        role = node.getRoleName()
    except Exception as exc:
        print(f"{'  ' * depth}[role-error] {exc}")
        return
    try:
        name = node.name or ""
    except Exception:
        name = ""
    try:
        description = node.description or ""
    except Exception:
        description = ""
    states = _state_names(node)
    print(f"{'  ' * depth}[{role}] name={name!r} description={description!r} states={states}")
    try:
        count = node.childCount
    except Exception:
        return
    for i in range(count):
        try:
            child = node.getChildAtIndex(i)
        except Exception as exc:
            print(f"{'  ' * depth}  [child-error idx={i}] {exc}")
            continue
        if child is not None:
            _dump_node(child, depth + 1)


try:
    desktop = pyatspi.Registry.getDesktop(0)
except Exception as exc:
    print(f"Cannot get desktop: {exc}", file=sys.stderr)
    sys.exit(1)

for app in desktop:
    try:
        name = app.name or "<unnamed>"
    except Exception:
        name = "<unnamed>"
    print(f"APPLICATION: {name}")
    _dump_node(app)
'''


def _results_dir(context: Any | None = None) -> str:
    """Resolve output dir: userdata > env var > default /tmp/results."""
    if context is not None:
        config = getattr(context, "config", None)
        if config and hasattr(config, "userdata"):
            value = config.userdata.get("results_dir")
            if value:
                return value
    return os.environ.get("TESTSUITE_RESULTS_DIR", "/tmp/results")


def _safe_fragment(value: str | None, fallback: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", (value or fallback).lower()).strip("_")
    return safe[:60] or fallback


def _bundle_dir(results_dir: str, scenario) -> str:
    """Return a unique bundle directory path for the failed scenario."""
    feature = _safe_fragment(getattr(getattr(scenario, "feature", None), "name", None), "feature")
    name = _safe_fragment(getattr(scenario, "name", None), "scenario")
    status_obj = getattr(scenario, "status", None)
    status = _safe_fragment(getattr(status_obj, "name", None), "unknown")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base = f"faillog_{feature}_{name}_{status}_{timestamp}"
    return os.path.join(results_dir, base)


def _write_text(bundle_dir: str, filename: str, content: str) -> None:
    path = os.path.join(bundle_dir, filename)
    with open(path, "w", encoding="utf-8", errors="replace") as file_obj:
        file_obj.write(content)


def _run_ssh_collector(context, cmd: str, timeout: int) -> tuple[str, int]:
    """Run an SSH command and return (stdout, rc) without letting exceptions escape.

    run_ssh mutates context attributes, which is acceptable after a scenario has ended.
    """
    try:
        stdout, rc = run_ssh(context, cmd, timeout=timeout)
        return stdout, rc
    except subprocess.TimeoutExpired:
        return "", -1
    except Exception:  # noqa: BLE001
        return "", -2


def _ssh_env_prefix() -> str:
    """Source the session environment so D-Bus and Wayland vars are available."""
    return "source /tmp/session.env 2>/dev/null && "


def _check_ssh(stdout: str, rc: int, label: str, allowed_rcs: tuple[int, ...] = (0,)) -> None:
    """Raise a descriptive error if an SSH collector did not succeed.

    rc=-1 is reserved for SSH/command timeout; rc=-2 is reserved for unexpected
    SSH helper failure.
    """
    if rc == -1:
        raise TimeoutError(f"{label} timed out")
    if rc not in allowed_rcs:
        raise RuntimeError(f"{label} exited rc={rc}; stdout={stdout[:500]!r}")


def collect_at_spi_tree(context, bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """Dump the AT-SPI accessibility tree over SSH."""
    cmd = f"{_ssh_env_prefix()}python3 -c {_quote_script(_AT_SPI_DUMP_SCRIPT)}"
    stdout, rc = _run_ssh_collector(context, cmd, timeout)
    _check_ssh(stdout, rc, "AT-SPI tree dump")
    _write_text(bundle_dir, "atspi_tree.txt", stdout)
    return {"rc": rc, "lines": len(stdout.splitlines())}


def collect_journalctl(context, bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """Capture the current boot journal with a bounded line count."""
    lines = int(os.environ.get("KDE_FAILLOG_JOURNAL_LINES", str(DEFAULT_JOURNAL_LINES)))
    cmd = f"journalctl -b --no-pager --lines={lines}"
    stdout, rc = _run_ssh_collector(context, cmd, timeout)
    _check_ssh(stdout, rc, "journalctl")
    _write_text(bundle_dir, "journalctl.log", stdout)
    return {"rc": rc, "lines": len(stdout.splitlines()), "capped_at": lines}


def collect_kwin_support_info(context, bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """Call org.kde.KWin.supportInformation() over the session bus."""
    cmd = (
        f"{_ssh_env_prefix()}"
        "gdbus call --session --dest org.kde.KWin "
        "--object-path /KWin --method org.kde.KWin.supportInformation"
    )
    stdout, rc = _run_ssh_collector(context, cmd, timeout)
    _check_ssh(stdout, rc, "KWin.supportInformation")
    _write_text(bundle_dir, "kwin_support_info.txt", stdout)
    return {"rc": rc, "lines": len(stdout.splitlines())}


def collect_plasma_layout(context, bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """Call org.kde.PlasmaShell.dumpCurrentLayoutJS() over the session bus."""
    cmd = (
        f"{_ssh_env_prefix()}"
        "gdbus call --session --dest org.kde.plasmashell "
        "--object-path /PlasmaShell --method org.kde.PlasmaShell.dumpCurrentLayoutJS"
    )
    stdout, rc = _run_ssh_collector(context, cmd, timeout)
    _check_ssh(stdout, rc, "dumpCurrentLayoutJS")
    _write_text(bundle_dir, "plasma_layout.js", stdout)
    return {"rc": rc, "lines": len(stdout.splitlines())}


def collect_coredumpctl(context, bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """List recent coredumps with a bounded line count."""
    lines = int(os.environ.get("KDE_FAILLOG_COREDUMP_LINES", str(DEFAULT_COREDUMP_LINES)))
    cmd = f"coredumpctl list --no-pager --lines={lines}"
    stdout, rc = _run_ssh_collector(context, cmd, timeout)
    # coredumpctl returns 1 when there are no entries, which is still useful output.
    _check_ssh(stdout, rc, "coredumpctl", allowed_rcs=(0, 1))
    _write_text(bundle_dir, "coredumpctl.txt", stdout)
    return {"rc": rc, "lines": len(stdout.splitlines()), "capped_at": lines}


def collect_qemu_screendump(bundle_dir: str, timeout: int = 30) -> dict[str, Any]:
    """Trigger a QEMU screendump and copy the resulting PNG into the bundle."""
    png_path = os.path.join(bundle_dir, "qemu_screendump.png")
    script_path = qemu_screendump.__file__
    try:
        result = subprocess.run(
            [sys.executable, script_path, png_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError("QEMU screendump timed out") from None
    except Exception:  # noqa: BLE001
        raise RuntimeError("QEMU screendump failed") from None
    if result.returncode != 0:
        raise RuntimeError(
            f"QEMU screendump exited rc={result.returncode}; "
            f"stdout={result.stdout[:500]!r} stderr={result.stderr[:500]!r}"
        )
    if not os.path.exists(png_path):
        raise RuntimeError("QEMU screendump did not produce a PNG")
    return {"rc": result.returncode, "path": png_path}


def _quote_script(script: str) -> str:
    """Return a single-quoted shell literal for a Python script string."""
    return "'" + script.replace("'", "'\"'\"'") + "'"


# Ordered list of collectors. Each entry is (collector_name, timeout_seconds, local).
# The name is resolved at call time via globals() so tests can patch individual
# collectors by name. "local" means the collector runs on the runner host rather
# than over SSH.
COLLECTORS = [
    ("collect_at_spi_tree", 30, False),
    ("collect_journalctl", 30, False),
    ("collect_kwin_support_info", 30, False),
    ("collect_plasma_layout", 30, False),
    ("collect_coredumpctl", 30, False),
    ("collect_qemu_screendump", 60, True),
]


def after_scenario(context, scenario) -> str | None:
    """Entry point for behave environment.py after_scenario hooks.

    Returns the bundle directory path if artifacts were collected, otherwise None.
    """
    status_obj = getattr(scenario, "status", None)
    status = getattr(status_obj, "name", None)
    if status not in FAILURE_STATUSES:
        return None

    results_dir = _results_dir(context)
    try:
        os.makedirs(results_dir, exist_ok=True)
    except OSError as exc:
        print(f"kde_faillog: cannot create results dir {results_dir}: {exc}", flush=True)
        return None

    bundle_dir = _bundle_dir(results_dir, scenario)
    try:
        os.makedirs(bundle_dir, exist_ok=True)
    except OSError as exc:
        print(f"kde_faillog: cannot create bundle dir {bundle_dir}: {exc}", flush=True)
        return None

    manifest = {
        "scenario": getattr(scenario, "name", "unknown"),
        "feature": getattr(getattr(scenario, "feature", None), "name", "unknown"),
        "status": status,
        "bundle_dir": bundle_dir,
        "results_dir": results_dir,
        "collectors": {},
        "errors": [],
    }

    for collector_name, timeout, local in COLLECTORS:
        started_at = time.monotonic()
        try:
            collector = globals()[collector_name]
            if local:
                info = collector(bundle_dir, timeout=timeout)
            else:
                info = collector(context, bundle_dir, timeout=timeout)
            info["elapsed_s"] = round(time.monotonic() - started_at, 3)
            manifest["collectors"][collector_name] = info
        except Exception as exc:  # noqa: BLE001
            elapsed = round(time.monotonic() - started_at, 3)
            error = {"collector": collector_name, "error": str(exc), "elapsed_s": elapsed}
            manifest["errors"].append(error)
            print(f"kde_faillog: collector {collector_name} failed: {exc}", flush=True)

    manifest_path = os.path.join(bundle_dir, "manifest.json")
    try:
        with open(manifest_path, "w", encoding="utf-8") as file_obj:
            json.dump(manifest, file_obj, indent=2)
    except OSError as exc:
        print(f"kde_faillog: cannot write manifest: {exc}", flush=True)

    _maybe_create_tarball(bundle_dir)
    return bundle_dir


def _maybe_create_tarball(bundle_dir: str) -> str | None:
    """Create a .tar.gz next to the bundle directory if possible.

    Non-fatal: if tarball creation fails the directory bundle is still retained.
    """
    tar_path = bundle_dir + ".tar.gz"
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(bundle_dir, arcname=os.path.basename(bundle_dir))
        return tar_path
    except Exception as exc:  # noqa: BLE001
        print(f"kde_faillog: cannot create tarball {tar_path}: {exc}", flush=True)
        return None
