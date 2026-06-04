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
| `suites` | string | `smoke` | Comma-separated suite names: `smoke`, `developer`, `dx`, `software`, `vanilla-gnome`, `bazzite`, `common`, `lifecycle` |
| `skip_native_apps` | boolean | `false` | When `true`, skips `@native_app` scenarios (Flatpak apps that may not be installed in all variants) |
| `screenshot_flatpaks` | string | `""` | Comma-separated Flatpak app IDs to launch-and-screenshot after the test run. See [Flatpak screenshot gallery](../flatpak-screenshots.md) for full details. |
| `chunked_enabled` | boolean | `false` | When `true`, sets `ZSTD_CHUNKED=true` so `@zstd_chunked` lifecycle scenarios run. Enable once the image ships `tar+zstd` OCI layers. |
| `test_ref` | string | `main` | `projectbluefin/testsuite` ref to check out for test content. Wrapper workflows that start from `workflow_dispatch` should resolve this on the caller side with `${{ github.event.inputs.test_ref || github.ref_name }}`. |

Multiple suites run as a matrix (parallel jobs):

```yaml
with:
  image: ghcr.io/projectbluefin/myimage:pr-123
  suites: smoke,developer
```

### Lifecycle suite — special execution model

The `lifecycle` and `common` suites do **not** run inside the VM container. They run from the GHA runner via SSH — `lifecycle` because the test process must survive the mid-upgrade reboot; `common` because it only needs dconf/shell access, not a full AT-SPI bus. The pipeline branches at the "Run behave suite" step:

```
if [[ "${SUITE}" == "common" || "${SUITE}" == "lifecycle" ]]
  → ssh bluefin-test@localhost -p 2222 python3 behave_retry.py ...   (from runner)
else
  → podman run --rm ghcr.io/projectbluefin/testsuite:runner \
      "python3 behave_retry.py ..."                                   (inside VM)
```

After the lifecycle suite finishes, a separate "Capture post-upgrade screenshot" step re-SSHes with `ControlMaster=no` (fresh connection after reboot), waits up to 60 s for the Wayland socket at `/run/user/1001/wayland-0`, and calls `org.gnome.Shell.Screenshot` via gdbus. The screenshot is saved to `results/screenshot_lifecycle_upgrade_final.png` and uploaded in the `e2e-results-*` artifact.

**Preferred manual trigger:** dispatch `upgrade-test.yml` in `projectbluefin/actions` — it calls `e2e.yml` cross-repo (which works). Do NOT dispatch `manual.yml` in this repo for lifecycle runs (see ops.md "manual.yml startup_failure").

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
10. **Load runner container + install test stack** — pipes the pre-built `ghcr.io/projectbluefin/testsuite:runner` container into the VM via `podman save | ssh podman load` (rootless, as `bluefin-test`). Before loading, ensures `bluefin-test` has `/etc/subuid`/`/etc/subgid` entries and runs `podman system migrate`. Then: loads kernel module (`uinput`), sets device permissions, copies SSH key for @plain_ssh scenarios, captures GNOME session environment (`DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`, etc.) into `/tmp/session.env`.
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

## Screenshots and GHCR artifacts

Every e2e run produces a desktop screenshot at end-of-run as visual proof of a working GNOME session.

### Desktop screenshot — two capture paths

**Primary path (in-VM):** `take_fastfetch_screenshot()` is called in `after_all` for every GUI suite. It uses `gnome-screenshot` or `grim` inside the VM and writes to `results/desktop_screenshot.png`.

**Fallback path (QEMU monitor screendump):** If no in-VM screenshot lands (behave crashed, container never started, AT-SPI unavailable), `e2e.yml` captures the QEMU VGA framebuffer directly via the monitor socket at `/tmp/qemu-monitor.sock`. QEMU maintains this framebuffer internally even with `-display none` because mutter uses bochs-drm (card1) as the KMS device, which maps to the VGA framebuffer. The screendump is converted PPM→PNG via Python stdlib (`tests/shared/qemu_screendump.py`).

If **both** paths fail (QEMU monitor socket missing or empty framebuffer), the "Promote desktop screenshot" step fails loud — a missing screenshot from a non-`common` suite is treated as a job failure, not a silent pass.

### Desktop screenshot distribution

After the behave suite finishes, `take_fastfetch_screenshot()` is called in `after_all` for every GUI suite. The screenshot is taken in-VM via AT-SPI/Wayland. If `after_all` was not reached (e.g. the runner container failed to start), the GHA runner falls back to a QEMU monitor screendump: `sudo python3 tests/shared/qemu_screendump.py` sends a `screendump` command to `/tmp/qemu-monitor.sock` (opened at QEMU boot) and converts the PPM output to PNG using the Python stdlib. The "Promote desktop screenshot" step fails loud with `::error::` if neither source produces a file — that failure is intentional and means the container never loaded or behave exited before `after_all`.

The screenshot is:

1. Uploaded to the `e2e-results-*` artifact (as `desktop_screenshot.png` or `screenshot_<suite>_fastfetch_endofrun.png`)
2. Rendered inline in the **GitHub Actions job summary**
3. Pushed to GHCR as an OCI artifact:

| Tag | Meaning |
|-----|---------|
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:latest` | Most recent run (any suite) |
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:<suite>-latest` | Most recent run for that suite, e.g. `:smoke-latest` |
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:<short-sha>` | Immutable per-commit tag |

Pull the latest screenshot locally:
```bash
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:smoke-latest
```

### Flatpak screenshot gallery

Set `screenshot_flatpaks` to capture per-app screenshots useful for app authors:

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/projectbluefin/bluefin:testing
  suites: smoke
  screenshot_flatpaks: "org.gnome.Calculator,io.github.kolunmi.Bazaar"
```

