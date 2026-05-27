"""
Security test environment — minimal, no qecore.
Handles both preflight checks (cosign, run from runner pod)
and in-VM checks (SELinux, run over SSH).
"""


def before_all(context):
    import os
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    context.command_stdout = ""


def before_scenario(context, scenario):
    context.command_stdout = ""


def after_scenario(context, scenario):
    pass
