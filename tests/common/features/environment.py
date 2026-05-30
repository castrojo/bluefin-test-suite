"""
Common layer test environment — plain SSH, no qecore.

This suite validates the projectbluefin/common OCI layer by running CLI- and
GSettings-focused checks over SSH against a live Bluefin session.
"""
import os
import shlex

from tests.shared.ssh_steps import *  # noqa: F401,F403

try:
    from tests.shared.timing import record_end, record_start
except Exception:  # noqa: BLE001
    def record_start(context):
        return None

    def record_end(context, scenario):
        return None


def _first_value(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def before_all(context):
    userdata = context.config.userdata
    context.vm_ip = _first_value(
        userdata.get("vm_ip", ""),
        userdata.get("host", ""),
        os.environ.get("VM_IP", ""),
        os.environ.get("TMT_SSH_HOST", ""),
    )
    context.ssh_user = _first_value(
        userdata.get("vm_user", ""),
        userdata.get("user", ""),
        os.environ.get("VM_USER", ""),
        os.environ.get("SSH_USER", ""),
        os.environ.get("TMT_SSH_USER", "bluefin-test"),
    )
    context.ssh_key = _first_value(
        userdata.get("ssh_key", ""),
        userdata.get("key", ""),
        os.environ.get("SSH_KEY", ""),
        os.environ.get("SSH_KEY_PATH", ""),
        os.environ.get("TMT_SSH_KEY", "/etc/ssh/test-key/id_ed25519"),
    )
    session_env = _first_value(
        userdata.get("session_env", ""),
        os.environ.get("COMMON_SESSION_ENV_FILE", ""),
    )
    session_prefix = ""
    if session_env:
        quoted = shlex.quote(session_env)
        session_prefix = f"if [ -f {quoted} ]; then . {quoted}; fi; "
    context.ssh_command_prefix = (
        session_prefix
        + 'XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}; '
        + 'export XDG_RUNTIME_DIR; '
        + 'SESSION_BUS=$(systemctl --user show-environment 2>/dev/null '
        + '| sed -n "s/^DBUS_SESSION_BUS_ADDRESS=//p" | head -1); '
        + '[ -z "$SESSION_BUS" ] && [ -S "$XDG_RUNTIME_DIR/bus" ] '
        + '&& SESSION_BUS="unix:path=$XDG_RUNTIME_DIR/bus"; '
        + '[ -n "$SESSION_BUS" ] && export DBUS_SESSION_BUS_ADDRESS="$SESSION_BUS"; '
        + 'WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-$(ls "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null '
        + '| head -1 | xargs -r basename 2>/dev/null || true)}; '
        + '[ -n "$WAYLAND_DISPLAY" ] && export WAYLAND_DISPLAY="$WAYLAND_DISPLAY"'
    )
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0


def before_scenario(context, scenario):
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0
    record_start(context)


def after_scenario(context, scenario):
    record_end(context, scenario)
