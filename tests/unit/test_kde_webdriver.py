"""Unit tests for tests/shared/kde_webdriver.py.

All tests are fully mocked: no live AT-SPI server, no network calls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from tests.shared import kde_webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    InvalidArgumentException,
    InvalidSessionIdException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    UnknownMethodException,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def driver():
    """A MagicMock standing in for a selenium WebDriver."""
    return MagicMock()


# ---------------------------------------------------------------------------
# AtSpiOptions and session creation
# ---------------------------------------------------------------------------


def test_atspi_options_has_w3c_capabilities():
    options = kde_webdriver.AtSpiOptions()
    caps = options.to_capabilities()

    assert caps["browserName"] == "at-spi"
    assert caps["platformName"] == "linux"


def test_atspi_options_sets_app_capability():
    options = kde_webdriver.AtSpiOptions(app="org.kde.dolphin")
    caps = options.to_capabilities()

    assert caps["app"] == "org.kde.dolphin"


def test_new_session_forces_implicit_wait_zero():
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver):
        driver = kde_webdriver.new_session()

    assert driver is mock_driver
    mock_driver.implicitly_wait.assert_called_once_with(0)


def test_new_session_bypasses_host_proxy_for_loopback_endpoint():
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.new_session()

    options = remote_mock.call_args.kwargs["options"]
    assert options._ignore_local_proxy is True


def test_new_session_with_app_uses_app_capability():
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.new_session(app="org.kde.konsole")

    options = remote_mock.call_args.kwargs["options"]
    assert options.to_capabilities()["app"] == "org.kde.konsole"


def test_launch_app_creates_session_with_app_capability():
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        driver = kde_webdriver.launch_app("org.kde.kate")

    assert driver is mock_driver
    options = remote_mock.call_args.kwargs["options"]
    assert options.to_capabilities()["app"] == "org.kde.kate"


# ---------------------------------------------------------------------------
# Executor URL precedence (explicit arg > KDE_WEBDRIVER_URL > default)
# ---------------------------------------------------------------------------


def test_new_session_uses_default_executor(monkeypatch):
    """No explicit arg, no env var → default http://127.0.0.1:4723."""
    monkeypatch.delenv("KDE_WEBDRIVER_URL", raising=False)
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.new_session()

    assert remote_mock.call_args.kwargs["command_executor"] == "http://127.0.0.1:4723"


def test_new_session_uses_env_var_executor(monkeypatch):
    """No explicit arg, env var set → env var wins."""
    monkeypatch.setenv("KDE_WEBDRIVER_URL", "http://10.0.0.5:9999")
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.new_session()

    assert remote_mock.call_args.kwargs["command_executor"] == "http://10.0.0.5:9999"


def test_new_session_explicit_arg_overrides_env_var(monkeypatch):
    """Explicit arg set + env var set → explicit arg wins."""
    monkeypatch.setenv("KDE_WEBDRIVER_URL", "http://10.0.0.5:9999")
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.new_session(command_executor="http://custom:1234")

    assert remote_mock.call_args.kwargs["command_executor"] == "http://custom:1234"


def test_launch_app_uses_env_var_executor(monkeypatch):
    """launch_app() respects KDE_WEBDRIVER_URL when no explicit arg is passed."""
    monkeypatch.setenv("KDE_WEBDRIVER_URL", "http://10.0.0.5:9999")
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.launch_app("org.kde.dolphin")

    assert remote_mock.call_args.kwargs["command_executor"] == "http://10.0.0.5:9999"


def test_launch_app_explicit_arg_overrides_env_var(monkeypatch):
    """launch_app() explicit arg > env var."""
    monkeypatch.setenv("KDE_WEBDRIVER_URL", "http://10.0.0.5:9999")
    mock_driver = MagicMock()

    with patch.object(kde_webdriver.webdriver, "Remote", return_value=mock_driver) as remote_mock:
        kde_webdriver.launch_app("org.kde.dolphin", command_executor="http://custom:5555")

    assert remote_mock.call_args.kwargs["command_executor"] == "http://custom:5555"


def test_e2e_forwards_loopback_webdriver_without_proxy():
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "e2e.yml"
    ).read_text()

    assert "hostfwd=tcp:127.0.0.1:4723-:4723" in workflow
    assert "-e KDE_WEBDRIVER_URL=http://127.0.0.1:4723" in workflow
    assert "-e NO_PROXY=127.0.0.1,localhost" in workflow
    assert "-e no_proxy=127.0.0.1,localhost" in workflow


def test_quit_session_calls_driver_quit():
    mock_driver = MagicMock()
    kde_webdriver.quit_session(mock_driver)
    mock_driver.quit.assert_called_once_with()


# ---------------------------------------------------------------------------
# find() locator preference
# ---------------------------------------------------------------------------


