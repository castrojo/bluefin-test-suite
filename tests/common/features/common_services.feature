@common @bluefin
Feature: Bluefin common systemd service health
  Validates high-risk custom Bluefin systemd services over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: rechunker-group-fix service completed successfully
    * Run SSH command: "systemctl show rechunker-group-fix.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"
    * Run SSH command: "systemctl list-units --state=failed --plain --no-legend | grep -F rechunker-group-fix.service || true"
    * SSH command output does not contain "rechunker-group-fix.service"

  Scenario: ublue-system-setup service completed successfully
    * Run SSH command: "systemctl show ublue-system-setup.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"

  Scenario: ublue-user-setup user service completed successfully
    * Run SSH command: "systemctl --user show ublue-user-setup.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"

  Scenario: flatpak-preinstall installed required applications
    * Run SSH command: "systemctl show flatpak-preinstall.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"
    * Run SSH command: "flatpak list --app --columns=application"
    * SSH command output contains "org.mozilla.firefox"
    * SSH command output contains "com.raggesilver.BlackBox"

  Scenario: flatpak remotes are flathub only
    * Run SSH command: "systemctl show flatpak-nuke-fedora.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"
    * Run SSH command: "flatpak remotes --columns=name"
    * SSH command output contains "flathub"
    * SSH command output does not contain "fedora"

  Scenario: dconf database is compiled
    * Run SSH command: "systemctl show dconf-update.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"
    * Run SSH command: "dconf dump /"
    * SSH command output is not empty

  Scenario: bootc unified storage service completed successfully
    * Run SSH command: "systemctl show bootc-unified-storage.service --property=ActiveState --value"
    * SSH command return code is "0"
    * SSH command output stripped "is" "active"
