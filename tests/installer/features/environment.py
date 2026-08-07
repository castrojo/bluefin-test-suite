"""
Installer post-boot test environment — plain SSH, no qecore/AT-SPI.

This suite validates post-install behavior after a fisherman (bootc-installer)
to-filesystem install. All checks execute over SSH against the installed system.
No GNOME session interaction needed — pure CLI commands.
"""
import os

from tests.shared.ssh_steps import *  # noqa: F401,F403

try:
    from tests.shared.timing import record_end, record_start
except Exception:  # noqa: BLE001
    def record_start(context):
        return None

    def record_end(context, scenario):
        return None


def before_all(context):
    """Set up SSH connection parameters from environment."""
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    context.ssh_port = os.environ.get("SSH_PORT", "") or None
    context.luks_enabled = os.environ.get("LUKS_ENABLED", "false").lower() in (
        "true", "1", "yes"
    )
    context.efibootmgr_available = None  # lazily probed


def before_scenario(context, scenario):
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    # Skip LUKS scenarios when the installed system does not use LUKS
    if "luks" in scenario.tags and not context.luks_enabled:
        scenario.skip(
            "LUKS_ENABLED not set — skip LUKS cmdline scenarios on non-LUKS install"
        )
        return
    context.scenario = scenario
    context.command_stdout = ""
    context.ssh_rc = None
    context.last_ssh_result = None
    record_start(context)


def after_scenario(context, scenario):
    record_end(context, scenario)
