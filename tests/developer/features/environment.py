"""
Developer test environment — qecore TestSandbox for Ptyxis + micro + Podman Desktop.

AT-SPI app names confirmed in tests/developer/conftest.py:
  - Ptyxis: root.application("ptyxis")
  - Podman Desktop: root.application("Podman Desktop")  (Flatpak, check at runtime)

Pattern: modehnal/GNOMETerminalAutomation features/environment.py
"""
import os
import re
import subprocess
import sys
import traceback

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403


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
    try:
        context.sandbox = TestSandbox("ptyxis", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False

        context.ptyxis = context.sandbox.get_application(
            name="ptyxis",
            a11y_app_name="ptyxis",
            desktop_file_name="org.gnome.Ptyxis.desktop",
        )
        context.ptyxis.exit_shortcut = "<Alt>F4"

        # micro is launched via terminal, not registered as a standalone app
        # Podman Desktop is a Flatpak — use get_flatpak for lifecycle management
        context.podman_desktop = context.sandbox.get_flatpak(
            flatpak_id="io.podman_desktop.PodmanDesktop",
        )
    except Exception as error:
        print(f"Environment error: before_all: {error}")
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        context.embed("text/plain", traceback.format_exc(), "Before Scenario Error")
        sys.exit(1)


def after_scenario(context, scenario) -> None:
    if scenario.status.name == 'failed':
        _take_screenshot(scenario.name)
    context.sandbox.after_scenario(context, scenario)
