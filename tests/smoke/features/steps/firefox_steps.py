from time import sleep

from behave import step
try:
    from dogtail import tree
except Exception:  # noqa: BLE001
    tree = None  # type: ignore[assignment]
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass
from app_support import launch_background, launch_url, unlock_screen


def _skip_if_no_atspi(context) -> bool:
    if tree is None:
        try:
            context.scenario.skip("AT-SPI unavailable: dogtail not imported in this environment")
        except Exception:  # noqa: BLE001
            pass
        return True
    return False


FIREFOX_APP_NAMES = ("firefox", "Firefox", "Mozilla Firefox")
FIREFOX_LAUNCH_TARGETS = (
    ("command", "firefox"),
    ("desktop", "firefox.desktop"),
    ("desktop", "org.mozilla.firefox.desktop"),
    ("flatpak", "org.mozilla.firefox"),
)


def _firefox_app(context):
    instance = getattr(getattr(context, "firefox", None), "instance", None)
    if instance is not None:
        return instance
    last_error = None
    for name in FIREFOX_APP_NAMES:
        try:
            return tree.root.application(name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise AssertionError(f"Firefox application was not found via AT-SPI: {last_error}")


@step("Launch Firefox via command")
def launch_firefox_via_command(context) -> None:
    if _skip_if_no_atspi(context):
        return
    context.firefox_launch_target = launch_background(FIREFOX_LAUNCH_TARGETS)


def _firefox_window(context):
    frames = _firefox_app(context).findChildren(lambda n: n.roleName in {"frame", "filler"} and n.showing)
    assert frames, "Firefox main window not found"
    return frames[0]


def _address_bar(context):
    bars = _firefox_window(context).findChildren(lambda n: n.roleName == "entry" and n.showing)
    matches = [n for n in bars if "address" in (n.name or "").lower()]
    assert matches or bars, "Firefox address bar not found"
    return (matches or bars)[0]


def _tab_count(context):
    lists = _firefox_window(context).findChildren(lambda n: n.roleName == "page tab list" and n.showing)
    assert lists, "Firefox tab list not found"
    return len(lists[0].findChildren(lambda n: n.roleName == "page tab"))


@step("Firefox main window is accessible")
def firefox_main_window_is_accessible(context) -> None:
    for _ in range(30):
        try:
            context.firefox_window = _firefox_window(context)
            return
        except Exception:  # noqa: BLE001
            sleep(0.5)
    raise AssertionError("Firefox main window not accessible after 15 seconds")


@step("Firefox is no longer running")
def firefox_is_no_longer_running(context) -> None:
    for _ in range(20):
        for name in FIREFOX_APP_NAMES:
            try:
                app = tree.root.application(name)
                frames = app.findChildren(lambda n: n.roleName in {"frame", "filler"} and n.showing)
                if frames:
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            return
        sleep(0.5)
    raise AssertionError("Firefox is still visible in the AT-SPI tree")


@step("Address bar is present in Firefox")
def address_bar_is_present(context) -> None:
    context.firefox_address_bar = _address_bar(context)
    context.firefox_address_bar.click()


@step('Navigate Firefox to "{url}"')
def navigate_firefox_to(context, url) -> None:
    _address_bar(context).click()
    context.execute_steps(f'''* Key combo: "<Ctrl><A>" with uinput
* Type text: "{url}" with uinput
* Press key: "Return" with uinput''')
    sleep(0.3)
    assert url in (_address_bar(context).text or ""), f"Firefox did not navigate to {url!r}"


def show_firefox_url(context, url: str) -> None:
    """Launch Firefox directly at ``url`` for an end-of-run screenshot."""
    unlock_screen()
    context.firefox_launch_target = launch_url(FIREFOX_LAUNCH_TARGETS, url)


@step('Firefox has "{number}" tabs')
def firefox_has_tabs(context, number) -> None:
    count = _tab_count(context)
    assert count == int(number), f"Expected {number} tabs, found {count}"


@step("Firefox tab count increases after Ctrl+T")
def firefox_tab_count_increases(context) -> None:
    context.firefox_tab_count = _tab_count(context)
    context.execute_steps('* Key combo: "<Ctrl><T>" with uinput')
    for _ in range(10):
        if _tab_count(context) > context.firefox_tab_count:
            return
        sleep(0.5)
    raise AssertionError("Firefox tab count did not increase after Ctrl+T")


@step("Firefox tab count decreases after Ctrl+W")
def firefox_tab_count_decreases(context) -> None:
    before = _tab_count(context)
    context.execute_steps('* Key combo: "<Ctrl><W>" with uinput')
    for _ in range(10):
        if _tab_count(context) < before:
            return
        sleep(0.5)
    raise AssertionError("Firefox tab count did not decrease after Ctrl+W")
