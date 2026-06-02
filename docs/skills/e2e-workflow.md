# Reusable E2E Workflow — GNOME in QEMU

Load when: integrating the testsuite into another repo's CI (e.g. `projectbluefin/dakota`), debugging e2e workflow failures, or understanding how the QEMU boot pipeline works.

## What it is

`projectbluefin/testsuite/.github/workflows/e2e.yml` is a reusable `workflow_call` workflow.  
It boots a bootc OCI image in a KVM-accelerated QEMU VM on `ubuntu-latest`, starts a GNOME session (via GDM autologin), and runs behave suites via qecore-headless.

**No self-hosted runners. Pure GitHub Actions.**

## How to call it from another repo

```yaml
# .github/workflows/e2e.yml  (in the consumer repo)
name: E2E tests

on:
  pull_request:
  workflow_dispatch:

jobs:
  e2e:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
    with:
      image: ghcr.io/projectbluefin/dakota:latest
      suites: smoke
```

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `image` | string | `ghcr.io/projectbluefin/dakota:latest` | OCI image to test (must be a bootc/ostree image) |
| `suites` | string | `smoke` | Comma-separated suite names: `smoke`, `developer`, `dx`, `software`, `vanilla-gnome`, `bazzite`, `common` |
| `skip_native_apps` | boolean | `false` | When `true`, skips `@native_app` scenarios (Flatpak apps that may not be installed in all variants) |

Multiple suites run as a matrix (parallel jobs):

```yaml
with:
  image: ghcr.io/projectbluefin/myimage:pr-123
  suites: smoke,developer
```

## Pipeline stages

1. **Resolve matrix** — splits `suites` CSV into a JSON array for the strategy matrix
2. **Free disk space** — uses `ublue-os/remove-unwanted-software` to reclaim ~20 GB
3. **Enable KVM** — udev rule for `/dev/kvm` access
4. **Install QEMU + pull OCI image** — parallel: `apt-get install qemu-system-x86` while `podman pull` runs in background
5. **Install OCI image to disk** — `bootc install to-disk` writes ostree layers to a 30 GB raw disk; bootupd failure is expected and caught (direct QEMU kernel boot is used instead of OVMF/systemd-boot)
6. **Configure disk** — mounts the raw disk and:
   - Copies `vmlinuz` + `initramfs.img` to workspace for direct kernel boot
   - Creates `bluefin-test` user (UID 1001)
   - Injects SSH public key
   - Pre-bakes GDM autologin
   - Enables sshd, pre-generates SSH host keys
   - Masks irrelevant services (bluetooth, cups, avahi…)
   - Sets `PermitUserEnvironment yes` for AT-SPI env forwarding
7. **Boot VM** — `qemu-system-x86_64` with KVM, 4 GB RAM, 4 vCPUs, `virtio-gpu`, forwarded SSH on port 2222; daemonized
8. **Wait for SSH** — polls port 2222 up to 5 minutes
9. **Wait for GNOME session** — polls `/run/user/1001/wayland-0` up to 3 minutes
10. **Install Python test stack** — pip installs `qecore behave dogtail python-uinput` inside the VM; captures `DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` into `/tmp/session.env`
11. **Copy testsuite + run behave** — SCPs `tests/<suite>` and `tests/shared` to VM; runs `qecore-headless behave … --format json.pretty`
12. **Write job summary** — parses `results.json`, writes pass/fail table + failed scenario list to GitHub Step Summary
13. **Upload artifacts** — `e2e-results-<image-slug>-<suite>` (results JSON + text + `artifact-metadata.json`, 30 days) and `vm-serial-log-<image-slug>-<suite>` (3 days)

## Image requirements

The OCI image under test **must**:

- Be a bootc/ostree image (`bootc install to-disk` compatible)
- Include GNOME + GDM
- Include `gnome-ponytail-daemon` (bridges AT-SPI to Wayland; required for dogtail)
- Have `python3` available for pip bootstrap

The workflow injects the test user, SSH keys, and autologin config at disk-prep time — nothing needs to be baked into the image for those.

## Artifacts

| Artifact | Content | Retention |
|----------|---------|-----------|
| `e2e-results-<image-slug>-<suite>` | `results.json` (behave JSON), `results.txt` (pretty output), `artifact-metadata.json` (image + suite metadata) | 30 days |
| `vm-serial-log-<image-slug>-<suite>` | QEMU serial console output | 3 days |

The serial log is always uploaded (even on failure) — it's the primary debug tool when the VM doesn't boot or SSH never comes up.

## Debugging failures

### SSH never became ready

Check the serial log artifact. Common causes:
- ostree deployment missing: `bootc install` exited before writing layers (check for `ERROR: ostree deployment missing` in the install step)
- Kernel args wrong: `root=UUID=…` mismatch — verify `ROOT_UUID` in the install step output
- `selinux=0` is set, so SELinux policy isn't the cause

### GNOME session did not start

Check the serial log for GDM/systemd errors. Common causes:
- `gnome-ponytail-daemon` missing from the image
- GDM failing due to a missing display driver (virtio-gpu should always work)

The "Wait for GNOME session" step runs `journalctl -u gdm --no-pager -n 50` on timeout — look for that in the step output.

### behave: UndefinedStep

The testsuite is checked out sparse (`tests/<suite>` + `tests/shared` only). If the suite imports from a path outside those two directories, the copy will be incomplete. Verify the suite's `environment.py` imports.

### Timeout (90 min job limit)

The install + configure step is the heaviest (~10–15 min depending on image size). If hitting the limit, reduce suite scope or check if the image pull is unusually large.

## Known limitations

- `bootupd` is expected to fail (not in bootc images by default) — the workflow catches this and uses direct kernel boot. This is intentional.
- No display output: `virtio-gpu` with `-display none`. Tests must use AT-SPI (dogtail/qecore), not pixel-based assertions.
- No GPU acceleration for GL/Vulkan in GHA runners. Hardware-specific tests require SSH-mode suites not yet in the GHA action (epics #43/#44).
- Partition layout assumes `p3` is the root partition. Tested against standard Anaconda/bootc partition tables. Non-standard layouts may break the disk-configure step.
