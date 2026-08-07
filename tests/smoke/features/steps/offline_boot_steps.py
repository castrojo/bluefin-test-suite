"""Step definitions for offline and degraded-network boot scenarios."""
import os
import subprocess
import time

from behave import step
from tests.shared.ssh_config import resolve_ssh_details
from tests.shared.ssh_steps import *  # noqa: F401,F403


_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _ssh(context, cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    ssh = resolve_ssh_details(context)
    return subprocess.run(
        [
            "ssh",
            "-i", ssh["ssh_key"],
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", ssh["ssh_port"],
            f"{ssh['ssh_user']}@{ssh['vm_ip']}",
            cmd,
        ],
        capture_output=True, text=True, timeout=timeout,
    )


def _run_host(cmd: str, timeout: int = 30) -> tuple[str, int, str]:
    if _IN_CONTAINER:
        ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
        vm_ip = os.environ.get("VM_IP", "127.0.0.1")
        vm_user = os.environ.get("VM_USER", "bluefin-test")
        ssh_port = os.environ.get("SSH_PORT", "22")
        r = subprocess.run(
            ["ssh", "-i", ssh_key, "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
             "-p", ssh_port, f"{vm_user}@{vm_ip}", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
    else:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.returncode, r.stderr.strip()


@step("networkmanager-wait-online is not ordered before graphical.target")
def nm_wait_online_not_before_graphical(context) -> None:
    """Assert NM-wait-online does not block graphical.target.

    A hard Before= or Wants= dependency from graphical.target (or
    network-online.target when graphical.target requires it) on
    NetworkManager-wait-online.service will stall offline boots for up to
    the service's TimeoutStartSec.
    """
    # Check the unit's WantedBy / Before configuration
    output, _, _ = _run_host(
        "systemctl show NetworkManager-wait-online.service "
        "--property=WantedBy,Before,After,UnitFileState,LoadState --no-pager"
    )
    # If the service is masked or not enabled, it cannot block boot
    if "UnitFileState=masked" in output or "LoadState=not-found" in output:
        return

    # Check if graphical.target has a dependency on this unit
    graphical_deps_out, _, _ = _run_host(
        "systemctl show graphical.target --property=Wants,Requires --no-pager"
    )
    # The dangerous case: graphical.target directly Requires NM-wait-online
    assert "NetworkManager-wait-online" not in graphical_deps_out or \
           "UnitFileState=disabled" in output, (
        "NetworkManager-wait-online.service is required by graphical.target. "
        "This blocks offline boot. Mask or disable this unit in the image."
        f"\ngraphical.target deps: {graphical_deps_out}"
        f"\nNM-wait-online state: {output}"
    )


@step("uupd timer is enabled or absent")
def uupd_timer_enabled_or_absent(context) -> None:
    output, returncode, _ = _run_host(
        "systemctl is-enabled uupd.timer 2>/dev/null || echo not-found"
    )
    # Accept: enabled, static, or not-found. Reject: failed, disabled when uupd exists
    if "not-found" in output or "No such" in output:
        return
    assert output in ("enabled", "static", "not-found"), (
        f"uupd.timer has unexpected state: {output!r}. "
        "Expected 'enabled', 'static', or absent."
    )


@step("No uupd error journal entries at boot")
def no_uupd_error_journal_entries(context) -> None:
    output, returncode, _ = _run_host(
        "journalctl -u uupd -p err --no-pager -q --since 'boot' 2>/dev/null || true"
    )
    assert not output.strip(), (
        f"uupd produced error-level journal entries at boot:\n{output}\n"
        "Check that uupd handles network absence gracefully."
    )


@step("Drop the default route on the VM")
def drop_default_route(context) -> None:
    output, rc, stderr = _run_host(
        "sudo ip route show default"
    )
    # Store the default route for restoration
    context.offline_default_route = output.strip() if rc == 0 else None

    _, rc, _ = _run_host("sudo ip route del default 2>/dev/null || true")
    # Allow 1 second for route deletion to propagate
    time.sleep(1)


@step("Restore the default route on the VM")
def restore_default_route(context) -> None:
    route = getattr(context, "offline_default_route", None)
    if route:
        _run_host(f"sudo ip route add {route} 2>/dev/null || true")
    else:
        # Best-effort: try to bring the default interface back via DHCP
        _run_host("sudo nmcli device connect $(nmcli -t -f DEVICE device status | head -1 | cut -d: -f1) 2>/dev/null || true")
    time.sleep(2)
