"""Shared screenshot helpers for behave GNOME GUI suites."""

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any


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

    try:
        subprocess.run(
            [
                'gdbus', 'call', '--session',
                '--dest', 'org.gnome.Shell',
                '--object-path', '/org/gnome/Shell/Screenshot',
                '--method', 'org.gnome.Shell.Screenshot.Screenshot',
                'true',    # include_cursor (GVariant boolean)
                'false',   # flash (GVariant boolean)
                json.dumps(path),  # filename as GVariant string (double-quoted)
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Screenshot error: {exc}", flush=True)
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
