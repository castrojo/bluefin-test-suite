---
name: e2e-workflow
description: "Use when integrating or debugging the reusable E2E workflow, changing QEMU boot pipeline steps, or adjusting GitHub Actions cache and workflow_call behavior."
metadata:
  type: reference
  context7-sources:
    - /websites/github_en_actions
    - /actions/cache
    - /bootc-dev/bootc
---

# Reusable E2E Workflow — GNOME in QEMU

Load when: integrating the testsuite into another repo's CI (e.g. `projectbluefin/dakota`), debugging e2e workflow failures, or understanding how the QEMU boot pipeline works.

## When to Use

- Changing `.github/workflows/e2e.yml` inputs, matrix behavior, job timeouts, or artifact handling
- Debugging OCI image pulls, QEMU boot/setup stages, or reusable `workflow_call` behavior
- Adding or troubleshooting GitHub Actions caching for the root podman image store

## When NOT to Use

- Writing or debugging behave steps inside `tests/**` — use `behave.md`, `gnome.md`, or `bootc.md`
- Changing Argo/KubeVirt lab infrastructure — that belongs in `projectbluefin/testing-lab`
- Updating repo-wide contribution policy — use `contributing.md`, `human-gates.md`, or `skill-drift.md`

## Core Process

1. Confirm the change belongs in the reusable workflow and not in a consumer repo or infra repo.
2. Preserve hard CI rules: SHA-pin external actions, keep `workflow_call` semantics stable, and respect human gates for interface changes.
3. For OCI pull performance work, cache the root podman store (`/var/lib/containers/storage`) because `e2e.yml` pulls with `sudo podman`.
4. Validate the workflow file parses, then run the repo's required local checks before committing.
5. Write back any non-obvious workflow pattern discovered during the change in this skill file.

## What it is

`projectbluefin/testsuite/.github/workflows/e2e.yml` is a reusable `workflow_call` workflow.  
It boots a bootc OCI image in a KVM-accelerated QEMU VM on `ubuntu-latest`, starts a GNOME session (via GDM autologin), and runs behave suites via qecore-headless.

**No self-hosted runners. Pure GitHub Actions.**

## PR validation sidecars

`pr-validate.yml` now includes a `quarantine-age` job that runs `python3 scripts/check_quarantine_age.py`.
The script walks `git log --follow` history for each `@quarantine` scenario and fails once the tag ages past the configured threshold.
Because the check needs full history, the checkout step for that job must use `fetch-depth: 0`.
Rollouts should start with `--grace-days` in CI (currently `--grace-days 30`) so the threshold can harden without instantly blocking every PR.

`e2e.yml` reuses the same script for job-summary reporting via `python3 scripts/check_quarantine_age.py --json`.
That summary path is informational only, but it still needs the same prerequisites: the workflow checkout must include `scripts/check_quarantine_age.py`, the `tests/` tree, and full git history (`fetch-depth: 0`) or the age calculations will be incomplete.

## How to call it from another repo

**Pin to `@v1`** — testsuite auto-updates v1 to main after every merge. Renovate does not need to manage this SHA.

```yaml
# .github/workflows/run-testsuite.yml  (in the consumer repo)
jobs:
  e2e:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
    with:
      image: ghcr.io/projectbluefin/bluefin:testing
      suites: smoke,common,vanilla-gnome
```

Do **not** use a full SHA pin (creates Renovate churn) or `@main` (floating, security risk).

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

**Dynamic suite sharding**: `suites: smoke` expands to `smoke-a` + `smoke-b`, and `suites: common` expands to `common-a` + `common-b`. After checkout, the workflow glob-resolves `tests/<suite>/features/*.feature`, sorts alphabetically, and splits into two deterministic shards:

```python
files = sorted(glob.glob(f"tests/{suite}/features/*.feature"))
chunk_size = math.ceil(len(files) / 2)
chunk = files[shard_index * chunk_size:(shard_index + 1) * chunk_size]
```

Do **not** hardcode per-shard feature lists. New `.feature` files must land in a shard automatically or they will be silently skipped.

Smoke shards still use `tests/smoke/` (same directory, same `environment.py`, same steps) and normalize screenshot publishing to `:smoke-latest` (last writer wins). Common shards use `tests/common/` and pass their feature-file paths directly to the runner-side behave invocation.

### Unit-test parallelism

