@common @bluefin
Feature: Bluefin common system scripts
  Verifies common-layer helper binaries are present and runnable over SSH.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: ujust lists available tasks
    * Run SSH command: "ujust --list"
    * SSH command return code is "0"
    * Last command output contains "install-"

  Scenario: ublue image info prints image metadata
    * Run SSH command: "command -v ublue-image-info.sh >/dev/null && ublue-image-info.sh || ublue-image-info"
    * SSH command return code is "0"
    * Last command output contains "ghcr.io"

  Scenario: ublue-system-setup is executable
    * Run SSH command: "test -x /usr/bin/ublue-system-setup"
    * SSH command return code is "0"

  Scenario: ublue-user-setup is executable
    * Run SSH command: "test -x /usr/bin/ublue-user-setup"
    * SSH command return code is "0"
