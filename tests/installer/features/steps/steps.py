"""
Installer post-boot step definitions — UEFI entries, Flatpak exclusion, LUKS cmdline.

Runner: plain SSH behave (no qecore/AT-SPI needed).
All steps execute commands on the installed VM over SSH.
"""
import re

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


def _skip_scenario(context, reason):
    """Skip the current scenario gracefully."""
    scenario = getattr(context, "scenario", None)
    if scenario is None:
        raise AssertionError(reason)
    try:
        scenario.skip(reason)
    except TypeError:
        scenario.skip()


# ---------------------------------------------------------------------------
# 1. UEFI boot entry written to firmware (fisherman #2)
# ---------------------------------------------------------------------------


@step("efibootmgr output contains BootCurrent entry")
def efibootmgr_has_bootcurrent(context):
    """Verify efibootmgr -v shows a BootCurrent entry (system booted via UEFI)."""
    run_ssh(context, "efibootmgr -v")
    rc = getattr(context, "ssh_rc", 1)
    if rc != 0:
        _skip_scenario(
            context,
            "efibootmgr is not available or failed (rc={rc}). "
            "This may indicate the system was not booted via UEFI or /sys "
            "is not accessible. Skipping UEFI boot entry scenario.".format(rc=rc),
        )
        return
    output = getattr(context, "command_stdout", "")
    assert "BootCurrent" in output, (
        f"Expected 'BootCurrent' in efibootmgr -v output.\nGot:\n{output}"
    )
    print("Confirmed: BootCurrent entry present in efibootmgr -v", flush=True)


@step("efibootmgr output contains BootXXXX entries")
def efibootmgr_has_boot_entries(context):
    """Verify efibootmgr -v shows at least one BootXXXX entry (installer wrote entry)."""
    run_ssh(context, "efibootmgr -v")
    rc = getattr(context, "ssh_rc", 1)
    if rc != 0:
        _skip_scenario(
            context,
            "efibootmgr is not available or failed (rc={rc}). "
            "This may indicate the system was not booted via UEFI or /sys "
            "is not accessible. Skipping UEFI boot entry scenario.".format(rc=rc),
        )
        return
    output = getattr(context, "command_stdout", "")
    # Boot entries look like: Boot0001* Fedora or Boot0000* Dakota
    boot_entries = re.findall(r"Boot[0-9A-Fa-f]{4}\*", output)
    assert len(boot_entries) >= 1, (
        f"Expected at least one BootXXXX* entry in efibootmgr -v output.\n"
        f"Got:\n{output}"
    )
    print(
        f"Confirmed: {len(boot_entries)} BootXXXX* entries found: {boot_entries}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# 2. Installer Flatpaks excluded from target (fisherman #1)
# ---------------------------------------------------------------------------


@step("no installer Flatpaks appear in system flatpak list")
def no_installer_flatpaks(context):
    """Verify the tuna-installer (org.bootcinstaller) Flatpak is NOT on the installed system.

    CopyFlatpaks copies the system flatpak store to the installed system.
    On the live ISO the tuna-installer app is in the system store and must
    not appear on the installed target.
    """
    run_ssh(context, "flatpak list --system --app 2>/dev/null || true")
    output = getattr(context, "command_stdout", "")
    assert "org.bootcinstaller" not in output, (
        f"Expected 'org.bootcinstaller' to be absent from flatpak list --system --app.\n"
        f"Got:\n{output}"
    )
    print("Confirmed: org.bootcinstaller is not installed on the target system", flush=True)


# ---------------------------------------------------------------------------
# 3. LUKS cmdline UUID parseable with rd.luks.name= format (common#385)
# ---------------------------------------------------------------------------


@step("kernel cmdline contains rd.luks.name= entry")
def cmdline_has_rd_luks_name(context):
    """Verify /proc/cmdline contains a parseable rd.luks.name= LUKS UUID entry.

    After a LUKS install, /proc/cmdline should contain either rd.luks.uuid=
    or rd.luks.name= format. This verifies the luks-tpm2-autounlock fix will
    work on the installed system.
    """
    run_ssh(context, "cat /proc/cmdline")
    output = getattr(context, "command_stdout", "")
    assert output.strip(), "No output from cat /proc/cmdline"

    # Check for rd.luks.name=<uuid>=<device> format
    # Example: rd.luks.name=luks-<uuid>=/dev/sda3
    luks_name_match = re.search(
        r"rd\.luks\.name=([a-f0-9-]+)=(\S+)", output
    )
    if luks_name_match:
        uuid = luks_name_match.group(1)
        device = luks_name_match.group(2)
        assert len(uuid) >= 32, (
            f"rd.luks.name= UUID {uuid!r} seems too short to be a valid LUKS UUID"
        )
        print(
            f"Confirmed: rd.luks.name= entry found — UUID={uuid}, device={device}",
            flush=True,
        )
        return

    # Fallback: check for rd.luks.uuid= format
    luks_uuid_match = re.search(r"rd\.luks\.uuid=([a-f0-9-]+)", output)
    if luks_uuid_match:
        uuid = luks_uuid_match.group(1)
        print(
            f"Confirmed: rd.luks.uuid= entry found — UUID={uuid}",
            flush=True,
        )
        return

    raise AssertionError(
        "Expected either rd.luks.name=<uuid>=<device> or rd.luks.uuid=<uuid> "
        "in /proc/cmdline, but neither was found.\n"
        f"Command line: {output}"
    )
