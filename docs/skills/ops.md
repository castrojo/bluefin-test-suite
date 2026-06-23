---
name: ops-gotchas
description: "Operational gotchas for projectbluefin/testsuite — VM boot failures, GDM autologin, Containerfile.runner requirements, GNOME session setup, and infra traps agents hit mid-task."
metadata:
  type: reference
---

# Operational Gotchas

## When to Use
- VM boots to GDM greeter instead of a GNOME session
- Debugging infra-layer CI failures (runner container, D-Bus, AT-SPI)
- Adding new packages or patches to `container/Containerfile.runner`
- SSH assertion failures from unexpected output
- common-suite service health scenarios fail with unexpected `ActiveState` values
- Polkit rules presence check returns zero results

## When NOT to Use
- Writing behave step logic → `docs/skills/behave.md`
- GNOME AT-SPI/dogtail patterns → `docs/skills/gnome.md`
- bootc lifecycle steps → `docs/skills/bootc.md`
- Workflow inputs, migration runs, manual.yml → `docs/skills/e2e-workflow.md`

---

## Oneshot systemd service state — use Result, not ActiveState

**Symptom:** `common_services.feature` scenarios fail with output `inactive` when
checking `ActiveState --value` even though the service ran successfully.

**Cause:** Oneshot services transition to `ActiveState=inactive` (dead) after they
finish — this is correct behaviour, not a failure. Asserting `active` always fails
for completed oneshot units.

**Fix:** Check `Result --value` instead. A successfully completed oneshot reports
`Result=success`:

```bash
systemctl show ublue-system-setup.service --property=Result --value
# → success
```

Affected services: `rechunker-group-fix.service`, `ublue-system-setup.service`,
`ublue-user-setup.service` (--user), `dconf-update.service`,
`bootc-unified-storage.service`.

See `docs/skills/behave.md` "Shared SSH helpers" section for the feature-file pattern.

**Exception:** Services that are masked in CI (`flatpak-preinstall.service`,
`flatpak-nuke-fedora.service`) will have `Result=exit-code` or no result at all.
Keep those quarantined until the masking is removed at the image level.

---

## Polkit rules path — check both directories

**Symptom:** `common_polkit.feature` "polkit rules directory has Bluefin rules"
returns zero even though Bluefin ships polkit rules.

**Cause:** Bluefin ships polkit rules under `/usr/share/polkit-1/rules.d/` (immutable
layer, read-only). The test was only checking `/etc/polkit-1/rules.d/` (mutable
override path, empty on a stock Bluefin install).

**Fix:** Scan both paths:

```bash
ls /etc/polkit-1/rules.d/*.rules /usr/share/polkit-1/rules.d/*.rules 2>/dev/null | wc -l
```

This returns a non-zero count as long as rules exist in either location.

---

## Fedora version targets

Three Fedora versions appear in this repo. They are not interchangeable.

| Context | Fedora version | Why |
|---|---|---|
| **`behave --dry-run` CI container** (`pr-validate.yml`) | `fedora:41` (pinned digest) | qecore/dogtail/GObject ABI target; PyGObject from Ubuntu breaks |
| **Test runner image** (`container/Containerfile.runner`) | `fedora-minimal:latest` (rebuilt weekly) | Base for the runner container shipped to the VM |
| **OS under test (gnomeos)** | `gnomeos-latest` (≈ Fedora 44 / GNOME 50) | `quay.io/gnome_infrastructure/gnome-build-meta` |
| **OS under test (Bluefin)** | Fedora 41 based (stable/gts/lts) | Do NOT test against F42 — Bluefin does not ship it |

**Never use F42**: no Bluefin or Bazzite image is based on Fedora 42.

---

## GDM autologin required

**Symptom:** VM boots but all scenarios fail — `gnome-ponytail-daemon` D-Bus name not activatable. Zero tests run.

**Cause:** `bib-disk-configure` did not write GDM autologin config. VM boots to GDM greeter; no graphical session starts.

**Required config** (must be on the golden disk image):
```ini
# /etc/gdm/custom.conf
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=bluefin-test
```

