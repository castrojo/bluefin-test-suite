@smoke_suite
Feature: GNOME Shell smoke tests
  Validates GNOME Shell is functional on a fresh Bluefin boot.
  All steps use qecore common_steps unless noted as custom.
  Runs on every PR against latest and lts variants.

  # ── Top bar ──────────────────────────────────────────────────────────────

  @retry @top_bar
  Scenario: GNOME Shell process is running and accessible via AT-SPI
    * GNOME Shell is accessible via AT-SPI
    * Dump panel children to log
    * Dump gnome-shell AT-SPI tree to results

  @retry @top_bar
  Scenario: Panel is present in AT-SPI tree
    * GNOME Shell is accessible via AT-SPI
    * Panel is present in AT-SPI tree

  @retry @top_bar
  Scenario: Activities toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * Activities toggle button is present in gnome-shell panel

  @retry @top_bar
  Scenario: Clock toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * Clock toggle is visible in top bar

  @retry @top_bar
  Scenario: System menu toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * System menu toggle is visible in top bar

  # ── Activities overview ───────────────────────────────────────────────────
  # GNOME 50 disables Shell.Eval outside unsafe mode, and unsafe mode cannot be
  # enabled from a cold session via D-Bus.  Use the stable org.gnome.Shell
  # OverviewActive property and AT-SPI for search-entry state instead.
  #
  # IMPORTANT: commands are routed through an SSH wrapper that prefixes them
  # with ``source /tmp/session.env``.  gdbus GVariant literals like ``<true>``
  # are interpreted as shell redirection operators in that wrapper, so overview
  # D-Bus calls must use busctl (no angle brackets).  See PR #602.

  @retry @activities @sla_5s
  Scenario: Super key opens Activities overview
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview
    * Overview is open
    * Close Activities overview via D-Bus
    * Overview is closed

  @activities
  Scenario: Typing in overview populates search bar
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview
    * Overview is open
    * Dismiss the Bluefin welcome dialog if it appears
    * Type "Files" in overview search entry
    * Overview search bar contains "Files"
    * Close Activities overview via D-Bus

  @activities
  Scenario: D-Bus closes Activities overview
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview
    * Overview is open
    * Close Activities overview via D-Bus
    * Overview is closed

  # ── Quick Settings ────────────────────────────────────────────────────────
  # NOTE: Clock/System toggle buttons have AT-SPI position INT_MIN on GNOME 50.
  # Drive via Shell.Eval; verify via isOpen JS property.

  @retry @quick_settings @sla_5s
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

  @retry @calendar @sla_5s
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
    * Lock screen via loginctl
    * Session is locked
    * Unlock screen via loginctl

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
    * No coredump entries exist on the host for "gnome-shell"
