"""
Lifecycle test step definitions — bootc upgrade, rollback, switch.

Runner: plain SSH behave (no qecore/AT-SPI needed).
All steps execute commands on the VM over SSH.
"""
import json
import subprocess
from time import sleep, time

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


def _parse_bootc_status(context):
    raw = getattr(context, "command_stdout", "")
    assert raw, "No bootc status output available"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid bootc status JSON: {exc}\n{raw}") from exc


def _skip_current_scenario(context, reason):
    scenario = getattr(context, "scenario", None)
    if scenario is None:
        raise AssertionError(reason)
    try:
        scenario.skip(reason)
    except TypeError:
        scenario.skip()


@step("Bluefin VM is booted and reachable over SSH")
def vm_reachable(context):
    """Verify SSH connectivity to the test VM with retries."""
    last_error = ""
    for attempt in range(1, 6):
        try:
            stdout, returncode = run_ssh(context, "echo ok")
            if returncode == 0 and stdout == "ok":
                return
            last_error = f"rc={returncode}, stdout={stdout!r}"
        except subprocess.TimeoutExpired as exc:
            last_error = f"timeout after {exc.timeout}s"
        if attempt < 5:
            sleep(5)
    raise AssertionError(
        f"Cannot reach Bluefin VM at {context.vm_ip} over SSH after 5 attempts: {last_error}"
    )


@step("Staged deployment is present in bootc status")
def staged_deployment_present(context):
    """Parse bootc status JSON and assert staged deployment exists."""
    payload = _parse_bootc_status(context)
    assert payload.get("staged") is not None, (
        f"Expected staged deployment in bootc status, got: {payload}"
    )


@step("Active deployment matches upgrade target digest")
def active_matches_target(context):
    """Validate the running deployment matches the expected upgrade digest."""
    expected_digest = getattr(context, "expected_upgrade_digest", None)
    if not expected_digest:
        _skip_current_scenario(context, "expected_upgrade_digest is not set")
        return

    active_digest = _parse_bootc_status(context).get("active", {}).get("imageDigest")
    assert active_digest == expected_digest, (
        f"Active digest mismatch: expected {expected_digest}, got {active_digest}"
    )


@step("Active deployment matches original image digest")
def active_matches_original(context):
    """After rollback, verify we're back on the original deployment."""
    original_digest = getattr(context, "original_digest", None)
    if not original_digest:
        _skip_current_scenario(context, "original_digest is not set")
        return

    active_digest = _parse_bootc_status(context).get("active", {}).get("imageDigest")
    assert active_digest == original_digest, (
        f"Active digest mismatch: expected {original_digest}, got {active_digest}"
    )


@step('Active image reference contains "{fragment}"')
def active_image_contains(context, fragment):
    """Verify active image ref contains expected string (e.g. 'bluefin-dx')."""
    active_image = _parse_bootc_status(context).get("active", {}).get("image", "")
    assert fragment in active_image, (
        f"Expected '{fragment}' in active image reference '{active_image}'"
    )


@step("Reboot VM and wait for SSH")
def reboot_and_wait(context):
    """Trigger VM reboot and wait for SSH to come back."""
    try:
        run_ssh(context, "sudo reboot")
    except subprocess.TimeoutExpired:
        pass

    deadline = time() + 120
    last_error = "SSH never became reachable after reboot"
    sleep(5)
    while time() < deadline:
        try:
            stdout, returncode = run_ssh(context, "echo ok")
            if returncode == 0 and stdout == "ok":
                return
            last_error = f"rc={returncode}, stdout={stdout!r}"
        except subprocess.TimeoutExpired as exc:
            last_error = f"timeout after {exc.timeout}s"
        sleep(5)

    raise AssertionError(
        f"Bluefin VM at {context.vm_ip} did not come back over SSH within 120s: {last_error}"
    )


@step("ostree status shows two deployments")
def ostree_two_deployments(context):
    """Parse ostree admin status and verify exactly 2 deployments listed."""
    lines = getattr(context, "command_stdout", "").splitlines()
    deployment_count = sum(1 for line in lines if line.startswith("* "))
    assert deployment_count == 2, (
        f"Expected 2 ostree deployments, found {deployment_count}\n{context.command_stdout}"
    )
