@accessibility @smoke_suite
Feature: GNOME accessibility
  GNOME ships built-in accessibility features. Verify the a11y
  infrastructure is functional and key settings are configurable.

  Background:
    * GNOME Shell is accessible via AT-SPI

  @retry @settings @accessibility @sla_15s
  Scenario: Accessibility settings panel is reachable
    * Launch Settings via command
    * Settings window is accessible
    * Navigate to Settings panel "Accessibility"
    * Settings panel "Accessibility" is visible
    * Key combo: "<Ctrl><Q>" with uinput
    * Settings is no longer running

  @accessibility @gsettings
  Scenario: High contrast mode can be toggled via gsettings
    * Run and save command output: "gsettings set org.gnome.desktop.a11y.interface high-contrast true"
    * Return code of last command output "is" "0"
    * Run and save command output: "gsettings get org.gnome.desktop.a11y.interface high-contrast"
    * Last command output "contains" "true"
    * Run and save command output: "gsettings set org.gnome.desktop.a11y.interface high-contrast false"
    * Return code of last command output "is" "0"

  @accessibility @keyboard
  Scenario: Keyboard accessibility settings key is readable
    * Run and save command output: "gsettings get org.gnome.desktop.a11y.keyboard enable"
    * Return code of last command output "is" "0"

  @accessibility @atspi
  Scenario: AT-SPI accessibility bus is reachable from the GNOME session
    * AT-SPI accessibility bus is reachable from the GNOME session

  @accessibility @regression
  Scenario: No accessibility-related journal errors after session start
    * Run and save command output: "journalctl -b --no-pager -p err -g 'at-spi|orca|accessibility' | grep -v '^$' | wc -l"
    * Last command output "contains" "0"
