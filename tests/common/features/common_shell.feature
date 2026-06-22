@common @bluefin
Feature: Bluefin common shell environment
  Ensures the common layer exposes the expected shell tooling and environment.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @requires_brew
  Scenario: zsh is available
    * Run SSH command: "zsh --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: fish is available
    * Run SSH command: "fish --version"
    * SSH command return code is "0"

  Scenario: System environment file is present
    * Run SSH command: "cat /etc/environment"
    * SSH command return code is "0"
    * SSH command output is not empty

  # ── Modern CLI tools (common layer) ──────────────────────────────────────
  # These tools are installed by brew-setup.service on first login. In CI,
  # brew-setup is masked for boot speed; the e2e workflow installs them
  # explicitly before the common suite runs.

  @requires_brew
  Scenario: fzf fuzzy finder is available
    * Run SSH command: "fzf --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: bat (modern cat) is available
    * Run SSH command: "bat --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: eza (modern ls) is available
    * Run SSH command: "eza --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: fd (modern find) is available
    * Run SSH command: "fd --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: ripgrep is available
    * Run SSH command: "rg --version"
    * SSH command return code is "0"

  @requires_brew
  Scenario: starship prompt binary is present
    * Run SSH command: "starship --version"
    * SSH command return code is "0"

  @common @requires_brew
  Scenario: zsh sources system configuration without errors
    * Run SSH command: "zsh -c 'exit 0' 2>&1"
    * SSH command return code is "0"

  @common
  Scenario: bash login shell sources profile.d without errors
    * Run SSH command: "bash -l -c 'exit 0' 2>&1"
    * SSH command return code is "0"

  @common @requires_brew
  Scenario: starship prompt binary initializes in bash
    * Run SSH command: "bash -c 'eval \"$(starship init bash 2>/dev/null)\" && echo ok' 2>&1"
    * SSH command output contains "ok"
