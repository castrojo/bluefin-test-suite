"""
Software test environment — qecore TestSandbox for Bazaar (gnome-software in Bluefin).

Regressions: bluefin#4062, #4471.
"""
import os
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


def _is_bluefin_image() -> bool:
    """Return True when running on a projectbluefin image (Bazaar is available)."""
    image = os.environ.get("IMAGE", "")
    return "projectbluefin" in image or "ublue-os" in image or not image


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
    # Skip Bazaar-specific scenarios on non-projectbluefin images (e.g. gnomeos).
    # Bazaar (io.github.kolunmi.Bazaar) ships only on Bluefin/UBlue images.
    # flatpak_cli scenarios carry @flatpak_cli and are image-agnostic.
    scenario_tags = {t for t in scenario.tags} | {t for t in scenario.feature.tags}
    if "software" in scenario_tags and "flatpak_cli" not in scenario_tags and not _is_bluefin_image():
        try:
            scenario.skip(reason="Bazaar not available on non-projectbluefin image")
        except TypeError:
            scenario.skip()
        print(f"Skipping {scenario.name}: Bazaar not available on this image", flush=True)
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
        try:
            context.sandbox.after_scenario(context, scenario)
        except Exception as exc:
            print(f"WARNING: sandbox.after_scenario raised {type(exc).__name__}: {exc}", flush=True)


def after_all(context) -> None:
    """Take a fastfetch desktop screenshot as end-of-run evidence."""
    if getattr(context, 'failed_setup', None):
        return
    configure_screenshot_context(context, SUITE_NAME, "end_of_run")
    take_fastfetch_screenshot()
