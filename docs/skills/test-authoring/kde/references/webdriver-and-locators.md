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

### Server endpoint configuration

The WebDriver endpoint URL follows a three-level precedence:

1. **Explicit parameter** — pass `command_executor="http://..."` to `new_session()` or `launch_app()`.
2. **`KDE_WEBDRIVER_URL` env var** — set in the environment (useful in CI).
3. **Default** — `http://127.0.0.1:4723`.

```python
# Uses env var or default:
driver = kde_webdriver.new_session()

# Explicit override (ignores env var):
driver = kde_webdriver.new_session(command_executor="http://127.0.0.1:9999")
```

### Server launch

The server is started by the upstream **`selenium-webdriver-at-spi-run`** Ruby wrapper (installed as part of `selenium-webdriver-at-spi`).  **Ruby is a required runtime dependency.**

`scripts/install-kde-webdriver.sh` installs a systemd `--user` unit (`kde-webdriver.service`) that starts the server inside the graphical session.  The server needs access to the Wayland compositor and AT-SPI session bus, so a bare `systemd --system` unit will NOT work.

The upstream `FLASK_PORT` env var can override the default port 4723:

```bash
FLASK_PORT=5000 systemctl --user start kde-webdriver.service
```

### Security: loopback-only binding

The server is an **unauthenticated input-injection service**.  It MUST bind `127.0.0.1` only — **NEVER `0.0.0.0`**.  Do NOT "fix" connection-refused errors by changing the bind address.  The CI runner reaches the server via QEMU port forwarding (`hostfwd=tcp::4723-:4723`), not by exposing the service on all interfaces.

### CI port forwarding

The QEMU netdev line in `e2e.yml` forwards both SSH (2222→22) and WebDriver (4723→4723):

```
-netdev user,id=net0,hostfwd=tcp::2222-:22,hostfwd=tcp::4723-:4723
```

### CI passed > 0 backstop

After a KDE suite run, CI asserts that the number of passing scenarios is > 0.  An all-skipped run fails the job.  This prevents the suite from silently self-disabling while CI stays green.

Create a session:

```python
from tests.shared import kde_webdriver

driver = kde_webdriver.new_session()
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
- Binding the server to `0.0.0.0` (see loopback-only rule above).
