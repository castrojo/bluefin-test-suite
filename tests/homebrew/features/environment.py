"""
Homebrew test environment — qecore TestSandbox for the active Brew/bctl
CLI lane plus ChairLift's managed-cask desktop and configured-UI
integration.

Brew and bctl scenarios drive Ptyxis via AT-SPI terminal typing (see
brew_steps.py / bctl_steps.py); ChairLift scenarios drive its own GTK4/
Libadwaita window via AT-SPI and local subprocess assertions (see
chairlift_steps.py).

Lane contract (see tests/homebrew/README.md and the lab's
`run-systemd-container-tests` template): this suite runs against a
systemd-booted target with Homebrew provisioned, as a test user whose
systemd user manager is reachable (`brew-preinstall.service` is a *user*
unit). The session's own `XDG_RUNTIME_DIR` is used as-is — relocating it
here would move the a11y and session bus out from under qecore.

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

try:
    from tests.shared.a11y import accessible_application_names
except Exception:  # noqa: BLE001
    def accessible_application_names():
        return ["<AT-SPI diagnostics helper unavailable>"]


SUITE_NAME = "homebrew"

BREW_SETUP_UNIT = "brew-setup.service"
BREW_PREINSTALL_UNIT = "brew-preinstall.service"
# brew-setup.service provisions this; the cask, the state file, and every
# ChairLift assertion below are downstream of it existing.
BREW_BINARY = Path("/var/home/linuxbrew/.linuxbrew/bin/brew")
# A completed Type=oneshot + RemainAfterExit=true run. Kept in sync with
# chairlift_steps.PREINSTALL_STATE (asserted in tests/unit/test_chairlift_steps.py).
PREINSTALL_ACTIVE_STATE = {
    "ActiveState": "active",
    "SubState": "exited",
    "Result": "success",
}
LANE_DOC = "tests/homebrew/README.md"


class HomebrewLaneError(RuntimeError):
    """A homebrew-lane precondition is unmet; the run must fail, not skip."""


def _systemctl_user(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _detail(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout).strip()


def _require_user_manager() -> None:
    """Fail explicitly when the test user's systemd user manager is unreachable.

    XDG_RUNTIME_DIR is reported, never rewritten: the running session's value
    is what qecore's a11y and session bus connections already use.
    """
    probe = _systemctl_user("show", "--property=Version", "--value")
    if probe.returncode != 0:
        raise HomebrewLaneError(
            f"systemd user manager unreachable for uid {os.getuid()} "
            f"(XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR')!r}): "
            f"{_detail(probe)!r}. {BREW_PREINSTALL_UNIT} is a user unit, so the "
            f"lane must enable lingering for the test user and start its "
            f"systemd user manager before behave; see {LANE_DOC}."
        )


def _require_brew_binary() -> None:
    """Fail explicitly when Homebrew was never provisioned on the target."""
    if not (BREW_BINARY.is_file() and os.access(BREW_BINARY, os.X_OK)):
        raise HomebrewLaneError(
            f"Homebrew is not provisioned: {BREW_BINARY} is missing or not "
            f"executable. The lane must unmask and start {BREW_SETUP_UNIT} "
            f"before behave — {BREW_PREINSTALL_UNIT} installs the managed casks "
            f"with this binary and cannot run without it; see {LANE_DOC}."
        )


def _parse_properties(output: str) -> dict:
    """Parse `systemctl show` key=value output into a dict."""
    properties = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key.strip()] = value.strip()
    return properties


def _start_brew_preinstall() -> None:
    """Start the shipped user unit and assert it completed; failure is the regression."""
    result = _systemctl_user("start", BREW_PREINSTALL_UNIT)
    if result.returncode != 0:
        raise HomebrewLaneError(
            f"{BREW_PREINSTALL_UNIT} failed to start: {_detail(result)!r}. "
            f"Homebrew must be provisioned on the target before this suite "
            f"runs; see {LANE_DOC}."
        )

    shown = _systemctl_user(
        "show", BREW_PREINSTALL_UNIT,
        *(f"--property={name}" for name in PREINSTALL_ACTIVE_STATE),
    )
    if shown.returncode != 0:
        raise HomebrewLaneError(
            f"cannot read {BREW_PREINSTALL_UNIT} state after starting it: "
            f"{_detail(shown)!r}; see {LANE_DOC}."
        )
    properties = _parse_properties(shown.stdout)
    actual = {name: properties.get(name) for name in PREINSTALL_ACTIVE_STATE}
    if actual != PREINSTALL_ACTIVE_STATE:
        raise HomebrewLaneError(
            f"{BREW_PREINSTALL_UNIT} did not complete: expected "
            f"{PREINSTALL_ACTIVE_STATE}, got {actual}. A `start` that returns 0 "
            f"without a completed run means the managed casks were never "
            f"installed; see {LANE_DOC}."
        )


def before_all(context) -> None:
    # qecore sandbox.py calls context.html_formatter in after_scenario reporting
    # hooks; set it to None so AttributeError doesn't spam the log when
    # behave-html-formatter is not installed / not configured.
    context.html_formatter = None
    context.lane_ready = False

    _require_user_manager()
    # brew-setup.service provisions the Homebrew prefix; without it,
    # brew-preinstall.service has nothing to run and every ChairLift
    # assertion below is meaningless.
    _require_brew_binary()
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
    # Diagnostics only — printed alongside the real failure, never in place of
    # it. A UI scenario that fails because ChairLift never registered on the
    # a11y bus is otherwise indistinguishable from a genuine UI regression.
    if scenario.status.name == 'failed' and 'chairlift_ui' in scenario.tags:
        print(
            f"AT-SPI applications registered after failed {scenario.name!r}: "
            f"{accessible_application_names()}",
            flush=True,
        )
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
