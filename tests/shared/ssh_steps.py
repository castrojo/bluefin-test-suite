"""
Shared SSH step definitions for non-GUI test suites.
Used by lifecycle, security, nvidia, and hardware suites.
Import with: from tests.shared.ssh_steps import *
Or register with behave via environment.py importing this module.
"""

import subprocess
from time import sleep

from behave import step


def run_ssh(context, cmd, timeout=60):
    """Run a command over SSH and store stdout/return code on context."""
    ssh_opts = [
        "ssh",
        "-i",
        context.ssh_key,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "LogLevel=ERROR",
        f"{context.ssh_user}@{context.vm_ip}",
        cmd,
    ]
    result = subprocess.run(ssh_opts, capture_output=True, text=True, timeout=timeout)
    stdout = result.stdout.strip()
    context.command_stdout = stdout
    context.ssh_rc = result.returncode
    context.last_ssh_result = result
    return stdout, result.returncode


@step("Bluefin VM is booted and reachable over SSH")
def vm_reachable_over_ssh(context):
    """Verify SSH connectivity to the test VM with retries (5 attempts, 10s apart)."""
    last_error = ""
    for attempt in range(1, 6):
        try:
            stdout, returncode = run_ssh(context, "echo ok", timeout=20)
            if returncode == 0 and stdout == "ok":
                return
            last_error = f"rc={returncode}, stdout={stdout!r}"
        except subprocess.TimeoutExpired as exc:
            last_error = f"timeout after {exc.timeout}s"
        if attempt < 5:
            sleep(10)
    raise AssertionError(
        f"Cannot reach VM at {context.vm_ip} over SSH after 5 attempts: {last_error}"
    )


@step('Run SSH command: "{cmd}"')
def run_ssh_command(context, cmd):
    run_ssh(context, cmd)


@step('SSH command output "is" "{expected}"')
def ssh_output_is(context, expected):
    actual = getattr(context, "command_stdout", "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


@step('SSH command return code is "{code}"')
def ssh_return_code_is(context, code):
    actual = getattr(context, "ssh_rc", None)
    last_result = getattr(context, "last_ssh_result", None)
    stderr = getattr(last_result, "stderr", "") if last_result else ""
    stdout = getattr(last_result, "stdout", "") if last_result else ""
    assert actual == int(code), (
        f"SSH command exited {actual}, expected {code}\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )


@step('SSH command output is not empty')
def ssh_output_not_empty(context):
    actual = getattr(context, "command_stdout", "")
    assert actual.strip(), "SSH command output is empty"


@step('SSH command output stripped "is" "{expected}"')
def ssh_output_stripped_is(context, expected):
    actual = getattr(context, "command_stdout", "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


@step('SSH command output is not "{a}" and not "{b}"')
def ssh_output_not_values(context, a, b):
    actual = getattr(context, "command_stdout", "").strip()
    assert actual not in (a, b), (
        f"System state is '{actual}' — expected neither '{a}' nor '{b}'"
    )
