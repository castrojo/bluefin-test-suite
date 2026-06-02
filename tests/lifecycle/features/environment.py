"""
Lifecycle test environment — plain SSH, no qecore/AT-SPI.

This suite validates bootc upgrade/rollback/switch over SSH.
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
    context.expected_upgrade_digest = None
    context.original_digest = None
    context.initial_version_id = None
    context.current_version_id = None
    context.migration_source_ref = None


def before_scenario(context, scenario):
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    context.scenario = scenario
    context.command_stdout = ""
    context.ssh_rc = None
    context.last_ssh_result = None
    context.expected_upgrade_digest = None
    context.original_digest = None
    context.initial_version_id = None
    context.current_version_id = None
    context.migration_source_ref = None
    record_start(context)


def after_scenario(context, scenario):
    record_end(context, scenario)
