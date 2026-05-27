"""
Software test environment — qecore TestSandbox for gnome-software (Bazaar).

Regressions: bluefin#4062, #4471.
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
        context.sandbox = TestSandbox("gnome-software", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False

        context.software = context.sandbox.get_application(
            name="gnome-software",
            a11y_app_name="gnome-software",
            desktop_file_name="org.gnome.Software.desktop",
        )
        context.software.exit_shortcut = "<Ctrl>Q"
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