Open an issue in the image repo referencing `bib-disk-configure`. Do not add this workaround to step code.

**GDM boot regression guard:** A `@health @gdm @regression` scenario in `system_health.feature` explicitly asserts `gdm.service` and `graphical.target` are both `active`. This catches the 2026-06-13 bluefin-lts emergency-console incident — if `gdm.service` fails, the VM boots to emergency console and all AT-SPI tests silently skip without a clear failure. If this scenario fails, check GDM autologin config above before investigating further.

---

## SSH step timeout

Default `run_ssh()` timeout is **60 seconds**, not 30. Hardware commands (bootc upgrade, disk ops) are slow in emulated VMs.

```python
run_ssh(context, "sudo bootc upgrade", timeout=180)
```

Never lower the default below 60s.

---

## Smoke suite: _run() vs _run_host() for network checks

**Symptom:** DNS health check in `system_health.feature` passes even when the VM has no connectivity.

**Cause:** `_run(cmd)` in the smoke suite executes on the test runner (inside the VM-side container), NOT in the actual VM guest OS. For network or system checks that need to reflect the VM's actual state, use `_run_host(cmd)` which executes in the VM via a shell bridge.

```python
# WRONG — tests the container's DNS, not the VM's
_run("getent hosts ghcr.io")

# CORRECT — tests DNS inside the VM
_run_host("getent hosts ghcr.io")
```

Use `_run_host()` for: DNS lookups, network connectivity, firewall state, systemd service status from the host OS.
Use `_run()` for: subprocess calls within the test runner environment (extension state via gdbus, GNOME shell interactions).

---

## sys.exit(1) in before_scenario kills behave

**Symptom:** All scenarios after the first failure appear to pass (not run). Behave exits non-zero but only shows the first failure.

**Cause:** `sys.exit(1)` inside `before_scenario` raises `SystemExit`, terminates the entire behave process.

**Fix:** Replace every `sys.exit(1)` with `raise`. Verify:
```bash
grep -r "sys.exit" tests/*/features/environment.py
# must return nothing
```

---

## GNOME 50 requires qecore >= 4.12

**Symptom:** `GetWindows` returns `AccessDenied`; `unsafe_mode` never set; `Shell.Eval` returns `""`.

**Cause:** qecore < 4.12 uses a unit name pattern that never matched GNOME 50's gnome-shell unit.

**Fix:** `e2e.yml` pins `qecore>=4.12`. Do not downgrade.

---

## OCI layer caching

Podman layers are cached at `/var/lib/containers/storage`, keyed by the resolved image digest.

- A cache hit skips the pull entirely; repeat runs drop from roughly 5-15 minutes to about 30 seconds for this stage.
- The cache invalidates automatically when the image digest changes.
- If you see digest-resolution failures in CI (for example `skopeo inspect` or manifest-inspect output), that is the cache-key resolution step — verify the image exists and is publicly accessible.

---

## @quarantine tag enforcement — two layers required

**Symptom:** Scenarios tagged `@quarantine` run and fail.

**How it works (two required layers):**
1. `behave_retry.py` calls `with_quarantine_filter()` — appends `--tags ~@quarantine` to every behave invocation.
2. `e2e.yml` sets `BEHAVE_TAG_ARGS="--tags ~@quarantine"` before calling `behave_retry.py`.

Do not remove either layer.

---

## --bootloader flag requires bootc >= 0.1.13

**Symptom:** `bootc install to-disk --bootloader systemd` fails with `unrecognized flag`.

Always probe before using:
```bash
BOOTLOADER_ARG=""
if bootc install to-disk --help 2>&1 | grep -q '\-\-bootloader'; then
  BOOTLOADER_ARG="--bootloader systemd"
fi
bootc install to-disk $BOOTLOADER_ARG ...
```

---

## NVIDIA services always fail in QEMU

`nvidia-persistenced.service` and `ublue-nvctk-cdi.service` require a physical GPU. Both are in `IGNORED_FAILED_UNITS_IN_VM` in `system_health_steps.py`. Do not remove them.

