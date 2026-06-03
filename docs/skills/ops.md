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

**Symptom:** `manual.yml` workflow_dispatch runs fail immediately with `startup_failure`. No jobs start.

**Cause:** GitHub Actions returns `startup_failure` when a `workflow_dispatch` workflow calls a same-repo reusable workflow with an **explicit ref**: `uses: ./.github/workflows/e2e.yml@main` or `uses: ./.github/workflows/e2e.yml@<sha>`. A bare local-ref call works fine.

**Fix (PR #245):** Use the bare local path — no `@ref`:
```yaml
uses: ./.github/workflows/e2e.yml    # works
# NOT:
# uses: ./.github/workflows/e2e.yml@main   # startup_failure
```

Cross-repo reusable workflow calls (`projectbluefin/testsuite/.github/workflows/e2e.yml@<sha>`) always work — that is how `nightly.yml → upgrade-test.yml → e2e.yml` runs.

**For lifecycle manual runs:** dispatch `upgrade-test.yml` in `projectbluefin/actions` — it calls `e2e.yml` cross-repo which supports `workflow_dispatch` with all lifecycle inputs.

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

---

## Python 3.14: sys.executable is empty in --pid=host containers

**Symptom:** All behave scenarios fail with `PermissionError: [Errno 13] Permission denied: ''` at `behave_retry.py` line ~134. The traceback ends at `subprocess.run(['', '-m', 'behave', ...])`.

**Cause:** Python 3.14 sets `sys.executable = ''` inside podman containers launched with `--pid=host`. `behave_retry.py` previously used `sys.executable` directly to re-invoke behave. An empty string causes subprocess to try to open a file named `''`, which fails with EACCES.

**Fix (in `tests/shared/behave_retry.py`):** `_find_python()` function probes `sys.executable`, then `shutil.which("python3")`, then known absolute paths. Always resolves to a real interpreter before invoking behave as a subprocess.

**Containerfile does not need to change** — this is a Python runtime issue. The fix is entirely in `behave_retry.py`.

## gobject-introspection and procps-ng required in Containerfile.runner

**Symptom (gobject-introspection):** Runner container load succeeds but behave immediately crashes:
```
gi.RepositoryError: Typelib file for namespace 'xlib', version '2.0' not found
```

**Cause:** Fedora 44 / `fedora-minimal` with `--setopt=install_weak_deps=0` does NOT install `gobject-introspection` as a weak dep of `python3-gobject`, even though it owns `/usr/lib64/girepository-1.0/xlib-2.0.typelib` (and many others). This typelib is required by dogtail/qecore at import time.

**Fix:** Explicitly add `gobject-introspection` to the `microdnf install` block in `container/Containerfile.runner`.

---

**Symptom (procps-ng):** `qecore-headless` wrapper exits immediately with:
```
bash: pgrep: command not found
```

**Cause:** `procps-ng` provides `pgrep`/`pkill`. `fedora-minimal` + `install_weak_deps=0` does not include it.

**Fix:** Explicitly add `procps-ng` to the `microdnf install` block.

After changing `Containerfile.runner`, dispatch the `build-runner.yml` workflow to rebuild and push the runner image before dispatching any test run that uses it.

## XDG_SESSION_TYPE and XDG_SESSION_DESKTOP must be forwarded to runner container

**Symptom:** behave starts but qecore raises `KeyError('XDG_SESSION_TYPE')` or sets `XDG_SESSION_TYPE=__unavailable__`, causing all AT-SPI calls to fail silently.

**Cause:** qecore-headless tries to read `XDG_SESSION_TYPE` and `XDG_SESSION_DESKTOP` from `/proc/<gnome-session-pid>/environ`. Inside `--pid=host` containers the proc read fails (permission denied), so qecore falls back to `__unavailable__` — a mode that bypasses all GNOME session setup.

**Fix (in e2e.yml):** Two places must be updated:
1. When writing `session.env`, add:
   ```bash
   printf 'export XDG_SESSION_TYPE=wayland\nexport XDG_SESSION_DESKTOP=gnome\n' >> /tmp/session.env
   ```
2. When invoking `podman run`, pass:
   ```bash
   -e XDG_SESSION_TYPE=wayland \
   -e XDG_SESSION_DESKTOP=gnome \
   ```

Both are required — `session.env` is sourced for the qecore boot path; `-e` flags cover any direct env lookup before sourcing.

## environment.py: guard before_scenario and after_scenario for failed_setup

**Symptom:** If `before_all` fails (e.g. `TestSandbox` init raises), all scenarios crash with `AttributeError: 'Context' object has no attribute 'sandbox'`, and each crash appears as a test failure rather than a setup skip.

**Cause:** `before_scenario` calls `context.sandbox.before_scenario(...)` unconditionally; `after_scenario` calls `context.sandbox.after_scenario(...)` unconditionally. If `before_all` raised before assigning `context.sandbox`, both hooks fail for every scenario.

**Fix pattern** (applies to every suite's `environment.py`):

```python
def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine
    if skip_quarantine(scenario):
        return
    if getattr(context, 'failed_setup', None):    # GUARD: skip if before_all failed
        try:
            scenario.skip(reason=context.failed_setup)
        except TypeError:
            scenario.skip()
        return
    context.scenario = scenario
    ...

def after_scenario(context, scenario) -> None:
    if getattr(context, 'failed_setup', None):    # GUARD: skip cleanup on failure
        return
    record_end(context, scenario)
    if scenario.status.name in ('passed', 'failed'):
        ...
    if hasattr(context, 'sandbox'):               # GUARD: sandbox may not exist
        context.sandbox.after_scenario(context, scenario)
```

All current suites (smoke, developer, software, dx, bazzite, lifecycle) must have both guards.

**⚠️ CRITICAL:** Use `getattr(context, 'failed_setup', None)` (truthiness check), NOT `hasattr(context, 'failed_setup')`. `TestSandbox.__init__` sets `context.failed_setup = None` on **every** run (even success), so `hasattr()` is always `True` and causes ALL scenarios to skip immediately. This was the root cause of 82/82 scenarios skipping in PR #255 debugging (commit f5647b2).

Also use `scenario.skip()` (the argument), NOT `context.scenario.skip()` — `context.scenario` is not set yet at this guard point.

## test_ref and github.ref_name in workflow_call vs workflow_dispatch

**Symptom:** Tests always run from `main` even when dispatching `manual.yml` from a feature branch. The `test_ref` input shows `main` in the run inputs despite the branch being something else.

**Cause:** `github.ref_name` inside a `workflow_call` reusable workflow resolves to the **default branch** (`main`), not the caller's branch. This is a GitHub Actions platform behavior.

**Fix:** Set `test_ref` in `manual.yml` (the `workflow_dispatch` side), where `github.ref_name` DOES correctly reflect the dispatched branch:

```yaml
# manual.yml
jobs:
  test:
    uses: ./.github/workflows/e2e.yml
    with:
      test_ref: ${{ github.event.inputs.test_ref || github.ref_name }}
```

The fallback chain is: user-supplied override → dispatched branch name → (never) empty. The old `|| 'main'` fallback was wrong and caused all dispatch runs to pull tests from main.

**Rule:** Never use `github.ref_name` as a test-checkout ref inside `e2e.yml` itself — it always gives `main` there. Pass `test_ref` through from the caller.

---

## machine-id empty in Fedora-minimal (D-Bus / ponytail fails)

**Symptom:** Container starts but every test shows:
```
org.freedesktop.DBus.Error.InvalidFileContent: D-Bus library appears to be incorrectly
set up … UUID file '/etc/machine-id' should contain a hex string of length 32, not length 0
```
Ponytail init fails; `sandbox.before_scenario` → `overview_action("hide")` → RuntimeError/AttributeError in every scenario.

**Cause:** `fedora-minimal` ships `/etc/machine-id` as a **zero-length file**. D-Bus refuses to initialize without a valid 32-hex-char UUID in that file.

**Fix (in `container/Containerfile.runner`)** — add after the `microdnf install` block (requires `dbus-tools`):
```dockerfile
RUN dbus-uuidgen > /etc/machine-id && \
    mkdir -p /var/lib/dbus && \
    ln -sf /etc/machine-id /var/lib/dbus/machine-id
```

Fixed in PR #255 commit ea14b33. Always rebuild the runner image after this change.

---

## ponytail hook_error: overview_action → click → window_id chain

**Symptom:** Every non-skipped scenario shows `hook_error` in behave JSON. Log shows:
```
HOOK_ERROR in before_scenario:
  overview_action(action="hide")
  → activities_toggle_button.click()
  → dogtail tree.py: window_id
  → ponytail_helper.get_window_id()
  → RuntimeError / AttributeError: 'NoneType' has no attribute 'window_list'
```

**Cause:** `sandbox.before_scenario` calls `overview_action("hide")` to reset GNOME Shell state. This requires ponytail (input injection) to click the Activities button. In a container where gnome-ponytail-daemon is unreachable, the chain raises.

**Two-layer fix:**

1. **Containerfile** — patch `dogtail/ponytail_helper.py` in the runner image:
```python
# get_ponytail_interface(): return None instead of raising RuntimeError
src = src.replace(
    'raise RuntimeError(self.error_message)',
    'print(f"WARNING: ponytail unavailable: {self.error_message}", flush=True); return None',
)
# get_window_id(): add None-guard after get_ponytail_interface() call
src = re.sub(
    r'(ponytail_interface\s*=\s*self\.get_ponytail_interface\(\))',
    r'\1\n        if ponytail_interface is None:\n            return None',
    src,
)
```

2. **environment.py** — catch the exception from `sandbox.before_scenario` and continue:
```python
try:
    sandbox.before_scenario(context, scenario)
except (RuntimeError, AttributeError) as e:
    # ponytail unavailable — overview_action failed; steps run anyway
    print(f"WARNING: sandbox.before_scenario ponytail error: {type(e).__name__}: {e}", flush=True)
except Exception:
    tb = traceback.format_exc()
    print(f"HOOK_ERROR in before_scenario:\n{tb}", flush=True)
    raise
```

Both layers are needed: the Containerfile patch eliminates the error at source; the environment.py catch is belt-and-suspenders for any ponytail path not yet patched.

Fixed in PR #255 commits f0e5259 + 4f54fcf.

---

## results.json artifact captures first-pass only

**Symptom:** You download the `e2e-results-*` artifact and see all scenarios as `hook_error` or `failed`, but the job log text says "N scenarios passed".

**Cause:** `behave_retry.py` runs behave up to 3 times. The `results.json` artifact is written after the **first pass** and is not overwritten by retries. Only the text summary lines in the job log reflect the true final state.

**Rule:** Always grep the job log for the last `scenarios passed` line to get true counts:
```bash
gh api "repos/org/repo/actions/jobs/$JOB_ID/logs" | grep "scenarios passed" | tail -3
```
Three lines appear (one per pass). The last line is the final result.

---

## setuptools / pkg_resources missing in Python 3.14

**Symptom:** Traceback spam per scenario during behave run:
```
ModuleNotFoundError: No module named 'pkg_resources'
  File ".../qecore/sandbox.py", line NNN, in _attach_version_status_to_report
```

**Cause:** `pkg_resources` is part of `setuptools`, which is not installed by default in Python 3.14. qecore's `_attach_version_status_to_report` uses it to report installed package versions in test reports.

**Fix:** Add `setuptools` to the pip install in `container/Containerfile.runner`. Fixed in PR #255 commit ea14b33.
