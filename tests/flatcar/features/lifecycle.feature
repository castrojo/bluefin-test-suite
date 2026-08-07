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

  @pending @flatcar @ignition
  Scenario: Ignition config is applied on first boot
    # BLOCKED (#704): the flatcar suite is not referenced anywhere in
    # .github/workflows/e2e.yml, so this scenario cannot run in CI.
    # ALSO BLOCKED: the assertions below only prove that a *generic* Ignition
    # run finished — a cleared first-boot marker and "some SSH key exists" are
    # both satisfied by an empty Ignition config with externally provisioned
    # keys. Proving that *this suite's* config was applied needs an artifact
    # uniquely provisioned by it (for example a suite-owned file or hostname),
    # and the Ignition config is supplied by the VM spec in projectbluefin/lab.
    # Unblock: wire flatcar into e2e.yml, land a suite-owned Ignition artifact,
    # assert on it, then drop @pending.
    #
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

  @pending @flatcar @updates @disable
  Scenario: Automatic updates can be disabled via update.conf
    # BLOCKED (#704): the flatcar suite is not referenced anywhere in
    # .github/workflows/e2e.yml, so this scenario cannot run in CI. It mutates
    # /etc/flatcar/update.conf on the VM, so it must not be advertised as
    # active coverage until the suite is actually wired up and its cleanup path
    # has been exercised against a real VM.
    # Unblock: add the flatcar suite to e2e.yml, then drop @pending.
    #
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
