@common @bluefin
Feature: Bluefin common dconf and GSettings defaults
  Validates the common layer's GNOME defaults and locked settings over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  # Transitioning to a custom logo menu — these checks are no longer valid.
  # Track replacement in: https://github.com/projectbluefin/common/issues
  @quarantine
  Scenario: Logo Menu extension is configured
    * Run SSH command: "gsettings get org.gnome.shell enabled-extensions"
    * Last command output contains "logomenu"

  @quarantine
  Scenario: Logo Menu activities button visibility is configured
    * Run SSH command: "dconf read /org/gnome/shell/extensions/Logo-menu/show-activities-button"
    * Last command output contains "true"

  Scenario: custom-command-list extension is enabled
    * Run SSH command: "gsettings get org.gnome.shell enabled-extensions"
    * Last command output contains "custom-command-list@storageb.github.com"

  Scenario: custom-command-list menu icon is configured
    * Run SSH command: "dconf read /org/gnome/shell/extensions/custom-command-list/menuicon-setting"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: dconf locked keys cannot be overridden
    * Run SSH command: "gsettings set org.gnome.software allow-updates true"
    * Last command exits with non-zero status

  Scenario: Custom keybindings are configured
    * Run SSH command: "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings"
    * SSH command output is not empty

  Scenario: GNOME interface color scheme preference is set
    * Run SSH command: "gsettings get org.gnome.desktop.interface color-scheme"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: GNOME clock format is configured
    * Run SSH command: "gsettings get org.gnome.desktop.interface clock-format"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: GNOME font-name setting is present
    * Run SSH command: "gsettings get org.gnome.desktop.interface font-name"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: GNOME show-battery-percentage setting is readable
    * Run SSH command: "gsettings get org.gnome.desktop.interface show-battery-percentage"
    * SSH command return code is "0"
