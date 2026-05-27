"""
DX variant test environment — qecore sandbox for GUI tests.
Identical to smoke/environment.py but for DX-specific scenarios.
"""
import sys
import traceback

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403


def before_all(context):
    import time
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
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        sys.exit(1)


def after_scenario(context, scenario):
    context.sandbox.after_scenario(context, scenario)
