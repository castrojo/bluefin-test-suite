"""W3C WebDriver client wrapper for KDE's selenium-webdriver-at-spi bridge.

KDE's server is a standalone Flask W3C WebDriver implementation on port 4723.
It is *not* an Appium driver, so the wrapper uses plain Selenium with a
``BaseOptions`` subclass and avoids mobile-only Appium APIs.

See ``docs/skills/test-authoring/kde/SKILL.md`` for locator policy and
exception taxonomy.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Callable, Pattern, TypeVar

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import BaseOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    InvalidArgumentException,
    InvalidSessionIdException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    UnknownMethodException,
    WebDriverException,
)

# The KDE AT-SPI server accepts the standard W3C "accessibility id" strategy,
# but Selenium's ``By`` enum does not expose it (it is Appium-specific).
ACCESSIBILITY_ID = "accessibility id"
NAME = By.NAME
CLASS_NAME = By.CLASS_NAME

_RETRYABLE = (NoSuchElementException, StaleElementReferenceException)
_STEP_FATAL = (TimeoutException,)
_SESSION_FATAL = (InvalidSessionIdException,)
_BUG = (InvalidArgumentException, UnknownMethodException)

# Default endpoint for the KDE AT-SPI WebDriver server.
# Override with ``KDE_WEBDRIVER_URL`` env var (e.g. for non-standard port).
_DEFAULT_EXECUTOR = "http://127.0.0.1:4723"

T = TypeVar("T")
Locator = str | Pattern[str] | tuple[str, str]


def _resolve_executor(explicit: str | None) -> str:
    """Return the WebDriver endpoint URL.

    Precedence: explicit parameter > ``KDE_WEBDRIVER_URL`` env var > default.
    """
    if explicit is not None:
        return explicit
    return os.environ.get("KDE_WEBDRIVER_URL", _DEFAULT_EXECUTOR)


class AtSpiOptions(BaseOptions):
    """Capability bundle for ``selenium-webdriver-at-spi``.

    Do not use ``desired_capabilities`` (removed in Selenium 4.10).
    """

    def __init__(self, app: str | None = None) -> None:
        super().__init__()
        if app is not None:
            self.set_capability("app", app)

    @property
    def default_capabilities(self) -> dict:
        return {
            "browserName": "at-spi",
            "platformName": "linux",
        }

    def to_capabilities(self) -> dict:
        return self._caps


def new_session(
    command_executor: str | None = None,
    options: BaseOptions | None = None,
    app: str | None = None,
) -> WebDriver:
    """Create a Remote WebDriver session against the KDE AT-SPI server.

    ``command_executor`` precedence: explicit arg > ``KDE_WEBDRIVER_URL``
    env var > ``http://127.0.0.1:4723``.

    Implicit waits are forced to 0 so explicit waits remain bounded.
    """
    url = _resolve_executor(command_executor)

    if options is None:
        options = AtSpiOptions(app=app)
    elif app is not None:
        options.set_capability("app", app)

    driver = webdriver.Remote(command_executor=url, options=options)
    driver.implicitly_wait(0)
    return driver


def quit_session(driver: WebDriver) -> None:
    """Tear down a WebDriver session."""
    driver.quit()


def launch_app(app_id: str, command_executor: str | None = None) -> WebDriver:
    """Start a session scoped to a single application using the ``app`` capability.

    ``command_executor`` precedence: explicit arg > ``KDE_WEBDRIVER_URL``
    env var > ``http://127.0.0.1:4723``.
    """
    return new_session(command_executor=command_executor, app=app_id)


def _candidate_locators(selector: str) -> list[tuple[str, str]]:
    """Return locator strategies in preferred order."""
    return [
        (ACCESSIBILITY_ID, selector),
        (NAME, selector),
        (CLASS_NAME, selector),
    ]


def _find_by_regex(driver: WebDriver, pattern: Pattern[str]) -> list[WebElement]:
    """Find elements whose AT-SPI ``name`` matches ``pattern``.

    The server's ``name`` strategy is exact-match only, so we scan the XML
    accessibility tree for names matching the regex and then resolve those
    names back through the W3C ``name`` strategy.
    """
    source = driver.page_source
    if not source:
        return []

    try:
        root = ET.fromstring(source.encode("utf-8"))
    except ET.ParseError:
        return []

    matched_names: list[str] = []
    seen: set[str] = set()
    for elem in root.iter():
        name = elem.get("name", "") or ""
        if pattern.search(name) and name not in seen:
            seen.add(name)
            matched_names.append(name)

    results: list[WebElement] = []
    for name in matched_names:
        try:
            results.extend(driver.find_elements(NAME, name))
        except _RETRYABLE:
            # The node vanished between the tree snapshot and resolution — normal
            # AT-SPI churn. Skip this name and keep going.
            continue
        except (*_SESSION_FATAL, *_BUG):
            # Session death and protocol/argument errors must surface immediately.
            # Swallowing them here would degrade a dead session into an eventual
            # TimeoutException and hide the real cause.
            raise
    return results


def _xpath_allowed() -> bool:
    """Whether xpath locators are permitted (quarantine-only escape hatch)."""
    return os.environ.get("KDE_ALLOW_XPATH", "").lower() in ("1", "true", "yes")


def _build_condition(
    locator: Locator,
) -> tuple[Callable[[WebDriver], WebElement], str]:
    """Return a wait condition and a human-readable description for ``locator``."""
    if isinstance(locator, tuple):
        by, value = locator
        if by == By.XPATH and not _xpath_allowed():
            raise ValueError(
                "xpath locators are banned outside quarantined tests: AT-SPI trees "
                "reshape constantly, so xpath is the KDE equivalent of a brittle "
                "openQA needle. Prefer accessibility id, then name, then class "
                "name. Set KDE_ALLOW_XPATH=1 only inside a quarantined scenario."
            )
        description = f"({by}={value!r})"

        def condition(driver: WebDriver) -> WebElement:
            return driver.find_element(by, value)

        return condition, description

    if isinstance(locator, Pattern):
        description = f"(name matches {locator.pattern!r})"

        def condition(driver: WebDriver) -> WebElement:
            matches = _find_by_regex(driver, locator)
            if not matches:
                raise NoSuchElementException(
                    f"no element with name matching {locator.pattern!r}"
                )
            return matches[0]

        return condition, description

    # Plain string: try accessibility id, then exact name, then class name.
    selector = locator
    description = f"({selector!r})"
    candidates = _candidate_locators(selector)

    def condition(driver: WebDriver) -> WebElement:
        last_exc: WebDriverException | None = None
        for by, value in candidates:
            try:
                return driver.find_element(by, value)
            except _RETRYABLE as exc:
                last_exc = exc
        raise NoSuchElementException(
            f"no element found for {selector!r} by accessibility id, name, or class name"
        ) from last_exc

    return condition, description


def _build_all_condition(
    locator: Locator,
) -> tuple[Callable[[WebDriver], list[WebElement]], str]:
    """Return a wait condition that returns a list of elements."""
    if isinstance(locator, tuple):
        by, value = locator
        if by == By.XPATH and not _xpath_allowed():
            raise ValueError(
                "xpath locators are banned outside quarantined tests: AT-SPI trees "
                "reshape constantly, so xpath is the KDE equivalent of a brittle "
                "openQA needle. Prefer accessibility id, then name, then class "
                "name. Set KDE_ALLOW_XPATH=1 only inside a quarantined scenario."
            )
        description = f"({by}={value!r})"

        def condition(driver: WebDriver) -> list[WebElement]:
            return driver.find_elements(by, value)

        return condition, description

    if isinstance(locator, Pattern):
        description = f"(name matches {locator.pattern!r})"

        def condition(driver: WebDriver) -> list[WebElement]:
            matches = _find_by_regex(driver, locator)
            if not matches:
                raise NoSuchElementException(
                    f"no elements with name matching {locator.pattern!r}"
                )
            return matches

        return condition, description

    selector = locator
    description = f"({selector!r})"
    candidates = _candidate_locators(selector)

    def condition(driver: WebDriver) -> list[WebElement]:
        for by, value in candidates:
            matches = driver.find_elements(by, value)
            if matches:
                return matches
        raise NoSuchElementException(
            f"no elements found for {selector!r} by accessibility id, name, or class name"
        )

    return condition, description


def _nearby_text(driver: WebDriver, max_items: int = 8) -> str:
    """Return a short description of nearby named AT-SPI nodes for diagnostics."""
    try:
        source = driver.page_source
        if not source:
            return "no accessibility tree available"
        root = ET.fromstring(source.encode("utf-8"))
    except Exception as exc:
        return f"could not read accessibility tree: {exc}"

    items: list[str] = []
    for elem in root.iter():
        if len(items) >= max_items:
            break
        name = elem.get("name", "")
        role = elem.tag
        if name:
            items.append(f"{role} {name!r}")

    if not items:
        return "no named elements found in accessibility tree"
    return "nearby elements: " + ", ".join(items)


def _make_wait(driver: WebDriver, timeout: float) -> WebDriverWait:
    """Build a WebDriverWait with the standard AT-SPI retry set."""
    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=0.2,
        ignored_exceptions=_RETRYABLE,
    )


def find(driver: WebDriver, locator: Locator, timeout: float = 15) -> WebElement:
    """Wait for and return a single element.

    ``locator`` may be:
      - a string: try accessibility id, then exact name, then class name;
      - a compiled regex: match AT-SPI names;
      - a tuple ``(strategy, value)`` for an explicit W3C locator strategy.
    """
    condition, description = _build_condition(locator)
    wait = _make_wait(driver, timeout)
    try:
        return wait.until(condition)
    except TimeoutException as exc:
        nearby = _nearby_text(driver)
        raise TimeoutException(
            f"Timed out after {timeout}s waiting for element {description}. {nearby}"
        ) from exc


def find_all(
    driver: WebDriver, locator: Locator, timeout: float = 15
) -> list[WebElement]:
    """Wait for and return all elements matching ``locator``."""
    condition, description = _build_all_condition(locator)
    wait = _make_wait(driver, timeout)
    try:
        return wait.until(condition)
    except TimeoutException as exc:
        nearby = _nearby_text(driver)
        raise TimeoutException(
            f"Timed out after {timeout}s waiting for elements {description}. {nearby}"
        ) from exc


def wait_for(driver: WebDriver, condition: Callable, timeout: float = 15):
    """Poll ``condition(driver)`` until it returns a truthy value.

    ``NoSuchElementException`` and ``StaleElementReferenceException`` are
    ignored during polling; everything else fails immediately.
    """
    wait = _make_wait(driver, timeout)
    return wait.until(condition)


def retry_atspi_action(fn: Callable[[], T], attempts: int = 3) -> T:
    """Run ``fn`` with surgical retry for structural AT-SPI churn.

    Retryable: ``NoSuchElementException``, ``StaleElementReferenceException``.
    Step-fatal: ``TimeoutException``.
    Session-fatal: ``InvalidSessionIdException`` (never retry).
    Bug: ``InvalidArgumentException``, ``UnknownMethodException`` (fail loudly).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    last_exc: WebDriverException | None = None
    for _attempt in range(1, attempts + 1):
        try:
            return fn()
        except _RETRYABLE as exc:
            last_exc = exc
            continue
        except _STEP_FATAL:
            raise
        except _SESSION_FATAL:
            raise
        except _BUG:
            raise
        except WebDriverException as exc:
            # Any other WebDriver error is unexpected: fail loudly rather than
            # masking it with a blanket retry.
            raise exc

    if last_exc is None:
        raise RuntimeError("retry_atspi_action exhausted attempts with no exception")
    raise last_exc


def save_screenshot(driver: WebDriver, path: str) -> bool:
    """Save a W3C screenshot to ``path``.

    Uses ``driver.save_screenshot()``. Do not use Chromium-only
    ``get_full_page_screenshot_as_file()`` against the AT-SPI server.
    """
    return driver.save_screenshot(path)
