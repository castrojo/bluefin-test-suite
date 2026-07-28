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

## Shared Helper API (real function names)

The kde-smoke suite imports shared helpers at **module scope with no try/except guard**. A missing or renamed helper must cause an immediate `ImportError` — never a silent skip that makes CI green while zero scenarios run.

### `tests/shared/kde_preconditions.py`

| Function | Signature | Purpose |
|---|---|---|
| `is_kde_session` | `(context) -> bool` | Probe whether the DUT is running a KDE/Plasma session |
| `apply_kde_session_preconditions` | `(context, username="bluefin-test") -> KDEResult` | Orchestrate the full KDE session precondition pipeline |
| `has_sddm` | `(context) -> bool` | Probe whether SDDM is the active display manager |
| `has_kwriteconfig6` | `(context) -> bool` | Probe whether kwriteconfig6 is available |
| `has_plasma_wayland_session` | `(context) -> bool` | Probe whether the Plasma Wayland session desktop file exists |
| `configure_sddm_autologin` | `(context, username, session) -> KDEResult` | Configure SDDM autologin |
| `suppress_welcome_wizard` | `(context, username) -> KDEResult` | Suppress Plasma Welcome Center and distro wizards |
| `emit_determinism_dropin` | `(context) -> KDEResult` | Write the systemd user-environment drop-in |
| `seed_home` | `(context, username, force) -> KDEResult` | Reset the test user's home directory |
| `wait_for_plasma_session` | `(context, timeout) -> KDEResult` | Poll until kwin_wayland, plasmashell, and AT-SPI are reachable |
| `is_kde_image` | `(image_ref) -> bool` | Pure string check for a KDE/Plasma image family (no SSH) |
| `ensure_kde_session` | `(context, username="bluefin-test") -> KDEResult` | Preferred runtime entry point: wait for Plasma, then suppress the wizard |
| `apply_disk_prep` | `(context, username, ...) -> KDEResult` | Full pre-boot (disk-prep) pipeline |
| `configure_autologin` | `(context, username, session) -> KDEResult` | DM-aware autologin drop-in (SDDM or PLM) |
| `detect_display_manager` | `(context) -> str` | Returns `"sddm"`, `"plm"`, or `"unknown"` |
| `has_plm` | `(context) -> bool` | Probe whether Plasma Login Manager is the active display manager |

`is_kde_image`, `ensure_kde_session`, `apply_disk_prep`, `configure_autologin`,
`detect_display_manager`, and `has_plm` are added by the KDE session-lifecycle
work (`fix/kde-session-lifecycle`); `configure_sddm_autologin` survives there as
a deprecated compat wrapper around `configure_autologin`. See
[references/session-preconditions.md](references/session-preconditions.md) for
the phase model (disk-prep vs runtime).

**Do not invent helper names.** This table plus the module source is the
complete public surface. Verify a name against `tests/shared/kde_preconditions.py`
on the branch you are actually targeting before importing it — the module grows,
so "it did not exist last week" is not evidence either way. The rule that never
changes is below: import at module scope, never guard the import.

### `tests/shared/kde_webdriver.py`

| Function | Signature | Purpose |
|---|---|---|
| `new_session` | `(command_executor, options, app) -> WebDriver` | Create a Remote WebDriver session against the KDE AT-SPI server |
| `quit_session` | `(driver) -> None` | Tear down a WebDriver session |
| `launch_app` | `(app_id, command_executor) -> WebDriver` | Start a session scoped to a single application |
| `find` | `(driver, locator, timeout) -> WebElement` | Wait for and return a single element |
| `find_all` | `(driver, locator, timeout) -> list[WebElement]` | Wait for and return all matching elements |
| `wait_for` | `(driver, condition, timeout)` | Poll condition until truthy |
| `retry_atspi_action` | `(fn, attempts) -> T` | Run fn with surgical retry for AT-SPI churn |
| `save_screenshot` | `(driver, path) -> bool` | Save a W3C screenshot |

**Do not invent helper names.** This table is the complete public surface of
`tests/shared/kde_webdriver.py`; there is no `start_driver` or `press_key`.
Check the module before importing, and never guard the import with `hasattr`
or `try/except` — a wrong name must raise, not silently disable a feature.

### No-silent-skip rule

This is the real D1 defect: `tests/kde-smoke/features/environment.py` imported
helper names that did not exist on that tree, a `try/except` swallowed the
`ImportError`, and all 13 scenarios were skipped while CI reported green. The
fix is not "memorise which names exist" — it is **never guard a helper import**,
so a wrong or renamed name fails loudly on the first run.

```python
# WRONG — swallows ImportError, sets _KDE_HELPERS_AVAILABLE = False, skips all scenarios silently
try:
    from tests.shared.kde_preconditions import some_helper, another_helper
    _KDE_HELPERS_AVAILABLE = True
except Exception:
    _KDE_HELPERS_AVAILABLE = False

# RIGHT — bare import at module scope; ImportError propagates and fails the run
from tests.shared.kde_preconditions import is_kde_session, apply_kde_session_preconditions
from tests.shared import kde_webdriver
```

A unit test at `tests/unit/test_kde_smoke_environment.py` asserts the correct names exist and are callable. If a helper is renamed, the test fails before CI can report a phantom green.

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
