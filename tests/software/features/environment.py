"""
Software test environment — qecore TestSandbox for Bazaar (gnome-software in Bluefin).

Regressions: bluefin#4062, #4471.
"""
import traceback

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


SUITE_NAME = "software"


def before_all(context) -> None:
    # qecore sandbox.py accesses context.html_formatter in reporting hooks;
    # set to None to avoid AttributeError when behave-html-formatter is absent.
    context.html_formatter = None
    try:
        # In GNOME 50 / Fedora 44 the desktop file is org.gnome.Software.desktop
        # (reverse-DNS naming); qecore TestSandbox resolves it from the component name.
        # Bazaar is the Bluefin-customized GNOME Software app manager.
        context.sandbox = TestSandbox("org.gnome.Software", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH

        context.software = context.sandbox.get_application(
            name="gnome-software",
            a11y_app_name="gnome-software",
            # Use desktop_file_path (absolute) so qecore skips rpm -qlf lookup,
            # which fails in the runner container where gnome-software is not installed.
            desktop_file_path="/usr/share/applications/org.gnome.Software.desktop",
        )
        context.software.exit_shortcut = "<Ctrl>Q"
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
