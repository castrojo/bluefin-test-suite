---
name: e2e-workflow
description: "How to call and debug the reusable testsuite e2e workflow. Load when changing e2e.yml, action inputs, or consumer-repo wiring."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

# Reusable E2E Workflow — GNOME in QEMU

Load when: integrating the testsuite into another repo's CI (e.g. `<image-org>/dakota`), debugging e2e workflow failures, or understanding how the QEMU boot pipeline works.


## When to Use


- Changing `.github/workflows/e2e.yml` inputs, matrix behavior, job timeouts, or artifact handling
- Debugging OCI image pulls, QEMU boot/setup stages, or reusable `workflow_call` behavior
- Adding or troubleshooting GitHub Actions caching for the root podman image store

## When NOT to Use


- Writing or debugging behave steps inside `tests/**` — use `behave.md`, `gnome.md`, or `bootc.md`
- Changing Argo/KubeVirt lab infrastructure — that belongs in `<image-org>/testing-lab`
- Updating repo-wide contribution policy — use `contributing.md`, `human-gates.md`, or `skill-drift.md`

## Core Process


1. Confirm the change belongs in the reusable workflow and not in a consumer repo or infra repo.
2. Preserve hard CI rules: SHA-pin external actions, keep `workflow_call` semantics stable, and respect human gates for interface changes.
3. For OCI pull performance work, cache the root podman store (`/var/lib/containers/storage`) because `e2e.yml` pulls with `sudo podman`.
4. Validate the workflow file parses, then run the repo's required local checks before committing.
5. Write back any non-obvious workflow pattern discovered during the change in this skill file.

## What it is


`<image-org>/testsuite/.github/workflows/e2e.yml` is a reusable `workflow_call` workflow.  
It boots a bootc OCI image in a KVM-accelerated QEMU VM on `ubuntu-latest`, starts a GNOME session (via GDM autologin), and runs behave suites via qecore-headless.

**No self-hosted runners. Pure GitHub Actions.**

## PR validation sidecars


`pr-validate.yml` now includes a `quarantine-age` job that runs `python3 scripts/check_quarantine_age.py`.
The script walks `git log --follow` history for each `@quarantine` scenario and fails once the tag ages past the configured threshold.
Because the check needs full history, the checkout step for that job must use `fetch-depth: 0`.
Rollouts should start with `--grace-days` in CI (currently `--grace-days 30`) so the threshold can harden without instantly blocking every PR.

`e2e.yml` reuses the same script for job-summary reporting via `python3 scripts/check_quarantine_age.py --json`.
That summary path is informational only, but it still needs the same prerequisites: the workflow checkout must include `scripts/check_quarantine_age.py`, the `tests/` tree, and full git history (`fetch-depth: 0`) or the age calculations will be incomplete.

## Pipeline stages


