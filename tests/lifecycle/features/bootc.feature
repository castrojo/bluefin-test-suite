@lifecycle @bluefin
Feature: bootc upgrade and rollback lifecycle
  Validates that atomic updates via bootc work correctly on Bluefin.
  Tests the most critical user journey: upgrade, verify, rollback.
  Runner: plain SSH behave (no qecore — no GUI interaction needed).

  # Requires: a second image tag to upgrade TO (pinned digest or test tag).
  # Requires: VM reboot capability (virtctl restart or guest systemctl reboot).
  # See QA-REVIEW.md Epic E06 for full design.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @lifecycle @status
  Scenario: bootc status shows expected image and is not dirty
    # TODO: Implement — validate image ref, digest, and staged deployment state.
    * Run SSH command: "bootc status --format=json"
    * SSH command return code is "0"

  @lifecycle @upgrade
  Scenario: bootc upgrade stages a new deployment
    # TODO: Implement — run bootc upgrade, verify staged deployment exists.
    # Needs: target image with known different digest than current.
    * Run SSH command: "sudo bootc upgrade"
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status

  @lifecycle @upgrade @reboot
  Scenario: VM boots into upgraded deployment after reboot
    # TODO: Implement — trigger reboot, wait for SSH, validate new deployment active.
    # Requires: Argo step that calls virtctl restart + SSH wait loop.
    * Run SSH command: "sudo bootc upgrade"
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest

  @lifecycle @rollback
  Scenario: bootc rollback reverts to previous deployment
    # TODO: Implement — after upgrade+reboot, rollback and reboot again.
    * Run SSH command: "sudo bootc rollback"
    * SSH command return code is "0"
    * Reboot VM and wait for SSH
    * Active deployment matches original image digest

  @lifecycle @switch
  Scenario: bootc switch transitions to a different variant
    # TODO: Implement — switch from standard to DX (or vice versa).
    # Requires: golden disk of source variant, target variant image available.
    * Run SSH command: "sudo bootc switch ghcr.io/ublue-os/bluefin-dx:latest"
    * SSH command return code is "0"
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active image reference contains "bluefin-dx"

  @lifecycle @etc_merge
  Scenario: /etc customizations survive upgrade
    # TODO: Implement — write a file to /etc, upgrade, reboot, verify file persists.
    * Run SSH command: "echo 'testsuite-marker' | sudo tee /etc/bluefin-test-marker"
    * Run SSH command: "sudo bootc upgrade"
    * Reboot VM and wait for SSH
    * Run SSH command: "cat /etc/bluefin-test-marker"
    * SSH command output "is" "testsuite-marker"

  @lifecycle @ostree
  Scenario: ostree admin status reports correct deployments
    # TODO: Implement — validate ostree deployment list matches bootc state.
    * Run SSH command: "ostree admin status"
    * SSH command return code is "0"
    * ostree status shows two deployments