---

## systemd-oomd: both .service AND .socket fail in QEMU

`systemd-oomd` monitors PSI files under `/proc/pressure/` which QEMU VMs don't expose. Both `systemd-oomd.service` **and** `systemd-oomd.socket` are in `IGNORED_FAILED_UNITS_IN_VM`. When adding entries to the allowlist, always check if both the `.service` and its companion `.socket` need ignoring.

---

## Bazzite extension state: use GetExtensionInfo, not Shell.Eval

`Shell.Eval` + `Main.extensionManager.lookup(uuid)?.state` is unreliable on GNOME 50 (Bazzite). Use the stable D-Bus method:

```python
import subprocess, re

def _extension_state(context, uuid: str) -> str:
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell/Extensions',
         '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
         f"'{uuid}'"],   # GVariant string — single quotes required
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return "99"
    m = re.search(r"'state':\s*<uint32\s+(\d+)>", result.stdout)
    return m.group(1) if m else "99"
```

**CRITICAL — GVariant quoting:** UUIDs like `logomenu@aryan_k` contain `@` which is invalid bare GVariant. Always wrap in single quotes: `f"'{uuid}'"`.

Extension state values:

| State | Meaning |
|---|---|
| 1 | ENABLED |
| 2 | DISABLED |
| 3 | ERROR |
| 6 | INITIALIZED (transient — poll through) |
| 99 | UNINSTALLED / call failed |

Poll through states 6 and 8 with a timeout — Bazzite's 11 extensions can take up to 90 seconds to fully activate.

---

## Rootless podman load fails in VM (exit 125)

**Symptom:** "Load runner container into VM" step exits 125 with:
```
lchown /var/spool/mail: invalid argument
potentially insufficient UIDs or GIDs available in user namespace
```

**Cause:** `fedora-minimal` has a layer that sets `/var/spool/mail` to `root:mail`. Rootless podman needs subuid/subgid mappings for the test user.

**Fix (in e2e.yml):** Before `podman load`:
```bash
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 \
  "sudo bash -c 'grep -q bluefin-test /etc/subuid || echo \"bluefin-test:100000:65536\" >> /etc/subuid; \
   grep -q bluefin-test /etc/subgid || echo \"bluefin-test:100000:65536\" >> /etc/subgid'"
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 podman system migrate 2>/dev/null || true
```

Do NOT switch to `sudo podman load` — that puts the image in root storage, but all `podman run` calls in the VM run as `bluefin-test`.

---

## YAML orphan keys in e2e.yml

**Symptom:** PRs fail merge queue validation with `{"total_count":0,"jobs":[]}`.

**Cause:** A step block missing its `- name:` header has its `if:`, `id:`, and `run:` keys treated as orphan keys on the prior step. `yaml.safe_load` silently uses last-wins; GHA schema checker rejects it.

**How to spot:** Visually scan for any `if:` / `id:` / `run:` at the 8-space indent level without a preceding `- name:` on the same level. `yaml.safe_load` will not catch this.

Always add `      - name: My Step Name` before each step's body.

---

## Containerfile.runner requirements

When `container/Containerfile.runner` is changed, dispatch `build-runner.yml` to rebuild and push before dispatching test runs.

**Required packages** (all must be in the `microdnf install` block):

| Package | Why |
|---|---|
| `gobject-introspection` | Owns `xlib-2.0.typelib` and many others; NOT a weak dep on Fedora-minimal with `--setopt=install_weak_deps=0` |
| `procps-ng` | Provides `pgrep`/`pkill`; not in fedora-minimal |
| `gcc`, `python3-devel` | Required to build `python-uinput` from source |
| `dbus-tools` | Provides `dbus-uuidgen` (not `dbus-daemon`) |

**machine-id must be seeded:**
```dockerfile
RUN dbus-uuidgen > /etc/machine-id && \
    mkdir -p /var/lib/dbus && \
    ln -sf /etc/machine-id /var/lib/dbus/machine-id
```
`fedora-minimal` ships `/etc/machine-id` as a zero-length file. D-Bus refuses to start without a valid 32-hex UUID.

