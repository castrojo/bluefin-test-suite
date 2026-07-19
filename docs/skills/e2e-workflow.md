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
| `target-image` | string | `""` | Full OCI ref to upgrade TO (optional). When set and the `lifecycle` suite is running, stages this image via `bootc switch` before the test suite. Used for migration testing. |
| `suites` | string | `smoke` | Comma-separated suite names: `smoke`, `developer`, `dx`, `software`, `vanilla-gnome`, `bazzite`, `common`. Note: `lifecycle` is also accepted but is not listed in the input description — use `manual.yml` or `projectbluefin/actions` wrapper workflows for lifecycle runs. |
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
if [[ "${SUITE_DIR}" == "common" || "${SUITE_DIR}" == "lifecycle" ]]
  → python3 tests/shared/behave_retry.py ...   (runner-side, SSH via VM_IP/VM_USER env vars)
else
  → scp tests/ to VM, then
    podman run --rm ghcr.io/projectbluefin/testsuite:runner \
      "python3 /tmp/bluefin-tests/tests/shared/behave_retry.py ..."  (inside VM)
```

When `target-image` is set and the `lifecycle` suite is running, the **"Pre-stage target image via bootc switch"** step SSHes into the VM and runs `sudo bootc switch '<target-image>'` before the behave run begins, staging the upgrade target.

After the lifecycle suite finishes, a separate **"Capture post-upgrade desktop screenshot"** step re-SSHes with `ControlMaster=no` (fresh connection after reboot), waits up to 60 s for the Wayland socket at `/run/user/1001/wayland-0`, and calls `org.gnome.Shell.Eval` via gdbus to capture a screenshot. The screenshot is saved to `results/screenshot_lifecycle_upgrade_final.png` and uploaded in the `e2e-results-*` artifact.

A **"Capture post-migration screenshot and status"** step also runs (`always()`, `continue-on-error: true`) for the lifecycle suite. It captures the QEMU framebuffer via `tests/shared/qemu_screendump.py` and SSHes in to write `results/migration-status.txt` containing `bootc status`, `fastfetch`, and `os-release` output — useful for confirming the active image ref and OS version after a migration reboot. Both files are included in the `e2e-results-*` artifact.

**Preferred manual trigger:** dispatch `upgrade-test.yml` in `projectbluefin/actions` — it calls `e2e.yml` cross-repo (which works). Do NOT dispatch `manual.yml` in this repo for lifecycle runs (see ops.md "manual.yml startup_failure").

## Pipeline stages

1. **Resolve matrix** — splits `suites` CSV into a JSON array for the strategy matrix; `smoke` becomes `smoke-a,smoke-b` and `common` becomes `common-a,common-b`
2. **Checkout testsuite** — sparse checkout of `flatpak-app-list.txt`, `tests/`, and `scripts/check_quarantine_age.py` from `projectbluefin/testsuite` at `inputs.test_ref`; always `fetch-depth: 0`
3. **Resolve suite shard** — Python step computes `SUITE_DIR` (physical directory), `FEATURE_ARGS` (specific `.feature` files for shards), and `SCREENSHOT_SUITE` (normalized suite name for GHCR tags)
4. **Install QEMU + pull OCI image** — parallel: `apt-get install qemu-system-x86` while `sudo podman pull <image>` and `sudo podman pull ghcr.io/projectbluefin/testsuite:runner` run concurrently in background
5. **Generate OOTB Flatpak manifest** — Bluefin GUI suites only; reads the image's `/usr/share/ublue-os/homebrew/system-flatpaks.Brewfile` (primary OOTB app list) and `/usr/share/flatpak/preinstall.d/*.preinstall` (supplemental entries such as Bazaar), parses `flatpak "<app-id>"` Brewfile lines and `[Flatpak Preinstall <app-id>]` section headers, filters out themes/runtimes/`Install=false` entries, writes `flatpak-app-list.txt`, and emits a SHA-256 hash for the cache key
6. **Restore/prime Flatpak download cache** — Bluefin GUI suites only; caches a runner-side user Flatpak repo keyed on the generated manifest hash
7. **Free disk space** — runs `ublue-os/remove-unwanted-software@v9`; keeps the 30 GB `disk.raw` allocation viable on GitHub-hosted runners
8. **Enable KVM** — udev rule for `/dev/kvm` access
9. **Generate SSH keypair** — creates `ed25519` keypair at `/tmp/vm_key`; public key stored in `VM_PUBKEY` env var
10. **Install OCI image and configure disk** — combined step that:
   - `fallocate -l 30G disk.raw`
   - `bootc install to-disk --via-loopback disk.raw --filesystem ext4` (with `--bootloader systemd` flag when bootc ≥0.1.13; older images skip the flag)
   - Mounts the raw disk, finds `ROOT_UUID` (partition 3), ostree deployment hash, and `KVER`
   - Copies `vmlinuz` + `initramfs.img` from deployment `usr/lib/modules/<kver>/` (or boot partition fallback)
   - Creates `boot.N` symlinks needed by `ostree-system-generator` (including canonical `boot.N` alias for versioned `boot.N.M` dirs produced by newer bootc)
   - Sets `KERNEL_ARGS` env (includes `root=UUID=...`, masked services, serial console, `selinux=0`)
   - Iterates all deployment directories and writes: `bluefin-test` user (UID 1001), GDM autologin, sshd drop-in `00-ci-auth.conf`, dconf `local.d/00-ci-testing` override, `tmpfiles.d/ci-user.conf`, masked service symlinks
   - Pre-installs `unsafe-mode@bluefin-test` gnome-shell extension files into var home (pre-boot, so gnome-shell finds it during `_loadExtensions()`)
   - Injects SSH authorized key into `/var/home/bluefin-test/.ssh/` and each deployment's `/etc/ssh/ci-authorized-keys`
11. **Boot VM** — `qemu-system-x86_64` with KVM, 4 GB RAM, 4 vCPUs, `virtio-gpu-pci`, forwarded SSH on port 2222; daemonized; QEMU monitor socket at `/tmp/qemu-monitor.sock` (chmod 666)
12. **Wait for SSH** — polls port 2222 up to **15 minutes** (900 s)
13. **Pre-stage target image via bootc switch** — lifecycle suite only, when `inputs.target-image` is set; SSHes into VM and runs `sudo bootc switch '<target-image>'` to stage the upgrade target before the test run
14. **Dump VM serial log** — always runs (`if: always()`); primary debug tool when SSH never comes up
15. **Wait for GNOME session** — polls `/run/user/1001/wayland-0` up to 3 minutes
16. **Capture boot time** — SSHes in, runs `systemd-analyze time`, appends result to `$GITHUB_STEP_SUMMARY`
17. **Install cached Flatpaks in VM** — Bluefin GUI suites (non-common/non-lifecycle) only; SCPs a tarred runner-side Flatpak repo into the VM and deploys missing apps with `sudo flatpak install --system --sideload-repo=...`, falling back to Flathub if cache is incomplete
18. **Install shell tools for common suite** — common suite only; installs `zsh`, `fish`, and brew CLI tools (`fzf`, `bat`, `eza`, `fd`, `ripgrep`, `starship`) via brew (if available) or `rpm-ostree --apply-live` / `dnf` fallback; `brew-setup.service` is masked in CI so these are installed manually
19. **Load runner container into VM** — non-common suites; ensures `bluefin-test` has `/etc/subuid`/`/etc/subgid`, runs `podman system migrate`, pipes `ghcr.io/projectbluefin/testsuite:runner` via `podman save | ssh podman load`; patches `openssh-clients` into the runner image if missing
20. **Install Python test stack** — non-common suites; loads `uinput` kernel module, sets device permissions, copies SSH private key into VM for `@plain_ssh` scenarios, queries GNOME session environment into `/tmp/session.env`, enables `unsafe-mode@bluefin-test` extension, sets `toolkit-accessibility true`, re-queries AT-SPI bus address after enabling accessibility, terminates any pre-started `gnome-control-center`
21. **Install gnome-ponytail-daemon** — non-common suites; builds `gnome-ponytail-daemon` (tag `0.0.11`) and `grim` from source inside a `debian:bookworm` container on the runner (without libei, uses Mutter D-Bus fallback for input events; wayland-protocols 1.37 built from source for grim); SCPs binaries into `~/.local/libexec/` and `~/.local/bin/`; registers D-Bus service file and pre-starts the daemon
22. **Run behave suite** — `common`/`lifecycle`: runner-side `python3 tests/shared/behave_retry.py` with `VM_IP/VM_USER/SSH_KEY/SSH_PORT` env vars; GUI suites: SCP `tests/<suite>` + `tests/shared` + `tests/__init__.py` to VM, then `podman run ... ghcr.io/projectbluefin/testsuite:runner "python3 .../behave_retry.py ... --format json.pretty"` inside VM; always `--tags ~quarantine`; retries controlled by `BEHAVE_RETRIES=2`
23. **Capture post-upgrade desktop screenshot** — lifecycle suite only; SSHes with `ControlMaster=no`, waits up to 60 s for Wayland socket, captures via `gdbus org.gnome.Shell.Eval`
24. **Capture post-migration screenshot and status** — lifecycle suite only; QEMU framebuffer capture via `qemu_screendump.py` + SSH for `bootc status`, `fastfetch`, `os-release` into `results/migration-status.txt`
25. **Capture Flatpak screenshots** — when `inputs.screenshot_flatpaks != ''`; runs `screenshot_cli.py` inside the runner container
26. **Capture desktop screenshot (QEMU screendump fallback)** — non-common suites; if no `screenshot_*fastfetch*.png` found in `results/`, captures QEMU VGA framebuffer via `/tmp/qemu-monitor.sock`
27. **Promote desktop screenshot** — finds best screenshot (`screenshot-post-migration.png` > upgrade > fastfetch); for non-common/non-lifecycle suites, fails loud if no screenshot found
28. **Push desktop screenshot to GHCR** — pushes `:<short-sha>`, `:<SCREENSHOT_SUITE>-latest`, and `:<image-slug>-<SCREENSHOT_SUITE>-latest` tags; also pushes per-Flatpak gallery tags
29. **Write job summary** — parses `results.json`, writes pass/fail table + failed scenarios; includes quarantine age summary from `scripts/check_quarantine_age.py --json`; includes screenshot pull commands and gh-pages URL
30. **Prepare artifact metadata** — writes `results/artifact-metadata.json`; computes `artifact_suffix` by sanitizing the full image reference (not just image name — the full `ghcr.io/org/image:tag` string is sanitized)
31. **Upload results artifact** — `e2e-results-<artifact-suffix>-<suite>` (30 days); includes `results.json`, `results.txt`, `artifact-metadata.json`, and any screenshots
32. **Upload serial log artifact** — `vm-serial-log-<artifact-suffix>-<suite>` (3 days)
33. **Fail job if tests failed** — exits with behave's return code
34. **Write + upload e2e metadata** — writes `meta/e2e-metadata.json` (`image`, `suite`, `conclusion`); uploaded as `e2e-metadata-<suite>` artifact (1 day)

Smoke-suite correctness rule: commands launched with plain `subprocess.run()` execute in the qecore runner container, not necessarily against the VM host state. In `tests/smoke/features/steps/system_health_steps.py`, host-facing probes (`systemctl`, `journalctl`, `df`, `getent hosts`, etc.) must use the VM helper (`_run_host()`). Using `_run()` for those checks only tests the runner container and can miss VM regressions.

## Image requirements

The OCI image under test **must**:

- Be a bootc/ostree image (`bootc install to-disk` compatible)
- Include GNOME + GDM
- Have `python3` available in the deployment

**`gnome-ponytail-daemon` is built at runtime** — the workflow compiles it from source in a `debian:bookworm` container on the runner and SCPs the binary into the VM. The image does NOT need to ship `gnome-ponytail-daemon`. (See step 20 above.)

The workflow injects the test user, SSH keys, autologin config, and the unsafe-mode gnome-shell extension at disk-prep time — nothing needs to be baked into the image for those.

## Common Rationalizations

- "The cache can target the runner user's podman storage."  
  It cannot here — the pulls run under `sudo`, so cache the root store or the pull will still miss.
- "A floating `uses:` tag is fine for a speedup-only change."  
  It is not; external actions in this repo must stay SHA-pinned.
- "We can replace `ublue-os/remove-unwanted-software` with an inline cleanup for speed."  
  The workflow currently uses `ublue-os/remove-unwanted-software@v9` for disk cleanup. Switching to an inline cleanup is only worthwhile if the action is the measured bottleneck — do not change this without profiling.

## Flatpak cache pattern for Bluefin GUI suites

`e2e.yml` masks `flatpak-preinstall.service` in `KERNEL_ARGS`, so CI first boot never waits on the image's bulk Flathub pull. For Bluefin-family GUI suites, the workflow derives the OOTB Flatpak manifest directly from the image under test and seeds those apps after GNOME is up.

1. **Generate the manifest at runtime** — create a throwaway container from the pulled image and copy `/usr/share/ublue-os/homebrew/system-flatpaks.Brewfile` (Bluefin's primary OOTB flatpak list) and `/usr/share/flatpak/preinstall.d/*.preinstall` (supplemental entries) to the runner. Parse `flatpak "<app-id>"` Brewfile lines and `[Flatpak Preinstall <app-id>]` preinstall sections. Skip themes, runtimes, and entries with `Install=false`. Write the sorted app IDs to `flatpak-app-list.txt` and emit a SHA-256 hash of the manifest as a step output (`steps.manifest.outputs.hash`).
2. **Cache the runner-side repo** — cache `${GITHUB_WORKSPACE}/.flatpak-cache-home/.local/share/flatpak` with `actions/cache` keyed on the generated manifest hash (`flatpak-ootb-<os>-<hash>`). Do not use broad restore keys: a stale cache would contain refs that do not match the image under test.
3. **Prime on miss** — run `flatpak install --user --no-deploy ...` on the runner to download refs/runtimes without deploying them.
4. **Inject and deploy in the VM** — copy the repo into the VM and deploy missing apps system-wide with `sudo flatpak install --system --sideload-repo=<copied repo> ...`, falling back to a normal Flathub pull only if the cache is incomplete.

Do **not** preload these apps on non-Bluefin images: that mutates dakota/gnomeos coverage instead of testing what those images actually ship. The manifest generation and cache steps are gated with `contains(inputs.image, '/bluefin')`.

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

**Dashboard source of truth:** The QA dashboard is now a modern Astro static-site project located in the `dashboard/` directory on `main`. Every run of the scheduled `publish-to-pages.yml` workflow checks out the repository, pulls the latest test results and screenshots from GHCR, parses/converts behave logs, aggregates historical statistics, compiles Astro to static HTML, indexes the entire site with Pagefind, and deploys it natively to GitHub Pages.

Never edit files on the `gh-pages` branch directly—always make edits inside the `dashboard/` directory on `main`.

Stable URL format:
```text
https://projectbluefin.github.io/testsuite/screenshots/{slug}-{suite}-latest.png
```

The historical runs are compiled and indexed natively at `qa.projectbluefin.io` (or `https://projectbluefin.github.io/testsuite/`).

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
| `e2e-results-<artifact-suffix>-<suite>` | `results.json` (behave JSON), `results.txt` (pretty output), `artifact-metadata.json` (image + suite metadata), screenshots, `migration-status.txt` (lifecycle only) | 30 days |
| `vm-serial-log-<artifact-suffix>-<suite>` | QEMU serial console output | 3 days |
| `e2e-metadata-<suite>` | `e2e-metadata.json` — `{"image":…,"suite":…,"conclusion":…}` for downstream promotion jobs | 1 day |

`<artifact-suffix>` is derived by sanitizing the full image reference (e.g. `ghcr.io/projectbluefin/bluefin:testing` → `ghcr.io-projectbluefin-bluefin-testing`), not just the image name.

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

### Timeout (120 min job limit)

The install + configure step is the heaviest (~10–15 min depending on image size). OCI layer caching should remove most repeat pull time; if jobs still hit the 120-minute limit, reduce suite scope or check for unusually large uncached images.

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
- `continue-on-error` set on a job that uses `uses:` — this is a parse-time error (see below)

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

After a lifecycle suite run, `e2e.yml` captures a full-screen desktop screenshot directly from the host runner via QEMU's monitor socket:

```bash
sudo python3 tests/shared/qemu_screendump.py results/screenshot_lifecycle_upgrade_final.png
```

This bypasses the fragile GDM session security, polkit rules, and GNOME 50 `gdbus` session-bus permission barriers entirely.

**Key constraints implemented for reliability:**
- **Wait with Settle Sleep**: The workflow SSHes into the VM using `ControlMaster=no` (since a reboot occurred mid-lifecycle) to wait up to 60s for `/run/user/1001/wayland-0`. Once active, it sleeps for an additional 5 seconds to allow GDM/GNOME Shell to finish painting the desktop before the screenshot is taken.
- **Root-to-Runner Permission Handling**: Because QEMU runs as root, the monitor socket writes files owned by root. The workflow executes `sudo chown runner:runner` and `sudo chmod 644` on the output PNG to guarantee the ORAS push and artifact upload steps can read the file without permission errors.

Saved to `results/screenshot_lifecycle_upgrade_final.png` and promoted to the `desktop-screenshot` artifact.

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

---

## GHCR screenshot push — cross-repo token scope

**Symptom:** `e2e.yml` "Push desktop screenshot to GHCR" step silently succeeds (exit 0) but no tag appears in `ghcr.io/projectbluefin/testsuite/desktop-screenshot`. Dashboard shows 0 screenshots.

**Cause:** When consumer repos (bluefin, bluefin-lts, dakota) call `e2e.yml` via `workflow_call`, `github.token` is scoped to the **caller's** repository. It can write to that repo's own GHCR packages, but NOT to `ghcr.io/projectbluefin/testsuite/desktop-screenshot` (owned by this repo). The push step has `continue-on-error: true`, so the failure is silent.

**Fix:** Grant explicit write access to each consumer repo on the `desktop-screenshot` package:
1. Go to [ghcr.io/projectbluefin/testsuite/desktop-screenshot](https://github.com/orgs/projectbluefin/packages/container/testsuite%2Fdesktop-screenshot/settings)
2. Package Settings → Manage Access
3. Add each consumer repo (`bluefin`, `bluefin-lts`, `dakota`) with `Write` role

This is a one-time UI operation — there is no programmatic API for cross-repo package grants.

---

## Dashboard seeding — initial population

If the `https://projectbluefin.github.io/testsuite/` dashboard shows "No JSONL results found" or no screenshots, the GHCR slug tags don't exist yet. Trigger manual e2e runs to populate them:

```bash
# Trigger smoke runs for each image (each takes ~2h)
gh workflow run "Manual Test Run" --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/bluefin:testing -f suites=smoke

gh workflow run "Manual Test Run" --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/bluefin-lts:testing -f suites=smoke

gh workflow run "Manual Test Run" --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/dakota:testing -f suites=smoke

# After runs complete, trigger publish immediately (instead of waiting 2h schedule):
gh workflow run publish-to-pages.yml --repo projectbluefin/testsuite
```

Prerequisites: GHCR cross-repo package write access must be granted first (see above).

---

## continue-on-error is forbidden on reusable-workflow jobs

**Symptom:** Every push to main produces "This run likely failed because of a workflow file issue." No jobs start. GitHub doesn't show a syntax error line number.

**Cause:** GitHub Actions forbids `continue-on-error` on a job that uses `uses:` to call a reusable workflow. The workflow is rejected at parse time — not at runtime — so every run fails before any job is created.

**Broken pattern:**
```yaml
jobs:
  e2e:
    continue-on-error: ${{ matrix.allow_failure == true }}  # FORBIDDEN with uses:
    uses: ./.github/workflows/run-testsuite.yml
    with:
      image: ${{ matrix.image }}
```

**Fix:** Remove `continue-on-error` entirely. If non-blocking matrix entries are needed, split blocking and non-blocking jobs into separate job definitions, each with its own `uses:` and `if:` condition — or just make all entries blocking.

**Verified with:** `actionlint` catches this (`continue-on-error is not available` for reusable workflow jobs). Run `actionlint` on any workflow that uses `uses:` before pushing.

---

## Dashboard Static-Site Compilation and Path Robustness

**Pattern**: Python helper scripts (such as `compile_data.py`) executed from repository root inside GitHub Actions, but developed locally inside subdirectories, must resolve their base directories dynamically relative to `Path(__file__)` rather than hardcoding relative string paths like `./raw-runs`. This avoids directory execution discrepancies between local and CI environments.

**Pattern**: In Astro static sites, using `import.meta.glob('../data/runs/*.json', { eager: true })` to load detailed raw JSON files at build-time allows robust, offline-safe compilation of metrics, sparklines, and broken scenario aggregations directly from logs, entirely removing runtime client-side fetch or API performance overhead.
