"""
Bazzite test environment — qecore TestSandbox for GNOME Shell + extensions.

Identical setup to the smoke suite. Bazzite ships 11 enabled extensions;
this environment enables unsafe_mode and waits for the full panel (including
Logo Menu which replaces the Activities button) to be ready.
"""
import os
import re
import subprocess
import sys
import traceback

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403


def _take_screenshot(scenario_name: str) -> None:
    safe = re.sub(r"[^a-z0-9]+", "_", scenario_name.lower())[:60]
    path = f"/tmp/results/screenshot_{safe}.png"
    os.makedirs("/tmp/results", exist_ok=True)
    try:
        subprocess.run(
            [
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Shell.Screenshot",
                "--object-path", "/org/gnome/Shell/Screenshot",
                "--method", "org.gnome.Shell.Screenshot.Screenshot",
                "true", "true", path,
            ],
            capture_output=True, text=True, timeout=8,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Screenshot error: {exc}", flush=True)


def before_all(context) -> None:
    import time

    # Wait for GDM autologin + all extensions to initialize
    time.sleep(8)

    # Enable unsafe_mode for Shell.Eval access
    for attempt in range(3):
        try:
            subprocess.run(
                [
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell",
                    "--object-path", "/org/gnome/Shell",
                    "--method", "org.gnome.Shell.Eval",
                    "global.context.unsafe_mode = true",
                ],
                capture_output=True, timeout=5,
            )
            print(f"unsafe_mode set (attempt {attempt + 1})", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"unsafe_mode attempt {attempt + 1} failed: {e}", flush=True)
            time.sleep(2)

    # Poll until panel toggle buttons appear (Logo Menu replaces Activities)
    from dogtail import tree as dtree
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            shell = dtree.root.application("gnome-shell")
            panels = shell.findChildren(lambda n: n.roleName == "panel")
            if panels:
                toggles = panels[0].findChildren(
                    lambda n: n.roleName == "toggle button" and n.showing
                )
                if len(toggles) >= 1:
                    print(
                        f"Panel ready — toggles: {[t.name for t in toggles]}",
                        flush=True,
                    )
                    break
        except Exception as e:  # noqa: BLE001
            print(f"AT-SPI poll: {e}", flush=True)
        time.sleep(1)
    else:
        print("WARNING: panel toggles not ready after 20s — proceeding", flush=True)

    try:
        context.sandbox = TestSandbox("gnome-shell", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH
        context.shell = context.sandbox.shell
    except Exception as error:
        print(f"Environment error: before_all: {error}", flush=True)
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    context.command_stdout = ""
    context.last_command_output = ""
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        sys.exit(1)


def after_scenario(context, scenario) -> None:
    if scenario.status.name == "failed":
        _take_screenshot(scenario.name)
    context.sandbox.after_scenario(context, scenario)


def after_step(context, step) -> None:
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
