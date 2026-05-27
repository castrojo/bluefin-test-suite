"""
DX variant test environment — qecore sandbox for GUI tests.
Identical to smoke/environment.py but for DX-specific scenarios.
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


def before_all(context):
    import time

    context.vm_ip = (
        os.environ.get("VM_IP")
        or os.environ.get("TMT_SSH_HOST")
        or os.environ.get("FLATCAR_VM_IP", "")
    )
    context.ssh_user = (
        os.environ.get("VM_USER")
        or os.environ.get("SSH_USER")
        or os.environ.get("TMT_SSH_USER", "bluefin-test")
    )
    context.ssh_key = (
        os.environ.get("SSH_KEY")
        or os.environ.get("SSH_KEY_PATH")
        or os.environ.get("TMT_SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    )
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0

    time.sleep(5)
    try:
        context.sandbox = TestSandbox("gnome-shell", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.shell = context.sandbox.shell
    except Exception as error:
        print(f"Environment error: before_all: {error}", flush=True)
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario):
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        sys.exit(1)


def after_scenario(context, scenario):
    if scenario.status.name == 'failed':
        _take_screenshot(scenario.name)
    context.sandbox.after_scenario(context, scenario)
