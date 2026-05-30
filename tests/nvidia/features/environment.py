"""
NVIDIA test environment — plain SSH, no qecore.
GPU tests are CLI-only (nvidia-smi, vulkaninfo, vainfo).
"""
import os

from tests.shared.ssh_steps import *  # noqa: F401,F403


def before_all(context):
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    context.command_stdout = ""


def before_scenario(context, scenario):
    context.command_stdout = ""


def after_scenario(context, scenario):
    pass
