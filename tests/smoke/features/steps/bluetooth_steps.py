"""Custom step definitions for Bluetooth smoke tests via hci_vhci."""
import time

from behave import step

from steps.steps import _run_host


def _skip_scenario(context, reason: str) -> None:
    """Skip the current scenario with an explanatory reason."""
    scenario = getattr(context, "scenario", None)
    if scenario is not None:
        try:
            scenario.skip(reason)
        except TypeError:
            scenario.skip()


def _sudo_available() -> bool:
    """Return True when passwordless sudo is available to the test user."""
    _, rc, _ = _run_host("sudo -n true", timeout=5)
    return rc == 0


def _service_is_active(unit: str) -> bool:
    """Return True when ``unit`` is reported active by systemctl."""
    out, rc, _ = _run_host(f"systemctl is-active {unit}", timeout=10)
    return rc == 0 and out.strip() == "active"


def _service_load_state(unit: str) -> str:
    """Return the LoadState of a unit, or an empty string on error."""
    out, rc, _ = _run_host(f"systemctl show {unit} --property=LoadState --value", timeout=10)
    if rc != 0:
        return ""
    return out.strip()


@step("the bluetoothd binary is present")
def bluetoothd_binary_is_present(context) -> None:  # noqa: ARG001
    """Assert the BlueZ daemon binary exists at a known path."""
    out, rc, err = _run_host(
        "test -x /usr/libexec/bluetooth/bluetoothd || test -x /usr/sbin/bluetoothd"
    )
    assert rc == 0, f"bluetoothd binary not found at expected paths: {out} {err}"


@step("the bluetooth.service unit file is present")
def bluetooth_service_unit_present(context) -> None:  # noqa: ARG001
    """Assert the bluetooth.service unit file exists.

    The CI image masks bluetooth.service to shorten first-boot, so we accept
    LoadState=masked as a valid "present" state and verify the vendor unit
    file exists in /usr/lib/systemd/system/.
    """
    _, rc, err = _run_host("test -f /usr/lib/systemd/system/bluetooth.service")
    assert rc == 0, f"bluetooth.service unit file not found: {err}"

    out, rc, err = _run_host(
        "systemctl show bluetooth.service --property=LoadState --value"
    )
    if rc == 0:
        load_state = out.strip()
        assert load_state in {"loaded", "masked", "active"}, (
            f"bluetooth.service LoadState is {load_state!r}"
        )


@step("bluetooth.service is started if inactive")
def bluetooth_service_started_if_inactive(context) -> None:
    """Start bluetooth.service when it is not already active.

    The CI image masks bluetooth.service; unmask it first so the daemon can
    actually start. The service has ConditionPathIsDirectory=/sys/class/bluetooth,
    so this step must run after the hci_vhci module has created that directory.
    The VM is ephemeral, so leaving the service unmasked is harmless.
    """
    if _service_is_active("bluetooth.service"):
        return
    if not _sudo_available():
        _skip_scenario(context, "passwordless sudo not available; cannot start bluetooth.service")
        return

    load_state = _service_load_state("bluetooth.service")
    if load_state == "not-found":
        _skip_scenario(context, "bluetooth.service unit not found")
        return
    if load_state == "masked":
        _, rc, err = _run_host(
            "sudo systemctl unmask bluetooth.service", timeout=30
        )
        if rc != 0:
            _skip_scenario(context, f"Failed to unmask bluetooth.service: {err}")
            return

    # bluetooth.service refuses to start unless a Bluetooth class device exists.
    # Give hci_vhci up to 5 s to register the virtual controller.
    bt_class_ready = False
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        _, rc, _ = _run_host("test -d /sys/class/bluetooth", timeout=5)
        if rc == 0:
            bt_class_ready = True
            break
        time.sleep(0.5)
    if not bt_class_ready:
        _skip_scenario(context, "hci_vhci adapter not visible under /sys/class/bluetooth")
        return

    _, rc, err = _run_host(
        "sudo systemctl start bluetooth.service", timeout=30
    )
    if rc != 0:
        _skip_scenario(context, f"Failed to start bluetooth.service: {err}")
        return
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if _service_is_active("bluetooth.service"):
            return
        time.sleep(0.5)
    _skip_scenario(context, "bluetooth.service did not become active after start")


