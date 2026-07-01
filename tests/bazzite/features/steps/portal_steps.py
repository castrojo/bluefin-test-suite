import time
from behave import given, when, then
from selenium import webdriver
from selenium.webdriver.common.by import By
from appium.options.common.base import AppiumOptions

@given("The Bazzite Portal application is running")
def step_impl_portal_application_running(context):
    """Launches the custom Bazzite Portal wizard inside KWin."""
    if not getattr(context, "is_kde", False):
        context.scenario.skip("This scenario requires a KDE/Plasma environment")
        return

    if not hasattr(context, "driver"):
        options = AppiumOptions()
        # Launch using the portal's desktop app ID
        options.set_capability("app", "com.ublue.bazzite-portal.desktop")

        context.driver = webdriver.Remote(
            command_executor='http://127.0.0.1:4723',
            options=options
        )
        context.driver.implicitly_wait(10)

@then('the "{window_name}" window is visible')
def step_impl_portal_window_visible(context, window_name):
    if not getattr(context, "is_kde", False):
        return
    context.window = context.driver.find_element(By.NAME, window_name)
    assert context.window is not None

@then('the update button "{btn_name}" is present')
def step_impl_update_button_present(context, btn_name):
    if not getattr(context, "is_kde", False):
        return
    btn = context.window.find_element(By.NAME, btn_name)
    assert btn is not None

@when('I click the button "{btn_name}" in "{window_name}"')
def step_impl_click_button_in_window(context, btn_name, window_name):
    if not getattr(context, "is_kde", False):
        return
    window = context.driver.find_element(By.NAME, window_name)
    btn = window.find_element(By.NAME, btn_name)
    btn.click()
    time.sleep(1) # Settle asynchronous UI transition

@then('a terminal execution window with title "{term_1}" or "{term_2}" is visible')
def step_impl_terminal_window_visible(context, term_1, term_2):
    """Wait for the backend ujust task window to be spawned."""
    if not getattr(context, "is_kde", False):
        return
    found = False
    for _ in range(20): # Try for 10 seconds (0.5s poll)
        try:
            context.term_window = context.driver.find_element(By.NAME, term_1)
            found = True
            break
        except Exception:
            try:
                context.term_window = context.driver.find_element(By.NAME, term_2)
                found = True
                break
            except Exception:
                time.sleep(0.5)
    assert found, "Spawning terminal did not appear"

@then("the update command is executing in the terminal")
def step_impl_update_executing_in_terminal(context):
    if not getattr(context, "is_kde", False):
        return
    term_node = context.term_window.find_element(By.CLASS_NAME, "Terminal")
    text = term_node.text or ""
    assert len(text.strip()) > 0, "Spawned terminal is blank or inactive"

