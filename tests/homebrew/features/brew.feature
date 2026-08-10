@homebrew @bluefin
@brew
Feature: Homebrew package management
  Validates Homebrew package operations through Ptyxis terminal interaction.

  Background:
    * Start application "ptyxis" via "command"
    * Make sure window is focused for wayland testing

  @brew_version
  Scenario: brew --version returns a version string
    * Run brew command in ptyxis and capture result: "brew --version"
    * brew command exits with status 0
    * brew command prints a Homebrew version

  @brew_list
  Scenario: brew list completes without error
    * Run brew command in ptyxis and capture result: "brew list"
    * brew command exits with status 0

  @brew_info
  Scenario: brew info git shows package information
    * Run brew command in ptyxis and capture result: "brew info git"
    * brew command exits with status 0
    * brew command output includes "git:"
    * brew command output includes "https://git-scm.com"

  @brew_search
  Scenario: brew search wget returns search results
    * Run brew command in ptyxis and capture result: "brew search wget"
    * brew command exits with status 0
    * brew command output includes "wget"

  @brew_doctor
  Scenario: brew doctor finishes with acceptable status
    * Run brew command in ptyxis and capture result: "brew doctor"
    * brew doctor exits cleanly or only reports warnings

  @brew_install
  Scenario: brew install and uninstall round-trip succeeds
    # cowsay: tiny formula, no C compilation, installs in seconds
    * Run brew command in ptyxis and capture result: "brew install --formula cowsay"
    * brew command exits with status 0
    * Run brew command in ptyxis and capture result: "cowsay bluefin-test"
    * brew command exits with status 0
    * brew command output includes "bluefin-test"
    * Run brew command in ptyxis and capture result: "brew uninstall cowsay"
    * brew command exits with status 0
