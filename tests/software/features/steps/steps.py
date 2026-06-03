"""Custom step definitions for software suite."""

import os
import subprocess

from behave import step
from qecore.common_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import *  # noqa: F401,F403

_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _flatpak(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run flatpak via SSH when inside the runner container."""
    if _IN_CONTAINER:
        ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
        vm_ip = os.environ.get("VM_IP", "127.0.0.1")
        vm_user = os.environ.get("VM_USER", "bluefin-test")
        ssh_port = os.environ.get("SSH_PORT", "22")
        return subprocess.run(
            ["ssh", "-i", ssh_key, "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
             "-p", ssh_port, f"{vm_user}@{vm_ip}",
             " ".join(["flatpak"] + [f"'{a}'" for a in args])],
            capture_output=True, text=True, timeout=timeout,
        )
    return subprocess.run(
        ["flatpak"] + args,
        capture_output=True, text=True, timeout=timeout,
    )


@step('Flatpak permissions table "{table}" is queryable')
def flatpak_permissions_table_is_queryable(context, table: str) -> None:
    result = _flatpak(["permissions", table])
    # rc=0 means success (table exists, possibly empty);
    # rc=1 with "No permissions" is also a valid empty-table response.
    assert result.returncode == 0 or "No permissions" in result.stdout or "No permissions" in result.stderr, (
        f"flatpak permissions {table!r} failed unexpectedly: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('Set flatpak user override "{override}" for "{app_id}"')
def set_flatpak_user_override(context, override: str, app_id: str) -> None:
    result = _flatpak(["override", "--user"] + override.split() + [app_id])
    assert result.returncode == 0, (
        f"flatpak override --user {override} {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('Flatpak user override "{fragment}" is active for "{app_id}"')
def flatpak_user_override_is_active(context, fragment: str, app_id: str) -> None:
    result = _flatpak(["override", "--user", "--show", app_id])
    assert result.returncode == 0, (
        f"flatpak override --show {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert fragment in result.stdout, (
        f"Override fragment {fragment!r} not found in override output for {app_id}:\n{result.stdout}"
    )


@step('Reset flatpak user overrides for "{app_id}"')
def reset_flatpak_user_overrides(context, app_id: str) -> None:
    result = _flatpak(["override", "--user", "--reset", app_id])
    assert result.returncode == 0, (
        f"flatpak override --user --reset {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('No flatpak user overrides exist for "{app_id}"')
def no_flatpak_user_overrides_exist(context, app_id: str) -> None:
    result = _flatpak(["override", "--user", "--show", app_id])
    # After reset, --show returns empty output (rc=0) or a minimal [Context] header.
    assert result.returncode == 0, (
        f"flatpak override --show {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # No override-specific keys should be present (filesystems, devices, etc.)
    override_keys = {"filesystems", "devices", "features", "sockets", "env"}
    lines_lower = {line.strip().lower() for line in result.stdout.splitlines()}
    found = override_keys & lines_lower
    assert not found, (
        f"Expected no user overrides for {app_id} after reset, "
        f"but found active override keys: {found}\n{result.stdout}"
    )


@step('Flatpak remote "{name}" is configured')
def flatpak_remote_is_configured(context, name: str) -> None:
    result = _flatpak(['remote-list', '--columns=name'])
    assert result.returncode == 0, (
        f'flatpak remote-list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    remotes = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert name in remotes, f'Flatpak remote {name!r} not found in {sorted(remotes)}'


@step('Flatpak app "{app_id}" is installed')
def flatpak_app_is_installed(context, app_id: str) -> None:
    result = _flatpak(['list', '--app', '--columns=application'])
    assert result.returncode == 0, (
        f'flatpak list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    apps = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert app_id in apps, f'Flatpak app {app_id!r} not found in installed apps'


@step('Flatpak app "{app_id}" is not installed')
def flatpak_app_is_not_installed(context, app_id: str) -> None:
    result = _flatpak(['list', '--app', '--columns=application'])
    assert result.returncode == 0, (
        f'flatpak list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    apps = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert app_id not in apps, f'Flatpak app {app_id!r} is still installed'
