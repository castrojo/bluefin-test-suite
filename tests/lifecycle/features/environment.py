"""
Lifecycle test environment — plain SSH, no qecore/AT-SPI.

This suite validates bootc upgrade/rollback/switch over SSH.
No GNOME session interaction needed — pure CLI commands.

TODO: Implement SSH helper that reads VM_IP from env and provides
context.ssh(cmd) → (stdout, returncode) helper for steps.
"""


def before_all(context):
    """Set up SSH connection parameters from environment.
    TODO: Read VM_IP, SSH_KEY from env vars (set by Argo runner)."""
    import os
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    # TODO: Store original image digest for rollback comparison
    context.original_digest = None


def before_scenario(context, scenario):
    context.command_stdout = ""


def after_scenario(context, scenario):
    pass
