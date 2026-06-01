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
2. `e2e.yml` sets `BEHAVE_TAG_ARGS="--tags ~quarantine"` before calling `behave_retry.py`.

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

## gnomeos: python-uinput build fails (no gcc)

**Symptom:** `pip install python-uinput` fails with `x86_64-unknown-linux-gnu-gcc: not found` or `gcc: not found`.

**Cause:** GNOME OS is compiled with a cross-toolchain. Python's build system looks for the cross-compiler, not the native `gcc`. Even setting `CC=gcc` only helps if `gcc` is present — on gnomeos it is not.

**Consequence:** Any scenario that uses `Type text: "X" with uinput` **cannot run on gnomeos** and must be `@quarantine`d.

**Workaround in e2e.yml:**
```bash
CC=gcc pip install python-uinput || echo "WARNING: python-uinput unavailable — keyboard input scenarios will be skipped"
```

The step continues (not `set -e` fatal) so other scenarios proceed.

## NVIDIA services always fail in QEMU

**Symptom:** `system_health.feature` fails with "failed units found" on nvidia-open images running in QEMU.

**Units:** `nvidia-persistenced.service` and `ublue-nvctk-cdi.service`

**Cause:** These services require a physical NVIDIA GPU. In QEMU with virtio-gpu, they fail unconditionally.

**Fix:** Both services are in `IGNORED_FAILED_UNITS_IN_VM` in `tests/smoke/features/steps/system_health_steps.py`. Do not remove them.

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
