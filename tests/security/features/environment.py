"""
Security test environment — minimal, no qecore.
Handles both preflight checks (cosign, run from runner pod)
and in-VM checks (SELinux, run over SSH).
"""
import os

from tests.shared.ssh_steps import *  # noqa: F401,F403


def before_all(context):
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    context.command_stdout = ""
    context.cosign_issuer = None
    context.cosign_identity = None
    context.cosign_output = None
    context.cosign_error = None


def before_scenario(context, scenario):
    context.command_stdout = ""
    context.ssh_rc = None
    context.last_ssh_result = None
    context.cosign_output = None
    context.cosign_error = None


def after_scenario(context, scenario):
    pass
