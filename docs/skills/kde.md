---
name: kde-testing-skills
description: "Use when authoring KDE/Plasma desktop GUI tests, working with selenium-webdriver-at-spi, or implementing CEF remote-debugging for Steam Gamescope."
metadata:
  type: reference
---

# KDE and Steam Gamescope Automation Skills

Load when: writing or debugging GUI tests for Bazzite/Aurora's KDE Plasma and Gamescope (handheld) variants.

## 1. KDE Desktop GUI Automation (AT-SPI / Appium)

KDE Plasma does not use GNOME-specific helpers or ponytail. Instead, we use **`selenium-webdriver-at-spi`** (the official KDE accessibility-bridged WebDriver).

### Essential Practices

* **`inputsynth` Simulation:** Input injection on KWin Wayland is handled by compiling and utilizing the native `inputsynth` utility. It translates Touch, Pointer, and Key simulation directly through KWin.
* **AT-SPI Bus Pre-binding:** Always pre-bind the `AT_SPI_BUS_ADDRESS` environment variable before launching the Flask webdriver or QML targets to prevent Qt's startup accessibility race.
* **Wayland Permission Overrides:** KWin Wayland has client isolation. In the test environment, ensure we set overrides:
  ```bash
  KWIN_WAYLAND_NO_PERMISSION_CHECKS=1
  KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1
  ```
* **Software Rendering (Mesa LLVMPipe):** In headless virtual machine environments (like GitHub Actions runners), force software rendering to prevent GPU-less crashes:
  ```bash
  LIBGL_ALWAYS_SOFTWARE=1
  ```

---

## 2. Steam Gaming Mode Automation (Gamescope / CEF CDP)

Gamescope does not run a desktop accessibility (AT-SPI2) bus. Standard UI automation engines fail. We bypass accessibility by connecting directly to Steam's browser DOM!

### Remote Debugging Port 9222

Because Steam's Big Picture and gamepad interfaces are rendered via the **Chromium Embedded Framework (CEF)**, we can automate them like a web browser using standard **Chrome DevTools Protocol (CDP)** over port `9222`.

#### The Wrapper Script Pattern

We inject the `--remote-debugging-port=9222` flag into Steam by placing wrapper scripts inside `~/.local/bin/` (which takes priority on `PATH`).

##### 1. Native Steam Wrapper (`~/.local/bin/steam`)
```bash
#!/bin/bash
exec /usr/bin/steam --remote-debugging-port=9222 "$@"
```

##### 2. Flatpak Steam Wrapper (`~/.local/bin/flatpak`)
Since Steam can run inside Flatpak (`com.valvesoftware.Steam`), we intercept `flatpak run` commands and append the debugger port dynamically:
```bash
#!/bin/bash
if [[ "$*" == *"run com.valvesoftware.Steam"* ]]; then
  args=()
  for arg in "$@"; do
    args+=("$arg")
    if [[ "$arg" == "com.valvesoftware.Steam" ]]; then
      args+=("--remote-debugging-port=9222")
    fi
  done
  exec /usr/bin/flatpak "${args[@]}"
else
  exec /usr/bin/flatpak "$@"
fi
```

#### Standard Selenium CDP Automation
In Python steps, we connect using standard Selenium Chrome options:
```python
from selenium import webdriver
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome(options=options)
quick_access = driver.find_element(By.CLASS_NAME, "quickaccessmenu_QuickAccessButton")
quick_access.click()
```

This bypasses Appium and AT-SPI entirely, providing highly robust web-based DOM testing for gamescope gamepad interfaces!
