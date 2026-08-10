"""
Homebrew test environment — qecore TestSandbox for the active Brew/bctl
CLI lane plus ChairLift's managed-cask desktop and configured-UI
integration.

Brew and bctl scenarios drive Ptyxis via AT-SPI terminal typing (see
brew_steps.py / bctl_steps.py); ChairLift scenarios drive its own GTK4/
Libadwaita window via AT-SPI and local subprocess assertions (see
chairlift_steps.py). Both require a systemd-booted target with Homebrew
actually provisioned — unlike the developer suite's `@pending` Brew/bctl
scenarios, this suite assumes `brew-preinstall.service` is unmasked and
starts it explicitly before registering the ChairLift application so the
managed cask state exists before any scenario runs.
"""
import subprocess
import traceback
from pathlib import Path

from qecore.sandbox import TestSandbox
from qecore.common_steps import *  # noqa: F401,F403

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


def before_all(context) -> None:
    # qecore sandbox.py calls context.html_formatter in after_scenario reporting
    # hooks; set it to None so AttributeError doesn't spam the log when
    # behave-html-formatter is not installed / not configured.
    context.html_formatter = None
    try:
        # brew-preinstall.service only runs at login; start it explicitly so
        # the managed cask (and its state file) exist before any scenario —
        # including a fresh boot where the login-triggered run hasn't fired
        # yet or a retry after a prior scenario changed the Brewfile hash.
        subprocess.run(
            ["systemctl", "--user", "start", "brew-preinstall.service"],
            check=True,
        )
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

        context.chairlift = context.sandbox.get_application(
            name="chairlift",
            a11y_app_name="ChairLift",
            desktop_file_path=str(
                Path.home() / ".local/share/applications/org.frostyard.ChairLift.desktop"
            ),
        )
        context.chairlift.exit_shortcut = "<Ctrl>Q"
        configure_screenshot_context(context, SUITE_NAME)
    except Exception as error:
        print(f"Environment error: before_all: {error}")
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    if getattr(context, 'failed_setup', None):
        try:
            scenario.skip(reason=context.failed_setup)
        except TypeError:
            scenario.skip()
        print(f"Skipping {scenario.name}: failed_setup set", flush=True)
        return
    context.scenario = scenario
    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    record_start(context)
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        print(f"WARNING: before_scenario setup error — skipping scenario:\n{tb}", flush=True)
        scenario.skip(reason="before_scenario setup failed (environment not ready)")


def after_scenario(context, scenario) -> None:
    if getattr(context, 'failed_setup', None):
        return
    record_end(context, scenario)
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        take_screenshot(scenario.status.name)
    if hasattr(context, 'sandbox'):
        context.sandbox.after_scenario(context, scenario)


def after_all(context) -> None:
    """Take a fastfetch desktop screenshot as end-of-run evidence."""
    if getattr(context, 'failed_setup', None):
        return
    configure_screenshot_context(context, SUITE_NAME, "end_of_run")
    take_fastfetch_screenshot()
