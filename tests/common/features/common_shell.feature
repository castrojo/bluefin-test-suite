@common @bluefin
Feature: Bluefin common shell environment
  Ensures the common layer exposes the expected shell tooling and environment.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: zsh is available
    * Run SSH command: "zsh --version"
    * SSH command return code is "0"

  Scenario: fish is available
    * Run SSH command: "fish --version"
    * SSH command return code is "0"

  Scenario: System environment file is present
    * Run SSH command: "cat /etc/environment"
    * SSH command return code is "0"
    * SSH command output is not empty
