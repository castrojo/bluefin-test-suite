@common @bluefin
Feature: Bluefin common shell environment
  Ensures the common layer exposes the expected shell tooling and environment.

  Background:
    * Bluefin VM is booted and reachable over SSH

  # zsh/fish are installed as RPMs but fail with "command not found" in the
  # CI bluefin-test user environment — PATH issue under investigation.
  # See: https://github.com/projectbluefin/testsuite/issues/209
  @quarantine
  Scenario: zsh is available
    * Run SSH command: "zsh --version"
    * SSH command return code is "0"

  @quarantine
  Scenario: fish is available
    * Run SSH command: "fish --version"
    * SSH command return code is "0"

  Scenario: System environment file is present
    * Run SSH command: "cat /etc/environment"
    * SSH command return code is "0"
    * SSH command output is not empty

  # ── Modern CLI tools (common layer) ──────────────────────────────────────
  # These tools are installed by brew-setup.service (cli.Brewfile) which is
  # masked in CI. Pre-baking them into the OCI image is tracked in:
  # https://github.com/projectbluefin/testsuite/issues/209

  @quarantine
  Scenario: fzf fuzzy finder is available
    * Run SSH command: "fzf --version"
    * SSH command return code is "0"

  @quarantine
  Scenario: bat (modern cat) is available
    * Run SSH command: "bat --version 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/bat --version 2>/dev/null || batcat --version 2>/dev/null || echo missing"
    * SSH command output is not empty
    * SSH command output does not contain "missing"

  @quarantine
  Scenario: eza (modern ls) is available
    * Run SSH command: "eza --version 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/eza --version"
    * SSH command return code is "0"

  @quarantine
  Scenario: fd (modern find) is available
    * Run SSH command: "fd --version 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/fd --version"
    * SSH command return code is "0"

  @quarantine
  Scenario: ripgrep is available
    * Run SSH command: "rg --version 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/rg --version"
    * SSH command return code is "0"

  @quarantine
  Scenario: starship prompt binary is present
    * Run SSH command: "starship --version 2>/dev/null || /home/linuxbrew/.linuxbrew/bin/starship --version 2>/dev/null"
    * SSH command return code is "0"
