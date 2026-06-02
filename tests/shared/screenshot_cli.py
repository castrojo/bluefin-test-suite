"""
Standalone CLI — screenshot one or more apps without a behave context.

Usage (inside the runner container):
    python3 screenshot_cli.py org.gnome.Calculator io.github.kolunmi.Bazaar

Each app is launched, held for SCREENSHOT_APP_WAIT seconds (default 4), then
screenshotted via GNOME Shell's Screenshot API. The PNG is written to
TESTSUITE_RESULTS_DIR (default /tmp/results) using the standard naming scheme:
    screenshot_<suite>_<app_slug>_flatpak_gallery.png

Exit code is 0 if at least one screenshot succeeded, 1 if all failed.
"""

import os
import sys
import types

# PYTHONPATH must point to the repo root so 'from tests.shared...' resolves.
# The runner container sets PYTHONPATH=/tmp/bluefin-tests.
_repo_root = os.environ.get("PYTHONPATH", "/tmp/bluefin-tests")
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from tests.shared.screenshot import (  # noqa: E402
    configure_screenshot_context,
    take_app_screenshot,
)

# Minimal context — sandbox just needs to be non-None to pass the guard check
# in take_screenshot; it is never dereferenced here.
_ctx = types.SimpleNamespace(
    sandbox=object(),
    config=types.SimpleNamespace(userdata={}),
)

_suite = os.environ.get("SUITE", "unknown")
configure_screenshot_context(_ctx, _suite, "flatpak_gallery")

if len(sys.argv) < 2:
    print("Usage: screenshot_cli.py <app_id> [<app_id> ...]", file=sys.stderr)
    sys.exit(1)

ok = 0
fail = 0
for app_id in sys.argv[1:]:
    path = take_app_screenshot(app_id, context=_ctx)
    if path:
        print(f"OK   {app_id}: {path}", flush=True)
        ok += 1
    else:
        print(f"FAIL {app_id}: no screenshot captured", flush=True)
        fail += 1

print(f"\nFlatpak gallery: {ok} captured, {fail} failed", flush=True)
sys.exit(1 if fail > 0 else 0)
