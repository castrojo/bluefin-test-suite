import sys
import subprocess
from behave import given, then
from selenium import webdriver
from selenium.webdriver.common.by import By

@given("Steam Gamepad UI is running in gamescope")
def step_impl_steam_gamepad_running(context):
    # Skip if we are not running on a KDE/Bazzite image that supports gamescope remote debugging
    if not getattr(context, "is_kde", False):
        context.scenario.skip("This scenario requires a KDE/Plasma/Gamescope environment")
        return

    # Install selenium if not already done
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "selenium"], check=True)
    except Exception:
        pass

    options = webdriver.ChromeOptions()
    # Connect directly to Steam's Chromium backend via CDP
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        context.steam_driver = webdriver.Chrome(options=options)
        context.steam_driver.implicitly_wait(10)
    except Exception as e:
        context.scenario.skip(f"Could not connect to Steam CDP debugger: {e}")

@then("the Quick Access menu can be opened")
def step_impl_quick_access_opened(context):
    if not hasattr(context, "steam_driver"):
        return
    # Click Steam's React component button using standard web locators
    quick_access = context.steam_driver.find_element(By.CLASS_NAME, "quickaccessmenu_QuickAccessButton")
    quick_access.click()

    # Assert Decky Loader or settings menu mounted in the DOM
    decky_header = context.steam_driver.find_element(By.XPATH, "//*[contains(text(), 'Decky')]")
    assert decky_header is not None

