"""
Homebrew test environment — qecore TestSandbox for the active Brew/bctl
CLI lane plus ChairLift's managed-cask desktop and configured-UI
integration.

Brew and bctl scenarios drive Ptyxis via AT-SPI terminal typing (see
brew_steps.py / bctl_steps.py); ChairLift scenarios drive its own GTK4/
Libadwaita window via AT-SPI and local subprocess assertions (see
chairlift_steps.py).

Lane contract (see tests/homebrew/README.md and the lab's
`run-systemd-container-tests` template): this suite runs as `bluefin-test`
(uid 1000) against a systemd-booted target with Homebrew provisioned, with
`XDG_RUNTIME_DIR=/run/user/1000` and a reachable `user@1000.service`
manager.

Preconditions here FAIL the run; they are never downgraded to a skip. A
missing Homebrew provisioning step, an unreachable user manager, or a
`brew-preinstall.service` that will not start is exactly the regression
this lane exists to catch, so `before_all` raises and behave aborts with a
nonzero exit instead of reporting skipped-green scenarios.
"""
import os
import subprocess
from pathlib import Path

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403

# Evidence-only helpers stay guarded: losing a screenshot or a timing record
# degrades the artifacts, it does not invalidate an assertion. Preconditions
# below are deliberately NOT guarded.
try:
    from tests.shared.timing import record_end, record_start
except Exception:  # noqa: BLE001
    def record_start(context):
        return None

    def record_end(context, scenario):
        return None

try:
    from tests.shared.screenshot import (
        configure_screenshot_context,
        take_fastfetch_screenshot,
        take_screenshot,
    )
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot helpers unavailable: {exc}", flush=True)

    def configure_screenshot_context(context, suite_name, scenario_name=None):
        return None

    def take_screenshot(label):
        return None

    def take_fastfetch_screenshot():
        return None


try:
    from tests.shared.screenshot_steps import *  # noqa: F401,F403 — registers screenshot steps
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot steps unavailable: {exc}", flush=True)


SUITE_NAME = "homebrew"

# Pinned lane contract: the suite user is bluefin-test (uid 1000) and its
# systemd user manager lives at /run/user/1000. The lab template starts
# user@1000.service and enables lingering; qecore, Ptyxis, and
# brew-preinstall.service all resolve through this runtime directory.
USER_RUNTIME_DIR = "/run/user/1000"
BREW_PREINSTALL_UNIT = "brew-preinstall.service"
LANE_DOC = "tests/homebrew/README.md"


class HomebrewLaneError(RuntimeError):
    """A homebrew-lane precondition is unmet; the run must fail, not skip."""


def _pin_user_runtime_dir() -> None:
    """Pin XDG_RUNTIME_DIR to the lane's uid-1000 user manager."""
    current = os.environ.get("XDG_RUNTIME_DIR")
    if current and current != USER_RUNTIME_DIR:
        raise HomebrewLaneError(
            f"homebrew lane requires XDG_RUNTIME_DIR={USER_RUNTIME_DIR} "
            f"(bluefin-test, uid 1000) but found {current!r}. "
            f"Run the suite through the lab's run-systemd-container-tests "
            f"template; see {LANE_DOC}."
        )
    os.environ["XDG_RUNTIME_DIR"] = USER_RUNTIME_DIR


def _require_user_manager() -> None:
    """Fail explicitly when the uid-1000 systemd user manager is unreachable."""
    probe = subprocess.run(
        ["systemctl", "--user", "show", "--property=Version", "--value"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip()
        raise HomebrewLaneError(
            f"systemd user manager unreachable via {USER_RUNTIME_DIR} "
            f"(uid {os.getuid()}): {detail!r}. The lane must run "
            f"`loginctl enable-linger bluefin-test` and "
            f"`systemctl start user@1000.service` before behave; see {LANE_DOC}."
        )


def _start_brew_preinstall() -> None:
    """Start the shipped user unit; a failure here is the regression."""
    result = subprocess.run(
        ["systemctl", "--user", "start", BREW_PREINSTALL_UNIT],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise HomebrewLaneError(
            f"{BREW_PREINSTALL_UNIT} failed to start: {detail!r}. Homebrew must "
            f"be provisioned on the target before this suite runs; see {LANE_DOC}."
        )


def before_all(context) -> None:
    # qecore sandbox.py calls context.html_formatter in after_scenario reporting
    # hooks; set it to None so AttributeError doesn't spam the log when
    # behave-html-formatter is not installed / not configured.
    context.html_formatter = None
    context.lane_ready = False

    _pin_user_runtime_dir()
    _require_user_manager()
    # brew-preinstall.service only runs at login; start it explicitly so the
    # managed cask (and its state file) exist before any scenario — including a
    # fresh boot where the login-triggered run hasn't fired yet or a retry
    # after a prior scenario changed the Brewfile hash.
    _start_brew_preinstall()

    context.sandbox = TestSandbox("chairlift", context=context)
    context.sandbox.attach_faf = False
    context.sandbox.production = False
    context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH

    context.ptyxis = context.sandbox.get_application(
        name="ptyxis",
        a11y_app_name="ptyxis",
        desktop_file_path="/usr/share/applications/org.gnome.Ptyxis.desktop",
    )
    context.ptyxis.exit_shortcut = "<Alt>F4"

    # AT-SPI exposes the application root under the binary name ("chairlift");
    # "ChairLift" is only the frame title asserted by the UI scenarios.
    context.chairlift = context.sandbox.get_application(
        name="chairlift",
        a11y_app_name="chairlift",
        desktop_file_path=str(
            Path.home() / ".local/share/applications/org.frostyard.ChairLift.desktop"
        ),
    )
    context.chairlift.exit_shortcut = "<Ctrl>Q"
    configure_screenshot_context(context, SUITE_NAME)
    context.lane_ready = True


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    context.scenario = scenario
    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    record_start(context)
    # Deliberately unguarded: a sandbox that cannot set up means the session
    # under test is broken, which must fail the run rather than skip it.
    context.sandbox.before_scenario(context, scenario)


def after_scenario(context, scenario) -> None:
    record_end(context, scenario)
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        take_screenshot(scenario.status.name)
    if hasattr(context, 'sandbox'):
        context.sandbox.after_scenario(context, scenario)


def after_all(context) -> None:
    """Take a fastfetch desktop screenshot as end-of-run evidence."""
    # behave still runs after_all when before_all aborted the run; skip the
    # evidence capture so the real precondition error stays the visible one.
    if not getattr(context, 'lane_ready', False):
        return
    configure_screenshot_context(context, SUITE_NAME, "end_of_run")
    take_fastfetch_screenshot()
