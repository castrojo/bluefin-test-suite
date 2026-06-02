"""
Flatcar test environment — plain behave, no qecore.

Flatcar has no GNOME desktop; tests run in the Argo runner pod and
issue SSH commands into the Flatcar VM. VM_IP is injected by the runner
as an environment variable.
"""
import os

from tests.shared.ssh_steps import *  # noqa: F401,F403


def before_all(context) -> None:
    context.vm_ip = (
        os.environ.get("FLATCAR_VM_IP")
        or os.environ.get("VM_IP")
        or os.environ.get("TMT_SSH_HOST")
        or ""
    )
    context.ssh_key = (
        os.environ.get("SSH_KEY")
        or os.environ.get("SSH_KEY_PATH")
        or os.environ.get("TMT_SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    )
    context.ssh_user = (
        os.environ.get("VM_USER")
        or os.environ.get("SSH_USER")
        or os.environ.get("TMT_SSH_USER", "core")
    )
    context.command_stdout = ""
    context.ssh_rc = 0
    context.last_ssh_result = None


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    context.command_stdout = ""
    context.ssh_rc = 0
    context.last_ssh_result = None


def after_scenario(context, scenario) -> None:
    pass
