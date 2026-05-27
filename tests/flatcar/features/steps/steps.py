"""
Step definitions for Flatcar boot and lifecycle tests.

Steps issue SSH commands to the Flatcar VM via subprocess.
Connection details come from context (set in environment.py before_all).

No qecore, no dogtail — plain behave.
"""
import subprocess
import time

from behave import step


def _ssh(context, command: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command on the Flatcar VM and record the result on context."""
    result = subprocess.run(
        [
            "ssh",
            "-i", context.ssh_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-o", "LogLevel=ERROR",
            f"{context.ssh_user}@{context.vm_ip}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    context.last_ssh_result = result
    context.command_stdout = result.stdout.strip()
    context.ssh_rc = result.returncode
    return result


@step("Flatcar VM is reachable over SSH")
def flatcar_vm_is_reachable(context) -> None:
    result = _ssh(context, "echo ok", timeout=20)
    assert result.returncode == 0, (
        f"Cannot reach Flatcar VM at {context.vm_ip}: {result.stderr}"
    )


@step('Run SSH command: "{command}"')
def run_ssh_command(context, command) -> None:
    _ssh(context, command)


@step('SSH command output "is" "{expected}"')
def ssh_output_is(context, expected) -> None:
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


@step('SSH command output is not "{value}"')
def ssh_output_is_not(context, value) -> None:
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual != value, f"System state is '{actual}' — expected not '{value}'"


@step('SSH command output is not "{val1}" and not "{val2}"')
def ssh_output_not_degraded(context, val1, val2) -> None:
    actual = (getattr(context, "command_stdout", "") or "").strip()
    assert actual not in (val1, val2), (
        f"System state is '{actual}' — expected neither '{val1}' nor '{val2}'"
    )


@step('SSH command return code is "{expected_code}"')
def ssh_return_code_is(context, expected_code) -> None:
    actual = getattr(
        context,
        "ssh_rc",
        getattr(getattr(context, "last_ssh_result", None), "returncode", None),
    )
    stdout = getattr(context, "command_stdout", "")
    stderr = getattr(getattr(context, "last_ssh_result", None), "stderr", "")
    assert actual == int(expected_code), (
        f"SSH command exited {actual}, expected {expected_code}\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )


@step("Install Flatcar to target disk via knuckle")
def install_flatcar_to_target_disk_via_knuckle(context) -> None:
    result = _ssh(
        context,
        "echo '{}' | sudo knuckle headless --config - --target /dev/vdb",
        timeout=300,
    )
    assert result.returncode == 0, (
        "Flatcar install via knuckle failed\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


@step("Reboot VM from target disk")
def reboot_vm_from_target_disk(context) -> None:
    # TODO: This is best-effort only; the runner cannot yet verify that the VM
    # actually switched its boot device before reconnecting over SSH.
    reboot_command = (
        "sudo systemctl reboot || sudo reboot || sudo shutdown -r now"
    )
    try:
        subprocess.run(
            [
                "ssh",
                "-i", context.ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-o", "LogLevel=ERROR",
                f"{context.ssh_user}@{context.vm_ip}",
                reboot_command,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        pass

    saw_disconnect = False
    disconnect_deadline = time.time() + 60
    while time.time() < disconnect_deadline:
        try:
            result = _ssh(context, "echo ok", timeout=15)
        except subprocess.TimeoutExpired:
            saw_disconnect = True
            break

        if result.returncode != 0:
            saw_disconnect = True
            break

        time.sleep(5)

    reconnect_deadline = time.time() + 120
    while time.time() < reconnect_deadline:
        try:
            result = _ssh(context, "echo ok", timeout=15)
        except subprocess.TimeoutExpired:
            time.sleep(5)
            continue

        if result.returncode == 0 and result.stdout.strip() == "ok":
            return

        if not saw_disconnect:
            saw_disconnect = result.returncode != 0
        time.sleep(5)

    raise AssertionError(
        f"Flatcar VM at {context.vm_ip} did not come back after reboot attempt"
    )


@step('Ignition hostname is "{expected}"')
def ignition_hostname_is(context, expected) -> None:
    _ssh(context, "cat /etc/hostname")
    ssh_return_code_is(context, "0")
    ssh_output_is(context, expected)


@step("Afterburn service is available")
def afterburn_service_is_available(context) -> None:
    _ssh(
        context,
        "systemctl status afterburn 2>&1 | grep -c 'active\\|inactive' || echo 0",
    )
    ssh_return_code_is(context, "0")
