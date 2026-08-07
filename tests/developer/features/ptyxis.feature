@developer_suite
Feature: Ptyxis terminal smoke tests
  Validates Ptyxis terminal launches, accepts input, and runs brew/podman.
  Ptyxis AT-SPI name confirmed: root.application("ptyxis").
  Regression coverage for bluefin#4620 (Vulkan spam in terminal).

  Background:
    * Start application "ptyxis" via "command"
    * Make sure window is focused for wayland testing

  @ptyxis @launch
  Scenario: Ptyxis launches and window is accessible
    * Application "ptyxis" is running
    * Ptyxis window is accessible

  @pending @ptyxis @input
  Scenario: Terminal accepts keyboard input
    # Pending: Background restarts ptyxis each scenario via SSH shim; ptyxis does
    # not re-register in AT-SPI within wait_before_app_starts(30s) on 2nd+ launches.
    # Tracked: projectbluefin/testsuite#368
    * Type text: "echo bluefin-test" with uinput
    * Press key: "Return" with uinput
    * Terminal output in ptyxis contains "bluefin-test"

  @pending @ptyxis @brew
  Scenario: brew is on PATH and returns version string
    # Pending: e2e workflow masks brew-setup.service, so Homebrew is unavailable in CI (see #487).
    * Type text: "brew --version" with uinput
    * Press key: "Return" with uinput
    * Terminal output in ptyxis contains "Homebrew"

  @pending @ptyxis @podman
  Scenario: podman is available in terminal
    # Pending: ptyxis AT-SPI restart issue (see #368) blocks terminal input scenarios.
    * Type text: "podman --version" with uinput
    * Press key: "Return" with uinput
    * Terminal output in ptyxis contains "podman version"

  @pending @ptyxis @regression @bluefin_4620
  Scenario: No Vulkan validation spam on terminal open (bluefin#4620)
    # Pending: Background restart errors cascade to this scenario (see #368).
    * No journal entries match "VUID-"

  @pending @ptyxis @new_tab
  Scenario: New tab opens via keyboard shortcut
    # Pending: ptyxis AT-SPI restart issue (see #368) blocks multi-scenario runs.
    * Key combo: "<Shift><Ctrl><T>" with uinput
    * Ptyxis has "2" tabs

  @pending @ptyxis @close
  Scenario: Ptyxis closes via shortcut
    # Pending: ptyxis AT-SPI restart issue (see #368) blocks multi-scenario runs.
    * Close application "ptyxis" via "shortcut"
    * Application "ptyxis" is no longer running
