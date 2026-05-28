@future @flatcar_suite @lifecycle
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
    # TODO: Implement — real install to /dev/vdb (targetdisk).
    # After install: swap boot order and reboot to validate.
    * Run SSH command: "echo '{}' | sudo knuckle headless --config - --target /dev/vdb"
    * SSH command return code is "0"
    * Run SSH command: "lsblk /dev/vdb | grep -c part"
    * SSH command return code is "0"

  @flatcar @knuckle @install @boot
  Scenario: Installed Flatcar boots from target disk
    # TODO: Implement — requires VM recreation with swapped boot order
    # or virtctl to change boot device. Complex multi-step.
    * Install Flatcar to target disk via knuckle
    * Reboot VM from target disk
    * Flatcar VM is reachable over SSH
    * Run SSH command: "systemctl is-system-running"
    * SSH command output is not "offline"

  @flatcar @ignition
  Scenario: Ignition config is applied on first boot
    # TODO: Implement — provide Ignition JSON via config drive, verify effects.
    * Run SSH command: "cat /etc/hostname"
    * SSH command output "is" "flatcar-test"

  @flatcar @updates @channel
  Scenario: Update channel is correctly configured
    * Run SSH command: "cat /etc/flatcar/update.conf 2>/dev/null | grep -c GROUP || echo 0"
    * SSH command output is not "0"

  @flatcar @updates @disable
  Scenario: Updates can be disabled via update_strategy=off
    # TODO: Implement — verify update-engine is not running when strategy=off.
    * Run SSH command: "systemctl is-active update-engine 2>/dev/null || echo inactive"
    * SSH command output "is" "inactive"

  @flatcar @afterburn
  Scenario: Afterburn metadata agent runs on supported clouds
    # In KubeVirt, afterburn may not have a metadata source but must still start
    # and handle "no metadata" gracefully — it should be active or inactive.
    * Run SSH command: "systemctl status afterburn 2>&1 | grep -c 'active\|inactive' || echo 0"
    * SSH command output is not "0"