`unit-tests.yml` runs pytest with `-n auto`, but coverage must stay on `coverage.py`, not a bare `pytest-cov` invocation. In this repo, xdist plus `pytest-cov` under-reports coverage. Keep this pattern:

```bash
COVERAGE_PROCESS_START=.coveragerc coverage run -m pytest -n auto tests/unit/ -v
coverage combine
coverage xml
coverage report --fail-under=75
```

`.coveragerc` must keep `parallel = True` and `patch = subprocess` so worker coverage files are written and merged correctly.

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

A **"Collect migration status"** step also runs (`always()`, `continue-on-error: true`) for the lifecycle suite. It SSHes in and writes `results/migration-status.txt` containing `bootc status` and `fastfetch` output — useful for confirming the active image ref and OS version after a migration reboot. This file is included in the `e2e-results-*` artifact alongside the screenshot.

**Preferred manual trigger:** dispatch `upgrade-test.yml` in `projectbluefin/actions` — it calls `e2e.yml` cross-repo (which works). Do NOT dispatch `manual.yml` in this repo for lifecycle runs (see ops.md "manual.yml startup_failure").

## Pipeline stages

1. **Resolve matrix** — splits `suites` CSV into a JSON array for the strategy matrix; `smoke` becomes `smoke-a,smoke-b` and `common` becomes `common-a,common-b`
2. **Free disk space** — fast inline cleanup removes the hosted runner's large unused SDK trees (`/usr/share/dotnet`, Android, GHC, CodeQL) plus `php*`, `dotnet*`, `mono*`, and `llvm*`; this keeps the 30 GB `disk.raw` allocation viable without the slower `ublue-os/remove-unwanted-software` action
3. **Enable KVM** — udev rule for `/dev/kvm` access
4. **Resolve digest + cache OCI layers** — restore `/var/lib/containers/storage` with `actions/cache`, keyed by the test image digest. The workflow uses `sudo podman pull`, so the cache must target root's podman store, not the runner user's storage.
5. **Install QEMU + pull OCI image** — parallel: `apt-get install qemu-system-x86` while `podman pull` runs in background. On an OCI cache hit, both image pulls are skipped entirely.
6. **Install OCI image to disk** — `bootc install to-disk` writes ostree layers to a 30 GB raw disk; a non-zero exit is only tolerated after the workflow logs the full install output and proves `/ostree/deploy/default/deploy/` is non-empty. This matches the bootc install docs, which treat the deployment tree as the post-install target for follow-up customization. Direct QEMU kernel boot is used instead of OVMF/systemd-boot.
7. **Configure disk** — mounts the raw disk and:
   - Copies `vmlinuz` + `initramfs.img` to workspace for direct kernel boot
   - Creates `bluefin-test` user (UID 1001)
   - Injects SSH public key
   - Pre-bakes GDM autologin
   - Enables sshd, pre-generates SSH host keys
   - Masks irrelevant services (bluetooth, cups, avahi…)
   - Sets `PermitUserEnvironment yes` for AT-SPI env forwarding
8. **Boot VM** — `qemu-system-x86_64` with KVM, 4 GB RAM, 4 vCPUs, `virtio-gpu`, forwarded SSH on port 2222; daemonized
9. **Wait for SSH** — polls port 2222 up to 5 minutes
10. **Wait for GNOME session** — polls `/run/user/1001/wayland-0` up to 3 minutes
11. **Capture boot time summary** — after GNOME is up, reuse the same runner-side SSH tuple (`bluefin-test@127.0.0.1:2222` with `/tmp/vm_key`) to run `systemd-analyze time` and append the single-line result to `$GITHUB_STEP_SUMMARY` under an image slug header. Put boot-time diagnostics here, not earlier at SSH-ready time, so the summary reflects a usable desktop session.
12. **Load runner container + install test stack** — pipes the pre-built `ghcr.io/projectbluefin/testsuite:runner` container into the VM via `podman save | ssh podman load` (rootless, as `bluefin-test`). Before loading, ensures `bluefin-test` has `/etc/subuid`/`/etc/subgid` entries and runs `podman system migrate`. Then: loads kernel module (`uinput`), sets device permissions, copies SSH key for @plain_ssh scenarios, captures GNOME session environment (`DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`, etc.) into `/tmp/session.env`.
13. **Copy testsuite + run behave** — SCPs `tests/<suite>` and `tests/shared` to VM; runs `qecore-headless behave … --format json.pretty`

