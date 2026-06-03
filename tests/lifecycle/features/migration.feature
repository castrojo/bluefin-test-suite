@migration @lifecycle
Feature: Migration from ublue-os/bluefin to projectbluefin/bluefin
  Validates that users can migrate from the legacy ublue-os/bluefin image
  (built with rpm-ostree / ublue-os/legacy-rechunker) to the new
  projectbluefin/bluefin image (built with chunkah), and can safely roll
  back to the legacy image if needed.

  These scenarios run via .github/workflows/migration-test.yml (workflow_dispatch).
  Set MIGRATION_TARGET env var to override the default target (ghcr.io/projectbluefin/bluefin:stable).

  Required env vars:
    MIGRATION_TARGET  — target image (default: ghcr.io/projectbluefin/bluefin:stable)

  The migration exercises the chunkah OCI layer format transition: the legacy
  image uses rpm-ostree chunked format (ublue-os/legacy-rechunker) while the
  projectbluefin image uses chunkah. A successful switch and rollback confirms
  bootc can handle the format boundary in both directions.

  Background:
    * Bluefin VM is booted and reachable over SSH

@migration @switch
  Scenario: bootc switch migrates from ublue-os/bluefin to projectbluefin/bluefin
    # Pre-condition: confirm we're actually on the legacy source image before switching.
    # This guards against a no-op if the workflow was accidentally invoked on the
    # wrong starting image, which would silently pass without testing the boundary.
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Switch to migration target
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"

  @migration @switch @rollback
  Scenario: Rolling back after migration returns to ublue-os/bluefin
    # Pre-condition: assert source registry before switching.
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Switch to migration target
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    # Verify we landed on the migrated image before attempting rollback.
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"
    * Run SSH command: "sudo bootc rollback"
    * SSH command return code is "0"
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches original image digest
    * Migration source image reference is restored after rollback

  @migration @switch @health
  Scenario: System identity and health are correct after migration
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Switch to migration target
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * bootc status image reference starts with "ghcr.io/projectbluefin/"
    * bootc status image digest is a valid sha256
    * bootc status shows deployment is compatible
    * Run SSH command: "cat /etc/os-release"
    * SSH command return code is "0"
    * os-release reports Fedora Bluefin identity

  @migration @switch @unified_storage
  Scenario: bootc switch with unified storage migrates from ublue-os/bluefin to projectbluefin/bluefin
    # Unified storage places the target image in containers-storage (/var/lib/bootc/storage/overlay)
    # rather than the legacy ostree repo. This lane mirrors the "experimental-unified-storage"
    # lane of the bluespeed 4-lane migration matrix.
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Check unified storage support and skip if unavailable
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Switch to migration target with unified storage
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"
    * Unified storage overlay directory is present on the VM
    * bootc status shows deployment is compatible

  @migration @switch @unified_storage @rollback
  Scenario: Rolling back after unified storage migration returns to ublue-os/bluefin
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Check unified storage support and skip if unavailable
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Switch to migration target with unified storage
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    # Confirm we landed on the migrated image (via unified storage) before rolling back.
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"
    * Unified storage overlay directory is present on the VM
    * Run SSH command: "sudo bootc rollback"
    * SSH command return code is "0"
    * Reboot VM and wait for SSH
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches original image digest
    * Migration source image reference is restored after rollback

  @migration @chunkah
  Scenario: Rollback deployment is preserved and matches legacy source after chunkah migration
    # Uses bootc status .rollback — stronger than counting ostree deployments because
    # it tests the exact field bootc rollback uses, and asserts the legacy digest is
    # correctly preserved across the rechunker format boundary.
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Switch to migration target
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Reboot VM and wait for SSH after migration
    * Run SSH command: "bootc status --format=json"
    * Active image reference contains "projectbluefin/bluefin"
    * bootc status shows rollback deployment is available
    * bootc status rollback deployment matches migration source digest

  @migration @zstd_chunked
  Scenario: bootc switch via podman zstd:chunked migrates from ublue-os/bluefin to projectbluefin/bluefin
    # zstd:chunked lane: pull target into root containers-storage via podman
    # (uses zstd:chunked partial-pull), then switch using the local copy.
    # Requires extra disk space (~10 GB) for the podman-pulled image layers.
    * Run SSH command: "bootc status --format=json"
    * Booted image is from the "ublue-os" registry
    * Capture booted image digest for rollback verification
    * Capture booted image reference as migration source
    * Pull migration target via podman for zstd:chunked transport
    * Switch to migration target via containers-storage transport
    * SSH command return code is "0"
    * Run SSH command: "bootc status --format=json"
    * Staged deployment is present in bootc status
    * Capture staged image digest as upgrade target
    * Reboot VM and wait for SSH after migration
    * Run SSH command: "bootc status --format=json"
    * Active deployment matches upgrade target digest
    * Active image reference contains "projectbluefin/bluefin"
