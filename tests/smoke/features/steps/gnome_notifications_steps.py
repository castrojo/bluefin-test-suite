"""Custom step definitions for GNOME notification smoke tests."""
import re
import subprocess
from time import sleep

from behave import step
from qecore.common_steps import *  # noqa: F401,F403


def _run(cmd: str):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _parse_notification_id(output: str) -> int:
    match = re.search(r"\(uint32\s+(\d+),\)", output)
    assert match is not None, f"Could not parse notification ID from gdbus output: {output!r}"
    return int(match.group(1))


@step("A test desktop notification is sent via gdbus")
def send_test_desktop_notification(context) -> None:
    output, returncode, stderr = _run(
        "gdbus call --session "
        "--dest org.freedesktop.Notifications "
        "--object-path /org/freedesktop/Notifications "
        "--method org.freedesktop.Notifications.Notify "
        "'' 0 '' 'Test Notification' 'Testsuite notification body' '[]' '{}' 3000"
    )
    assert returncode == 0, f"gdbus notification send failed: {stderr or output}"
    context.notification_gdbus_output = output
    context.notification_id = _parse_notification_id(output)
    sleep(1)


@step("Notification request returns a positive notification ID")
def notification_request_returns_positive_id(context) -> None:
    notification_id = getattr(context, "notification_id", None)
    assert notification_id is not None, "Notification ID was not captured from the gdbus response"
    assert notification_id > 0, f"Expected notification ID > 0, got {notification_id}"


@step("Dismiss the notification via gdbus CloseNotification")
def dismiss_notification_via_gdbus(context) -> None:
    notification_id = getattr(context, "notification_id", None)
    assert notification_id is not None, (
        "No notification ID captured — run 'A test desktop notification is sent via gdbus' first"
    )
    _, returncode, stderr = _run(
        f"gdbus call --session "
        f"--dest org.freedesktop.Notifications "
        f"--object-path /org/freedesktop/Notifications "
        f"--method org.freedesktop.Notifications.CloseNotification "
        f"{notification_id}"
    )
    assert returncode == 0, f"CloseNotification failed for id={notification_id}: {stderr}"


@step("Notification banner is no longer showing via Shell.Eval")
def notification_banner_no_longer_showing(context) -> None:
    import re
    # Wait up to 4 s for the banner to be dismissed from the message tray.
    # The banner ref becomes null once Shell finishes the dismiss animation.
    banner_js = (
        "(Main.messageTray._banner !== null && "
        "Main.messageTray._banner !== undefined).toString()"
    )
    last_out = ""
    for _ in range(8):
        result = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", "org.gnome.Shell",
             "--object-path", "/org/gnome/Shell",
             "--method", "org.gnome.Shell.Eval",
             banner_js],
            capture_output=True, text=True, timeout=5,
        )
        last_out = result.stdout
        m = re.search(r",\s*'(true|false)'\s*\)", last_out, re.IGNORECASE)
        if m and m.group(1).lower() == "false":
            return
        sleep(0.5)
    raise AssertionError(
        f"Notification banner still showing after 4s — Shell.Eval returned: {last_out!r}"
    )
def no_gnome_shell_notification_journal_errors(context) -> None:
    output, returncode, stderr = _run("journalctl --no-pager -b -p err..emerg --lines=200")
    assert returncode == 0, f"journalctl failed: {stderr or output}"

    pattern = re.compile(r"gnome-shell.*notif", re.IGNORECASE)
    matches = [line for line in output.splitlines() if pattern.search(line)]
    assert not matches, f"Unexpected gnome-shell notification journal errors: {matches}"
