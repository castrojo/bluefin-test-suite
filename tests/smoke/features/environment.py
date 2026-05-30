"""
Smoke test environment — qecore TestSandbox for GNOME Shell.

Pattern sourced from: modehnal/GNOMETerminalAutomation features/environment.py
qecore source: gitlab.com/dogtail/qecore

qecore-headless (invoked by the Argo runner) handles:
  - DBUS_SESSION_BUS_ADDRESS
  - WAYLAND_DISPLAY / XDG_RUNTIME_DIR
  - gnome-ponytail-daemon activation
  - AT-SPI bus bridge
"""
import os
import re
import subprocess
import sys
import traceback

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403 — registers all common @step definitions
from steps.app_support import launch_target_available

try:
    from tests.shared.timing import record_end, record_start
except Exception:  # noqa: BLE001
    def record_start(context):
        return None

    def record_end(context, scenario):
        return None


OPTIONAL_SCENARIO_TARGETS = {
    "firefox": (
        ("command", "firefox"),
        ("desktop", "firefox.desktop"),
        ("desktop", "org.mozilla.firefox.desktop"),
        ("flatpak", "org.mozilla.firefox"),
    ),
    "calculator": (
        ("command", "gnome-calculator"),
        ("desktop", "org.gnome.Calculator.desktop"),
    ),
    "text_editor": (
        ("command", "gnome-text-editor"),
        ("desktop", "org.gnome.TextEditor.desktop"),
        ("desktop", "org.gnome.TextEditor.Devel.desktop"),
    ),
}


def _take_screenshot(scenario_name: str) -> None:
    safe = re.sub(r'[^a-z0-9]+', '_', scenario_name.lower())[:60]
    path = f'/tmp/results/screenshot_{safe}.png'
    os.makedirs('/tmp/results', exist_ok=True)
    try:
        result = subprocess.run(
            ['gdbus', 'call', '--session',
             '--dest', 'org.gnome.Shell.Screenshot',
             '--object-path', '/org/gnome/Shell/Screenshot',
             '--method', 'org.gnome.Shell.Screenshot.Screenshot',
             'true',
             'true',
             path],
            capture_output=True, text=True, timeout=8,
        )
        if result.returncode == 0:
            print(f'Screenshot saved: {path}', flush=True)
        else:
            print(f'Screenshot gdbus failed: {result.stderr.strip()}', flush=True)
    except Exception as exc:
        print(f'Screenshot error: {exc}', flush=True)


def before_all(context) -> None:
    import time
    import subprocess

    # Give GDM/GNOME Shell time to start the session
    time.sleep(5)

    # Enable unsafe_mode so Shell.Eval works for the rest of the session.
    # gdbus returns (true, 'null') on success, (false, '...') on failure.
    for attempt in range(3):
        try:
            r = subprocess.run(
                ['gdbus', 'call', '--session',
                 '--dest', 'org.gnome.Shell',
                 '--object-path', '/org/gnome/Shell',
                 '--method', 'org.gnome.Shell.Eval',
                 'global.context.unsafe_mode = true'],
                capture_output=True, text=True, timeout=5,
            )
            out = r.stdout.strip()
            if r.returncode == 0 and out.startswith('(true'):
                print(f"unsafe_mode enabled (attempt {attempt+1}): {out}", flush=True)
                break
            print(f"unsafe_mode attempt {attempt+1} returned: {out!r}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"unsafe_mode attempt {attempt+1} failed: {e}", flush=True)
        time.sleep(2)
    else:
        print("WARNING: could not confirm unsafe_mode=true; Shell.Eval steps may fail", flush=True)

    # Poll until clock + system toggles appear in AT-SPI (up to 15s)
    from dogtail import tree as dtree
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            shell = dtree.root.application('gnome-shell')
            panels = shell.findChildren(lambda n: n.roleName == 'panel')
            if panels:
                toggles = panels[0].findChildren(
                    lambda n: n.roleName == 'toggle button' and n.showing)
                toggle_names = [t.name for t in toggles]
                print(f"Panel toggles: {toggle_names}", flush=True)
                # Need more than just Activities + Show Apps
                non_activities = [t for t in toggles if t.name != 'Activities']
                if len(non_activities) >= 1:
                    print("Clock/System toggles visible — proceeding", flush=True)
                    break
        except Exception as e:  # noqa: BLE001
            print(f"AT-SPI poll: {e}", flush=True)
        time.sleep(1)
    else:
        print("WARNING: clock/system toggles not found after 15s — proceeding anyway", flush=True)

    # Initialize sandbox
    try:
        context.optional_scenario_availability = {
            tag: launch_target_available(targets)
            for tag, targets in OPTIONAL_SCENARIO_TARGETS.items()
        }
        print(
            f"Optional app availability: {context.optional_scenario_availability}",
            flush=True,
        )
        context.sandbox = TestSandbox("gnome-shell", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.shell = context.sandbox.shell
    except Exception as error:
        print(f"Environment error: before_all: {error}", flush=True)
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    context.scenario = scenario
    context.html_formatter = None
    # Initialize qecore command output attributes (attribute name varies by version)
    # qecore 4.16: command_stdout; older: last_command_output
    context.command_stdout = ""
    context.last_command_output = ""
    record_start(context)
    availability = getattr(context, "optional_scenario_availability", {})
    for tag, present in availability.items():
        scenario_tags = set(getattr(scenario, "effective_tags", scenario.tags))
        feature_name = os.path.basename(getattr(getattr(scenario, "feature", None), "filename", ""))
        if feature_name == "firefox.feature":
            scenario_tags.add("firefox")
        if tag in scenario_tags and not present:
            try:
                scenario.skip(f"{tag} app is not installed in this image")
            except TypeError:
                scenario.skip()
            print(f"Skipping {scenario.name}: {tag} app is not installed in this image", flush=True)
            return
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        sys.exit(1)


def after_scenario(context, scenario) -> None:
    record_end(context, scenario)
    if scenario.status.name == 'failed':
        _take_screenshot(scenario.name)
    context.sandbox.after_scenario(context, scenario)


def after_step(context, step) -> None:
    """Print full traceback for errored steps — needed because behave JSON
    serialises error_message as empty when the exception has no str()."""
    if step.status.name in ("error", "failed") and step.exception is not None:
        print(
            f"\nSTEP_ERROR [{step.name!r}]: "
            f"{type(step.exception).__name__}: {step.exception}",
            flush=True,
        )
        traceback.print_exception(
            type(step.exception),
            step.exception,
            step.exception.__traceback__,
            file=sys.stderr,
        )


def after_all(context) -> None:
    """Dump gnome-shell AT-SPI tree to results for node name discovery.
    Runs after the last scenario while the session is still active enough
    for the sandbox to have a valid shell handle.
    """
    try:
        import os
        if os.path.exists("/tmp/results/atspi_tree.txt"):
            return  # already written by after_scenario
        shell = context.sandbox.shell
        lines = []
        for child in shell.children[:60]:
            lines.append(f"role={child.roleName!r:30} name={child.name!r}")
            for gc in child.children[:20]:
                lines.append(f"  role={gc.roleName!r:30} name={gc.name!r}")
        os.makedirs("/tmp/results", exist_ok=True)
        with open("/tmp/results/atspi_tree.txt", "w") as f:
            f.write("\n".join(lines))
    except Exception:   # noqa: BLE001
        pass
