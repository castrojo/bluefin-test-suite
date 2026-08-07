@developer @bluefin
@bctl
Feature: bluefinctl (bctl) headless CLI
  Validates bluefinctl's headless subcommands through Ptyxis terminal
  interaction. bctl is installed by default on all Bluefin variants via
  Homebrew, and every ujust recipe checks `command -v bctl` first before
  falling back to a bash-only path. Without bctl present, only the bash
  fallback is ever exercised.
  # Pending: e2e.yml masks brew-setup.service, so Homebrew (and therefore
  # bctl) is never provisioned in CI. Unmasking it — and thereby the CI
  # job/infra change needed to run these scenarios — is a design-gated
  # CI-interface change tracked in #487. These scenarios are written ahead
  # of that infra so they are ready to un-pend once the contract is approved.

  Background:
    * Start application "ptyxis" via "command"
    * Make sure window is focused for wayland testing

  @pending @bctl_status
  Scenario: bctl status prints system identity information
    * Run bctl command in ptyxis and capture result: "bctl status"
    * bctl command exits with status 0
    * bctl command output includes "Bluefin"

  @pending @bctl_update_check
  Scenario: bctl update --check exits 0 or 1 without applying updates
    * Run bctl command in ptyxis and capture result: "bctl update --check"
    * bctl update --check exits with status 0 or 1

  @pending @bctl_devmode_status
  Scenario: bctl devmode status reports the current developer-mode state
    * Run bctl command in ptyxis and capture result: "bctl devmode status"
    * bctl command exits with status 0

  @pending @bctl_help
  Scenario: bctl --help lists the headless subcommands
    * Run bctl command in ptyxis and capture result: "bctl --help"
    * bctl command exits with status 0
    * bctl command output includes "status"
    * bctl command output includes "update"
    * bctl command output includes "devmode"
