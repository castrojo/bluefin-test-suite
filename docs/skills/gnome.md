---
name: gnome-testing
description: "Use when writing or debugging GNOME Shell, AT-SPI/dogtail, or headless QEMU desktop tests in testsuite."
metadata:
  type: reference
  context7-sources:
    - /dogtail/qecore
    - /dogtail/dogtail
    - /GNOME/pygobject
---

# GNOME Desktop Testing Reference

## When to Use
- Writing or debugging GNOME Shell, AT-SPI, or dogtail interactions
- Implementing Shell.Eval-based steps (quick settings, overview, extensions)
- Adding extension-state checks for smoke or bazzite suites
- Debugging AT-SPI accessibility node failures in headless QEMU

## When NOT to Use
- SSH-based system checks → `docs/skills/behave.md` shared SSH steps
- CI workflow or runner container setup → `docs/skills/ops.md`
- Suite scaffolding or step hygiene → `docs/skills/behave.md`

## Core Process

1. Identify whether the scenario needs AT-SPI interaction, Shell.Eval, or only subprocess/CLI checks.
2. Reuse existing smoke helpers first (`launch_background()`, `_run_host()`, `_eval_bool()`, `_wait_eval_bool()`).
3. Prefer desktop-file launch targets before direct commands for GUI apps so D-Bus activation and AT-SPI registration work in CI.
4. Poll for visible widgets or windows; avoid unconditional sleeps when a retry loop can prove readiness.
5. Validate locally with `python3 -m py_compile tests/<suite>/features/steps/*.py`, duplicate-step detection, `ruff`, and `behave --dry-run`.

## Stack

| Layer | Component | Install |
|---|---|---|
| BDD runner | behave | pip |
| Session bridge | qecore-headless | pip |
| GUI automation | dogtail (AT-SPI) | pip |
| Wayland coord bridge | gnome-ponytail-daemon | `sudo dnf install gnome-ponytail-daemon` inside VM |
| Shell bridge | `org.gnome.Shell.Eval` | built-in (requires `unsafe_mode=true`) |

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

## GNOME Shell 50+ top-bar

AT-SPI nodes for clock and system-status have `INT_MIN` position — coordinate-based clicks are unreliable. Use `Shell.Eval` for:
- Overview toggle
- Quick-settings panel
- Date/calendar menu

```python
from tests.shared.gnome_shell_steps import _shell_eval

# qecore's context.sandbox.shell is an AT-SPI Accessible, not a JS bridge.
# Drive Shell.Eval with gdbus via the shared helper instead.
_shell_eval("Main.panel.statusArea.quickSettings.menu.open()")
```

`gdbus` equivalent:
```bash
gdbus call --session \
  --dest org.gnome.Shell \
  --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "global.context.unsafe_mode = true"
```

## Shell.Eval via gdbus — critical parsing rule

`gdbus call` always returns `(success_bool, 'js_result')`. The success flag
is **always** `true` when the Eval method itself runs — even if the JS result
is `false`. **Never use `'true' in out`** to check a boolean JS result:

```python
# WRONG — always True because gdbus wraps result as (true, 'false')
assert 'true' in out.lower()

# CORRECT — extract the JS result (second tuple element)
import re
m = re.search(r",\s*'(true|false)'\s*\)", out, re.IGNORECASE)
result = m.group(1).lower() == 'true'  # True only if JS returned true
```

Use the `_eval_bool(js)` / `_wait_eval_bool(js, expected)` helpers from
`tests/smoke/features/steps/steps.py` rather than hand-rolling this.

### Avoid local re-definitions of `_shell_eval`
**CRITICAL**: Never define local/duplicate versions of `_shell_eval` or `_eval_bool` (such as in `vanilla-gnome/features/steps/steps.py`). Always import and reuse the shared helper from `tests.shared.gnome_shell_steps`. 
*Why:* GNOME 50 resets `unsafe_mode` to `false` aggressively after almost any UI event (modal dialogs, menus, overview toggle). The shared `_shell_eval` is specifically engineered to prepended `global.context.unsafe_mode = true` on every single invocation, whereas local hand-rolled versions that omit this will immediately fail on subsequent steps.

