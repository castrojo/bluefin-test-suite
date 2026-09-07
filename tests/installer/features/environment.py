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


_TRUTHY = ("true", "1", "yes")


def _luks_override():
    """Return True/False when LUKS_ENABLED is set explicitly, else None.

    An unset variable means "decide by probing the target", not "no LUKS" —
    the difference matters, see :func:`target_uses_luks`.
    """
    raw = os.environ.get("LUKS_ENABLED")
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in _TRUTHY


def target_uses_luks(context):
    """Return True when the installed target actually has a LUKS volume.

    `LUKS_ENABLED` used to be the only signal, and nothing ever set it: the
    reusable `e2e.yml` passes a fixed env list to the installer suite
    (VM_IP / VM_USER / SSH_KEY / SSH_PORT / ZSTD_CHUNKED) with no LUKS entry
    and no workflow input to add one. The `@luks` scenario therefore skipped on
    every run since it landed, which reads as "passed" in the report — the
    assertion for projectbluefin/common#385 was never actually exercised
    (projectbluefin/dakota#651).

    Probing the device under test fixes that without a workflow change: the
    scenario runs exactly when the target is a LUKS install and still skips
    cleanly everywhere else. `lsblk -rno TYPE` lists `crypt` for an unlocked
    dm-crypt mapping, which is what a booted LUKS system always has.

    `LUKS_ENABLED` is still honoured as an explicit override in both
    directions, so an operator can force the scenario on (to prove a
    regression) or off (to keep it out of a run) without editing code.
    """
    override = _luks_override()
    if override is not None:
        return override

    cached = getattr(context, "luks_enabled", None)
    if cached is not None:
        return cached

    from tests.shared.ssh_steps import run_ssh

    try:
        _, returncode = run_ssh(context, "lsblk -rno TYPE | grep -qx crypt", timeout=30)
    except Exception:  # noqa: BLE001 -- an unreachable DUT is not a LUKS target
        returncode = 1
    context.luks_enabled = returncode == 0
    return context.luks_enabled


def before_all(context):
    """Set up SSH connection parameters from environment."""
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/etc/ssh/test-key/id_ed25519")
    context.ssh_port = os.environ.get("SSH_PORT", "") or None
    # None = "not decided yet"; target_uses_luks() probes the DUT on first use
    # and caches the answer here.
    context.luks_enabled = _luks_override()
    context.efibootmgr_available = None  # lazily probed


def before_scenario(context, scenario):
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    # Skip LUKS scenarios when the installed system does not use LUKS
    if "luks" in scenario.tags and not target_uses_luks(context):
        scenario.skip(
            "target has no LUKS volume (no `crypt` device in lsblk, and "
            "LUKS_ENABLED not set) — skip LUKS cmdline scenarios"
        )
        return
    context.scenario = scenario
    context.command_stdout = ""
    context.ssh_rc = None
    context.last_ssh_result = None
    record_start(context)


def after_scenario(context, scenario):
    record_end(context, scenario)
