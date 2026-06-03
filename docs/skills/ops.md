# Operational Gotchas

Load when: a VM boots to GDM greeter, or you're debugging infra-layer failures.

These are testsuite-affecting infra issues. This doc records the symptoms and workarounds agents need mid-task.

## Fedora version targets (where each Fedora version is used)

Three different Fedora versions appear in this repo. They are not interchangeable:

| Context | Fedora version | Why |
|---|---|---|
| **`behave --dry-run` CI container** (`pr-validate.yml`) | `fedora:41` (pinned digest) | qecore/dogtail/GObject ABI target; PyGObject from Ubuntu breaks |
| **Test runner image** (`container/Containerfile.runner`) | `fedora-minimal:latest` (rebuilt weekly) | Base for the runner container shipped to the VM; needs Python + pip + GObject |
| **OS under test (gnomeos)** | `gnomeos-latest` (≈ Fedora 44 / GNOME 50) | The actual GNOME upstream image from `quay.io/gnome_infrastructure/gnome-build-meta` |
| **OS under test (Bluefin)** | Fedora 41 based (for stable/gts/lts) | Do NOT test against F42 — Bluefin does not ship it |

**Never try F42**: there is no Bluefin or Bazzite image based on Fedora 42. If a test or workflow mentions F42, it is wrong.

## GDM autologin required

**Symptom:** VM boots but all scenarios fail in `before_scenario` with `gnome-ponytail-daemon` D-Bus name not activatable. Zero tests run.

**Cause:** `bib-disk-configure` did not write GDM autologin config. VM boots to GDM greeter — no graphical session starts, so `gnome-ponytail-daemon` cannot activate.

**Required config** (must be on the golden disk image):
```ini
# /etc/gdm/custom.conf
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=bluefin-test
```

**Fix:** Open an issue in the image repo referencing the `bib-disk-configure` step. Do not add this workaround to testsuite step code.

Tracked: testsuite issue #33.

## SSH step timeout tuning

Default `run_ssh()` timeout is **60 seconds**, not 30. Hardware commands (bootc upgrade, disk ops, systemctl restart) are slow in emulated VMs. If a step times out at 30s, check the `timeout=` kwarg in `tests/shared/ssh_steps.py` — you can override it per-call:

```python
run_ssh(context, "sudo bootc upgrade", timeout=180)
```

Never lower the default below 60s.

## sys.exit(1) in before_scenario kills behave — always use raise

**Symptom:** All scenarios from the second failure onward appear to pass (not run), but behave exits non-zero and only shows the first failure in logs.

**Cause:** `sys.exit(1)` inside `before_scenario` (or anywhere in a before-hook) raises `SystemExit`, which is caught by qecore and propagated, but it terminates the entire behave process — not just the current scenario.

**Fix:** Replace every `sys.exit(1)` with `raise` (re-raises the exception and lets behave mark the scenario failed, then continues). Check all `environment.py` files:

```bash
grep -r "sys.exit" tests/*/features/environment.py
```

Should return nothing. Any hit must be replaced with `raise`.

## GNOME 50 requires qecore >= 4.12

**Symptom:** `GetWindows` returns `AccessDenied`; `unsafe_mode` is never set; `Shell.Eval` returns `""`.

**Cause:** qecore 3.35.3 on Fedora 44 uses a unit name pattern that never matched GNOME 50's gnome-shell unit, so `unsafe_mode` was never activated. All AT-SPI window queries fail silently.

**Fix:** `e2e.yml` pins `qecore>=4.12` in the pip install step. Do not downgrade.

## @quarantine tag enforcement

**Symptom:** Scenarios tagged `@quarantine` run anyway and fail.

**Cause:** The `@quarantine` tag was historically cosmetic — `--tags ~quarantine` was never passed to behave. The `skip_quarantine()` helper in `tests/shared/quarantine.py` does skip inside `before_scenario`, but only if the scenario reaches that hook (retries pass the raw failing entries without re-checking tags).

**Fix (now in place, two layers):**
1. `behave_retry.py` calls `with_quarantine_filter()` which always appends `--tags ~@quarantine` to the behave invocation.
2. `e2e.yml` sets `BEHAVE_TAG_ARGS="--tags ~@quarantine"` before calling `behave_retry.py`.

Both layers are required. Do not remove either.

## --bootloader flag requires bootc >= 0.1.13

**Symptom:** `bootc install to-disk --bootloader systemd` fails with `unrecognized flag`.

**Cause:** The `--bootloader` flag was added in bootc 0.1.13. Older LTS images ship an earlier bootc.

**Fix (in e2e.yml):**
```bash
BOOTLOADER_ARG=""
if bootc install to-disk --help 2>&1 | grep -q '\-\-bootloader'; then
  BOOTLOADER_ARG="--bootloader systemd"
fi
bootc install to-disk $BOOTLOADER_ARG ...
```

Always probe before using. Never hard-code `--bootloader`.

## python-uinput now builds in the runner image

**Previous symptom:** `pip install python-uinput` failed with `x86_64-unknown-linux-gnu-gcc: not found` or `gcc: not found`.

