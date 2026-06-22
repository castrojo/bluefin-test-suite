@common @bluefin
Feature: Bluefin Flatpak-only desktop model
  Validates Bluefin's system-level Flatpak delivery model over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Flathub is the only configured Flatpak remote
    * Run SSH command: "flatpak remotes --columns=name"
    * SSH command return code is "0"
    * SSH command output contains "flathub"
    * SSH command output does not contain "fedora"

  Scenario: No Fedora system Flatpak remote is configured
    * Run SSH command: "flatpak remotes --system --columns=name,url"
    * SSH command return code is "0"
    * SSH command output does not contain "fedora-flathub"
    * SSH command output does not contain "fedora"

  Scenario: Required system Flatpaks are installed
    * Run SSH command: "flatpak list --app --columns=application"
    * SSH command return code is "0"
    * SSH command output contains "org.mozilla.firefox"
    * Run SSH command: "flatpak list --app --columns=application | grep -Eq '^(org.gnome.Ptyxis|com.raggesilver.BlackBox)$' && echo present || echo missing"
    * SSH command output "is" "present"

  Scenario: No graphical RPM desktop entries point to /usr/bin executables
    * Run SSH command: "grep -r \"^Exec=/usr/bin\" /usr/share/applications/ --include=\"*.desktop\" -l | grep -v -e \"ublue\" -e \"ujust\" -e \"just\" | wc -l | tr -d '[:space:]'"
    * SSH command output "is" "0"

  Scenario: Flatpak apps can be listed without errors
    * Run SSH command: "flatpak list --app"
    * SSH command return code is "0"
    * SSH command output is not empty
