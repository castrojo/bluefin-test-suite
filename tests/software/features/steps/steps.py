"""Custom step definitions for software suite."""

import subprocess

from behave import step
from qecore.common_steps import *  # noqa: F401,F403


@step('Last command output contains "{text}"')
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
