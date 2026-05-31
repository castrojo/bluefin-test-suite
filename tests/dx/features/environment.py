"""
DX variant test environment -- qecore sandbox for GUI tests.
Sandbox is initialized eagerly in before_all so qecore can track session state.
SSH-only (@plain_ssh) scenarios still work -- sandbox is initialized but unused.
"""
import os
import time
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
    from tests.shared.screenshot_steps import *  # noqa: F401,F403 -- registers screenshot steps
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot steps unavailable: {exc}", flush=True)


SUITE_NAME = "dx"


def before_all(context):
    from qecore.sandbox import TestSandbox

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
    # failed_setup must be falsy so qecore before_scenario does not call sys.exit(1)
    context.failed_setup = None
    context.sandbox = None
    context.shell = None

    time.sleep(5)
    try:
        context.sandbox = TestSandbox("gnome-shell", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH
        context.shell = context.sandbox.shell
        configure_screenshot_context(context, SUITE_NAME)
    except BaseException as error:  # noqa: BLE001 -- catch SystemExit too
        print(f"Environment error: before_all: {error}", flush=True)
        # Do NOT set context.failed_setup -- qecore calls sys.exit(1) when it is set.


def before_scenario(context, scenario):
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    context.scenario = scenario
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0
    record_start(context)

    # qecore only clears _scenario_skipped inside sandbox.before_scenario(), which
    # is never called for @plain_ssh scenarios.  Notify it here so after_all doesn't
    # assert "No scenario matched tags" when all GUI scenarios are @quarantine'd.
    if context.sandbox is not None:
        context.sandbox._scenario_skipped = False

    if 'plain_ssh' in scenario.tags:
        return

    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    if context.sandbox is None:
        print("HOOK_ERROR: sandbox not initialized for GUI scenario", flush=True)
        raise RuntimeError("sandbox not initialized for GUI scenario")

    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        raise


def after_scenario(context, scenario):
    record_end(context, scenario)
    if 'plain_ssh' in scenario.tags:
        return
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        take_screenshot(scenario.status.name)
    if context.sandbox is not None:
        context.sandbox.after_scenario(context, scenario)
