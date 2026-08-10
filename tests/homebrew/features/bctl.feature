@homebrew @bluefin
@bctl
Feature: bluefinctl (bctl) headless CLI
  Validates bluefinctl's headless subcommands through Ptyxis terminal
  interaction. bctl is installed by default on all Bluefin variants via
  Homebrew, and every ujust recipe checks `command -v bctl` first before
  falling back to a bash-only path. Without bctl present, only the bash
  fallback is ever exercised.

  Background:
    * Start application "ptyxis" via "command"
    * Make sure window is focused for wayland testing

  @bctl_status
  Scenario: bctl status prints system identity information
    * Run bctl command in ptyxis and capture result: "bctl status"
    * bctl command exits with status 0
    * bctl command output includes "Bluefin"

  @bctl_update_check
  Scenario: bctl update --check exits 0 or 1 without applying updates
    * Run bctl command in ptyxis and capture result: "bctl update --check"
    * bctl update --check exits with status 0 or 1

  @bctl_devmode_status
  Scenario: bctl devmode status reports the current developer-mode state
    * Run bctl command in ptyxis and capture result: "bctl devmode status"
    * bctl command exits with status 0

  @bctl_help
  Scenario: bctl --help lists the headless subcommands
    * Run bctl command in ptyxis and capture result: "bctl --help"
    * bctl command exits with status 0
    * bctl command output includes "status"
    * bctl command output includes "update"
    * bctl command output includes "devmode"
