@common @bluefin
Feature: Bluefin common desktop entry validation
  Checks common-layer desktop integration artifacts over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Sample of installed desktop files passes validation
    * Run SSH command: "find /usr/share/applications -name '*.desktop' | head -20 | xargs desktop-file-validate 2>&1 | grep -v '^$' | wc -l | tr -d '[:space:]'"
    * SSH command output "is" "0"

  Scenario: Bluefin-specific desktop entries are present
    * Run SSH command: "test -f /usr/share/applications/ujust.desktop || test -f /usr/share/applications/org.gnome.Shell.desktop"
    * SSH command return code is "0"