## Screen Lock/Unlock D-Bus calls (GNOME 50)

In GNOME 50, `Main.screenShield.lock(true)` via `Shell.Eval` is deprecated and fails. Use the stable D-Bus interface `org.gnome.ScreenSaver.Lock` to lock the session, and `org.gnome.ScreenSaver.SetActive false` to unlock it:

```python
# Locking screen:
cmd = "source /tmp/session.env 2>/dev/null; gdbus call --session --dest org.gnome.ScreenSaver --object-path /org/gnome/ScreenSaver --method org.gnome.ScreenSaver.Lock"
_run_host(cmd)

# Unlocking screen:
cmd = "source /tmp/session.env 2>/dev/null; gdbus call --session --dest org.gnome.ScreenSaver --object-path /org/gnome/ScreenSaver --method org.gnome.ScreenSaver.SetActive false"
_run_host(cmd)
```

## Overview open/closed detection

**Do not** use AT-SPI `n.name.lower() == "overview"` — the node name varies
across GNOME versions. Use Shell.Eval instead:

```python
# Reliable across GNOME 45–50
_wait_eval_bool('Main.overview.visible.toString()', expected=True)
```

## Overview search entry

**Do not** call `Main.overview._onSearchChanged()` — it was removed in GNOME 47.
Use `clutter_text.set_text()` which emits the `text-changed` signal and
triggers the search controller via the public signal path:

```python
_shell_eval(f'Main.overview.searchEntry.clutter_text.set_text("{text}")')
```

To read back the current search text:
```python
_shell_eval('Main.overview.searchEntry.clutter_text.get_text()')
# returns: (true, 'Files')  — parse with regex on the second element
```

## Quick Settings DND property drift

GNOME Shell has exposed the Do Not Disturb toggle under multiple private names:
- `_doNotDisturb`
- `_do_not_disturb`
- `_dnd`

Smoke helpers should resolve all known aliases before touching `.checked` or
`.toggle()`. If no quick-settings object exists, fall back to the canonical
`org.gnome.desktop.notifications show-banners` gsettings key.

**GNOME 50 caveat**: `quickSettings._doNotDisturb` may exist as an object but
`.checked` is not accessible (TypeError). `_dnd_toggle_exists_js()` must
verify `?.checked !== undefined` (not just `!== null`) to trigger the
gsettings fallback correctly. The test in steps.py:

```python
def _dnd_toggle_exists_js() -> str:
    return f"({_DND_TOGGLE_JS})?.checked !== undefined"
```

## xdg-mime in container mode

`_xdg_mime_default(mime_type)` in smoke steps.py runs `xdg-mime query default`
to check MIME handler registration. When `_IN_CONTAINER` is True (runner
container SSHing into the VM), `xdg-mime` is not installed on the container
host — it lives in the Bluefin VM. Always route through `_ssh_run` in that
case.

**Critical**: SSH sessions do NOT inherit the GNOME user session `XDG_DATA_DIRS`.
Flatpak apps (Firefox, Papers, Loupe, Showtime) register MIME handlers under
`/var/lib/flatpak/exports/share/applications/`. Without this path in
`XDG_DATA_DIRS`, `xdg-mime query default` returns empty for Flatpak MIME types.

**Keep allowlists synced to the OOTB set**: the `DOCUMENT_VIEWERS` /
`IMAGE_VIEWERS` / `TEXT_EDITORS` / `VIDEO_PLAYERS` sets in smoke `steps.py`
must match what `flatpak_permissions.feature` says the image actually ships.
Bluefin ships `org.gnome.Showtime` as its OOTB video player — a stale
allowlist (e.g. Celluloid-only) blocks the matching mimeapps.list default in
projectbluefin/common from ever passing.

