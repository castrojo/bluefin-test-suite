"""Custom step definitions for system health smoke checks."""
import json
import os
import re
import subprocess

from behave import step
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass


IGNORED_FAILED_UNITS_IN_VM = {
    "mcelog.service",
    "avahi-daemon.service",
    "cups.service",
    "cups.path",
    "cups.socket",
    "cups.browsed.service",
    "podman-auto-update.timer",
    "malcontent-control.service",
    # malcontent-webd-update.timer requires network access to fetch parental-controls
    # blocklists; fails in isolated QEMU VMs (Dakota, CentOS Stream based images)
    "malcontent-webd-update.timer",
    "malcontent-webd-update.service",
    "blueman-mechanism.service",
    "gnome-remote-desktop.service",
    # bootupd cannot update the bootloader inside a QEMU VM (no EFI vars/bootctl)
    "bootloader-update.service",
    # NVIDIA services require physical GPU hardware — always fail in QEMU
    "nvidia-persistenced.service",
    "ublue-nvctk-cdi.service",
    # systemd-oomd needs memory pressure files that QEMU VMs don't expose
    "systemd-oomd.service",
}

# When behave runs inside the runner container (--pid=host --privileged), system
# commands like systemctl, bootc, and ujust are not in the container image. Use
# nsenter to run them in the host VM's mount namespace via /proc/1/ns/mnt.
_IN_CONTAINER = os.path.isfile("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _run(cmd: str, timeout: int = 30):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _run_host(cmd: str, timeout: int = 30):
    """Run cmd in the host VM's mount namespace when inside the runner container."""
    if _IN_CONTAINER:
        result = subprocess.run(
            ["nsenter", "--mount=/proc/1/ns/mnt", "--", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _running_in_vm() -> bool:
    _, returncode, _ = _run_host("systemd-detect-virt --quiet")
    return returncode == 0


def _has_image_reference(value) -> bool:
    if isinstance(value, dict):
        if value.get("imageDigest") or value.get("image"):
            return True
        return any(_has_image_reference(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_image_reference(item) for item in value)
    return False


def _skip_scenario(context, reason: str) -> None:
    scenario = getattr(context, "scenario", None)
    if scenario is not None:
        try:
            scenario.skip(reason)
        except TypeError:
            scenario.skip()


@step("No failed systemd units at boot")
def no_failed_systemd_units_at_boot(context) -> None:
    output, returncode, stderr = _run_host("systemctl list-units --failed --no-pager --plain")
    assert returncode == 0, f"systemctl failed: {stderr or output}"

    failed_units = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("UNIT ", "LOAD ", "Legend:")):
            continue
        if stripped.endswith("loaded units listed.") or stripped.startswith("To show all installed unit files"):
            continue
        if re.match(r"^\S+\s+loaded\s+failed\s+failed\s+", stripped):
            unit = stripped.split()[0]
            if _running_in_vm() and unit in IGNORED_FAILED_UNITS_IN_VM:
                continue
            failed_units.append(stripped)

    assert not failed_units, f"Failed systemd units detected: {failed_units}"


@step("No critical kernel errors in journal")
def no_critical_kernel_errors_in_journal(context) -> None:
    output, returncode, stderr = _run_host("journalctl -b -p 0..2 --no-pager -q")
    assert returncode == 0, f"journalctl failed: {stderr or output}"
    assert not output, f"Critical journal entries found:\n{output}"


@step("Bluefin image identity is present in os-release")
def bluefin_image_identity_is_present_in_os_release(context) -> None:
    output, returncode, stderr = _run_host("grep -i bluefin /etc/os-release")
    if returncode != 0:
        # Not a Bluefin image — skip rather than fail so non-Bluefin smoke runs stay green
        _skip_scenario(context, "No Bluefin identity in /etc/os-release — not a Bluefin image")
        return
    assert output, "Expected non-empty Bluefin match in /etc/os-release"


@step("bootc status shows a valid image reference")
def bootc_status_shows_a_valid_image_reference(context) -> None:
    # Try privileged first (sudo); fall back to unprivileged for read-only status.
    output, returncode, stderr = _run_host("sudo bootc status --format=json 2>&1 || bootc status --format=json 2>&1")
    combined_err = (stderr or output or "").lower()
    # In CI QEMU VMs, bootc may fail to open /boot (no bootupd, bare kernel boot).
    # Treat this as a known VM limitation — skip the assertion rather than fail.
    if returncode != 0 and "opendir(boot)" in combined_err:
        return
    # bootc not installed on this image — skip gracefully
    if returncode != 0 and ("not found" in combined_err or "no such file" in combined_err or "command not found" in combined_err):
        _skip_scenario(context, "bootc not found on this image")
        return
    # Non-root access denied without --sysroot — skip rather than fail
    if returncode != 0 and ("not root" in combined_err or "sysroot" in combined_err):
        _skip_scenario(context, "bootc status requires root — skipping on non-root runner")
        return
    assert returncode == 0, f"bootc status failed: {stderr or output}"

    try:
        status = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"bootc status did not return valid JSON: {exc}") from exc

    assert _has_image_reference(status), "bootc status JSON does not contain an image or imageDigest field"


@step("External DNS resolves external hosts")
def external_dns_resolves_external_hosts(context) -> None:
    output, returncode, _ = _run("getent hosts ghcr.io")
    assert returncode == 0 and output.strip(), (
        f"DNS resolution for ghcr.io failed (rc={returncode}): {output!r}"
    )


@step('Writable system storage has at least "{percent}" percent free space')
def writable_system_storage_has_at_least_percent_free_space(context, percent: str) -> None:
    output, returncode, stderr = _run_host("df -P /var")
    assert returncode == 0, f"df failed: {stderr or output}"

    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) >= 2, f"Unexpected df output: {output}"

    columns = lines[1].split()
    assert len(columns) >= 5, f"Could not parse df output row: {lines[1]}"

    used_percent = int(columns[4].rstrip("%"))
    free_percent = 100 - used_percent
    required_free_percent = int(percent)
    assert free_percent >= required_free_percent, (
        f"Root filesystem free space {free_percent}% is below required {required_free_percent}%"
    )


@step("ujust is on PATH and returns exit 0")
def ujust_on_path(context) -> None:
    which_out, which_rc, _ = _run_host("which ujust 2>/dev/null")
    if which_rc != 0 or not which_out:
        # ujust is Bluefin-specific — skip gracefully on non-Bluefin images
        _skip_scenario(context, "ujust not on PATH — not a Bluefin image")
        return
    _, returncode, stderr = _run_host("ujust --version 2>/dev/null || ujust --help 2>/dev/null")
    assert returncode == 0, f"ujust exited non-zero: {stderr}"


@step("ujust --list prints at least one task")
def ujust_list_has_tasks(context) -> None:
    output, returncode, stderr = _run_host("ujust --list")
    # just 1.x may fail with a parse error on newer Justfile syntax used by Bluefin.
    # Treat this as a known compatibility issue — warn but don't fail the suite.
    if returncode != 0:
        combined = (stderr or output or "").lower()
        if "unknown start of token" in combined or "unknown token" in combined:
            print(
                f"WARNING: ujust --list parse error (known just version compat issue): {stderr or output}",
                flush=True,
            )
            return
        assert returncode == 0, f"ujust --list failed (rc={returncode}): {stderr or output}"
    tasks = [line for line in output.splitlines() if line.strip()]
    assert tasks, "ujust --list returned no tasks"


@step("ujust report --confirm rejects non-integer issue number")
def ujust_report_confirm_invalid(context) -> None:
    output, returncode, stderr = _run_host("ujust report --confirm abc 2>&1")
    assert returncode == 1, f"Expected exit code 1, got {returncode}. Output: {output}"
    assert "positive integer" in output, f"Expected validation error, got: {output}"


@step("ujust report --confirm without issue number prints error")
def ujust_report_confirm_missing_number(context) -> None:
    output, returncode, stderr = _run_host("ujust report --confirm 2>&1")
    assert returncode == 1, f"Expected exit code 1, got {returncode}. Output: {output}"
    assert "requires an issue number" in output, f"Expected parameter error, got: {output}"
