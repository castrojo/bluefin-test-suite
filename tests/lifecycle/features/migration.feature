@migration @lifecycle
Feature: Migration from ublue-os/bluefin to projectbluefin/bluefin
  Validates that users can migrate from the legacy ublue-os/bluefin image
  (built with rpm-ostree / ublue-os/legacy-rechunker) to the new
  projectbluefin/bluefin image (built with chunkah), and can safely roll
  back to the legacy image if needed.

  These scenarios are designed to run with:
    image: ghcr.io/ublue-os/bluefin:latest
  via the projectbluefin/actions upgrade-test workflow:
    uses: projectbluefin/actions/.github/workflows/upgrade-test.yml@v1
    with:
      image: ghcr.io/ublue-os/bluefin:latest
      suites: lifecycle

  The migration exercises the chunkah OCI layer format transition: the legacy
  image uses rpm-ostree chunked format (ublue-os/legacy-rechunker) while the
  projectbluefin image uses chunkah. A successful switch and rollback confirms
  bootc can handle the format boundary in both directions.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @migration @switch
  Scenario: bootc switch migrates from ublue-os/bluefin to projectbluefin/bluefin
    # Confirms the core migration path: legacy-rechunker → chunkah image.
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Run SSH command: "sudo bootc switch ghcr.io/projectbluefin/bluefin:latest"
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"

  @migration @switch @rollback
  Scenario: Rolling back after migration returns to ublue-os/bluefin
    # Confirms users are not stranded if they need to revert.
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Run SSH command: "sudo bootc switch ghcr.io/projectbluefin/bluefin:latest"
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active image reference contains "projectbluefin/bluefin"
    * Run SSH command: "sudo bootc rollback"
    * SSH command return code is "0"
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches original image digest
    * Migration source image reference is restored after rollback

  @migration @switch @health
  Scenario: System identity and health are correct after migration
    # After switching to chunkah image the OS must still report Fedora Bluefin
    # identity and bootc must see a clean, pinnable deployment.
    * Run SSH command: "sudo bootc switch ghcr.io/projectbluefin/bluefin:latest"
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * bootc status image reference starts with "ghcr.io/projectbluefin/"
    * bootc status image digest is a valid sha256
    * bootc status shows deployment is compatible
    * Run SSH command: "cat /etc/os-release"
    * SSH command return code is "0"
    * os-release reports Fedora Bluefin identity

  @migration @chunkah
  Scenario: Two deployments are present after chunkah migration — rollback is available
    # ostree must keep both the legacy-rechunker deployment and the new chunkah
    # deployment so the rollback path above is always available immediately
    # after migration without requiring a second boot.
    * Run SSH command: "sudo bootc switch ghcr.io/projectbluefin/bluefin:latest"
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Reboot VM and wait for SSH
    * Run SSH command: "sudo ostree admin status"
    * SSH command return code is "0"
    * ostree status shows two deployments
    * Run SSH command: "bootc status --format=json"
    * Active image reference contains "projectbluefin/bluefin"
    * bootc status shows deployment is compatible
