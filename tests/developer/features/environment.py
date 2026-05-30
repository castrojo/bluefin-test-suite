"""
Developer test environment — qecore TestSandbox for Ptyxis + micro + Podman Desktop.

AT-SPI app names confirmed in tests/developer/conftest.py:
  - Ptyxis: root.application("ptyxis")
  - Podman Desktop: root.application("Podman Desktop")  (Flatpak, check at runtime)

Pattern: modehnal/GNOMETerminalAutomation features/environment.py
"""
import sys
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
    from tests.shared.screenshot import take_screenshot
    from tests.shared.screenshot_steps import *  # noqa: F401,F403 — registers screenshot steps
except Exception:  # noqa: BLE001
    def take_screenshot(label):
        return None


SUITE_NAME = "developer"


def before_all(context) -> None:
    try:
        context.sandbox = TestSandbox("ptyxis", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False

        context.ptyxis = context.sandbox.get_application(
            name="ptyxis",
            a11y_app_name="ptyxis",
            desktop_file_name="org.gnome.Ptyxis.desktop",
        )
        context.ptyxis.exit_shortcut = "<Alt>F4"

        # micro is launched via terminal, not registered as a standalone app
        # Podman Desktop is a Flatpak — use get_flatpak for lifecycle management
        context.podman_desktop = context.sandbox.get_flatpak(
            flatpak_id="io.podman_desktop.PodmanDesktop",
        )
    except Exception as error:
        print(f"Environment error: before_all: {error}")
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    record_start(context)
    try:
        context.sandbox.before_scenario(context, scenario)
    except Exception:
        context.embed("text/plain", traceback.format_exc(), "Before Scenario Error")
        sys.exit(1)


def after_scenario(context, scenario) -> None:
    record_end(context, scenario)
    if scenario.status.name in ('passed', 'failed'):
        label = f"{SUITE_NAME}_{scenario.status.name}_{scenario.name}"
        take_screenshot(label)
    context.sandbox.after_scenario(context, scenario)