**setuptools must be explicit:**
`pkg_resources` (used by qecore) is part of `setuptools`, not installed by default in Python 3.14. Add `setuptools` to the pip install block.

**stop_display_manager must be wrapped:**
`qecore-headless` cleanup calls `stop_display_manager()` after the user script. Inside the runner container there is no systemd, so it raises `CalledProcessError`. Wrap it:
```python
try:
    if self.enable_stop or self.user_script_exit_code != 0:
        self.display_manager_control.stop_display_manager()
except Exception:
    pass
```
Without this, the container exits 1 even when all tests pass.

**rawinput ponytail None-guard:**
`sandbox.before_scenario` → `overview_action("hide")` → `rawinput.click()` → `ponytail_interface.window_list` crashes when ponytail is unreachable. Patch `ponytail_helper.py` in the runner image to return `None` instead of raising, and add a `None` guard before `.window_list`.

**qecore-headless env retrieval:**
`qecore-headless` reads `/proc/<pid>/environ` for GNOME session env. With `--pid=host`, this fails with `Permission denied`. The code must handle this gracefully (warn + continue) rather than `sys.exit(1)`.

---

## Python 3.14: sys.executable is empty in --pid=host containers

**Symptom:** All scenarios fail with `PermissionError: [Errno 13] Permission denied: ''` in `behave_retry.py`.

**Cause:** Python 3.14 sets `sys.executable = ''` inside podman `--pid=host` containers.

**Fix:** `_find_python()` in `behave_retry.py` probes `sys.executable`, then `shutil.which("python3")`, then known absolute paths. Never use `sys.executable` directly for subprocess invocation.

---

## XDG_SESSION_TYPE and XDG_SESSION_DESKTOP must be forwarded

**Symptom:** qecore raises `KeyError('XDG_SESSION_TYPE')` or sets it to `__unavailable__`, causing all AT-SPI calls to fail silently.

**Fix (two places in e2e.yml):**
1. When writing `session.env`:
   ```bash
   printf 'export XDG_SESSION_TYPE=wayland\nexport XDG_SESSION_DESKTOP=gnome\n' >> /tmp/session.env
   ```
2. When invoking `podman run`:
   ```bash
   -e XDG_SESSION_TYPE=wayland \
   -e XDG_SESSION_DESKTOP=gnome \
   ```

Both are required — `session.env` covers the qecore boot path; `-e` flags cover any direct env lookup.

---

## bootc install creates .0.origin alongside .0 — DEPLOY find must use -type d

**Symptom:** `Install OCI image and configure disk` fails with:
```
ls: cannot access '/mnt/root/ostree/deploy/default/deploy/<hash>.0.origin/usr/lib/modules/': Not a directory
deploy=<hash>.0.origin  kver=
ERROR: vmlinuz not found in deployment or boot partition
```

**Cause:** `bootc install to-disk` writes two entries in the deploy directory:
- `<hash>.0` — the actual deployment directory (correct)
- `<hash>.0.origin` — a small metadata file (NOT a directory)

Without `-type d`, `find -printf '%f\n' | head -1` may return `.0.origin` before `.0` depending on filesystem ordering. Setting `DEPLOY` to a file path causes `ls $D/usr/lib/modules/` to fail with "Not a directory", leaving `KVER` empty.

**Fix (e2e.yml line 281 — the critical one):**
```bash
# WRONG (picks up .0.origin):
DEPLOY=$(sudo find /mnt/root/ostree/deploy/default/deploy/ -mindepth 1 -maxdepth 1 -printf '%f\n' 2>/dev/null | head -1)

# CORRECT:
DEPLOY=$(sudo find /mnt/root/ostree/deploy/default/deploy/ -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | head -1)
```

**Note:** The later `for DEP in $(sudo find ... -type d)` loops (lines 406, 528, 537) already have `-type d`. Only the `DEPLOY=` assignment at line 281 was missing it.

