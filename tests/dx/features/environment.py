"""
DX variant test environment — qecore sandbox for GUI tests.
Identical to smoke/environment.py but for DX-specific scenarios.
Sandbox is initialized lazily — only when a GUI (@vscode) scenario runs.
SSH-only (@plain_ssh) scenarios skip the sandbox entirely.
"""
import os
import sys
import traceback

try:
    from tests.shared.timing import record_end, record_start
except Exception:  # noqa: BLE001
    def record_start(context):
        return None

    def record_end(context, scenario):
        return None

try:
    from tests.shared.screenshot import configure_screenshot_context, take_screenshot
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot helpers unavailable: {exc}", flush=True)

    def configure_screenshot_context(context, suite_name, scenario_name=None):
        return None

    def take_screenshot(label):
        return None


try:
    from tests.shared.screenshot_steps import *  # noqa: F401,F403 — registers screenshot steps
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot steps unavailable: {exc}", flush=True)


SUITE_NAME = "dx"


def _init_sandbox(context):
    """Initialize the qecore TestSandbox on first GUI scenario."""
    if getattr(context, '_sandbox_initialized', False):
        return

    import time
    from qecore.sandbox import TestSandbox

    time.sleep(5)
    try:
        context.sandbox = TestSandbox("gnome-shell", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.shell = context.sandbox.shell
        context._sandbox_initialized = True
        configure_screenshot_context(context, SUITE_NAME)
    except Exception as error:
        print(f"Environment error: _init_sandbox: {error}", flush=True)
        context.failed_setup = traceback.format_exc()


def before_all(context):
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
    context._sandbox_initialized = False
    context.sandbox = None
    context.shell = None


def before_scenario(context, scenario):
    context.scenario = scenario
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0
    record_start(context)

    if 'plain_ssh' in scenario.tags:
        return

    _init_sandbox(context)
    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    if context.sandbox is None:
        print("HOOK_ERROR: sandbox not initialized for GUI scenario", flush=True)
        sys.exit(1)

    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        sys.exit(1)


def after_scenario(context, scenario):
    record_end(context, scenario)
    if 'plain_ssh' in scenario.tags:
        return
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        take_screenshot(scenario.status.name)
    if context.sandbox is not None:
        context.sandbox.after_scenario(context, scenario)
