---
name: kde
description: "How to write KDE/Plasma e2e tests with selenium-webdriver-at-spi and raw CDP for Steam Gamescope. Use when authoring KDE tests, setting up the KDE runner image, or deciding where inputsynth must live."
metadata:
  type: pattern
  audience: agents
  maturity: draft
---

# KDE and Steam Gamescope Testing Reference

## When to Use

- Writing or debugging KDE/Plasma GUI tests for Aurora, Kinoite, Bazzite-Deck, or KDE Linux.
- Connecting to the standalone W3C WebDriver server shipped by `selenium-webdriver-at-spi`.
- Automating Steam's CEF-based Big Picture UI inside nested Gamescope via raw Chrome DevTools Protocol.
- Deciding what belongs in the `testsuite-kde-runner` image versus what must be installed on the DUT.

## When NOT to Use

- GNOME Shell / AT-SPI / dogtail tests → `../gnome/SKILL.md`
- Generic behave step hygiene → `../behave/SKILL.md`
- CI workflow or runner container plumbing → `../../ci-ops/e2e-workflow/SKILL.md`
- Lab/infra gotchas (GDM, oomd, Argo) → `../../ci-ops/ops/SKILL.md`

## Core Process

### 1. Runner image versus device-under-test split

The `ghcr.io/projectbluefin/testsuite-kde-runner:kde-runner` image carries **host-side orchestration dependencies only**:

| Layer | Ships in runner image | Ships on DUT |
|---|---|---|
| BDD runner | `behave` | — |
| WebDriver client | `selenium` | — |
| Raw CDP / WebSocket | `websocket-client` | — |
| Parsing helpers | `lxml`, `PyYAML` | — |
| AT-SPI input synthesizer | **NOT here** | `selenium-webdriver-at-spi-inputsynth` |
| WebDriver server | **NOT here** | `selenium-webdriver-at-spi` |

`selenium-webdriver-at-spi-inputsynth` is a Qt6 Wayland client that links `PlasmaWaylandProtocols`' `fake-input.xml`. Plasma protocol versions and the Qt/KWin ABI differ across Fedora (Aurora/Kinoite/Bazzite), Ubuntu-based KDE Neon, and Arch-based KDE Linux. Building it once on Fedora and copying it into every DUT is not portable — it will silently fail or segfault. Upstream KDE runs it inside the SUT for exactly this reason, so we do too.

### 2. Required Plasma session environment

Apply these as a systemd drop-in or environment wrapper before the session starts:

```bash
KWIN_WAYLAND_NO_PERMISSION_CHECKS=1
KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
QT_QPA_PLATFORM=wayland
LIBGL_ALWAYS_SOFTWARE=1
KWIN_NO_ANIMATIONS=1
```

`KWIN_WAYLAND_NO_PERMISSION_CHECKS=1` is the most commonly forgotten; without it KWin silently ignores injected keyboard/mouse events.

### 3. W3C WebDriver client for AT-SPI

`selenium-webdriver-at-spi` is a standalone W3C WebDriver server, **not** an Appium driver. Do not use `Appium-Python-Client`; use plain Selenium with a custom options class:

```python
from selenium import webdriver
from selenium.webdriver.common.options import BaseOptions

class AtSpiOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        self.set_capability("platformName", "linux")
        self.set_capability("browserName", "at-spi")

driver = webdriver.Remote(
    command_executor="http://127.0.0.1:4723",
    options=AtSpiOptions(),
)
```

Hard rules:

- Use options objects, not the removed `desired_capabilities` dict (deleted in Selenium 4.10).
- Set `driver.implicitly_wait(0)` globally. Mixing implicit and explicit waits multiplies timeout durations.
- Prefer `accessibility id` > `name` > `class name`. Avoid `xpath` outside quarantine.
- `driver.save_screenshot()` uses the mandatory W3C endpoint. Do not use `get_full_page_screenshot_as_file()`, which is Chromium-only.

### 4. Gamescope / Steam CEF over raw CDP

Steam Big Picture is a CEF browser inside nested Gamescope, which has no AT-SPI bus. Drive it over raw Chrome DevTools Protocol on WebSocket, not chromedriver:

