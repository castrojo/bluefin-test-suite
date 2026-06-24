@smoke_suite @bluefin
Feature: OOTB Flatpak sandbox permission auditing
  Verify that OOTB Flatpaks are installed and do not hold excessive
  host filesystem access. Runs in the smoke suite where Flatpaks are
  pre-staged via the sideload cache.

  @permissions
  Scenario: org.gnome.Calculator is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.Calculator >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.gnome.Loupe is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.Loupe >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.gnome.TextEditor is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.TextEditor >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.gnome.Papers is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.Papers >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.mozilla.firefox is installed system-wide
    * Run and save command output: "flatpak info --system org.mozilla.firefox >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.gnome.clocks is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.clocks >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: org.gnome.Calendar is installed system-wide
    * Run and save command output: "flatpak info --system org.gnome.Calendar >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: io.missioncenter.MissionCenter is installed system-wide
    * Run and save command output: "flatpak info --system io.missioncenter.MissionCenter >/dev/null 2>&1 && echo installed || echo missing"
    * Last command output "contains" "installed"

  @permissions
  Scenario: Calculator Flatpak has no host filesystem access (strict sandbox)
    * Run and save command output: "flatpak info --system --show-permissions org.gnome.Calculator 2>/dev/null | grep -qE 'filesystems=(host|home)' && echo over-permissioned || echo ok"
    * Last command output "contains" "ok"

  @permissions
  Scenario: Loupe Flatpak has no host filesystem access (document portal only)
    * Run and save command output: "flatpak info --system --show-permissions org.gnome.Loupe 2>/dev/null | grep -qE 'filesystems=(host|home)' && echo over-permissioned || echo ok"
    * Last command output "contains" "ok"

  @permissions
  Scenario: Firefox sandbox permissions metadata is readable
    * Run and save command output: "flatpak info --system --show-permissions org.mozilla.firefox 2>/dev/null | grep -q 'Context' && echo ok || echo fail"
    * Last command output "contains" "ok"

  @permissions
  Scenario: Flatpak portal permission tables are accessible
    * Run and save command output: "flatpak permissions screenshot 2>/dev/null && flatpak permissions notifications 2>/dev/null && echo done"
    * Last command output "contains" "done"