def test_find_string_uses_accessibility_id_first(driver):
    element = MagicMock()
    calls = []

    def fake_find(by, value):
        calls.append((by, value))
        if by == kde_webdriver.ACCESSIBILITY_ID and value == "kickoff":
            return element
        raise NoSuchElementException("nope")

    driver.find_element.side_effect = fake_find

    result = kde_webdriver.find(driver, "kickoff", timeout=0.1)

    assert result is element
    assert calls[0] == (kde_webdriver.ACCESSIBILITY_ID, "kickoff")
    # No fallback should occur when accessibility id succeeds.
    assert all(c[0] == kde_webdriver.ACCESSIBILITY_ID for c in calls)


def test_find_string_falls_back_to_name_then_class_name(driver):
    element = MagicMock()
    calls = []

    def fake_find(by, value):
        calls.append((by, value))
        if by == kde_webdriver.NAME and value == "Search":
            return element
        raise NoSuchElementException("nope")

    driver.find_element.side_effect = fake_find

    result = kde_webdriver.find(driver, "Search", timeout=0.1)

    assert result is element
    assert calls[0] == (kde_webdriver.ACCESSIBILITY_ID, "Search")
    assert calls[1] == (kde_webdriver.NAME, "Search")


def test_find_string_falls_back_to_class_name(driver):
    element = MagicMock()
    calls = []

    def fake_find(by, value):
        calls.append((by, value))
        if by == kde_webdriver.CLASS_NAME and value == "[button | OK]":
            return element
        raise NoSuchElementException("nope")

    driver.find_element.side_effect = fake_find

    result = kde_webdriver.find(driver, "[button | OK]", timeout=0.1)

    assert result is element
    assert calls[0] == (kde_webdriver.ACCESSIBILITY_ID, "[button | OK]")
    assert calls[1] == (kde_webdriver.NAME, "[button | OK]")
    assert calls[2] == (kde_webdriver.CLASS_NAME, "[button | OK]")


def test_find_explicit_tuple_skips_fallback(driver):
    element = MagicMock()
    driver.find_element.return_value = element

    result = kde_webdriver.find(driver, (kde_webdriver.NAME, "Konsole"), timeout=0.1)

    assert result is element
    driver.find_element.assert_called_once_with(kde_webdriver.NAME, "Konsole")


def test_find_regex_matches_name(driver):
    element = MagicMock()
    driver.page_source = (
        '<window name="Konsole" accessibility-id="">'
        '<push_button name="New Tab"/>'
        '</window>'
    )
    driver.find_elements.return_value = [element]

    result = kde_webdriver.find(driver, re.compile("New.*"), timeout=0.1)

    assert result is element
    driver.find_elements.assert_called_with(kde_webdriver.NAME, "New Tab")


# ---------------------------------------------------------------------------
# find() timeout diagnostics
# ---------------------------------------------------------------------------


def test_find_timeout_raises_with_nearby_elements(driver):
    driver.page_source = (
        '<window name="Dolphin">'
        '<push_button name="Back"/>'
        '<label name="Places"/>'
        '</window>'
    )
    driver.find_element.side_effect = NoSuchElementException("not found")

    with pytest.raises(TimeoutException, match="nearby elements:") as exc_info:
        kde_webdriver.find(driver, "Missing", timeout=0.1)

    assert "Back" in str(exc_info.value)
    assert "Places" in str(exc_info.value)


def test_find_timeout_mentions_locator(driver):
    driver.page_source = "<window/>"
    driver.find_element.side_effect = NoSuchElementException("not found")

    with pytest.raises(TimeoutException, match="'Gone'"):
        kde_webdriver.find(driver, "Gone", timeout=0.1)


# ---------------------------------------------------------------------------
# find_all()
# ---------------------------------------------------------------------------


def test_find_all_returns_list_from_first_matching_strategy(driver):
    elements = [MagicMock(), MagicMock()]
    driver.find_elements.side_effect = lambda by, value: (
        elements if by == kde_webdriver.NAME else []
    )

    result = kde_webdriver.find_all(driver, "Files", timeout=0.1)

    assert result == elements


def test_find_all_with_regex_returns_matched_elements(driver):
    elements = [MagicMock()]
    driver.page_source = '<window><label name="Notifications"/></window>'
    driver.find_elements.return_value = elements

    result = kde_webdriver.find_all(driver, re.compile("Notif.*"), timeout=0.1)

    assert result == elements


def test_find_all_timeout_includes_nearby_elements(driver):
    driver.page_source = "<window><label name='Clock'/></window>"
    driver.find_elements.return_value = []

    with pytest.raises(TimeoutException, match="nearby elements:") as exc_info:
        kde_webdriver.find_all(driver, "Nothing", timeout=0.1)

    assert "Clock" in str(exc_info.value)


# ---------------------------------------------------------------------------
# wait_for()
# ---------------------------------------------------------------------------


def test_wait_for_uses_wait_with_retryable_ignored_exceptions(driver):
    condition = MagicMock(return_value="done")

    with patch.object(kde_webdriver, "WebDriverWait") as wait_mock:
        wait_mock.return_value.until.return_value = "done"
        result = kde_webdriver.wait_for(driver, condition, timeout=5)

    assert result == "done"
    wait_mock.assert_called_once_with(
        driver,
        5,
        poll_frequency=0.2,
        ignored_exceptions=kde_webdriver._RETRYABLE,
    )
    wait_mock.return_value.until.assert_called_once_with(condition)