```python
import json, urllib.request, websocket

version = json.loads(
    urllib.request.urlopen("http://127.0.0.1:9222/json/version").read()
)
ws = websocket.create_connection(version["webSocketDebuggerUrl"])
ws.send(json.dumps({
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {"expression": "document.title", "returnByValue": True},
}))
```

Do **not** ship `chromedriver` in the runner image. chromedriver strictly version-validates against the target Chromium, and Steam's embedded CEF is routinely older than the host chrome, so any skew raises `SessionNotCreatedException`.

### 5. `org.kde.PlasmaShell.evaluateScript` boundaries

`org.kde.PlasmaShell.evaluateScript` is the structural analogue of GNOME `Shell.Eval`, but it is a **diagnostics and session-reset hook, not an interaction API**:

- It is gated by `immutability() != SystemImmutable` **and** `KAuthorized::authorize("plasma-desktop/scripting_console")`, so hardened/kiosk images may refuse it.
- Real users do not drive the desktop through `evaluateScript`. Tests that open Kickoff or change a KCM through it validate a debugging path, not the user path.

Permitted uses: state inspection, layout dumps (`dumpCurrentLayoutJS()`), KWin support information, and between-scenario session reset. All user-facing interaction must go through AT-SPI/WebDriver, app D-Bus/CLI entry points (`kcmshell6`, KRunner D-Bus, desktop-file activation), or `qdbus` calls that mirror what a user actually triggers.

## Common Rationalizations

- *"I'll just build inputsynth once in the runner image."*
  - **Rebuttal:** It will link against the Fedora Qt/KWin ABI and break on Neon or KDE Linux. Build/install it on the DUT, keyed to the DUT's distro and Plasma version.
- *"Appium-Python-Client is more convenient."*
  - **Rebuttal:** The KDE server is W3C WebDriver, not Appium. Appium methods like `install_app` and `hide_keyboard` return `404`/`501` and add mobile-only dependencies.
- *"I'll use chromedriver for Steam because I know Selenium."*
  - **Rebuttal:** chromedriver version-checks Steam's embedded CEF and fails. Raw CDP over WebSocket removes that class of failure entirely.
- *"`evaluateScript` is the KDE equivalent of `Shell.Eval`, so I can use it everywhere."*
  - **Rebuttal:** Only for diagnostics and reset. Primary interaction must mirror real user input.

## Red Flags

- `selenium-webdriver-at-spi-inputsynth` present in `testsuite-kde-runner`.
- `Appium-Python-Client` or `chromedriver` in KDE runner dependencies.
- Runtime `pip install`, `curl`, or `urllib` fetches of executable test code.
- Missing `KWIN_WAYLAND_NO_PERMISSION_CHECKS=1` before sending input events.
- Using `org.kde.PlasmaShell.evaluateScript` to click UI elements or change settings.
- Mixing implicit waits with explicit `WebDriverWait`.
- `xpath` locators in AT-SPI tests without a documented quarantine reason.

## Verification

- [ ] `testsuite-kde-runner` image contains only behave, selenium, websocket-client, lxml, and PyYAML.
- [ ] No perceptual image differ is installed. The PyPI package `odiff` is an unrelated JSON/YAML utility, **not** the image differ of the same name — never add it.
- [ ] No `inputsynth`, `Appium-Python-Client`, or `chromedriver` in the runner image.
- [ ] DUT environment sets `KWIN_WAYLAND_NO_PERMISSION_CHECKS=1`, `KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1`, `QT_ACCESSIBILITY=1`, `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`, `QT_QPA_PLATFORM=wayland`, `LIBGL_ALWAYS_SOFTWARE=1`, `KWIN_NO_ANIMATIONS=1`.
- [ ] `evaluateScript` is used only for diagnostics, layout dumps, or session reset.
- [ ] WebDriver client uses an options subclass, not `desired_capabilities`.
- [ ] Gamescope/Steam automation uses raw CDP over WebSocket, not chromedriver.
- [ ] `ruff check tests/ --select E,F,W --ignore E501` passes.
- [ ] `behave --dry-run tests/<suite>/features` passes for the touched suite.

## Read-only KDE boundary

`invent.kde.org` and all KDE properties are strictly read-only in this repository. Clone, fetch, read files, and call read-only APIs are allowed. Never create issues, MRs, comments, branches, tags, forks, or authenticated writes to a KDE host.
