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

---

## zstd:chunked migration toggle

The `@zstd_chunked` tag gates the final-state migration scenario (unified storage + zstd:chunked layers).
It is **skipped** (not failed) when disabled.

| Toggle | Default | Effect |
|---|---|---|
| `ZSTD_CHUNKED=true` | on | `@zstd_chunked` scenarios run |
| `ZSTD_CHUNKED=false` | — | `@zstd_chunked` scenarios are skipped |
| `chunked_enabled: false` (workflow input) | default | sets `ZSTD_CHUNKED=false` |
| `chunked_enabled: true` (workflow input) | — | sets `ZSTD_CHUNKED=true` |

**Enable once** `ghcr.io/projectbluefin/bluefin:latest` ships with `tar+zstd` OCI layers.
Verify via `skopeo inspect --raw docker://ghcr.io/projectbluefin/bluefin:latest | jq '.layers[0].mediaType'`.

**Run the lifecycle test manually:**
Go to [projectbluefin/actions → Actions → bootc Upgrade and Rollback Test → Run workflow](https://github.com/projectbluefin/actions/actions/workflows/upgrade-test.yml).
- Default: runs lifecycle suite without `@zstd_chunked`
- With `chunked_enabled: true`: also tests zstd:chunked lane

---

## manual.yml startup_failure (same-repo reusable workflow bug)

**Symptom:** `manual.yml` workflow_dispatch runs always fail immediately with `startup_failure`. No jobs start. No log available.

**Cause:** GitHub Actions returns `startup_failure` when a `workflow_dispatch` workflow calls a reusable workflow in the **same repository** via either `uses: ./.github/workflows/e2e.yml` or `uses: projectbluefin/testsuite/.github/workflows/e2e.yml@ref`. Cross-repo reusable workflow calls (like `nightly.yml → upgrade-test.yml → e2e.yml`) work fine.

**Workaround:** Use `upgrade-test.yml` in `projectbluefin/actions` for manual lifecycle runs — it calls `e2e.yml` cross-repo and has `workflow_dispatch` support.

**Do not attempt to fix** `manual.yml` by changing the ref format or adding `permissions:`. The failure is a GitHub platform limitation with same-repo reusable workflow calls from `workflow_dispatch`.

---

## Post-upgrade desktop screenshot

After a lifecycle suite run, `e2e.yml` captures a full-screen GNOME screenshot via:
```bash
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "const Shell = imports.gi.Shell; const s = new Shell.Screenshot(); s.screenshot(false, false, '/tmp/upgrade_screenshot.png', () => {}); 'ok'"
```
The screenshot is saved to `results/screenshot_lifecycle_upgrade_final.png` and promoted to the `desktop-screenshot` workflow artifact. The step uses `ControlMaster=no` because the VM may have rebooted during the lifecycle suite, invalidating any existing SSH multiplex socket.

The step waits up to 60 s for the Wayland socket (`/run/user/1001/wayland-0`) before attempting the screenshot.
