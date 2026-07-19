@input_methods @smoke_suite
Feature: Input method and keyboard layout smoke tests
  Verify the GNOME input-method stack (IBus) is present, the default keyboard
  layout is readable, a second layout can be added and switched via gsettings,
  and localectl reports a console keymap. All checks are headless-safe and run
  inside the VM via qecore-headless.

  @ibus @session
  Scenario: IBus daemon is running in the user session
    * Run and save command output: "pgrep -x ibus-daemon"
    * Return code of last command output "is" "0"
    * Run and save command output: "busctl --user list | grep -q org.freedesktop.IBus"
    * Return code of last command output "is" "0"

  @gsettings @layout @default
  Scenario: Default input sources contain a usable keyboard layout
    * Run and save command output: "gsettings get org.gnome.desktop.input-sources sources"
    * Return code of last command output "is" "0"
    * Last command output "contains" "xkb"

  @gsettings @layout @switch
  Scenario: A second keyboard layout can be added and switched via gsettings
    * original input sources are saved for restoration
    * Run and save command output: "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'us'), ('xkb', 'de')]\""
    * Return code of last command output "is" "0"
    * Run and save command output: "gsettings get org.gnome.desktop.input-sources sources"
    * Last command output "contains" "('xkb', 'de')"
    * Run and save command output: "gsettings set org.gnome.desktop.input-sources current 1"
    * Return code of last command output "is" "0"
    * Run and save command output: "gsettings get org.gnome.desktop.input-sources current"
    * Last command output "contains" "1"
    * Run and save command output: "gsettings get org.gnome.desktop.input-sources mru-sources"
    * Last command output "contains" "('xkb', 'de')"
    * restore original input sources

  @localectl @keymap
  Scenario: localectl reports a virtual console keymap
    * Run and save command output: "localectl status"
    * Return code of last command output "is" "0"
    * Last command output "contains" "VC Keymap"
