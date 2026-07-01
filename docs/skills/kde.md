---
name: kde-testing-skills
description: "Use when authoring KDE/Plasma desktop GUI tests, working with selenium-webdriver-at-spi, or implementing CEF remote-debugging for Steam Gamescope."
metadata:
  type: reference
  context7-sources:
    - /seleniumhq/selenium
---

# KDE and Steam Gamescope Automation Skills

Guidelines and technical practices for automating End-to-End (E2E) GUI testing within KDE Plasma and Steam Gamescope environments.

## When to Use

* When writing, refactoring, or debugging GUI tests for Bazzite or Aurora KDE/Plasma-based image variants.
* When automating Steam's gamepad user interface in nested Gamescope (Steam Deck Gaming Mode) environments.
* When interacting with native Qt6/QML/GTK applications on KDE where standard GNOME dogtail/qecore helpers are unavailable.

## When NOT to Use

* When testing GNOME-based variants where standard `qecore` and `dogtail` tools are natively integrated.
* When testing non-GUI system states, CLI-only configurations, or background systemd services (use direct bash/SSH or custom behave shell assertions instead).

## Core Process

### 1. KDE Desktop Automation Setup (AT-SPI / Appium)

To automate native applications on KDE Wayland compositors:

1. **Wayland Permission Overrides:** KWin enforces strict client isolation. Force bypass rules inside testing runners to allow input and screenshot injection:
   ```bash
   export KWIN_WAYLAND_NO_PERMISSION_CHECKS=1
   export KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1
   ```
2. **Software Rendering:** Ensure headless virtual machines utilize software rendering to avoid GPU-related failures:
   ```bash
   export LIBGL_ALWAYS_SOFTWARE=1
   ```
3. **Compile and Deploy `inputsynth`:** Compile the official native input helper from the KDE `selenium-webdriver-at-spi` project and install it to `$HOME/.local/bin/`.
4. **Pre-bind accessibility bus:** Avoid startup accessibility race conditions by querying and locking `AT_SPI_BUS_ADDRESS` into the environmental wrapper before starting the target application.
5. **Orchestrate with Behave Hooks:** Define specific environment hooks to spin up the local Flask accessibility server wrapper during `before_all` or `before_feature` stages.

### 2. Gamescope/Steam CEF Automation Setup

Gamescope isolates the gaming mode session and lacks AT-SPI desktop accessibility support. Automate the interface using Chrome DevTools Protocol (CDP):

1. **Inject Debugging Flags:** Supply `--remote-debugging-port=9222` to Steam on startup.
2. **Deploy PATH Wrappers:** Override standard launching by dropping interceptor scripts in `~/.local/bin/` for both native `steam` and `flatpak run` commands.
3. **Connect WebDriver:** Initialize a standard Selenium Chrome WebDriver targeting the active debugging session:
   ```python
   from selenium import webdriver
   from selenium.webdriver.common.by import By

   options = webdriver.ChromeOptions()
   options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

   driver = webdriver.Chrome(options=options)
   # Now target elements directly in Steam's CEF DOM
   button = driver.find_element(By.CLASS_NAME, "quickaccessmenu_QuickAccessButton")
   button.click()
   ```

## Common Rationalizations

* *"I can just use general input emulation keys (like `xdotool` or `ydotool`) for Gamescope."*
  * **Rebuttal:** No. General input emulation fails inside nested Gamescope contexts due to input isolation and focus issues. CEF automation over CDP on port `9222` targets the web rendering tree directly, providing deterministic clicks and text entry.
* *"I should write a custom python library to parse AT-SPI registers instead of Appium or selenium-webdriver-at-spi."*
  * **Rebuttal:** Banned. Do not reinvent existing accessibility drivers. Re-use the official KDE WebDriver implementation to keep tests stable and compliant with upstream specifications.

## Red Flags

* Forgetting to set `KWIN_WAYLAND_NO_PERMISSION_CHECKS=1`, causing Wayland keyboard/mouse inputs to be ignored silently.
* Attempting to run standard `dogtail` inside a KDE compositor, resulting in GNOME accessibility service connection failures.
* Over-engineering Gamescope tests with separate emulator instances when a direct WebSockets/CDP connection to Steam's internal CEF browser suffices.

## Verification

- [ ] `ruff check tests/ --select E,F,W --ignore E501` is fully clean.
- [ ] `behave --dry-run tests/` passes with all feature scenarios mapped to valid Python step functions.
- [ ] No duplicate step implementation names (every function is uniquely named, resolving Ruff F811 errors).
- [ ] Target images correctly match `@bluefin` or `@dakota_only` tags.

