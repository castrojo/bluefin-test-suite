"""Reusable screenshot step definitions for GNOME GUI test suites."""

from behave import step

from tests.shared.screenshot import take_app_screenshot, take_screenshot


@step('I take a screenshot labeled "{label}"')
def step_take_screenshot_labeled(context, label) -> None:
    """Capture the desktop right now, tagged with the given label."""
    path = take_screenshot(label)
    assert path is not None, f"Screenshot failed for label '{label}'"


@step('I launch and screenshot the "{app_id}" app')
def step_launch_and_screenshot(context, app_id) -> None:
    """Launch app_id, wait for it to render, screenshot, then close."""
    path = take_app_screenshot(app_id)
    assert path is not None, f"Screenshot failed for app '{app_id}'"
