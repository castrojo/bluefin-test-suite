"""
DX variant step definitions.

Most steps reuse qecore common_steps (GUI) or plain SSH steps.
Only DX-specific custom steps defined here.
"""
import subprocess

from behave import step
from qecore.common_steps import *  # noqa: F401,F403


def _ssh(context, cmd, timeout=60):
    """Run a DX command over SSH when a VM is configured, else locally."""
    if getattr(context, "vm_ip", ""):
        result = subprocess.run(
            [
                "ssh",
                "-i", context.ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-o", "LogLevel=ERROR",
                f"{context.ssh_user}@{context.vm_ip}",
                cmd,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    else:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    context.command_stdout = result.stdout.strip()
    context.last_command_output = context.command_stdout
    context.last_ssh_result = result
    context.ssh_rc = result.returncode
    return context.command_stdout, result.returncode


@step('Run and save command output: "{cmd}"')
def run_and_save_command_output(context, cmd):
    _ssh(context, cmd)


@step('SSH command return code is "{code}"')
def ssh_return_code_is(context, code):
    actual = getattr(context, "ssh_rc", None)
    last_result = getattr(context, "last_ssh_result", None)
    stderr = getattr(last_result, "stderr", "") if last_result else ""
    assert actual == int(code), (
        f"Expected SSH return code {code}, got {actual}\n"
        f"stdout: {getattr(context, 'command_stdout', '')}\n"
        f"stderr: {stderr}"
    )


@step('SSH command output "is" "{expected}"')
def ssh_output_is(context, expected):
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


@step('Last command output does not contain "{text}"')
def output_does_not_contain(context, text):
    """Assert last command output does NOT contain the given text."""
    actual = getattr(context, 'command_stdout', '') or ''
    assert text not in actual, f"Output unexpectedly contains '{text}': {actual}"


@step('Last command output contains "{text}"')
def output_contains(context, text):
    """Assert last command output contains the given text."""
    actual = getattr(context, 'command_stdout', '') or ''
    assert text in actual, f"Output does not contain '{text}': {actual}"
