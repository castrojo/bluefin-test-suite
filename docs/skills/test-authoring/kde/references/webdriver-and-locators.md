---
name: webdriver-and-locators
description: "KDE WebDriver client wrapper, locator policy, exception taxonomy, and why Appium/chromedriver are not used. Load when editing tests/shared/kde_webdriver.py."
metadata:
  type: reference
  audience: agents
  maturity: draft
---

# KDE WebDriver Client and Locators

## Scope

This reference describes `tests/shared/kde_webdriver.py`, the W3C WebDriver wrapper for KDE's `selenium-webdriver-at-spi` bridge.

## WebDriver client

KDE's `selenium-webdriver-at-spi` is a **standalone W3C WebDriver server** (Flask on port 4723), not an Appium driver.

| Wrong | Right |
|---|---|
| `from appium import webdriver` | `from selenium import webdriver` |
| `desired_capabilities={...}` (removed Selenium 4.10) | `AtSpiOptions()` subclass of `BaseOptions` |
| `driver.implicitly_wait(10)` | `driver.implicitly_wait(0)` + explicit waits |
| `get_full_page_screenshot_as_file()` | `driver.save_screenshot()` |

Create a session:

```python
from tests.shared import kde_webdriver

driver = kde_webdriver.new_session("http://127.0.0.1:4723")
try:
    ...
finally:
    kde_webdriver.quit_session(driver)
```

Launch a single app (uses the server's ``app`` capability):

```python
driver = kde_webdriver.launch_app("org.kde.dolphin")
```

## Locator policy

Preference order: **accessibility id > name > class name**.

```python
from tests.shared import kde_webdriver

# String: tries accessibility id, then exact name, then class name.
elem = kde_webdriver.find(driver, "kickoff-launcher-button")

# Regex: matches AT-SPI names (useful when accessibleId is absent).
elem = kde_webdriver.find(driver, re.compile(r"Konsole"))

# Explicit tuple for a single strategy.
elem = kde_webdriver.find(driver, (kde_webdriver.NAME, "Search"))
```

| Strategy | Server semantics | When to use |
|---|---|---|
| `accessibility id` | `accessibleId.endswith(selector)` | Stable IDs like `kickoff-launcher-button`. |
| `name` | exact match on AT-SPI `name` | Localized but reliable widget labels. |
| `class name` | `[roleName \| name]` | Role-based searches. |
| `xpath` | **banned** except in `@quarantine` tests | Brittle, encourages structural dependency. |

Real-world caveat: many KDE widgets (Konsole terminal view, Dolphin list items, KCM rows) expose no stable `accessibleId`. Prefer `name` with a regex fallback, and always run under `LANG=C.UTF-8` for deterministic matching.

## Exception taxonomy and retry

AT-SPI nodes are invalidated whenever Qt/KDE widgets repaint, hide, or reparent, so stale-element churn is structural. Retry must be surgical.

| Exception | Policy | Why |
|---|---|---|
| `NoSuchElementException` | retryable | Transient tree state. |
| `StaleElementReferenceException` | retryable | AT-SPI node invalidated by repaint/reparent. |
| `TimeoutException` | step-fatal | Wait condition genuinely never satisfied. |
| `InvalidSessionIdException` | session-fatal | Server/session crashed; abort, never retry. |
| `InvalidArgumentException` / `UnknownMethodException` | bug | Fail loudly; do not mask. |

Helpers:

```python
# Polls every 0.2s, ignoring only retryable exceptions.
elem = kde_webdriver.wait_for(driver, lambda d: d.find_element(...))

# Retries only NoSuchElementException / StaleElementReferenceException.
kde_webdriver.retry_atspi_action(lambda: elem.click(), attempts=3)
```

`WebDriverWait` inside the helpers uses `poll_frequency=0.2` and `ignored_exceptions=(NoSuchElementException, StaleElementReferenceException)`.

## Why not Appium or chromedriver

- **Appium Python client** adds mobile-only methods (`install_app`, `lock`, `hide_keyboard`) that return 404/501 against `selenium-webdriver-at-spi`. It adds no value.
- **chromedriver** version-validates against the target Chromium. Steam's embedded CEF is often older, so chromedriver fails with `SessionNotCreatedException`. The Gamescope/Steam Big Picture plane uses raw CDP over WebSocket without chromedriver.

## Red flags

- Importing `appium` or `AppiumBy` in KDE helpers.
- Using `desired_capabilities` dicts.
- Mixing `implicitly_wait(N)` with explicit waits.
- Using `xpath` in non-quarantine KDE scenarios.
- Calling `get_full_page_screenshot_as_file()` against the AT-SPI server.
- Blanket `except WebDriverException: continue` loops.