Smoke-suite correctness rule: commands launched with plain `subprocess.run()` execute in the qecore runner container, not necessarily against the VM host state. In `tests/smoke/features/steps/system_health_steps.py`, host-facing probes (`systemctl`, `journalctl`, `df`, `getent hosts`, etc.) must use the VM helper (`_run_host()`). Using `_run()` for those checks only tests the runner container and can miss VM regressions.
14. **Write job summary** — parses `results.json`, writes pass/fail table + failed scenario list to GitHub Step Summary
15. **Upload artifacts** — `e2e-results-<image-slug>-<suite>` (results JSON + text + `artifact-metadata.json`, 30 days) and `vm-serial-log-<image-slug>-<suite>` (3 days)
11. **Load runner container + install test stack** — pipes the pre-built `ghcr.io/projectbluefin/testsuite:runner` container into the VM via `podman save | ssh podman load` (rootless, as `bluefin-test`). Before loading, ensures `bluefin-test` has `/etc/subuid`/`/etc/subgid` entries and runs `podman system migrate`. Then: loads kernel module (`uinput`), sets device permissions, copies SSH key for @plain_ssh scenarios, captures GNOME session environment (`DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`, etc.) into `/tmp/session.env`.
12. **Copy testsuite + run behave** — SCPs `tests/<suite>` and `tests/shared` to VM; runs `qecore-headless behave … --format json.pretty`

Smoke-suite correctness rule: commands launched with plain `subprocess.run()` execute in the qecore runner container, not necessarily against the VM host state. In `tests/smoke/features/steps/system_health_steps.py`, host-facing probes (`systemctl`, `journalctl`, `df`, `getent hosts`, etc.) must use the VM helper (`_run_host()`). Using `_run()` for those checks only tests the runner container and can miss VM regressions.
13. **Write job summary** — parses `results.json`, writes pass/fail table + failed scenario list to GitHub Step Summary
14. **Upload artifacts** — `e2e-results-<image-slug>-<suite>` (results JSON + text + `artifact-metadata.json`, 30 days) and `vm-serial-log-<image-slug>-<suite>` (3 days)

## Image requirements

The OCI image under test **must**:

- Be a bootc/ostree image (`bootc install to-disk` compatible)
- Include GNOME + GDM
- Include `gnome-ponytail-daemon` (bridges AT-SPI to Wayland; required for dogtail)
- Have `python3` available for pip bootstrap

The workflow injects the test user, SSH keys, and autologin config at disk-prep time — nothing needs to be baked into the image for those.

## Common Rationalizations

- "The cache can target the runner user's podman storage."  
  It cannot here — the pulls run under `sudo`, so cache the root store or the pull will still miss.
- "A floating `uses:` tag is fine for a speedup-only change."  
  It is not; external actions in this repo must stay SHA-pinned.
- "We can keep the slow disk cleanup because it already works."  
  No — if a faster inline cleanup frees enough space for `disk.raw`, prefer the faster path.

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
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:<suite>-latest` | Most recent run for that suite, e.g. `:smoke-latest` |
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:<slug>-<suite>-latest` | Per-image slug tag, e.g. `bluefin-testing-smoke-latest` — used by publish-to-pages |
| `ghcr.io/projectbluefin/testsuite/desktop-screenshot:<short-sha>` | Immutable per-commit tag |

**No `:latest` tag is pushed.** `latest` is not a tag used in this repo — do not add it.

Pull the latest screenshot locally:
```bash
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:smoke-latest
```

### gh-pages screenshot publishing

**Architecture: schedule-based polling, not workflow_run.**

`workflow_run` only fires for workflows running in the **same repository**. When consumer repos (bluefin, bluefin-lts, dakota) call `e2e.yml` via `workflow_call`, the run is recorded in the **caller's** repo — testsuite's `workflow_run` never fires. The metadata-artifact handoff approach is dead for cross-repo calls.

The working approach:

