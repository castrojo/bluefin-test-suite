@common @bluefin
Feature: Bluefin common dconf and GSettings defaults
  Validates the common layer's GNOME defaults and locked settings over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Logo Menu extension is configured
    * Run SSH command: "gsettings get org.gnome.shell enabled-extensions"
    * Last command output contains "logomenu"

  Scenario: Activities button is hidden
    * Run SSH command: "gsettings get org.gnome.shell.extensions.Logo-menu hide-activities-button"
    * Last command output contains "true"

  Scenario: dconf locked keys cannot be overridden
    * Run SSH command: "gsettings set org.gnome.shell enabled-extensions '[]'"
    * Last command exits with non-zero status

  Scenario: Custom keybindings are configured
    * Run SSH command: "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings"
    * SSH command output is not empty