**History:** PR #518 fixed the identical line in `action.yml` (legacy composite action kept for historical reasons) but missed `e2e.yml` where the actual running code lives. PR #519 fixed the real location. Always verify by checking `e2e.yml` line 281, not `action.yml`.

---



**Pattern** — every suite's `environment.py` must have both guards:

```python
def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine
    if skip_quarantine(scenario):
        return
    if getattr(context, 'failed_setup', None):    # GUARD
        try:
            scenario.skip(reason=context.failed_setup)
        except TypeError:
            scenario.skip()
        return
    ...

def after_scenario(context, scenario) -> None:
    if getattr(context, 'failed_setup', None):    # GUARD
        return
    ...
    if hasattr(context, 'sandbox'):               # GUARD: sandbox may not exist
        context.sandbox.after_scenario(context, scenario)
```

**CRITICAL:** Use `getattr(context, 'failed_setup', None)` (truthiness check), NOT `hasattr()`. `TestSandbox.__init__` sets `context.failed_setup = None` on every run (even success), so `hasattr()` is always `True` and causes every scenario to skip.

Also use `scenario.skip()`, NOT `context.scenario.skip()` — `context.scenario` is not set yet at the guard point.

---

## results.json captures first-pass only

`behave_retry.py` runs behave up to 3 times. `results.json` is written after the **first pass** and is not overwritten by retries. Always grep the job log for the true final count:
```bash
gh api "repos/org/repo/actions/jobs/$JOB_ID/logs" | grep "scenarios passed" | tail -3
```

---

## ublue-motd prepended to SSH output

**Symptom:** SSH assertions fail — step expects `stdout == "ok"` but gets `"Welcome to Bluefin...\nok"`.

**Cause:** Some images ship `/etc/profile.d/ublue-motd.sh` which prints a MOTD in login shells.

**Fix (in e2e.yml VM setup):**
```bash
sudo touch "${VAR}/home/bluefin-test/.config/no-show-user-motd"
```

`ssh_steps.py` checks the **last line** of stdout (not the whole output) as a defensive measure. Do not change assertions to substring-match — the last-line approach is more robust.

---

## Do not add a second -monitor flag to QEMU

`e2e.yml` opens a QEMU monitor unix socket at boot:
```
-monitor unix:/tmp/qemu-monitor.sock,server,nowait
```
`tests/shared/qemu_screendump.py` uses this socket for fallback screenshots. A second `-monitor` flag competes for VM state. To capture the framebuffer from a custom step:
```bash
sudo python3 tests/shared/qemu_screendump.py results/my-screenshot.png
```

---

## common shell tools missing on bluefin:lts / bluefin-gdx

**Symptom:** `common` suite: 7 failures — `zsh`, `fish`, `bat`, `eza`, `fd`, `ripgrep`, `starship` not found.

**Cause:** `LockLayering=true` prevents `rpm-ostree install --apply-live`. `brew-setup.service` is masked in CI.

**Status:** Image quality issue — tests correctly detect missing tools. Report to image maintainers. If tools are not expected on an image, add `@requires_brew` tag to scenarios in `common_shell.feature`.

---

## lifecycle / on-pr-opened: pr/needs-review label must exist

**Symptom:** Every new PR fails `lifecycle / on-pr-opened` with `'pr/needs-review' not found`.

**Cause:** The `projectbluefin/common` lifecycle workflow labels new PRs with `pr/needs-review`. If the label doesn't exist, `gh pr edit --add-label` exits 1.

**Fix:** Ensure the label exists in the repo:
```bash
gh label create "pr/needs-review" --repo projectbluefin/testsuite \
  --color "#0075ca" --description "Needs review from a maintainer"
```

Do not delete this label.

---

## ARC ghost runners — local dev routing

The testsuite can run on the ghost k3s cluster's ARC runners instead of GitHub-hosted runners. ARC replicates the `ubuntu-latest` GHA environment exactly, which is required for reliable debugging.

### How it works

