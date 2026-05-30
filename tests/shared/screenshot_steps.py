"""Reusable screenshot step definitions for GNOME GUI test suites.

Import in environment.py to register these steps:

    from tests.shared.screenshot_steps import *  # noqa: F401,F403

Available steps
---------------
Given/When/Then:
  I take a screenshot labeled "{label}"
      Capture the current desktop and save as screenshot_{label}.png.
      Use this to capture a specific moment inside a scenario, e.g.:

          When I click "File" menu
          And  I take a screenshot labeled "firefox-file-menu-open"

  I launch and screenshot the "{app_id}" app
      Launch app_id (Flatpak ID or command), wait for it to render,
      capture, then close.  Useful for quick smoke-checks, e.g.:

          Then I launch and screenshot the "org.gnome.Cheese" app
          Then I launch and screenshot the "gnome-calculator" app
"""

from behave import step

from tests.shared.screenshot import take_app_screenshot, take_screenshot


@step('I take a screenshot labeled "{label}"')
def step_take_screenshot_labeled(context, label) -> None:
    """Capture the desktop right now, tagged with the given label."""
    take_screenshot(label)


@step('I launch and screenshot the "{app_id}" app')
def step_launch_and_screenshot(context, app_id) -> None:
    """Launch app_id, wait for it to render, screenshot, then close.

    app_id may be:
    - a Flatpak application ID  (e.g. 'org.mozilla.firefox')
    - a bare command name        (e.g. 'firefox', 'gnome-calculator')
    - a .desktop file stem       (e.g. 'org.gnome.TextEditor')
    """
    path = take_app_screenshot(app_id)
    assert path is not None, f"Screenshot failed for app '{app_id}'"
