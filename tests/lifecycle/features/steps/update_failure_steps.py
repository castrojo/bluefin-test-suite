"""Step definitions for update failure and rollback guard scenarios."""
import json
import time

from behave import step
from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


def _parse_bootc_status(context):
    raw = getattr(context, "command_stdout", "")
    assert raw, "No bootc status output — run 'sudo bootc status --format=json' first"
    try:
        return json.loads(raw).get("status", json.loads(raw))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"bootc status is not valid JSON: {exc}\n{raw}") from exc


def _skip(context, reason: str) -> None:
    scenario = getattr(context, "scenario", None)
    if scenario is not None:
        try:
            scenario.skip(reason)
        except TypeError:
            scenario.skip()


@step("bootc status rollback deployment matches original image digest")
def bootc_rollback_matches_original(context) -> None:
    """Assert .status.rollback digest matches the pre-upgrade original digest."""
    original_digest = getattr(context, "original_digest", None)
    if not original_digest:
        _skip(context, "original_digest not set — run 'Capture booted image digest' first")
        return

    status = _parse_bootc_status(context)
    rollback = status.get("rollback")
    assert rollback is not None, (
        "bootc status has no rollback deployment (.status.rollback is null). "
        "The rollback guard is broken — the previous deployment was not preserved."
    )
    rollback_digest = (
        rollback.get("image", {}).get("imageDigest")
        or rollback.get("imageDigest")
        or ""
    )
    assert rollback_digest == original_digest, (
        f"Rollback deployment digest {rollback_digest!r} != "
        f"original digest {original_digest!r}"
    )


@step("Force bootc rollback and reboot")
def force_bootc_rollback_and_reboot(context) -> None:
    """Invoke bootc rollback then reboot and wait for SSH to come back up."""
    run_ssh(context, "sudo bootc rollback", timeout=60)
    assert getattr(context, "command_returncode", 1) == 0, (
        f"bootc rollback failed: {context.command_stdout}"
    )
    # Trigger reboot (accept disconnect)
    try:
        run_ssh(context, "sudo systemctl reboot", timeout=10)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(5)
    # Wait for SSH to come back (up to 3 minutes)
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            run_ssh(context, "true", timeout=10)
            if getattr(context, "command_returncode", 1) == 0:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(5)
    raise AssertionError("VM did not come back after forced rollback reboot")
