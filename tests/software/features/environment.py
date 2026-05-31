"""
Software test environment — qecore TestSandbox for gnome-software (Bazaar).

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
    from tests.shared.screenshot import configure_screenshot_context, take_screenshot
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot helpers unavailable: {exc}", flush=True)

    def configure_screenshot_context(context, suite_name, scenario_name=None):
        return None

    def take_screenshot(label):
        return None


try:
    from tests.shared.screenshot_steps import *  # noqa: F401,F403 — registers screenshot steps
except Exception as exc:  # noqa: BLE001
    print(f"WARNING: screenshot steps unavailable: {exc}", flush=True)


SUITE_NAME = "software"


def before_all(context) -> None:
    try:
        # In GNOME 50 / Fedora 44 the desktop file is org.gnome.Software.desktop
        # (reverse-DNS naming); qecore TestSandbox resolves it from the component name.
        context.sandbox = TestSandbox("org.gnome.Software", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH

        context.software = context.sandbox.get_application(
            name="gnome-software",
            a11y_app_name="gnome-software",
            # qecore 4.16: rpm -qlf lookup fails for Flatpak-style apps; use full path
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
    context.scenario = scenario
    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    record_start(context)
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        tb = traceback.format_exc()
        try:
            context.embed("text/plain", tb, "Before Scenario Error")
        except Exception:
            print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
        raise


def after_scenario(context, scenario) -> None:
    record_end(context, scenario)
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        take_screenshot(scenario.status.name)
    context.sandbox.after_scenario(context, scenario)
