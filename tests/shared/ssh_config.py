"""Shared SSH connection details resolution.

One source of truth for the SSH connection parameters used by the shared
SSH steps (``tests/shared/ssh_steps.py``), by suite-local helpers that run
commands on the VM (e.g. ``_flatpak`` in the software suite), and by suite
``environment.py`` hooks that probe the VM directly.

``resolve_ssh_details(context)`` reads, in priority order:

1. Behave ``context`` attributes (``ssh_key``, ``vm_ip``, ``ssh_user``,
   ``ssh_port``) — set by ``populate_ssh_context`` in ``before_all``.
2. Behave userdata keys (``ssh_key``, ``vm_ip``/``host``, ``vm_user``/``user``,
   ``ssh_port``) — behave's ``userdata`` is a plain dict; on a mock context
   without userdata, attribute lookup falls through to step 3 automatically.
3. Environment variables (``SSH_KEY``/``SSH_KEY_PATH``, ``VM_IP``,
   ``VM_USER``/``SSH_USER``, ``SSH_PORT``/``VM_PORT``).
4. Built-in defaults matching the runner container layout.
"""

import os

DEFAULT_SSH_KEY = "/home/bluefin-test/.ssh/id_ed25519"
DEFAULT_VM_IP = "127.0.0.1"
DEFAULT_VM_USER = "bluefin-test"
DEFAULT_SSH_PORT = "22"


def _first_value(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def resolve_ssh_details(context) -> dict:
    """Return SSH connection details for the current run.

    Keys: ``ssh_key``, ``vm_ip``, ``ssh_user``, ``ssh_port`` (all strings).
    """
    userdata = context.config.userdata
    return {
        "ssh_key": _first_value(
            getattr(context, "ssh_key", ""),
            userdata.get("ssh_key", ""),
            userdata.get("key", ""),
            os.environ.get("SSH_KEY", ""),
            os.environ.get("SSH_KEY_PATH", ""),
        ) or DEFAULT_SSH_KEY,
        "vm_ip": _first_value(
            getattr(context, "vm_ip", ""),
            userdata.get("vm_ip", ""),
            userdata.get("host", ""),
            os.environ.get("VM_IP", ""),
        ) or DEFAULT_VM_IP,
        "ssh_user": _first_value(
            getattr(context, "ssh_user", ""),
            userdata.get("vm_user", ""),
            userdata.get("user", ""),
            os.environ.get("VM_USER", ""),
            os.environ.get("SSH_USER", ""),
        ) or DEFAULT_VM_USER,
        "ssh_port": _first_value(
            getattr(context, "ssh_port", ""),
            userdata.get("ssh_port", ""),
            os.environ.get("SSH_PORT", ""),
            os.environ.get("VM_PORT", ""),
        ) or DEFAULT_SSH_PORT,
    }


def populate_ssh_context(context) -> None:
    """Set the context attributes ``run_ssh`` requires.

    Any suite whose steps star-import ``tests.shared.ssh_steps`` must call
    this from ``before_all`` — otherwise the shared steps raise
    ``AttributeError`` on first use.
    """
    details = resolve_ssh_details(context)
    context.ssh_key = details["ssh_key"]
    context.vm_ip = details["vm_ip"]
    context.ssh_user = details["ssh_user"]
    context.ssh_port = details["ssh_port"]
