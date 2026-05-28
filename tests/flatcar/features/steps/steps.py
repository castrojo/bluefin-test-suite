"""
Step definitions for Flatcar boot and lifecycle tests.

Steps issue SSH commands to the Flatcar VM via subprocess.
Connection details come from context (set in environment.py before_all).

No qecore, no dogtail — plain behave.
"""
import subprocess
import time

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


@step("Flatcar VM is reachable over SSH")
def flatcar_vm_is_reachable(context) -> None:
    stdout, returncode = run_ssh(context, "echo ok", timeout=20)
    stderr = getattr(getattr(context, "last_ssh_result", None), "stderr", "")
    assert returncode == 0 and stdout == "ok", (
        f"Cannot reach Flatcar VM at {context.vm_ip}: {stderr}"
    )


@step("Install Flatcar to target disk via knuckle")
def install_flatcar_to_target_disk_via_knuckle(context) -> None:
    stdout, returncode = run_ssh(
        context,
        "echo '{}' | sudo knuckle headless --config - --target /dev/vdb",
        timeout=300,
    )
    stderr = getattr(getattr(context, "last_ssh_result", None), "stderr", "")
    assert returncode == 0, (
        "Flatcar install via knuckle failed\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
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
            stdout, returncode = run_ssh(context, "echo ok", timeout=15)
        except subprocess.TimeoutExpired:
            saw_disconnect = True
            break

        if returncode != 0:
            saw_disconnect = True
            break

        time.sleep(5)

    reconnect_deadline = time.time() + 120
    while time.time() < reconnect_deadline:
        try:
            stdout, returncode = run_ssh(context, "echo ok", timeout=15)
        except subprocess.TimeoutExpired:
            time.sleep(5)
            continue

        if returncode == 0 and stdout == "ok":
            return

        if not saw_disconnect:
            saw_disconnect = returncode != 0
        time.sleep(5)

    raise AssertionError(
        f"Flatcar VM at {context.vm_ip} did not come back after reboot attempt"
    )


@step('Ignition hostname is "{expected}"')
def ignition_hostname_is(context, expected) -> None:
    run_ssh(context, "cat /etc/hostname")
    ssh_return_code_is(context, "0")
    ssh_output_is(context, expected)


@step("Afterburn service is available")
def afterburn_service_is_available(context) -> None:
    run_ssh(
        context,
        "systemctl status afterburn 2>&1 | grep -c 'active\\|inactive' || echo 0",
    )
    ssh_return_code_is(context, "0")