1. **Resolve matrix** — splits `suites` CSV into a JSON array for the strategy matrix; `smoke` becomes `smoke-a,smoke-b` and `common` becomes `common-a,common-b`
2. **Checkout testsuite** — sparse checkout of `flatpak-app-list.txt`, `tests/`, and `scripts/check_quarantine_age.py` from `<image-org>/testsuite` at `inputs.test_ref`; always `fetch-depth: 0`
3. **Resolve suite shard** — Python step computes `SUITE_DIR` (physical directory), `FEATURE_ARGS` (specific `.feature` files for shards), and `SCREENSHOT_SUITE` (normalized suite name for GHCR tags)
4. **Restore/prime Flatpak download cache** — Bluefin GUI suites only; caches a runner-side user Flatpak repo keyed on `flatpak-app-list.txt` hash
5. **Free disk space** — runs `<readonly-upstream>/remove-unwanted-software@v9`; keeps the 30 GB `disk.raw` allocation viable on GitHub-hosted runners
6. **Enable KVM** — udev rule for `/dev/kvm` access
7. **Install QEMU + pull OCI image** — parallel: `apt-get install qemu-system-x86` while `sudo podman pull <image>` and `sudo podman pull ghcr.io/<image-org>/testsuite:runner` run concurrently in background
8. **Generate SSH keypair** — creates `ed25519` keypair at `/tmp/vm_key`; public key stored in `VM_PUBKEY` env var
9. **Install OCI image and configure disk** — combined step that:
   - `fallocate -l 30G disk.raw`
   - `bootc install to-disk --via-loopback disk.raw --filesystem ext4` (with `--bootloader systemd` flag when bootc ≥0.1.13; older images skip the flag)
   - Mounts the raw disk, finds `ROOT_UUID` (partition 3), ostree deployment hash, and `KVER`
   - Copies `vmlinuz` + `initramfs.img` from deployment `usr/lib/modules/<kver>/` (or boot partition fallback)
   - Creates `boot.N` symlinks needed by `ostree-system-generator` (including canonical `boot.N` alias for versioned `boot.N.M` dirs produced by newer bootc)
   - Sets `KERNEL_ARGS` env (includes `root=UUID=...`, masked services, serial console, `selinux=0`)
   - Iterates all deployment directories and writes: `bluefin-test` user (UID 1001), GDM autologin, sshd drop-in `00-ci-auth.conf`, dconf `local.d/00-ci-testing` override, `tmpfiles.d/ci-user.conf`, masked service symlinks
   - Pre-installs `unsafe-mode@bluefin-test` gnome-shell extension files into var home (pre-boot, so gnome-shell finds it during `_loadExtensions()`)
   - Injects SSH authorized key into `/var/home/bluefin-test/.ssh/` and each deployment's `/etc/ssh/ci-authorized-keys`
10. **Boot VM** — `qemu-system-x86_64` with KVM, 4 GB RAM, 4 vCPUs, `virtio-gpu-pci`, forwarded SSH on port 2222; daemonized; QEMU monitor socket at `/tmp/qemu-monitor.sock` (chmod 666)
11. **Wait for SSH** — polls port 2222 up to **15 minutes** (900 s)
12. **Pre-stage target image via bootc switch** — lifecycle suite only, when `inputs.target-image` is set; SSHes into VM and runs `sudo bootc switch '<target-image>'` to stage the upgrade target before the test run
13. **Dump VM serial log** — always runs (`if: always()`); primary debug tool when SSH never comes up
14. **Wait for GNOME session** — polls `/run/user/1001/wayland-0` up to 3 minutes
15. **Capture boot time** — SSHes in, runs `systemd-analyze time`, appends result to `$GITHUB_STEP_SUMMARY`
16. **Install cached Flatpaks in VM** — Bluefin GUI suites (non-common/non-lifecycle) only; SCPs a tarred runner-side Flatpak repo into the VM and deploys missing apps with `sudo flatpak install --system --sideload-repo=...`, falling back to Flathub if cache is incomplete
17. **Install shell tools for common suite** — common suite only; installs `zsh`, `fish`, and brew CLI tools (`fzf`, `bat`, `eza`, `fd`, `ripgrep`, `starship`) via brew (if available) or `rpm-ostree --apply-live` / `dnf` fallback; `brew-setup.service` is masked in CI so these are installed manually
18. **Load runner container into VM** — non-common suites; ensures `bluefin-test` has `/etc/subuid`/`/etc/subgid`, runs `podman system migrate`, pipes `ghcr.io/<image-org>/testsuite:runner` via `podman save | ssh podman load`; patches `openssh-clients` into the runner image if missing
19. **Install Python test stack** — non-common suites; loads `uinput` kernel module, sets device permissions, copies SSH private key into VM for `@plain_ssh` scenarios, queries GNOME session environment into `/tmp/session.env`, enables `unsafe-mode@bluefin-test` extension, sets `toolkit-accessibility true`, re-queries AT-SPI bus address after enabling accessibility, terminates any pre-started `gnome-control-center`
20. **Install gnome-ponytail-daemon** — non-common suites; builds `gnome-ponytail-daemon` (tag `0.0.11`) and `grim` from source inside a `debian:bookworm` container on the runner (without libei, uses Mutter D-Bus fallback for input events; wayland-protocols 1.37 built from source for grim); SCPs binaries into `~/.local/libexec/` and `~/.local/bin/`; registers D-Bus service file and pre-starts the daemon
21. **Run behave suite** — `common`/`lifecycle`: runner-side `python3 tests/shared/behave_retry.py` with `VM_IP/VM_USER/SSH_KEY/SSH_PORT` env vars; GUI suites: SCP `tests/<suite>` + `tests/shared` + `tests/__init__.py` to VM, then `podman run ... ghcr.io/<image-org>/testsuite:runner "python3 .../behave_retry.py ... --format json.pretty"` inside VM; always `--tags ~quarantine`; retries controlled by `BEHAVE_RETRIES=2`
22. **Capture post-upgrade desktop screenshot** — lifecycle suite only; SSHes with `ControlMaster=no`, waits up to 60 s for Wayland socket, captures via `gdbus org.gnome.Shell.Eval`
23. **Capture post-migration screenshot and status** — lifecycle suite only; QEMU framebuffer capture via `qemu_screendump.py` + SSH for `bootc status`, `fastfetch`, `os-release` into `results/migration-status.txt`
24. **Capture Flatpak screenshots** — when `inputs.screenshot_flatpaks != ''`; runs `screenshot_cli.py` inside the runner container
25. **Capture desktop screenshot (QEMU screendump fallback)** — non-common suites; if no `screenshot_*fastfetch*.png` found in `results/`, captures QEMU VGA framebuffer via `/tmp/qemu-monitor.sock`
26. **Promote desktop screenshot** — finds best screenshot (`screenshot-post-migration.png` > upgrade > fastfetch); for non-common/non-lifecycle suites, fails loud if no screenshot found
27. **Push desktop screenshot to GHCR** — pushes `:<short-sha>`, `:<SCREENSHOT_SUITE>-latest`, and `:<image-slug>-<SCREENSHOT_SUITE>-latest` tags; also pushes per-Flatpak gallery tags
28. **Write job summary** — parses `results.json`, writes pass/fail table + failed scenarios; includes quarantine age summary from `scripts/check_quarantine_age.py --json`; includes screenshot pull commands and gh-pages URL
29. **Prepare artifact metadata** — writes `results/artifact-metadata.json`; computes `artifact_suffix` by sanitizing the full image reference (not just image name — the full `ghcr.io/org/image:tag` string is sanitized)
30. **Upload results artifact** — `e2e-results-<artifact-suffix>-<suite>` (30 days); includes `results.json`, `results.txt`, `artifact-metadata.json`, and any screenshots
31. **Upload serial log artifact** — `vm-serial-log-<artifact-suffix>-<suite>` (3 days)
32. **Fail job if tests failed** — exits with behave's return code
33. **Write + upload e2e metadata** — writes `meta/e2e-metadata.json` (`image`, `suite`, `conclusion`); uploaded as `e2e-metadata-<suite>` artifact (1 day)

