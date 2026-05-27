"""
Hardware emulation step definitions.

Most steps are SSH command + output checks executed against the guest VM.
"""
import subprocess
import time

from behave import step


def _ssh(context, cmd, timeout=60):
    """Run a command on the hardware test VM and record its result."""
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
    context.command_stdout = result.stdout.strip()
    context.last_command_output = context.command_stdout
    context.last_ssh_result = result
    context.ssh_rc = result.returncode
    return context.command_stdout, result.returncode


@step('Bluefin VM is booted and reachable over SSH')
def bluefin_vm_is_booted_and_reachable(context):
    last_output = ""
    last_rc = None
    for attempt in range(5):
        try:
            last_output, last_rc = _ssh(context, "echo ok", timeout=20)
        except subprocess.TimeoutExpired:
            last_output, last_rc = "", None
        if last_rc == 0 and last_output == "ok":
            return
        if attempt < 4:
            time.sleep(10)

    raise AssertionError(
        f"Bluefin VM is not reachable over SSH at {context.vm_ip}; "
        f"last rc={last_rc}, output={last_output!r}"
    )


@step('Run SSH command: "{command}"')
def run_ssh_command(context, command):
    _ssh(context, command)


@step('SSH command return code is "{expected_code}"')
def ssh_return_code_is(context, expected_code):
    actual = getattr(context, "ssh_rc", None)
    last_result = getattr(context, "last_ssh_result", None)
    stderr = getattr(last_result, "stderr", "") if last_result else ""
    assert actual == int(expected_code), (
        f"SSH command exited {actual}, expected {expected_code}\n"
        f"stdout: {getattr(context, 'command_stdout', '')}\n"
        f"stderr: {stderr}"
    )


@step('SSH command output "is" "{expected}"')
def ssh_output_is(context, expected):
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


@step('SSH command output stripped "is" "{expected}"')
def ssh_output_stripped_is(context, expected):
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"
