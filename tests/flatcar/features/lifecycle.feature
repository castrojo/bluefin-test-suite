@flatcar_suite @lifecycle
Feature: Flatcar/KnuckleOS installation and update lifecycle
  Validates the full knuckle install flow (not just dry-run) and
  Flatcar's update channel behavior.
  Runner: plain SSH behave from Argo runner pod.

  # Requires: Two-disk VM (rootdisk=live, targetdisk=install target).
  # The provision-flatcar-vm template already creates this layout.
  # See QA-REVIEW.md Epic E09.

  Background:
    * Flatcar VM is reachable over SSH

  @flatcar @knuckle @install
  Scenario: knuckle headless installs Flatcar to target disk
    * Install Flatcar to target disk via knuckle
    * Flatcar target disk has partitions

  @future @flatcar @knuckle @install @boot
  Scenario: Installed Flatcar boots from target disk
    # Requires VM recreation with swapped boot order or virtctl boot-device changes.
    * Install Flatcar to target disk via knuckle
    * Reboot VM from target disk
    * Flatcar VM is reachable over SSH
    * Run SSH command: "systemctl is-system-running"
    * SSH command output is not "offline"

  @future @flatcar @ignition
  Scenario: Ignition config is applied on first boot
    # Requires providing Ignition JSON via config drive and verifying the applied state.
    * Run SSH command: "cat /etc/hostname"
    * SSH command output "is" "flatcar-test"

  @flatcar @updates @channel
  Scenario: Update channel is correctly configured
    * Flatcar update channel is configured

  @future @flatcar @updates @disable
  Scenario: Updates can be disabled via update_strategy=off
    # Requires explicit update_strategy=off provisioning before asserting service state.
    * Run SSH command: "systemctl is-active update-engine 2>/dev/null || echo inactive"
    * SSH command output "is" "inactive"

  @flatcar @afterburn
  Scenario: Afterburn metadata agent runs on supported clouds
    # In KubeVirt, afterburn may not have a metadata source but must still start
    # and handle "no metadata" gracefully — it should be active or inactive.
    * Afterburn service is available
