@common @bluefin
Feature: Bluefin common ujust recipes
  Validates non-destructive, non-interactive ujust recipes over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: ujust check-local-overrides exits cleanly on a fresh system
    * Run SSH command: "NO_COLOR=1 ujust check-local-overrides"
    * SSH command return code is "0"

  Scenario: ujust logs-this-boot prints the current boot journal
    * Run SSH command: "ujust logs-this-boot"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: ujust bios-info prints firmware metadata
    * Run SSH command: "ujust bios-info"
    * SSH command return code is "0"
    * SSH command output contains "Manufacturer"

  @pending @wip
  Scenario: ujust toggle-updates flips the automatic update timer
    * Run SSH command: "if systemctl cat -- uupd.timer >/dev/null 2>&1; then TIMER=uupd.timer; else TIMER=rpm-ostreed-automatic.timer; fi; before=$(systemctl is-enabled \"$TIMER\" || true); ujust toggle-updates; after=$(systemctl is-enabled \"$TIMER\" || true); test \"$before\" != \"$after\""
    * SSH command return code is "0"

  Scenario: ujust changelogs renders release notes
    * Run SSH command: "command -v glow >/dev/null && ujust changelogs"
    * SSH command return code is "0"
    * SSH command output is not empty
