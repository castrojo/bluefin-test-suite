"""
Aurora test environment — qecore TestSandbox for KDE/Plasma.
"""
import subprocess
import sys
import traceback

from qecore.common_steps import *  # noqa: F401,F403

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


SUITE_NAME = "aurora"


def _is_kde_environment() -> bool:
    from steps.app_support import _IN_CONTAINER, _ssh_run
    try:
        if _IN_CONTAINER:
            r = _ssh_run("pgrep -x kwin_wayland")
            return r.returncode == 0
        else:
            r = subprocess.run(["pgrep", "-x", "kwin_wayland"], capture_output=True)
            return r.returncode == 0
    except Exception:
        return False


def _setup_kde_environment(context) -> None:
    import urllib.request
    import os
    import sys
    import time

    print("KDE/Plasma environment detected — configuring KDE testing stack", flush=True)
    context.is_kde = True
    context.is_bluefin_image = True
    context.is_dakota_image = False

    # 1. Install required python packages for selenium/appium
    print("Installing selenium, Appium-Python-Client, flask, and lxml...", flush=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "selenium", "Appium-Python-Client", "flask", "lxml"],
            check=True,
            timeout=60,
        )
        print("Python packages installed successfully.", flush=True)
    except Exception as e:
        print(f"WARNING: failed to install selenium packages: {e}", flush=True)

    # 2. Download selenium-webdriver-at-spi files
    print("Downloading KDE selenium-webdriver-at-spi.py and app_roles.py...", flush=True)
    try:
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/KDE/selenium-webdriver-at-spi/master/selenium-webdriver-at-spi.py",
            "/tmp/selenium-webdriver-at-spi.py"
        )
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/KDE/selenium-webdriver-at-spi/master/app_roles.py",
            "/tmp/app_roles.py"
        )
        print("Download complete.", flush=True)
    except Exception as e:
        print(f"WARNING: failed to download KDE driver files: {e}", flush=True)

    # 3. Start the Flask webdriver server
    print("Starting KDE selenium-webdriver-at-spi.py server...", flush=True)
    env = os.environ.copy()
    env["PATH"] = f"/home/bluefin-test/.local/bin:{env.get('PATH', '')}"
    try:
        context.webdriver_process = subprocess.Popen(
            [sys.executable, "/tmp/selenium-webdriver-at-spi.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        print("KDE Flask webdriver server started.", flush=True)
    except Exception as e:
        print(f"ERROR: failed to start KDE Flask driver server: {e}", flush=True)
        context.failed_setup = str(e)


def before_all(context) -> None:
    if _is_kde_environment():
        _setup_kde_environment(context)
        return
    else:
        # If not KDE, we skip all scenarios
        context.failed_setup = "This suite requires a KDE/Plasma environment"


def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine

    context.command_stdout = ""
    context.last_command_output = ""

    if getattr(context, "is_kde", False):
        context.scenario = scenario
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        return

    if skip_quarantine(scenario):
        return
    configure_screenshot_context(context, SUITE_NAME, scenario.name)
    scenario.skip(reason="before_scenario setup failed (environment not ready)")


def after_scenario(context, scenario) -> None:
    if scenario.status.name in ('passed', 'failed'):
        configure_screenshot_context(context, SUITE_NAME, scenario.name)
        if getattr(context, 'is_kde', False):
            driver = getattr(context, 'driver', None)
            if driver:
                try:
                    driver.get_screenshot_as_file(f"/tmp/results/failed_{scenario.name}.png")
                    print(f"KDE Screenshot captured: results/failed_{scenario.name}.png", flush=True)
                except Exception as e:
                    print(f"WARNING: failed to capture KDE driver screenshot: {e}", flush=True)
        else:
            take_screenshot(scenario.status.name)


def after_step(context, step) -> None:
    if step.status.name in ("error", "failed") and step.exception is not None:
        print(
            f"\nSTEP_ERROR [{step.name!r}]: "
            f"{type(step.exception).__name__}: {step.exception}",
            flush=True,
        )
        traceback.print_exception(
            type(step.exception),
            step.exception,
            step.exception.__traceback__,
            file=sys.stderr,
        )


def after_all(context) -> None:
    """Take a fastfetch desktop screenshot as end-of-run evidence."""
    if getattr(context, 'is_kde', False):
        proc = getattr(context, 'webdriver_process', None)
        if proc:
            print("Stopping KDE Flask webdriver server...", flush=True)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        return

    configure_screenshot_context(context, SUITE_NAME, "end_of_run")
    take_fastfetch_screenshot()