# ---------------------------------------------------------------------------
# retry_atspi_action() taxonomy
# ---------------------------------------------------------------------------


def _make_raising_fn(exc: Exception) -> Callable[[], str]:
    def fn():
        raise exc
    return fn


def test_retry_succeeds_on_second_attempt():
    calls = []

    def fn():
        calls.append(len(calls))
        if len(calls) == 1:
            raise NoSuchElementException("transient")
        return "ok"

    result = kde_webdriver.retry_atspi_action(fn, attempts=3)

    assert result == "ok"
    assert len(calls) == 2


def test_retry_succeeds_on_third_attempt():
    calls = []

    def fn():
        calls.append(len(calls))
        if len(calls) < 3:
            raise StaleElementReferenceException("repaint")
        return "ok"

    result = kde_webdriver.retry_atspi_action(fn, attempts=3)

    assert result == "ok"
    assert len(calls) == 3


def test_retry_exhaustion_raises_last_retryable_exception():
    fn = _make_raising_fn(NoSuchElementException("last"))

    with pytest.raises(NoSuchElementException, match="last"):
        kde_webdriver.retry_atspi_action(fn, attempts=2)


def test_retry_invalid_session_id_not_retried():
    fn = MagicMock(side_effect=InvalidSessionIdException("session dead"))

    with pytest.raises(InvalidSessionIdException):
        kde_webdriver.retry_atspi_action(fn, attempts=3)

    assert fn.call_count == 1


def test_retry_timeout_exception_not_retried():
    fn = MagicMock(side_effect=TimeoutException("too slow"))

    with pytest.raises(TimeoutException):
        kde_webdriver.retry_atspi_action(fn, attempts=3)

    assert fn.call_count == 1


@pytest.mark.parametrize(
    "exc_class",
    [InvalidArgumentException, UnknownMethodException],
)
def test_retry_bug_exceptions_not_retried(exc_class):
    fn = MagicMock(side_effect=exc_class("bad call"))

    with pytest.raises(exc_class):
        kde_webdriver.retry_atspi_action(fn, attempts=3)

    assert fn.call_count == 1


def test_retry_requires_positive_attempts():
    with pytest.raises(ValueError, match="attempts must be >= 1"):
        kde_webdriver.retry_atspi_action(lambda: None, attempts=0)


# ---------------------------------------------------------------------------
# save_screenshot()
# ---------------------------------------------------------------------------


def test_save_screenshot_uses_w3c_endpoint(driver):
    driver.save_screenshot.return_value = True

    result = kde_webdriver.save_screenshot(driver, "/results/kde.png")

    assert result is True
    driver.save_screenshot.assert_called_once_with("/results/kde.png")


def test_save_screenshot_propagates_failure(driver):
    driver.save_screenshot.return_value = False

    assert kde_webdriver.save_screenshot(driver, "/missing/x.png") is False


class TestReviewFixes:
    """Regression tests for issues found in code review of PR #643."""

    def test_regex_lookup_reraises_session_fatal(self):
        """A dead session must surface immediately, not decay into a timeout."""
        driver = mock.Mock()
        driver.page_source = '<root><node name="Dolphin"/></root>'
        driver.find_elements.side_effect = InvalidSessionIdException("session gone")
        with pytest.raises(InvalidSessionIdException):
            kde_webdriver._find_by_regex(driver, re.compile("Dolphin"))

    def test_regex_lookup_reraises_protocol_bug(self):
        driver = mock.Mock()
        driver.page_source = '<root><node name="Dolphin"/></root>'
        driver.find_elements.side_effect = UnknownMethodException("not implemented")
        with pytest.raises(UnknownMethodException):
            kde_webdriver._find_by_regex(driver, re.compile("Dolphin"))

    def test_regex_lookup_skips_stale_nodes(self):
        """Stale/missing nodes are normal AT-SPI churn and must not abort the scan."""
        driver = mock.Mock()
        driver.page_source = '<root><node name="A"/><node name="B"/></root>'
        sentinel = mock.Mock()
        driver.find_elements.side_effect = [
            StaleElementReferenceException("gone"),
            [sentinel],
        ]
        assert kde_webdriver._find_by_regex(driver, re.compile("A|B")) == [sentinel]

    def test_xpath_locator_rejected_by_default(self, monkeypatch):
        monkeypatch.delenv("KDE_ALLOW_XPATH", raising=False)
        with pytest.raises(ValueError, match="xpath locators are banned"):
            kde_webdriver._build_condition((By.XPATH, "//node"))

    def test_xpath_locator_allowed_under_quarantine_override(self, monkeypatch):
        monkeypatch.setenv("KDE_ALLOW_XPATH", "1")
        condition, description = kde_webdriver._build_condition((By.XPATH, "//node"))
        assert "//node" in description