Smoke-suite correctness rule: commands launched with plain `subprocess.run()` execute in the qecore runner container, not necessarily against the VM host state. In `tests/smoke/features/steps/system_health_steps.py`, host-facing probes (`systemctl`, `journalctl`, `df`, `getent hosts`, etc.) must use the VM helper (`_run_host()`). Using `_run()` for those checks only tests the runner container and can miss VM regressions.

## Image requirements


The OCI image under test **must**:

- Be a bootc/ostree image (`bootc install to-disk` compatible)
- Include GNOME + GDM
- Have `python3` available in the deployment

**`gnome-ponytail-daemon` is built at runtime** — the workflow compiles it from source in a `debian:bookworm` container on the runner and SCPs the binary into the VM. The image does NOT need to ship `gnome-ponytail-daemon`. (See step 20 above.)

The workflow injects the test user, SSH keys, autologin config, and the unsafe-mode gnome-shell extension at disk-prep time — nothing needs to be baked into the image for those.

## Artifacts


| Artifact | Content | Retention |
|----------|---------|-----------|
| `e2e-results-<artifact-suffix>-<suite>` | `results.json` (behave JSON), `results.txt` (pretty output), `artifact-metadata.json` (image + suite metadata), screenshots, `migration-status.txt` (lifecycle only) | 30 days |
| `vm-serial-log-<artifact-suffix>-<suite>` | QEMU serial console output | 3 days |
| `e2e-metadata-<suite>` | `e2e-metadata.json` — `{"image":…,"suite":…,"conclusion":…}` for downstream promotion jobs | 1 day |

