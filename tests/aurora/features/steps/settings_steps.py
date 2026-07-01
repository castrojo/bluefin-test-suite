import time
from behave import given, when, then
from selenium import webdriver
from selenium.webdriver.common.by import By
from appium.options.common.base import AppiumOptions

@given('the KCM module "{module_name}" is running under kcmshell6')
def step_impl_kcm_module_running(context, module_name):
    """KDE Optimization: Launching single settings panels is faster than the full settings shell."""
    if not getattr(context, "is_kde", False):
        context.scenario.skip("This scenario requires a KDE/Plasma environment")
        return

    if not hasattr(context, "driver"):
        options = AppiumOptions()
        # Launching the individual panel directly bypasses global settings navigation
        options.set_capability("app", f"kcmshell6 {module_name}")

        context.driver = webdriver.Remote(
            command_executor='http://127.0.0.1:4723',
            options=options
        )
        context.driver.implicitly_wait(10)

@then('the "{window_name}" window is visible')
def step_impl_kce_window_visible(context, window_name):
    if not getattr(context, "is_kde", False):
        return
    context.window = context.driver.find_element(By.NAME, window_name)
    assert context.window is not None

@then('the "{item_name}" theme entry is present in the list')
def step_impl_theme_entry_present(context, item_name):
    if not getattr(context, "is_kde", False):
        return
    list_items = context.driver.find_elements(By.CLASS_NAME, "QListView")
    found = False
    for l_item in list_items:
        try:
            target = l_item.find_element(By.NAME, item_name)
            if target:
                context.target_item = target
                found = True
                break
        except Exception:
            continue
    assert found, f"Theme {item_name} not found"

@when('I click the list item "{item_name}"')
def step_impl_click_list_item(context, item_name):
    if not getattr(context, "is_kde", False):
        return
    assert context.target_item is not None
    context.target_item.click()
    time.sleep(0.5)

@then('the "{btn_name}" button is enabled')
def step_impl_button_is_enabled(context, btn_name):
    if not getattr(context, "is_kde", False):
        return
    btn = context.driver.find_element(By.NAME, btn_name)
    assert btn.is_enabled()

