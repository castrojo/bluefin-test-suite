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

  Scenario: Bluefin accent color is slate
    * Run SSH command: "gsettings get org.gnome.desktop.interface accent-color"
    * SSH command return code is "0"
    * SSH command output stripped "is" "'slate'"

  Scenario: Desktop app grid has Bluefin folder layout
    * Run SSH command: "gsettings get org.gnome.desktop.app-folders folder-children"
    * SSH command return code is "0"
    * SSH command output contains "GamingUtilities"
    * SSH command output contains "Utilities"
    * SSH command output contains "Containers"
    * SSH command output contains "Development"
    * SSH command output contains "Productivity"

  Scenario: Ptyxis terminal custom keybinding is set
    * Run SSH command: "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings"
    * SSH command return code is "0"
    * SSH command output contains "custom0"
    * Run SSH command: "dconf read /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/binding"
    * SSH command return code is "0"
    * SSH command output stripped "is" "'<Control><Alt>t'"
    * Run SSH command: "dconf read /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/command"
    * SSH command return code is "0"
    * SSH command output stripped "is" "'xdg-terminal-exec'"

  Scenario: Searchlight extension is configured
    * Run SSH command: "dconf read /org/gnome/shell/extensions/search-light/shortcut-search"
    * SSH command return code is "0"
    * SSH command output stripped "is" "['<Super>space']"

  Scenario: Ptyxis color palette is deployed
    * Run SSH command: "dconf read /org/gnome/Ptyxis/Profiles/2871e8027773ae74d6c87a5f659bbc74/palette"
    * SSH command return code is "0"
    * SSH command output stripped "is" "'catppuccin-dynamic'"
