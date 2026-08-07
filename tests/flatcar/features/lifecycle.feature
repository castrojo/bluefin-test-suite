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
    # BLOCKED: the KubeVirt VM must boot /dev/vdb instead of the live rootdisk.
    # Boot-device ordering lives in the VM spec, which is owned by
    # projectbluefin/lab, not this repo. Without it a reboot silently returns to
    # the live disk and this scenario would pass while testing nothing.
    # Unblock: lab-side boot-order/virtctl support, then drop @future.
    * Install Flatcar to target disk via knuckle
    * Reboot VM from target disk
    * Flatcar VM is reachable over SSH
    * Run SSH command: "systemctl is-system-running"
    * SSH command output is not "offline"

  @flatcar @ignition
  Scenario: Ignition config is applied on first boot
    # Ignition runs in the initramfs, so its units are not visible from the
    # booted root. The observable proof of a successful run is the ESP
    # first-boot marker being deleted, plus the provisioned user's SSH keys
    # (which are what this suite authenticates with).
    * Flatcar ESP is mounted at /boot
    * Ignition first-boot marker is cleared
    * Ignition-provisioned SSH keys are present for the test user

  @flatcar @updates @channel
  Scenario: Update channel is correctly configured
    * Flatcar update channel is configured

  @flatcar @updates @disable
  Scenario: Automatic updates can be disabled via update.conf
    # Flatcar's supported disable switch is an invalid SERVER value in
    # /etc/flatcar/update.conf; upstream explicitly discourages masking
    # update-engine because that breaks manual updates. The original stub
    # asserted `update_strategy=off`, which is not a Flatcar setting.
    * Flatcar update config is backed up
    * Automatic updates are disabled via update.conf
    * Flatcar automatic updates are reported as disabled
    * update-engine restarts cleanly
    * Flatcar update config is restored
    * Flatcar update channel is configured

  @flatcar @afterburn
  Scenario: Afterburn metadata agent runs on supported clouds
    # In KubeVirt, afterburn may not have a metadata source but must still start
    # and handle "no metadata" gracefully — it should be active or inactive.
    * Afterburn service is available