A global pre-push hook (`~/.git-hooks/pre-push`) intercepts pushes to `projectbluefin/*` repos and:
1. Creates `ghost/<branch>` with `ubuntu-latest` → `ghost-runners` patched in workflow files
2. Pushes the ghost branch, triggering push-based workflows automatically
3. Auto-dispatches `workflow_dispatch` workflows (skips `manual.yml`)

### Running the full matrix manually on ghost

```bash
GHOST_REF="ghost/<your-branch>"
SUITES="smoke,developer,dx,software,vanilla-gnome,bazzite,lifecycle"

for image in \
  "ghcr.io/projectbluefin/bluefin:testing" \
  "ghcr.io/projectbluefin/bluefin:stable" \
  "ghcr.io/projectbluefin/bluefin-lts:testing" \
  "ghcr.io/projectbluefin/bluefin-lts:stable" \
  "ghcr.io/projectbluefin/bluefin-lts-hwe:testing" \
  "ghcr.io/projectbluefin/bluefin-lts-hwe:stable" \
  "ghcr.io/projectbluefin/dakota:testing" \
  "ghcr.io/projectbluefin/dakota:stable"; do
  gh workflow run manual.yml \
    --repo projectbluefin/testsuite \
    --ref "${GHOST_REF}" \
    --field image="${image}" \
    --field suites="${SUITES}"
done
```

### ARC health check

```bash
# Listener running?
kubectl get pods -n arc-systems

# Jobs being picked up? (empty arc-runners is healthy — minRunners=0)
kubectl get ephemeralrunners -n arc-runners

# Runner logs (catch before pod completes)
kubectl logs -f -n arc-runners -l actions.github.com/scale-set-name=ghost-runners
```

### Ghost branch cleanup

Ghost branches auto-delete after 2 hours via the hook's background process. Manual cleanup:
```bash
git push origin :ghost/<branch-name>
```

---

## oras pull: always use a directory, never a file path

`oras pull <ref> --output <path>` (or `-o <path>`) expects a **directory**. Passing a file path creates a directory with that name and puts the artifact inside it.

```bash
# WRONG — creates scratch/smoke.png/ directory, cp fails silently
oras pull "${REGISTRY}:smoke-latest" --output scratch/smoke.png

# CORRECT — pull to dir, then find the PNG inside
mkdir -p scratch/smoke
oras pull "${REGISTRY}:smoke-latest" -o scratch/smoke/
SHOT=$(find scratch/smoke/ -name "*.png" | head -1)
cp "$SHOT" screenshots/target.png
```

The artifact filename inside the OCI artifact is `desktop-screenshot.png` (set at push time with `oras push ... desktop-screenshot.png:image/png`).

---

## GitHub API: rulesets require PUT not PATCH

`PATCH /repos/{owner}/{repo}/rulesets/{id}` returns 404 even with `repo` scope and admin access.

Use `PUT` with the **full** ruleset body (including `name`, `enforcement`, `conditions`, `bypass_actors`, and all `rules`):

```bash
gh api --method PUT repos/projectbluefin/bluefin/rulesets/17070404 \
  --input /tmp/full-ruleset.json \
  --jq '.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count'
```

To get the current body for editing:
```bash
gh api repos/projectbluefin/bluefin/rulesets/17070404 \
  | jq '{name, enforcement, conditions, bypass_actors, rules}' > /tmp/ruleset.json
# edit /tmp/ruleset.json, then PUT
```

---

## Cross-image tag skipping: @bluefin on non-bluefin images

The common suite skips scenarios tagged `@bluefin` when `IMAGE` env var refers to a
non-bluefin image (e.g. dakota). This is implemented via `_is_bluefin_image()` in
`tests/common/features/environment.py`.

**Pitfall**: match the image *name*, not the full URL. The org name `projectbluefin`
contains `"bluefin"`, so naively checking `"bluefin" in image_url.lower()` returns
`True` for `ghcr.io/projectbluefin/dakota:testing`.

Correct pattern:

```python
def _is_bluefin_image(image: str) -> bool:
    lower = image.lower()
    name = lower.split("/")[-1].split(":")[0].split("@")[0]
    return "bluefin" in name or "bazzite" in lower
```

