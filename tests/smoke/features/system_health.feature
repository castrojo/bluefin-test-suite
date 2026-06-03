@smoke_suite
Feature: System health smoke checks
  Validates the booted image is healthy, identifiable as Bluefin, and has
  enough free root filesystem space for normal operation.

  @health @systemd @sla_10s
  Scenario: No failed systemd units at boot
    * No failed systemd units at boot

  @health @journal @sla_10s
  Scenario: No critical journal errors at boot
    * No critical kernel errors in journal

  @health @bluefin
  Scenario: Bluefin image identity is present in /etc/os-release
    * Bluefin image identity is present in os-release

  @health @bluefin
  Scenario: bootc status shows a known image reference
    * bootc status shows a valid image reference

  @health @storage
  Scenario: Writable system storage has more than 20 percent free space
    * Writable system storage has at least "20" percent free space

  @health @network
  Scenario: External DNS resolves external hosts
    * External DNS resolves external hosts

  @system_health @ujust @sla_10s
  Scenario: ujust is available and lists at least one task
    * ujust is on PATH and returns exit 0
    * ujust --list prints at least one task

  # ujust report --confirm is not yet implemented in any current image variant.
  # The skip logic misdetects the "wrong argument count" error from just as a
  # missing-recipe skip, causing false failures. Re-enable when --confirm mode lands.
  # See: https://github.com/projectbluefin/bluefin/issues/240
  @system_health @ujust @ujust_report @quarantine
  Scenario: ujust report confirm validation rejects invalid inputs
    * ujust is on PATH and returns exit 0
    * ujust report --confirm rejects non-integer issue number
    * ujust report --confirm without issue number prints error