1. **`e2e.yml` pushes a slug-specific GHCR tag per run** alongside the existing suite tag:
   ```
   ghcr.io/projectbluefin/testsuite/desktop-screenshot:<slug>-<suite>-latest
   ```
   Slug derivation: strip `ghcr.io/<org>/` from `inputs.image`, replace `:` with `-`.
   Example: `ghcr.io/projectbluefin/bluefin:testing` → `bluefin-testing-smoke-latest`

   **SCREENSHOT_SUITE normalization:** smoke sharding pushes `SCREENSHOT_SUITE=smoke` for both
   `smoke-a` and `smoke-b`. The GHCR tag is always `{slug}-smoke-latest`, never `{slug}-smoke-a-latest`.
   If you add new shards, update the `SCREENSHOT_SUITE` normalization block in e2e.yml and keep
   `SUITES=(smoke common vanilla-gnome)` in `publish-to-pages.yml` unchanged.

   The tag is annotated with `io.github.projectbluefin.run_id` and `io.github.projectbluefin.caller_repo` for JSONL traceability.

2. **`publish-to-pages.yml` runs on a 2-hour schedule** (+ `workflow_dispatch` for manual trigger). It pulls the known slug-specific tags directly from GHCR — no metadata artifacts, no cross-repo auth. JSONL reads `run_id` and `caller_repo` from OCI manifest annotations via `oras manifest fetch`.

Known slugs hardcoded in `publish-to-pages.yml`:
```bash
SLUGS=(bluefin-testing bluefin-lts-testing dakota-testing)
SUITES=(smoke common vanilla-gnome)
```
Add new slugs here when the fleet grows. **Do not add `dx`, `developer`, or `lifecycle` to SUITES** — these suites are not tracked by publish-to-pages (dx/developer run on gdx images not in the SLUGS list; lifecycle is a migration workflow with no desktop screenshots).

**Dashboard source of truth:** `docs/dashboard/index.html` in `main` is the canonical dashboard HTML. `publish-to-pages.yml` syncs it to `gh-pages` on every run. Edit the source in `main`, not the copy on `gh-pages` directly.

Stable URL format:
```text
https://projectbluefin.github.io/testsuite/screenshots/{slug}-{suite}-latest.png
```

The JSONL records at `data/results-YYYYMMDD.jsonl` on `gh-pages` feed the static build-health dashboard at `https://projectbluefin.github.io/testsuite/`.

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

### Timeout (45 min job limit)

The install + configure step is the heaviest (~10–15 min depending on image size). OCI layer caching should remove most repeat pull time; if jobs still hit the 45-minute limit, reduce suite scope or check for unusually large uncached images.

## Consumer constraints — what you cannot do from the reusable action

When calling this workflow from another repo, the following are explicitly banned:

- **No RPM installs** — do not add `dnf install` or `rpm -i` steps to consumer workflows or to the action inputs (`setup_script`). The test VM is a fully-baked bootc image; package mutations break repeatability and may conflict with the image's ostree deployment. Use Flatpak installs or pre-bake packages into the image.
- **No `apt install` in test steps** — the GHA runner uses `ubuntu-latest` for QEMU hosting only; apt installs in test steps (as opposed to the infrastructure setup) are not permitted.
- **No VM tuning inputs** — do not request inputs for CPU/RAM/kernel params. The pipeline runs on GitHub-hosted runners; the VM spec is fixed.

## Known limitations