`<artifact-suffix>` is derived by sanitizing the full image reference (e.g. `ghcr.io/<image-org>/bluefin:testing` → `ghcr.io-projectbluefin-bluefin-testing`), not just the image name.

The serial log is always uploaded (even on failure) — it's the primary debug tool when the VM doesn't boot or SSH never comes up.

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

## zstd:chunked migration toggle


The `@zstd_chunked` tag gates the final-state migration scenario. It is **skipped** (not failed) when disabled.

| Workflow input | Effect |
|---|---|
| `chunked_enabled: false` (default) | `@zstd_chunked` scenarios skip |
| `chunked_enabled: true` | `@zstd_chunked` scenarios run |

Enable once `ghcr.io/<image-org>/bluefin:latest` ships `tar+zstd` OCI layers. Verify:
```bash
skopeo inspect --raw docker://ghcr.io/<image-org>/bluefin:latest \
  | jq '.layers[0].mediaType'
```

---

## Running migration tests manually


Use `migration-test.yml` in `<image-org>/actions` to run only the `@migration` scenario group.

**Go to:** [<image-org>/actions → Actions → bootc Migration Test → Run workflow](https://github.com/<image-org>/actions/actions/workflows/migration-test.yml)

| Field | Non-LTS | LTS |
|---|---|---|
| `source_image` | `ghcr.io/<readonly-upstream>/bluefin:latest` | `ghcr.io/<readonly-upstream>/bluefin-lts:lts` |
| `migration_target` | _(leave blank)_ | `ghcr.io/<image-org>/bluefin-lts:stable` |
| `chunked_enabled` | `false` (default) | `false` (default) |

Wire as a consumer post-build gate:
```yaml
migration-test:
  needs: build
  uses: <image-org>/actions/.github/workflows/migration-test.yml@<ref>
  with:
    source_image: ghcr.io/<readonly-upstream>/bluefin-lts:lts
    migration_target: ghcr.io/<image-org>/bluefin-lts@${{ needs.build.outputs.digest }}
```

For non-migration lifecycle runs: dispatch `upgrade-test.yml` in `<image-org>/actions`.

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

## Gating :testing behind a post-build smoke check


Every consuming repo has a local `run-testsuite.yml` wrapper that pins the testsuite SHA. **Always call the wrapper — never call `<image-org>/testsuite/.github/workflows/e2e.yml` directly.** Renovate manages the SHA in one place; all callers inherit it automatically.

### `publish_stream_tag: "false"` — the gate input

`<image-org>/actions/.github/workflows/reusable-build.yml` has a `publish_stream_tag` input (default `"true"`). When set to `"false"`, the build pushes only the SHA-tagged image (`:$sha`) and withholds the stream tag (`:testing`, `:stable`). The post-build smoke workflow promotes the stream tag only after smoke passes.

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

## Dashboard seeding — initial population


If the `https://projectbluefin.github.io/testsuite/` dashboard shows "No JSONL results found" or no screenshots, the GHCR slug tags don't exist yet. Trigger manual e2e runs to populate them:

```bash
# Trigger smoke runs for each image (each takes ~2h)
gh workflow run "Manual Test Run" --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin:testing -f suites=smoke

gh workflow run "Manual Test Run" --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin-lts:testing -f suites=smoke

gh workflow run "Manual Test Run" --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/dakota:testing -f suites=smoke

# After runs complete, trigger publish immediately (instead of waiting 2h schedule):
gh workflow run publish-to-pages.yml --repo <image-org>/testsuite
```

Prerequisites: GHCR cross-repo package write access must be granted first (see above).

---

## On-demand references

Load these when you hit the specific topic:

- [How downstream repos call the reusable e2e workflow.](references/downstream-call.md)
- [Deep dive: Common Rationalizations](references/common-rationalizations.md)
- [Workflow inputs, outputs, artifacts, and screenshot handling.](references/inputs-outputs.md)
- [Troubleshooting e2e workflow failures and flake signatures.](references/troubleshooting.md)
- [Permission and runtime constraints when calling the reusable action.](references/permissions.md)
