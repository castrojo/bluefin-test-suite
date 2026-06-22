@smoke_suite @bluefin
Feature: Bluefin desktop identity
  Verifies Bluefin's desktop is correctly configured: Wayland session,
  hardware acceleration active, and key desktop components visible.

  Background:
    * GNOME Shell is accessible via AT-SPI

  @bluefin
  Scenario: Session is running under Wayland
    * Wayland session type is active

  @bluefin
  Scenario: No software rendering fallback (LLVMpipe)
    * GNOME Shell is not using software rendering

  @bluefin
  Scenario: Dash to Dock is visible in the shell
    * Dash to Dock panel is visible

  @bluefin
  Scenario: System tray indicators are available
    * System tray area is present in the panel