Always set `XDG_DATA_DIRS` explicitly in the SSH call:

```python
from app_support import _IN_CONTAINER, _ssh_run
if _IN_CONTAINER:
    result = _ssh_run(
        "XDG_DATA_DIRS=/var/lib/flatpak/exports/share"
        ":/home/bluefin-test/.local/share/flatpak/exports/share"
        ":/usr/local/share:/usr/share "
        f"xdg-mime query default {mime_type}"
    )
    return result.stdout.strip()
```

`xdg-mime query default` does NOT require a running D-Bus session.

## Activities overview (GNOME 50 QEMU)

`Main.overview.visible.toString()` consistently returns `false` in QEMU on GNOME 50
even after `Main.overview.show()` is called. Do NOT assert `Main.overview.visible` or
switch to `Main.overview._shown` without confirming on a live GNOME 50 QEMU run —
the behavior is not reproducible locally without a full VM boot. Scenarios that depend
on overview visibility must be quarantined (`@quarantine`) until the correct GNOME 50
API is confirmed.

## Screenshot on failure

Hook in `after_scenario`, before sandbox cleanup:

```python
from tests.shared.screenshot import take_screenshot

def after_scenario(context, scenario):
    if scenario.status == "failed":
        take_screenshot("failed", context)
```

`take_screenshot()` calls the native `org.gnome.Shell.Screenshot` D-Bus API.
Do not call `context.sandbox.shell.eval_js(...)` for screenshots — in qecore
4.16 `sandbox.shell` is an accessibility object and has no `eval_js` method.

## GNOME Extensions CLI (subprocess)

Smoke-suite extension steps run inside the VM via `subprocess`, not AT-SPI:

```python
import subprocess

# List installed extensions
result = subprocess.run(["gnome-extensions", "list"], capture_output=True, text=True)
extensions = [e.strip() for e in result.stdout.splitlines() if e.strip()]

# List enabled extensions
result = subprocess.run(["gnome-extensions", "list", "--enabled"], capture_output=True, text=True)
enabled = [e.strip() for e in result.stdout.splitlines() if e.strip()]
```

Note: `gnome-extensions` requires the GNOME session to be running. These steps run inside the qecore VM (local subprocess), not over SSH.

## Preinstalled Flatpak desktop app launch checks

For smoke tests that only need to prove a preinstalled Flatpak desktop app
launches, reuse the `gnome_apps.feature` pattern: launch, wait for one visible
top-level frame in the AT-SPI tree, send `<Alt><F4>`, then assert the frame is
gone.

Use `app_support.launch_background()` with **desktop-first** targets and a
Flatpak fallback:

```python
LAUNCH_TARGETS = (
    ("desktop", "io.missioncenter.MissionCenter.desktop"),
    ("flatpak", "io.missioncenter.MissionCenter"),
)
```

Why: in CI/container runs the helper resolves desktop files from Flatpak export
dirs (`/var/lib/flatpak/exports/...`) and launches them on the VM via SSH, so
you should not hardcode `/usr/share/applications/<app>.desktop` for Flatpak-only
apps.

## Extension state via D-Bus (bazzite / GNOME 50)

For suites that need to poll an extension's activation state (e.g. the bazzite suite which runs over SSH), **do not** use `Shell.Eval + Main.extensionManager.lookup(uuid)?.state`. On GNOME 50 this API consistently returns state=6 (INITIALIZED) regardless of actual activation.

Use `org.gnome.Shell.Extensions.GetExtensionInfo` instead:

```python
import subprocess, re

def _extension_state(uuid: str) -> str:
    """Return extension state as a string integer. 99 = unknown / uninstalled."""
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell/Extensions',
         '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
         f"'{uuid}'"],            # ← single-quotes required; see GVariant note below
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return "99"
    m = re.search(r"'state':\s*<uint32\s+(\d+)>", result.stdout)
    return m.group(1) if m else "99"
```