Each app is launched, held for 3 seconds, then captured. Results pushed to:
`ghcr.io/projectbluefin/testsuite/desktop-screenshot:flatpak-<slug>-latest`

See [`docs/flatpak-screenshots.md`](../flatpak-screenshots.md) for full documentation.

## Artifacts

| Artifact | Content | Retention |
|----------|---------|-----------|
| `e2e-results-<image-slug>-<suite>` | `results.json` (behave JSON), `results.txt` (pretty output), `artifact-metadata.json` (image + suite metadata), `screenshot_lifecycle_upgrade_final.png` (lifecycle only) | 30 days |
| `vm-serial-log-<image-slug>-<suite>` | QEMU serial console output | 3 days |

The serial log is always uploaded (even on failure) — it's the primary debug tool when the VM doesn't boot or SSH never comes up.

## Debugging failures

### podman load exits 125 (all GUI suites fail at "Load runner container into VM")

**Root cause:** `bluefin-test` lacks `/etc/subuid`/`/etc/subgid` entries. The Fedora 44 runner base image has a layer with `gid=12` (mail group) for `/var/spool/mail`. Rootless podman can't map this gid without subgid entries.

**Evidence:** Look for `lchown /var/spool/mail: invalid argument` in the "Load runner container into VM" step log.

**Fix:** The `e2e.yml` "Load runner container into VM" step now adds the entries and runs `podman system migrate` before loading. If you see this on an older branch, cherry-pick PR #224.

### behave crashes with PermissionError: [Errno 13] at ''

**Root cause:** Python 3.14 sets `sys.executable = ''` inside podman containers with `--pid=host`. Old `behave_retry.py` passed `sys.executable` directly to `subprocess.run`.

**Evidence:** Traceback in the "Run behave suite" step log ending at `subprocess.run(['', '-m', 'behave', ...])`.

**Fix:** `_find_python()` in `tests/shared/behave_retry.py` resolves a real interpreter via `shutil.which`. If you see this, the tests are being checked out from `main` (which lacks the fix) rather than the fix branch. Check `test_ref` in the run inputs.

### behave crashes with gi.RepositoryError: Typelib file for namespace 'xlib' not found

**Root cause:** `gobject-introspection` is not installed in the runner container. Fedora 44 + `--setopt=install_weak_deps=0` skips it even though `python3-gobject` depends on it weakly.

**Fix:** Rebuild the runner container after adding `gobject-introspection` to `container/Containerfile.runner`. Dispatch `build-runner.yml` to push a new `ghcr.io/projectbluefin/testsuite:runner`.

### qecore-headless exits with "pgrep: command not found"

**Root cause:** `procps-ng` is not in the runner container.

**Fix:** Same as above — add `procps-ng` to `Containerfile.runner` and rebuild.

### All AT-SPI calls silently fail / KeyError('XDG_SESSION_TYPE')

**Root cause:** `XDG_SESSION_TYPE` and `XDG_SESSION_DESKTOP` are not forwarded to the podman container. qecore-headless can't read them from `/proc/<pid>/environ` inside the container (permission denied), so it enters `__unavailable__` mode.

**Fix:** Add `-e XDG_SESSION_TYPE=wayland -e XDG_SESSION_DESKTOP=gnome` to the `podman run` call in `e2e.yml`, and write those same vars into `/tmp/session.env` before starting the container.

### Tests always run from main regardless of dispatched branch

**Root cause:** `github.ref_name` inside a `workflow_call` reusable workflow always resolves to the default branch (`main`). If `e2e.yml` uses it directly as the test checkout ref, it always pulls from `main`.

**Fix:** Pass `test_ref` through the `workflow_dispatch` caller (`manual.yml`, `migration-test.yml`, or another wrapper) using `github.ref_name` on the **workflow_dispatch** side (where it correctly reflects the dispatched branch), then forward it as an input to `e2e.yml`. Inside `e2e.yml`, the checkout must use `inputs.test_ref` directly — never `github.ref_name`. See ops.md "test_ref and github.ref_name" for the exact pattern.

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

## Consumer constraints — what you cannot do from the reusable action

When calling this workflow from another repo, the following are explicitly banned:

- **No RPM installs** — do not add `dnf install` or `rpm -i` steps to consumer workflows or to the action inputs (`setup_script`). The test VM is a fully-baked bootc image; package mutations break repeatability and may conflict with the image's ostree deployment. Use Flatpak installs or pre-bake packages into the image.
- **No `apt install` in test steps** — the GHA runner uses `ubuntu-latest` for QEMU hosting only; apt installs in test steps (as opposed to the infrastructure setup) are not permitted.
- **No VM tuning inputs** — do not request inputs for CPU/RAM/kernel params. The pipeline runs on GitHub-hosted runners; the VM spec is fixed.

## Known limitations

- `bootupd` is expected to fail (not in bootc images by default) — the workflow catches this and uses direct kernel boot. This is intentional.
- No display output: `virtio-gpu` with `-display none`. Tests must use AT-SPI (dogtail/qecore), not pixel-based assertions.
- No GPU acceleration for GL/Vulkan in GHA runners. Hardware-specific tests require SSH-mode suites not yet in the GHA action (epics #43/#44).
- Partition layout assumes `p3` is the root partition. Tested against standard Anaconda/bootc partition tables. Non-standard layouts may break the disk-configure step.
