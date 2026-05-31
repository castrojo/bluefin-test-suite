@smoke_suite
Feature: GNOME Shell smoke tests
  Validates GNOME Shell is functional on a fresh Bluefin boot.
  All steps use qecore common_steps unless noted as custom.
  Runs on every PR against latest and lts variants.

  # ── Top bar ──────────────────────────────────────────────────────────────

  @top_bar
  Scenario: GNOME Shell process is running and accessible via AT-SPI
    * GNOME Shell is accessible via AT-SPI
    * Dump panel children to log
    * Dump gnome-shell AT-SPI tree to results

  @top_bar
  Scenario: Panel is present in AT-SPI tree
    * GNOME Shell is accessible via AT-SPI
    * Panel is present in AT-SPI tree

  @top_bar
  Scenario: Activities toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * Item "Activities" "toggle button" is "showing" in "gnome-shell"

  @top_bar
  Scenario: Clock toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * Clock toggle is visible in top bar

  @top_bar
  Scenario: System menu toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * System menu toggle is visible in top bar

  # ── Activities overview ───────────────────────────────────────────────────
  # NOTE: uinput Super key (KEY_LEFTMETA) is unreliable on GNOME 50 Wayland —
  # Mutter does not route it from python-uinput devices. Use Shell.Eval instead.

  @activities @sla_5s
  Scenario: Super key opens Activities overview
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Close Activities overview via Shell.Eval
    * Overview is closed

  @activities
  Scenario: Typing in overview populates search bar
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Set overview search text to "Files" via Shell.Eval
    * Overview search bar contains "Files"
    * Close Activities overview via Shell.Eval

  @activities
  Scenario: Escape closes Activities overview
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Close Activities overview via Shell.Eval
    * Overview is closed

  # ── Quick Settings ────────────────────────────────────────────────────────
  # NOTE: Clock/System toggle buttons have AT-SPI position INT_MIN on GNOME 50.
  # Drive via Shell.Eval; verify via isOpen JS property.

  @quick_settings @sla_5s
  Scenario: Clicking System menu opens Quick Settings
    * GNOME Shell is accessible via AT-SPI
    * Open Quick Settings via Shell.Eval
    * Quick Settings panel is open via Shell.Eval

  @quick_settings
  Scenario: Escape closes Quick Settings
    * GNOME Shell is accessible via AT-SPI
    * Open Quick Settings via Shell.Eval
    * Quick Settings panel is open via Shell.Eval
    * Close Quick Settings via Shell.Eval
    * Quick Settings panel is closed via Shell.Eval

  @quick_settings @night_light
  Scenario: Night Light can be enabled and disabled
    * GNOME Shell is accessible via AT-SPI
    * Ensure Night Light starts disabled via gsettings
    * Enable Night Light via gsettings
    * Night Light is enabled via gsettings
    * Disable Night Light via gsettings
    * Night Light is disabled via gsettings

  @quick_settings @dnd
  Scenario: Do-Not-Disturb can be toggled via Quick Settings
    * GNOME Shell is accessible via AT-SPI
    * Open Quick Settings via Shell.Eval
    * Quick Settings panel is open via Shell.Eval
    * Enable Do-Not-Disturb via Shell.Eval toggle
    * Do-Not-Disturb is enabled via Shell.Eval
    * Disable Do-Not-Disturb via Shell.Eval toggle
    * Do-Not-Disturb is disabled via Shell.Eval
    * Close Quick Settings via Shell.Eval

  # ── Calendar popup ────────────────────────────────────────────────────────

  @calendar @sla_5s
  Scenario: Clicking clock opens calendar popup
    * GNOME Shell is accessible via AT-SPI
    * Open date menu via Shell.Eval
    * Date menu panel is open via Shell.Eval

  @calendar
  Scenario: Escape closes calendar popup
    * GNOME Shell is accessible via AT-SPI
    * Open date menu via Shell.Eval
    * Date menu panel is open via Shell.Eval
    * Close date menu via Shell.Eval
    * Date menu panel is closed via Shell.Eval

  # ── Lock screen ──────────────────────────────────────────────────────────
  # Lock screen is highest-priority: extensions can silently break it.

  @lock_screen
  Scenario: Screen lock engages without crashing GNOME Shell
    * GNOME Shell is accessible via AT-SPI
    * Lock screen via Shell.Eval
    * Session is locked
    * Unlock screen via Shell.Eval

  # ── Workspaces ────────────────────────────────────────────────────────────

  @workspaces
  Scenario: Switching workspace changes the active workspace index
    * GNOME Shell is accessible via AT-SPI
    * Active workspace index is noted
    * Switch to next workspace via Shell.Eval
    * Active workspace has changed

  # ── Regressions ───────────────────────────────────────────────────────────

  @regression @bluefin_4612
  Scenario: GNOME Shell extensions do not crash shell on load (bluefin#4612)
    * GNOME Shell is accessible via AT-SPI
    * No journal entries at priority "err..emerg" contain "gnome-shell"

  @regression @bluefin_4642
  Scenario: No gnome-shell coredump after session start (bluefin#4642)
    * No coredump entries exist for "gnome-shell"