**GVariant quoting (critical):** Extension UUIDs contain `@` and `.` which are invalid in a bare GVariant token. Always wrap the UUID in single quotes inside the Python string: `f"'{uuid}'"` → produces `'logomenu@aryan_k'` on the command line.

**State values:** 1=ENABLED, 2=DISABLED, 3=ERROR, 4=OUT_OF_DATE, 5=DOWNLOADING, 6=INITIALIZED (transient), 7=DISABLING (transient), 8=ENABLING (transient), 99=UNINSTALLED.

Poll through 6 and 8 with a deadline (Bazzite: use 90s — 11 extensions need time post-boot).

## Extension state in smoke suite (local subprocess / SSH bridge)

The smoke suite's UUID-specific extension checks use the same
`GetExtensionInfo` D-Bus call as bazzite, but route through the suite-local
`_run_host(...)` helper so they work both inside the VM and from the Fedora
runner container over SSH.

Bluefin's 9 bundled extensions each get a named scenario in
`tests/smoke/features/bluefin_extensions.feature`. Tag the
`search-light@icedman.github.com` scenario with `@bluefin` so dakota smoke runs
skip it via `environment.py`.

Use the distinct step phrase `GNOME extension "{uuid}" is enabled` (not
bazzite's `Extension "{uuid}" is enabled`) to avoid cross-suite step collisions.

## Bazaar on Bluefin: wait out the Refreshing spinner

Bluefin ships **Bazaar** (`io.github.kolunmi.Bazaar`), not GNOME Software's old
Explore/Installed toggle-button layout. For Bazaar UI tests:

- wait for a visible window named **`Bazaar`**
- then poll until any visible tab named **`Curated`**, **`Explore`**,
  **`Library`**, or **`Search`** appears
- accept both `page tab` and `toggle button` roles for those tabs

The first launch often shows a **Refreshing** spinner page before the
`AdwViewStack` content is ready. On GNOME 50, AT-SPI cache drops can also make
nodes disappear mid-query, so wrap Bazaar window/tab lookups in retry loops
with short sleeps and re-query the tree each attempt.

## Desktop notifications via gdbus (smoke suite)

Send a test notification from inside the VM:

```bash
gdbus call --session \
  --dest org.freedesktop.Notifications \
  --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.Notify \
  '' 0 '' 'Title' 'Body' '[]' '{}' 3000
# Returns: (uint32 N,)  — N is the notification ID (>0 on success)
```

Parse the ID from `context.notify_output` with `re.search(r'\(uint32 (\d+),\)', output)`. An ID of `0` means failure.

## Smoke desktop-identity checks: use `_run_host` + session env

For smoke steps that need session-scoped shell state (`XDG_SESSION_TYPE`,
`DISPLAY`, `WAYLAND_DISPLAY`) or VM-installed tools like `glxinfo`, prefer the
suite-local `_run_host(...)` helper over plain `subprocess.run(...)`.

Why: local smoke scenarios execute inside the VM during ad-hoc runs, but CI can
run them from the Fedora runner container. `_run_host(...)` transparently hops
to the VM over SSH in that case, and `source /tmp/session.env 2>/dev/null; ...`
preserves the GNOME user-session environment before probing Wayland or renderer
state.

## Sleep discipline in step definitions

Unconditional `sleep(N)` calls inflate suite time — avoid them. Rules:

1. **`launch_background()` from qecore** — do NOT add `sleep(1)` after calling qecore's built-in `launch_background()`. The immediately-following "window is accessible" step has its own AT-SPI polling loop; the launch sleep is redundant there.

   **EXCEPTION — `_launch_app()` custom launcher**: The suite-local `_launch_app()` in `gnome_apps_steps.py` uses D-Bus app activation (`gio open` or `gtk-launch`), which is **asynchronous**. `sleep(1)` after a successful `_launch_app()` return is **required** as a D-Bus activation settle time — without it, `_wait_for_window()` starts polling before the process has registered with the AT-SPI accessibility bus, exhausts all retries (~10s), and fails on slower images (e.g. Dakota testing). Do not remove this sleep. The regression in PR #465 was caused by removing it.

2. **Polling loop intervals** — use 0.2s intervals in retry loops (`for _ in range(N): sleep(0.2)`). 0.5s is the old default; the loops already exit-early on success so tighter intervals help.

3. **GNOME Shell open/close animations** — use 0.2s after `_shell_eval()` open/close commands before checking state. The `_wait_eval_bool()` helper handles the real confirmation wait.

4. **Screenshot fastfetch** — terminal keep-open is `fastfetch; sleep 3` (not 10). Pre-screenshot delay `time.sleep(2)` (not 4). Both are already on QEMU where timing is slow.

5. **Never remove** — small sleeps after user-visible actions (sidebar clicks, key combos, focus transitions) that have no async poll to catch up: `sleep(0.2)` is the minimum. Do not go below 0.1s.

The pattern `for _ in range(N): ... sleep(X)` that returns early already IS exit-early. The gains come from removing the PRECEDING unconditional sleep, not from changing the loop.

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

## Red Flags

- Using `'true' in out` to check a Shell.Eval result (success_bool is always true)
- Calling `Shell.Eval` without first setting `global.context.unsafe_mode = true`
- Using `requireResult=False` with `findChild` (removed in dogtail 4.16)
- Importing `tests.shared.ssh_steps` into the smoke suite
- Using AT-SPI coordinate clicks on the top-bar (unreliable on GNOME 50+)
- Polling `Main.extensionManager.lookup(uuid)?.state` via Shell.Eval (returns 6 on GNOME 50)
- Using the SSH-based `_extension_state()` pattern in the smoke suite (smoke uses local subprocess)
- `_<app>_app()` helper does a single-pass lookup with no retry loop — will flake on GNOME 50 QEMU

## Verification

- [ ] Shell.Eval results extracted with `_eval_bool()` / regex on second tuple element, never `'true' in out`
- [ ] `unsafe_mode=true` set before any Shell.Eval that reads protected state
- [ ] Extension state checked via `org.gnome.Shell.Extensions.GetExtensionInfo`, not `Shell.Eval`
- [ ] UUID wrapped in single quotes for GVariant: `f"'{uuid}'"` not `uuid`
- [ ] Smoke suite steps use `subprocess.run`, not SSH helpers
- [ ] `behave --dry-run tests/smoke/features/` passes before pushing
## Common Rationalizations

- "A direct command launch is simpler." → For GUI apps, desktop-file activation is usually more reliable for AT-SPI registration.
- "I'll just sleep after launch." → Poll for the visible window instead; fixed sleeps bloat the suite and still flake.
- "This title match is good enough." → Prefer app-level AT-SPI lookup first, then use title fallback only when the app name is unstable.

## Red Flags

- New smoke app steps hardcode `/usr/share/applications/...` for Flatpak-only apps
- Step code uses `findChild(..., requireResult=...)`
- New GNOME steps duplicate existing step phrases in the suite
- New launch steps add unconditional post-launch sleeps instead of relying on accessibility polling

## Verification

- [ ] Reused existing GNOME/smoke helpers before adding new ones
- [ ] Launch targets prefer desktop files, with Flatpak or command fallback only when needed
- [ ] AT-SPI polling or Shell.Eval assertions replace fixed waits where possible
- [ ] `python3 -m py_compile tests/<suite>/features/steps/*.py` passes
- [ ] `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d` returns no duplicates
- [ ] `ruff check tests/ --select E,F,W --ignore E501` passes
- [ ] `behave --dry-run tests/<suite>/features/` passes for the touched suite
