"""Custom step definitions for software suite."""

import subprocess

from behave import step
from qecore.common_steps import *  # noqa: F401,F403


@step('Flatpak permissions table "{table}" is queryable')
def flatpak_permissions_table_is_queryable(context, table: str) -> None:
    result = subprocess.run(
        ["flatpak", "permissions", table],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # rc=0 means success (table exists, possibly empty);
    # rc=1 with "No permissions" is also a valid empty-table response.
    assert result.returncode == 0 or "No permissions" in result.stdout or "No permissions" in result.stderr, (
        f"flatpak permissions {table!r} failed unexpectedly: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('Set flatpak user override "{override}" for "{app_id}"')
def set_flatpak_user_override(context, override: str, app_id: str) -> None:
    result = subprocess.run(
        ["flatpak", "override", "--user"] + override.split() + [app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"flatpak override --user {override} {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('Flatpak user override "{fragment}" is active for "{app_id}"')
def flatpak_user_override_is_active(context, fragment: str, app_id: str) -> None:
    result = subprocess.run(
        ["flatpak", "override", "--user", "--show", app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"flatpak override --show {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert fragment in result.stdout, (
        f"Override fragment {fragment!r} not found in override output for {app_id}:\n{result.stdout}"
    )


@step('Reset flatpak user overrides for "{app_id}"')
def reset_flatpak_user_overrides(context, app_id: str) -> None:
    result = subprocess.run(
        ["flatpak", "override", "--user", "--reset", app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"flatpak override --user --reset {app_id} failed: "
        f"rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@step('No flatpak user overrides exist for "{app_id}"')
def no_flatpak_user_overrides_exist(context, app_id: str) -> None:
    result = subprocess.run(
        ["flatpak", "override", "--user", "--show", app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
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
def last_command_output_contains(context, text: str) -> None:
    actual = (
        getattr(context, "command_stdout", None)
        or getattr(context, "last_command_output", None)
        or getattr(context, "last_run_output", None)
        or ""
    )
    assert text in actual, (
        f"Last command output does not contain {text!r}:\n{actual}"
    )


@step('No journal entries match "{pattern}"')
def no_journal_entries_match(context, pattern: str) -> None:
    result = subprocess.run(
        ['journalctl', '-b', '--no-pager', '-g', pattern],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode in (0, 1), (
        f'journalctl failed while searching for {pattern!r}:\n'
        f'rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}'
    )
    assert result.stdout.strip() == '', (
        f'Unexpected journal entries matched {pattern!r}:\n{result.stdout.strip()}'
    )


@step('No coredump entries exist for "{name}"')
def no_coredump_entries_exist(context, name: str) -> None:
    result = subprocess.run(
        ['coredumpctl', 'list', name, '--no-pager', '--lines=10'],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode in (0, 1), (
        f'coredumpctl failed for {name}:\n'
        f'rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}'
    )
    matches = [line for line in result.stdout.splitlines() if name in line]
    assert not matches, f'Unexpected coredump entries for {name}: {matches}'


@step('Flatpak remote "{name}" is configured')
def flatpak_remote_is_configured(context, name: str) -> None:
    result = subprocess.run(
        ['flatpak', 'remote-list', '--columns=name'],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f'flatpak remote-list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    remotes = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert name in remotes, f'Flatpak remote {name!r} not found in {sorted(remotes)}'


@step('Flatpak app "{app_id}" is installed')
def flatpak_app_is_installed(context, app_id: str) -> None:
    result = subprocess.run(
        ['flatpak', 'list', '--app', '--columns=application'],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f'flatpak list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    apps = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert app_id in apps, f'Flatpak app {app_id!r} not found in installed apps'


@step('Flatpak app "{app_id}" is not installed')
def flatpak_app_is_not_installed(context, app_id: str) -> None:
    result = subprocess.run(
        ['flatpak', 'list', '--app', '--columns=application'],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f'flatpak list failed: rc={result.returncode}\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
    apps = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert app_id not in apps, f'Flatpak app {app_id!r} is still installed'
