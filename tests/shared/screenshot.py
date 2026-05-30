"""Screenshot helpers for behave GNOME test environments.

All GNOME GUI suites import from here instead of duplicating the logic.
"""

import os
import re
import shutil
import subprocess
import time

RESULTS_DIR = "/tmp/results"


def take_screenshot(label: str) -> str | None:
    """Capture a full-screen PNG via gnome-shell D-Bus Screenshot API.

    Args:
        label: Human-readable label used to derive the filename.
               Should include suite + status + scenario for uniqueness.

    Returns:
        Path to the saved file, or None if capture failed.
    """
    safe = re.sub(r'[^a-z0-9]+', '_', label.lower())[:120]
    path = os.path.join(RESULTS_DIR, f"screenshot_{safe}.png")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        result = subprocess.run(
            ['gdbus', 'call', '--session',
             '--dest', 'org.gnome.Shell.Screenshot',
             '--object-path', '/org/gnome/Shell/Screenshot',
             '--method', 'org.gnome.Shell.Screenshot.Screenshot',
             'true', 'true', path],
            capture_output=True, text=True, timeout=8,
        )
        if result.returncode == 0:
            print(f'Screenshot saved: {path}', flush=True)
            return path
        print(f'Screenshot gdbus failed: {result.stderr.strip()}', flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f'Screenshot error: {exc}', flush=True)
    return None


def take_fastfetch_screenshot() -> str | None:
    """Open a terminal, run fastfetch, screenshot the result, then close.

    Tries ptyxis, then kgx (GNOME Console), then gnome-terminal.
    Uses 'sleep 10' to keep the window open long enough to capture.

    Returns:
        Path to the saved file, or None if any step failed.
    """
    candidates = [
        ('ptyxis', ['ptyxis', '--', 'bash', '-c', 'fastfetch; sleep 10']),
        ('kgx', ['kgx', '--', 'bash', '-c', 'fastfetch; sleep 10']),
        ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', 'fastfetch; sleep 10']),
    ]

    for term, cmd in candidates:
        if not shutil.which(term):
            continue
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Allow time for the terminal window and fastfetch to render
            time.sleep(4)
            path = take_screenshot('fastfetch')
            return path
        except Exception as exc:  # noqa: BLE001
            print(f'Fastfetch screenshot ({term}): {exc}', flush=True)
        finally:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:  # noqa: BLE001
                    pass

    print('Fastfetch screenshot: no terminal emulator found', flush=True)
    return None