This extracts the image name component (`bluefin`, `dakota`, etc.) before checking.

The smoke suite environment replicates this same pattern so `@bluefin` tags are
respected in AT-SPI tests as well.

## composefs file-capability regression (dakota#841)

A `@health @composefs @regression` scenario in `system_health.feature` checks
that `newuidmap`, `newgidmap`, and `ping` retain their `security.capability`
xattrs after a composefs-backed ostree deployment.

**Root cause of the 2026-06-13 incident:** `buildah commit` (without
`--squash`) produced a multi-layer OCI image. The composefs xattr injection
expected a flat single-layer input; the multi-layer output silently stripped
`security.capability` xattrs. The composefs tree could not mount at boot.
Fix: `podman build --squash-all` in the export recipe
(projectbluefin/dakota#846).

If `getcap` returns no capabilities for these binaries, the image build
pipeline produced a multi-layer OCI artifact. File the regression against the
image build repo, not the test suite.
## Red Flags

- Using `_run(cmd)` in smoke suite for DNS or network checks (runs on container, not VM)
- Setting `sys.exit(1)` inside `before_scenario` (kills all subsequent scenarios silently)
- Lowering the SSH timeout below 60 seconds (hardware commands are slow in QEMU)
- Adding a second `-monitor` flag to QEMU (breaks `qemu_screendump.py`)
- Using `hasattr(context, 'failed_setup')` instead of `getattr(..., None)` (always True)
- Calling `sudo podman load` instead of rootless load (image goes to root storage)
- Using `oras pull` with a file path instead of a directory

## Verification

- [ ] Smoke suite network/DNS checks use `_run_host()` not `_run()`
- [ ] No `sys.exit()` calls in `before_scenario` / `after_scenario`
- [ ] `before_scenario` guard uses `getattr(context, 'failed_setup', None)`, not `hasattr()`
- [ ] SSH step timeout is 60s or higher for hardware/bootc commands
- [ ] `oras pull` targets a directory, not a file path
- [ ] Runner container changes followed by `build-runner.yml` dispatch before test runs

---

## git restore vs git checkout for full directory reset

When a branch-sync workflow merges main into another branch, the merge can pull in
new files under `.github/workflows/`. Pushing those changes requires `workflows: write`
which `GITHUB_TOKEN` does not have by default.

**Fix:** After the merge, fully reset the target directory to its pre-merge state with:

```bash
git restore --source='HEAD@{1}' --staged --worktree -- .github/workflows/
```

**Do NOT use** `git checkout HEAD@{1} -- .github/workflows/` — that command only restores
paths that existed before the merge. It will **not** delete files newly added by the merge.
`git restore --staged --worktree` makes the working tree and index exactly match the
pre-merge ref, including deletions.

After restoring, stage the directory before amending the merge commit:
```bash
git add .github/workflows/
git commit --amend --no-edit
git push origin <branch>
```

## Composite actions vs checkout for cross-repo scripts

**Never** check out `projectbluefin/actions` into the caller repo workspace to run a script.
Placing a nested git repo in the workspace causes `git add -A` to capture it as an
undeclared gitlink (mode 160000 with no `.gitmodules` entry). That gitlink ends up in
squash commits and breaks any consumer build using `submodules: recursive`:

```
fatal: No url found for submodule path '.workflow-scripts' in .gitmodules
```

**Fix:** Wrap the script as a composite action. Composite actions get `$GITHUB_ACTION_PATH`
pointing at the action's own directory — the script is accessible with no checkout:

```yaml
# .github/actions/my-action/action.yml
runs:
  using: composite
  steps:
    - shell: bash
      run: python3 "$GITHUB_ACTION_PATH/my_script.py" ...
```

Call it from a reusable workflow with `uses: projectbluefin/actions/.github/actions/my-action@v1`.
GitHub checks out the actions repo to a runner cache path, never inside the caller workspace.

Also: `.gitignore` rules without a leading `/` match anywhere in the tree.
`actions/` ignores `.github/actions/` too. Use `/actions/` to scope to the repo root.
