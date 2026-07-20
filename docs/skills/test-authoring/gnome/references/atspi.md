---
name: atspi
description: "dogtail and AT-SPI lookup patterns and retry discipline."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## dogtail 4.16 API

`requireResult` was removed from `findChild` in 4.16. Patterns:

```python
# no-raise presence check
nodes = app.findChildren(GenericPredicate(name="Settings"))

# fast-fail (raises immediately if not found)
node = app.findChild(GenericPredicate(name="Settings"), retry=False)

# WRONG — crashes at runtime
node = app.findChild(pred, requireResult=False)  # ← do not use
```
## AT-SPI app-lookup helpers must retry

Every `_<app>_app()` helper must poll with a deadline, not check once and raise. GNOME 50 AT-SPI
registration is slower in QEMU; a single-pass lookup fails even when the process is already running.

**Canonical pattern (mirrors `_settings_app()`):**

```python
import time
from time import sleep

def _myapp_app(timeout: int = 15):
    """Find the app in the AT-SPI tree, retrying for up to ``timeout`` seconds."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        for name in MYAPP_APP_NAMES:
            try:
                return tree.root.application(name)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        sleep(1)
    raise AssertionError(
        f"MyApp application was not found via AT-SPI after {timeout}s: {last_error}"
    )
```

A scenario-level `@retry` tag does NOT substitute for this — it re-launches the whole scenario,
potentially opening a second instance of the app. The retry loop in `_<app>_app()` is the right fix.

The `@retry` tag is for infrastructure-flaky scenarios (network timeouts, D-Bus races at startup).
AT-SPI registration lag on first lookup is always fixed at the helper level.


When scaffolding multiple feature areas at once:
- One agent per feature area, all in parallel
- Each agent needs: feature file path, steps file path, a reference feature to follow, dogtail API constraints, the duplicate-step check command
- After swarm completes, always validate:

```bash
python3 -m py_compile tests/<suite>/features/steps/*.py
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d
```
