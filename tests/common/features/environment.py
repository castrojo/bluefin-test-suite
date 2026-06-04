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


def _is_bluefin_image(image: str) -> bool:
    """Return True if the image reference looks like a Bluefin image."""
    lower = image.lower()
    return "bluefin" in lower or "bazzite" in lower


def before_all(context):
    userdata = context.config.userdata
    # When IMAGE env var is set (GHA runner), auto-detect image family so
    # @bluefin scenarios can be skipped gracefully on non-Bluefin images.
    image_ref = os.environ.get("IMAGE", userdata.get("image", ""))
    context.is_bluefin_image = _is_bluefin_image(image_ref) if image_ref else True
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
    # Set up Homebrew PATH so brew-installed tools (bat, eza, fd, rg, etc.) are
    # accessible in non-interactive SSH sessions.  The explicit PATH export
    # ensures standard system directories are present before brew shellenv
    # runs, which also fixes zsh/fish lookup in the bluefin-test SSH session.
    brew_prefix = (
        'export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH; '
        '[ -x /home/linuxbrew/.linuxbrew/bin/brew ] '
        '&& eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv 2>/dev/null)" '
        '|| true; '
    )
    context.ssh_command_prefix = (
        session_prefix
        + brew_prefix
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
    context.ssh_port = _first_value(
        userdata.get("ssh_port", ""),
        os.environ.get("SSH_PORT", ""),
        os.environ.get("VM_PORT", ""),
        os.environ.get("TMT_SSH_PORT", ""),
    ) or None
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0


def before_scenario(context, scenario):
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    # Skip @bluefin scenarios when running against a non-Bluefin image (e.g. Dakota).
    # Feature-level @bluefin tags are inherited by all scenarios in those features.
    is_bluefin = getattr(context, "is_bluefin_image", True)
    if not is_bluefin and "bluefin" in scenario.effective_tags:
        scenario.skip(
            f"Skipping @bluefin scenario on non-Bluefin image "
            f"(IMAGE={os.environ.get('IMAGE', 'unknown')})"
        )
        return
    context.command_stdout = ""
    context.last_command_output = ""
    context.last_ssh_result = None
    context.ssh_rc = 0
    record_start(context)


def after_scenario(context, scenario):
    record_end(context, scenario)
