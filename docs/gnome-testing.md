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

## Screenshot on failure

Hook in `after_scenario`, before sandbox cleanup:

```python
def after_scenario(context, scenario):
    if scenario.status == "failed":
        path = f"/tmp/results/screenshot-{scenario.name}.png"
        context.sandbox.shell.eval_js(
            f"imports.gi.Shell.Screenshot.screenshot(true, true, '{path}')"
        )
        # or via gdbus:
        # gdbus call --session \
        #   --dest org.gnome.Shell.Screenshot \
        #   --object-path /org/gnome/Shell/Screenshot \
        #   --method org.gnome.Shell.Screenshot.Screenshot \
        #   true true <path>
```

Output path `/tmp/results/screenshot-<name>.png` is SCP'd back by the runner.

## Parallel agent (swarm) pattern for desktop features

When scaffolding multiple feature areas at once:
- One agent per feature area, all in parallel
- Each agent needs: feature file path, steps file path, a reference feature to follow, dogtail API constraints, the duplicate-step check command
- After swarm completes, always validate:

```bash
# compile-check all new step files
python3 -m py_compile tests/<suite>/features/steps/*.py

# find duplicate step patterns
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d
```