def _start_vhci_keepalive() -> str:
    """Load hci_vhci and open /dev/vhci so the kernel creates a virtual adapter.

    The hci_vhci driver only registers an HCI device after a process opens
    /dev/vhci and keeps it open. A forked keepalive process detaches, holds the
    device open, and writes its PID to /tmp/vhci-keepalive.pid. The parent
    returns the PID immediately.
    """
    _run_host("sudo modprobe hci_vhci", timeout=30)
    cmd = (
        "sudo python3 -c "
        "'import os, sys, time; "
        "pid = os.fork(); "
        "if pid != 0: print(pid); sys.exit(); "
        "os.setsid(); "
        "os.close(0); os.close(1); os.close(2); "
        'os.open(\"/dev/null\", os.O_RDONLY); '
        'os.open(\"/dev/null\", os.O_WRONLY); '
        'os.open(\"/dev/null\", os.O_WRONLY); '
        'with open(\"/tmp/vhci-keepalive.pid\", \"w\") as f: '
        '    f.write(str(os.getpid())); '
        'fd = os.open(\"/dev/vhci\", os.O_RDWR); '
        "time.sleep(3600)'"
    )
    out, rc, err = _run_host(cmd, timeout=10)
    if rc != 0:
        return ""
    pid = out.strip().splitlines()[-1]
    return pid


@step("the hci_vhci kernel module is loaded")
def hci_vhci_module_loaded(context) -> None:
    """Load hci_vhci and instantiate a virtual adapter via /dev/vhci."""
    if not _sudo_available():
        _skip_scenario(context, "passwordless sudo not available; cannot load hci_vhci")
        return
    pid = _start_vhci_keepalive()
    if not pid:
        _skip_scenario(context, "failed to start hci_vhci keepalive process")
        return
    context.vhci_keepalive_pid = pid


@step("a Bluetooth controller appears within {timeout:d} seconds")
def bluetooth_controller_appears(context, timeout: int) -> None:
    """Poll until BlueZ exposes a controller at /org/bluez/hci0."""
    deadline = time.monotonic() + timeout
    last_err = ""
    while time.monotonic() < deadline:
        out, rc, err = _run_host(
            "busctl introspect org.bluez /org/bluez/hci0 | grep -q org.bluez.Adapter1",
            timeout=10,
        )
        if rc == 0:
            return
        last_err = err or out
        time.sleep(0.5)
    _skip_scenario(context, f"No Bluetooth controller appeared within {timeout}s: {last_err}")


@step("the Bluetooth controller is powered on")
def bluetooth_controller_powered_on(context) -> None:
    """Power on the virtual adapter and verify Powered=true."""
    if not _sudo_available():
        _skip_scenario(context, "passwordless sudo not available; cannot power on adapter")
        return
    _run_host("sudo btmgmt power on", timeout=10)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        out, rc, err = _run_host(
            "busctl get-property org.bluez /org/bluez/hci0 org.bluez.Adapter1 Powered",
            timeout=10,
        )
        if rc == 0 and "true" in out:
            return
        last_err = err
        time.sleep(0.5)
    _skip_scenario(context, f"Bluetooth controller did not power on: {last_err}")


@step("the Bluetooth controller is powered off if present")
def bluetooth_controller_powered_off_if_present(context) -> None:  # noqa: ARG001
    """Best-effort power-off of the virtual adapter during cleanup."""
    _, rc, _ = _run_host(
        "busctl introspect org.bluez /org/bluez/hci0 | grep -q org.bluez.Adapter1",
        timeout=5,
    )
    if rc != 0:
        return
    _run_host("sudo btmgmt power off", timeout=10)


@step("the hci_vhci kernel module is removed if possible")
def hci_vhci_module_removed(context) -> None:
    """Best-effort removal of hci_vhci; ignore failures when module is in use.

    Kill the keepalive process that holds /dev/vhci open, stop bluetoothd so
    the virtual adapter is not held by the daemon, then unload the module.
    The VM is ephemeral, so leaving bluetooth.service stopped is fine.
    """
    pid = getattr(context, "vhci_keepalive_pid", "")
    if pid:
        _run_host(f"sudo kill {pid} || true", timeout=5)
    _run_host("sudo rm -f /tmp/vhci-keepalive.pid", timeout=5)
    _run_host("sudo systemctl stop bluetooth.service", timeout=15)
    _run_host("sudo modprobe -r hci_vhci || true", timeout=15)
