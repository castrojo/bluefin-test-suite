"""
Developer test environment — qecore TestSandbox for Ptyxis + micro + Podman Desktop.

AT-SPI app names confirmed in tests/developer/conftest.py:
  - Ptyxis: root.application("ptyxis")
  - Podman Desktop: root.application("Podman Desktop")  (Flatpak, check at runtime)

Pattern: modehnal/GNOMETerminalAutomation features/environment.py
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


SUITE_NAME = "developer"


def before_all(context) -> None:
    try:
        context.sandbox = TestSandbox("ptyxis", context=context)
        context.sandbox.attach_faf = False
        context.sandbox.production = False
        context.sandbox.set_keyring = False  # GNOME 50: GDM restart flushes PATH

        context.ptyxis = context.sandbox.get_application(
            name="ptyxis",
            a11y_app_name="ptyxis",
            desktop_file_name="org.gnome.Ptyxis.desktop",
        )
        context.ptyxis.exit_shortcut = "<Alt>F4"

        # micro is launched via terminal, not registered as a standalone app
        # Podman Desktop is only present on bluefin-dx; skip gracefully on base images.
        try:
            context.podman_desktop = context.sandbox.get_flatpak(
                flatpak_id="io.podman_desktop.PodmanDesktop",
            )
        except Exception as _pd_err:
            print(f"INFO: Podman Desktop not installed ({_pd_err}) — @podman_desktop scenarios will be skipped")
            context.podman_desktop = None
        configure_screenshot_context(context, SUITE_NAME)
    except Exception as error:
        print(f"Environment error: before_all: {error}")
        context.failed_setup = traceback.format_exc()


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    if skip_quarantine(scenario):
        return
    if hasattr(context, 'failed_setup'):
        context.scenario.skip(reason=context.failed_setup)
        return
    # Podman Desktop is only on bluefin-dx; skip those scenarios on the base image.
    if "podman_desktop" in scenario.tags and getattr(context, "podman_desktop", None) is None:
        scenario.skip("Podman Desktop Flatpak not installed on this image")
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
    if hasattr(context, 'sandbox'):
        context.sandbox.after_scenario(context, scenario)


def after_all(context) -> None:
    """Take a fastfetch desktop screenshot as end-of-run evidence."""
    configure_screenshot_context(context, SUITE_NAME, "end_of_run")
    take_fastfetch_screenshot()