**Current state:** PR #192 installs `gcc` and `python3-devel` before `pip install python-uinput`, so uinput-backed keyboard scenarios no longer need `@quarantine` for that reason alone.

**What to do now:** If a `Type text: "X" with uinput` scenario fails, treat it as a test or app regression and investigate the actual failure instead of assuming the runner image cannot build python-uinput.

## NVIDIA services always fail in QEMU

**Symptom:** `system_health.feature` fails with "failed units found" on nvidia-open images running in QEMU.

**Units:** `nvidia-persistenced.service` and `ublue-nvctk-cdi.service`

**Cause:** These services require a physical NVIDIA GPU. In QEMU with virtio-gpu, they fail unconditionally.

**Fix:** Both services are in `IGNORED_FAILED_UNITS_IN_VM` in `tests/smoke/features/steps/system_health_steps.py`. Do not remove them.

## Rootless podman load fails in VM (exit 125)

**Symptom:** "Load runner container into VM" step exits 125. Error in the step log:

```
lchown /var/spool/mail: invalid argument
potentially insufficient UIDs or GIDs available in user namespace (requested 0:12 ...)
Check /etc/subuid and /etc/subgid if configured locally and run "podman system migrate"
```

**Cause:** The Fedora 44 `fedora-minimal` base image (used in the runner container since PR #218) has a layer that sets `/var/spool/mail` ownership to `root:mail` (uid=0, gid=12). Rootless podman needs `bluefin-test` to have `/etc/subuid`/`/etc/subgid` entries to map this gid — but the BIB-built golden disk may not include them.

The old Fedora 42 runner base did not have this layer so the issue was invisible until the base was pinned to Fedora 44.

**Fix (in e2e.yml):** Before calling `podman load`, ensure the mappings exist and migrate:

```bash
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 \
  "sudo bash -c 'grep -q bluefin-test /etc/subuid || echo \"bluefin-test:100000:65536\" >> /etc/subuid; \
   grep -q bluefin-test /etc/subgid || echo \"bluefin-test:100000:65536\" >> /etc/subgid'"
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 podman system migrate 2>/dev/null || true
```

This is idempotent: it only appends if the entry is absent.

**DO NOT** try to fix this by switching to `sudo podman load` — that puts the image in root storage, but all `podman run` calls inside the VM run as `bluefin-test`. Keep the load rootless and fix subuid/subgid instead.

Tracked: fixed in PR #224 (2026-06-02).

## Direct kernel boot blocks migration VM reboots

**Symptom:** After `bootc switch` + `sudo reboot` inside the VM, the new deployment never takes effect — SSH reconnects to the **old** image.

**Cause:** `e2e.yml` launches QEMU with `-kernel vmlinuz -initrd initramfs.img -append KERNEL_ARGS`. The kernel args include an `ostree=` path pointing to the initial deployment hash. When QEMU restarts after `sudo reboot`, it re-uses the same command-line args and boots the **old** deployment unconditionally. systemd-boot is never consulted.

This is why `lifecycle/migration.feature` is listed in `suite-map.md` as "SSH-mode suites not yet in the GHA action" — the existing workflow cannot support migration testing.

**Fix:** Replace direct kernel boot with UEFI boot via OVMF pflash:
```yaml
- name: Install OVMF
  run: sudo apt-get install -y ovmf

- name: Launch QEMU (UEFI)
  run: |
    cp /usr/share/OVMF/OVMF_VARS.fd ./OVMF_VARS.fd
    sudo qemu-system-x86_64 \
      -machine q35,accel=kvm -cpu host -m 4096 -smp 4 \
      -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
      -drive if=pflash,format=raw,unit=1,file=./OVMF_VARS.fd \
      ...
```

After `bootc switch` + reboot, systemd-boot reads the **new** deployment's BLS entry and boots the migrated image.

UEFI boot also requires:
- `bootc install to-disk --bootloader systemd` (not `grub2`) to populate BLS entries
- CI kernel args written to **all** BLS entries in the ESP (not as QEMU kernel args)
- `loader.conf timeout 0` in the ESP to skip interactive boot menu in headless mode
- `/etc/selinux/config` and systemd service masks written as `/etc` symlinks (survives 3-way merge into new deployment)

Tracked: spike issue #229 verifies the UEFI approach on `ubuntu-latest`. Epic #227.

## unified_storage lane requires bootc ≥ 1.16

**Symptom:** `bootc switch --experimental-unified-storage <target>` fails with `error: unexpected argument '--experimental-unified-storage'`.

**Cause:** The `--experimental-unified-storage` flag is not present in bootc 1.15.x. Both `ghcr.io/ublue-os/bluefin:stable` (bootc 1.15.1) and `ghcr.io/projectbluefin/bluefin:stable` (bootc 1.15.2) as of 2026-06 lack this flag.

**Fix:** Always probe before using:
```bash
bootc switch --help 2>&1 | grep -q -- '--experimental-unified-storage'
```
If the flag is absent, skip the scenario gracefully. The `Check unified storage support and skip if unavailable` step in `tests/lifecycle/features/steps/steps.py` does this automatically (implemented in PR #235, closes #230).

## `unified_storage_overlay_present` step reads wrong context attribute

**Symptom:** The `unified_storage_overlay_present` behave step always evaluates the SSH return code as 1 (failed) even when the command succeeds.

**Cause (line 433 of `tests/lifecycle/features/steps/steps.py`):**
```python
rc = getattr(context, "command_returncode", 1)  # BUG
```
`run_ssh()` in `tests/shared/ssh_steps.py` sets `context.ssh_rc`, not `context.command_returncode`. The `getattr` default of `1` always fires.

**Fix:**
```python
rc = getattr(context, "ssh_rc", 1)
```

Fixed in PR feat/lifecycle/ublue-os-to-projectbluefin-migration (closes #228).

## rechunker-group-fix required before migration (ublue-os → projectbluefin)

**Symptom:** After `bootc switch` from `ghcr.io/ublue-os/bluefin` to `ghcr.io/projectbluefin/bluefin`, the first reboot shows a black screen (login manager never starts). The **second** reboot succeeds.

**Cause:** The legacy `ublue-os/legacy-rechunker` build process moves `/etc/group` entries to `/usr/lib/group` for `nss-altfiles`. The new `projectbluefin/bluefin` image (chunkah) does not ship `nss-altfiles`, so on first boot `/etc/gshadow` desyncs from `/etc/group` and `systemd-sysusers` fails.

**Fix:** `rechunker-group-fix` service + script, shipped in `projectbluefin/bluefin` (PR #18). This service runs once on first boot and reconciles gshadow. The second boot is always clean.

**Impact on migration tests:** The e2e test workflow boots the VM into the **migrated** image, not the legacy source. If `rechunker-group-fix` is absent from the target image, the migration tests will fail on the post-switch reboot with a timeout waiting for SSH.

References:
- https://github.com/ublue-os/bluefin/issues/3852
- https://github.com/ublue-os/bluefin-lts/issues/918
- https://github.com/bootc-dev/bootc/issues/1179

## YAML orphan keys in e2e.yml break merge queue

**Symptom:** PRs fail merge queue validation with 0 jobs (`{"total_count":0,"jobs":[]}`). The nightly run may still work (YAML's last-wins for duplicate keys makes the workflow _load_, but GHA schema validation rejects it for queue contexts).

**Cause:** Any step block that is missing its `- name: StepName` header will have its `if:`, `id:`, and `run:` keys treated as duplicate/orphan keys on the prior step. `yaml.safe_load` silently uses last-wins. GHA's schema checker is stricter and rejects the file.

**How to spot:** Run `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/e2e.yml'))"` — it passes even on broken files. Instead, visually scan for any `if:` / `id:` / `run:` that appears at the 8-space indent level _without_ a preceding `- name:` on the same level.

**Fix:** Always add `      - name: My Step Name` before each step's `if:`/`id:`/`run:`.

Tracked: fixed in PR #224 (2026-06-02).

## Running behave --dry-run for GNOME suites in CI

**Problem:** GNOME suites (smoke, bazzite, developer, dx, software, vanilla-gnome) import `qecore.sandbox` which loads `gi.repository.Atspi` at module import time. Without a real AT-SPI bus, `libatspi` calls `g_error()` → `SIGTRAP` (core dump). This happens even during `behave --dry-run`.

**Solution:** Use `dbus-run-session` to create a session bus, then start `at-spi-bus-launcher` before running behave. The required Fedora 41 packages:

```yaml
dnf install -y \
  python3-gobject \   # PyGObject (gi.repository.*)
  at-spi2-core \      # Atspi-2.0 typelib + at-spi-bus-launcher
  dbus-daemon \       # provides dbus-run-session (NOT dbus-tools, NOT dbus)
  gtk3 \              # Gtk-3.0 typelib
  gsettings-desktop-schemas  # org.gnome.desktop.interface (isA11yEnabled())
```

**Pattern (from `.github/workflows/pr-validate.yml`):**

```bash
cat > /tmp/dry-run.sh << 'DRYEOF'
/usr/libexec/at-spi-bus-launcher --launch-immediately &
sleep 1
# ... behave --dry-run loop ...
DRYEOF
chmod +x /tmp/dry-run.sh
dbus-run-session -- bash /tmp/dry-run.sh
```

**Key facts:**
- `dbus-run-session` is in `dbus-daemon` on Fedora 41 (not `dbus-tools` or `dbus`)
- `at-spi-bus-launcher` is at `/usr/libexec/at-spi-bus-launcher` from `at-spi2-core`
- `isA11yEnabled()` from dogtail reads `org.gnome.desktop.interface` → needs `gsettings-desktop-schemas`
- PyGObject from Ubuntu always fights ABI with the GHA toolcache Python → always use Fedora
- `dogtail` has a `tests/` package in site-packages that shadows local `tests/` → fix with empty `tests/__init__.py` (already in repo)
