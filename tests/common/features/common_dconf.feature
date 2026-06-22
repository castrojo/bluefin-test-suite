@common @bluefin
Feature: Bluefin common dconf and GSettings defaults
  Validates the common layer's GNOME defaults and locked settings over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: custom-command-list extension is in distribution defaults
    * Run SSH command: "python3 -c \"import gi; gi.require_version('Gio','2.0'); from gi.repository import Gio; v = Gio.Settings.new('org.gnome.shell').get_default_value('enabled-extensions'); print(v.unpack() if v else [])\""
    * Last command output contains "custom-command-list@storageb.github.com"

  Scenario: legacy Logo Menu extension is not enabled
    * Run SSH command: "gsettings get org.gnome.shell enabled-extensions"
    * SSH command output does not contain "logomenu@aryan_k"

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

  Scenario: GNOME interface color scheme preference matches the shipped Bluefin default
    * Run SSH command: "gsettings get org.gnome.desktop.interface color-scheme"
    * SSH command return code is "0"
    * SSH command output contains "prefer-dark"

  Scenario: GNOME clock format matches the shipped Bluefin default
    * Run SSH command: "gsettings get org.gnome.desktop.interface clock-format"
    * SSH command return code is "0"
    * SSH command output contains "12h"

  Scenario: GNOME font-name matches the shipped Bluefin default
    * Run SSH command: "gsettings get org.gnome.desktop.interface font-name"
    * SSH command return code is "0"
    * SSH command output stripped "is" "'Adwaita Sans 11'"

  Scenario: GNOME show-battery-percentage matches the shipped Bluefin default
    * Run SSH command: "gsettings get org.gnome.desktop.interface show-battery-percentage"
    * SSH command return code is "0"
    * SSH command output stripped "is" "false"
