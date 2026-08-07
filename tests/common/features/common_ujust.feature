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

  # Blocked on projectbluefin/common: the recipe declares a `ACTION="prompt"`
  # parameter but never reads it. When `bctl` is present the recipe execs
  # `bctl --screen updates` and hands off to a GUI panel; only without `bctl`
  # does it fall back to a `gum choose` prompt, and that fallback blocks a
  # non-interactive run. Neither branch has a non-interactive entry point.
  # See docs/skills/test-authoring/behave/SKILL.md and projectbluefin/testsuite#499.
  @pending @wip
  Scenario: ujust toggle-updates flips the automatic update timer
    * Run SSH command: "if systemctl cat -- uupd.timer >/dev/null 2>&1; then TIMER=uupd.timer; else TIMER=rpm-ostreed-automatic.timer; fi; before=$(systemctl is-enabled \"$TIMER\" || true); ujust toggle-updates; after=$(systemctl is-enabled \"$TIMER\" || true); test \"$before\" != \"$after\""
    * SSH command return code is "0"

  # Pending: glow is unavailable because brew-setup.service is masked in CI (#487).
  @pending
  Scenario: ujust changelogs renders release notes
    * Run SSH command: "command -v glow >/dev/null && ujust changelogs"
    * SSH command return code is "0"
    * SSH command output is not empty
