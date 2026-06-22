@smoke_suite @dakota_only
Feature: Dakota desktop identity
  Validates Dakota-specific desktop components that differ from Bluefin and
  must remain present for basic usability.

  @dakota_only
  Scenario: ghostty is available as Dakota's terminal
    * Run and save command output: "ghostty --version"
    * Return code of last command output "is" "0"

  @dakota_only
  Scenario: sudo-rs provides the sudo command
    * Run and save command output: "sudo --version"
    * Return code of last command output "is" "0"
    * Last command output "contains" "sudo-rs"

  @dakota_only
  Scenario: Homebrew is preinstalled
    * Run and save command output: "brew --version"
    * Return code of last command output "is" "0"

  @dakota_only
  Scenario: distrobox is available
    * Run and save command output: "distrobox --version"
    * Return code of last command output "is" "0"

  @dakota_only
  Scenario: Bazaar Integration extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * GNOME extension "bazaar-integration@kolunmi.github.io" is enabled
