# GNOME Desktop Testing Reference

Load when: writing or debugging GNOME Shell, AT-SPI, or dogtail interactions.

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
# Enable unsafe mode first (once per session)
context.sandbox.shell.eval_js("global.context.unsafe_mode = true")

# Open quick-settings via Shell.Eval
context.sandbox.shell.eval_js(
    "Main.panel.statusArea.quickSettings.menu.open()"
)
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

## Screenshot on failure

Hook in `after_scenario`, before sandbox cleanup:

```python
def after_scenario(context, scenario):
    if scenario.status == "failed":
        path = f"/tmp/results/screenshot-{scenario.name}.png"
        context.sandbox.shell.eval_js(
            f"imports.gi.Shell.Screenshot.screenshot(true, true, '{path}')"
        )
```

Output path `/tmp/results/screenshot-<name>.png` is SCP'd back by the runner.

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

## Parallel agent (swarm) pattern for desktop features

When scaffolding multiple feature areas at once:
- One agent per feature area, all in parallel
- Each agent needs: feature file path, steps file path, a reference feature to follow, dogtail API constraints, the duplicate-step check command
- After swarm completes, always validate:

```bash
python3 -m py_compile tests/<suite>/features/steps/*.py
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d
```