- `bootupd` may fail (not in bootc images by default), but a non-zero `bootc install to-disk` exit is only acceptable if the ostree deployment directory is populated. The workflow now logs the full install output, records the exit code, and hard-fails if the deployment directory is empty.
- No display output: `virtio-gpu` with `-display none`. Tests must use AT-SPI (dogtail/qecore), not pixel-based assertions.
- No GPU acceleration for GL/Vulkan in GHA runners. Hardware-specific tests require SSH-mode suites not yet in the GHA action (epics #43/#44).
- Partition layout assumes `p3` is the root partition. Tested against standard Anaconda/bootc partition tables. Non-standard layouts may break the disk-configure step.

## Red Flags

- A cache step targets `~/.local/share/containers` or another non-root path even though pulls use `sudo podman`
- `workflow_call` checkout logic starts using `github.ref_name` inside `e2e.yml`
- External actions are added with floating tags instead of full SHAs
- A workflow change lands without updating this skill file with the discovered rule or workaround

## Verification

- [ ] `.github/workflows/e2e.yml` parses with `yaml.safe_load`
- [ ] Every external `uses:` line in `e2e.yml` is SHA-pinned with a version comment
- [ ] Repo-required local check passes: `python3 -m ruff check tests/ --select E,F,W --ignore E501`
- [ ] Any new workflow-specific workaround or convention discovered in the session is captured here

---

## test_ref and github.ref_name

**Symptom:** Tests always run from `main` even when dispatching `manual.yml` from a feature branch.

**Cause:** `github.ref_name` inside a `workflow_call` reusable workflow always resolves to the **default branch** (`main`), not the caller's branch. This is a GitHub Actions platform behavior — it does not reflect the dispatched branch.

**Fix:** Set `test_ref` in the `workflow_dispatch` caller (`manual.yml`, `migration-test.yml`), where `github.ref_name` correctly reflects the dispatched branch:

```yaml
jobs:
  test:
    uses: ./.github/workflows/e2e.yml
    with:
      test_ref: ${{ github.event.inputs.test_ref || github.ref_name }}
```

Never use `github.ref_name` as a test-checkout ref inside `e2e.yml` itself — always `inputs.test_ref`.

---

## manual.yml: do not add @ref to same-repo workflow calls

**Symptom:** `manual.yml` workflow_dispatch runs fail immediately with `startup_failure`.

**Cause:** GitHub Actions returns `startup_failure` when a `workflow_dispatch` workflow calls a same-repo reusable workflow with an explicit ref (`uses: ./.github/workflows/e2e.yml@main`).

**Fix:** Use the bare local path with no ref:
```yaml
uses: ./.github/workflows/e2e.yml    # correct
# NOT:
# uses: ./.github/workflows/e2e.yml@main   # causes startup_failure
```

Cross-repo calls (`projectbluefin/testsuite/.github/workflows/e2e.yml@<sha>`) work correctly.

For lifecycle manual runs, dispatch `upgrade-test.yml` in `projectbluefin/actions` — it calls `e2e.yml` cross-repo with full lifecycle inputs.

---

## zstd:chunked migration toggle

The `@zstd_chunked` tag gates the final-state migration scenario. It is **skipped** (not failed) when disabled.

| Workflow input | Effect |
|---|---|
| `chunked_enabled: false` (default) | `@zstd_chunked` scenarios skip |
| `chunked_enabled: true` | `@zstd_chunked` scenarios run |

Enable once `ghcr.io/projectbluefin/bluefin:latest` ships `tar+zstd` OCI layers. Verify:
```bash
skopeo inspect --raw docker://ghcr.io/projectbluefin/bluefin:latest \
  | jq '.layers[0].mediaType'
```

---

## Running migration tests manually

Use `migration-test.yml` in `projectbluefin/actions` to run only the `@migration` scenario group.

**Go to:** [projectbluefin/actions → Actions → bootc Migration Test → Run workflow](https://github.com/projectbluefin/actions/actions/workflows/migration-test.yml)

| Field | Non-LTS | LTS |
|---|---|---|
| `source_image` | `ghcr.io/ublue-os/bluefin:latest` | `ghcr.io/ublue-os/bluefin-lts:lts` |
| `migration_target` | _(leave blank)_ | `ghcr.io/projectbluefin/bluefin-lts:stable` |
| `chunked_enabled` | `false` (default) | `false` (default) |

Wire as a consumer post-build gate:
```yaml
migration-test:
  needs: build
  uses: projectbluefin/actions/.github/workflows/migration-test.yml@<ref>
  with:
    source_image: ghcr.io/ublue-os/bluefin-lts:lts
    migration_target: ghcr.io/projectbluefin/bluefin-lts@${{ needs.build.outputs.digest }}
```

For non-migration lifecycle runs: dispatch `upgrade-test.yml` in `projectbluefin/actions`.

---

## Post-upgrade desktop screenshot

After a lifecycle suite run, `e2e.yml` captures a full-screen GNOME screenshot:
```bash
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "const Shell = imports.gi.Shell; const s = new Shell.Screenshot(); \
   s.screenshot(false, false, '/tmp/upgrade_screenshot.png', () => {}); 'ok'"
```

Saved to `results/screenshot_lifecycle_upgrade_final.png` and promoted to the `desktop-screenshot` artifact.

The step uses `ControlMaster=no` because the VM may have rebooted during the lifecycle suite, invalidating any existing SSH multiplex socket. It waits up to 60s for `/run/user/1001/wayland-0` before attempting the screenshot.

## dconf local.d overrides and test interference (2026-06-21)

**Pattern**: The e2e.yml VM setup writes `enabled-extensions=['unsafe-mode@bluefin-test']` to `/etc/dconf/db/local.d/00-ci-testing`. The dconf profile shipped by bluefin images is:
```
user-db:user
system-db:local
system-db:site
system-db:distro
```

`local` has higher priority than `distro`. Any `gsettings get` call on a key set in `local.d/00-ci-testing` will return the CI value, NOT the distribution default. This means tests that check `gsettings get org.gnome.shell enabled-extensions` will see only `['unsafe-mode@bluefin-test']`, not what the distro configured.

**Fix for tests checking distribution defaults**: Use `Gio.Settings.get_default_value()` which reads the compiled gschema default, bypassing ALL dconf databases:
```gherkin
* Run SSH command: "python3 -c \"import gi; gi.require_version('Gio','2.0'); from gi.repository import Gio; v = Gio.Settings.new('org.gnome.shell').get_default_value('enabled-extensions'); print(v.unpack() if v else [])\""
* Last command output contains "custom-command-list@storageb.github.com"
```

**When to use `gsettings get` vs `get_default_value`**:
- `gsettings get`: tests the EFFECTIVE value (what a real user sees). Affected by `local.d` CI overrides.
- `get_default_value`: tests whether the DISTRIBUTION ships a default. Immune to CI overrides.
- Use `gsettings get` for tests of locked keys (in `distro.d/locks/`) — locked keys aren't overridable by `local.d`.

**Keys written by local.d/00-ci-testing**:
- `org.gnome.shell allow-extension-installation` = `true`
- `org.gnome.shell enabled-extensions` = `['unsafe-mode@bluefin-test']`

---

## Gating :testing behind a post-build smoke check

Every consuming repo has a local `run-testsuite.yml` wrapper that pins the testsuite SHA. **Always call the wrapper — never call `projectbluefin/testsuite/.github/workflows/e2e.yml` directly.** Renovate manages the SHA in one place; all callers inherit it automatically.

### `publish_stream_tag: "false"` — the gate input

`projectbluefin/actions/.github/workflows/reusable-build.yml` has a `publish_stream_tag` input (default `"true"`). When set to `"false"`, the build pushes only the SHA-tagged image (`:$sha`) and withholds the stream tag (`:testing`, `:stable`). The post-build smoke workflow promotes the stream tag only after smoke passes.

Set it conditionally in the consuming repo's build workflow:
```yaml
publish_stream_tag: ${{ (github.ref == 'refs/heads/lts' || github.event_name == 'pull_request') && 'true' || 'false' }}
```
This keeps `:lts` publishing directly (via `execute-release.yml`) and gates `:testing` for all push events.

### Post-build promote pattern (4 jobs)

The canonical post-build gate follows bluefin's `post-testing-e2e.yml`:

```
get-image   — download image-digest-testing-<brand>-main-x86_64 artifact from build run
    └── e2e-smoke  — run-testsuite.yml, suites: smoke,common
          └── promote-to-testing  — skopeo copy :sha → :testing for all digest entries
          └── report-failure      — open/update GitHub issue; :testing not promoted
```

Digest artifact name pattern: `image-digest-{stream_name}-{brand_name}-{image_flavor}-{architecture}`
Digest file format (two lines per image): `IMAGE_NAME=sha256:...` (= format) and `IMAGE_NAME|platform|sha256:...` (| format).
Use the `=` format to extract the digest; use `--pattern "image-digest-testing-*"` to download all flavors at promote time.

```yaml
DIGEST=$(grep "^bluefin-lts-hwe=" /tmp/digest/*.txt | head -1 | cut -d= -f2-)
echo "image=ghcr.io/${{ github.repository_owner }}/bluefin-lts-hwe@${DIGEST}" >> "$GITHUB_OUTPUT"
```

### Per-repo wiring state

| Repo | Gate location | Pattern |
|---|---|---------|
| `bluefin` | `post-testing-e2e.yml` | digest artifact → smoke,common → promote |
| `bluefin-lts` | `post-merge-e2e.yml` | digest artifact → smoke,common → promote; `build-regular-hwe.yml` sets `publish_stream_tag: false` |
| `dakota` | `publish.yml` (`smoke` job) | `:sha` image → smoke → `promote` job; SBOM runs in parallel |
