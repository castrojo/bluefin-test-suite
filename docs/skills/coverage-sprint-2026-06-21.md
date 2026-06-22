---
name: coverage-sprint-2026-06-21
description: "Fleet agent work plan for the 2026-06-21 coverage sprint. Covers bctl, Bluefin extensions, desktop assertions, service health checks, AI stack, shell integrity, polkit, udev, portals, containers, a11y, and the fix/471 CI breakage. Load when picking up work from this sprint."
metadata:
  type: sprint-plan
  status: complete
  owner: fleet
---

# Coverage Sprint — 2026-06-21

## Sprint Status: COMPLETE (2026-06-22)

All 13 PRs opened and merged/queued. Final scenario count: 287.

Completed: all items except bctl-suite (blocked: brew-setup.service masked in CI, needs infra decision).

## Context

A full coverage gap analysis was run on 2026-06-21. The research report is at:
`~/.copilot/session-state/34e53a27-d322-4c77-a3c9-02dea8748b85/research/find-out-what-s-left-to-test-what-s-in-bluefin-tha.md`

**Key findings:**

**Blocking:**
1. **Issue #471 — FIXED** — PR #472 merged/queued. `bootc install to-disk` silent failure via `|| echo` patched with hard-fail guard.

**Bugs (code review found):**
2. **DNS health check tests the runner, not the VM** — `getent hosts` runs locally, not via SSH into VM.
3. **Extensions smoke test is vacuous** — CI's own `unsafe-mode@bluefin-test` satisfies "at least one enabled."
4. **dconf tests only check readability** — `color-scheme`, `clock-format` don't assert Bluefin's expected values.

**Identity gaps (Bluefin-specific, high priority):**
5. **bctl (bluefinctl)** — default-installed, zero tests. brew masking means CI tests bash fallbacks, not real user code paths.
6. **GNOME extensions** — 7 shipped, 0 named per-extension tests (Bazzite has 14).
7. **AI/ML stack** — Bluefin is "AI-native": ramalama, ollama, goose, llmfit, ai-tools.Brewfile, claude-code. **Zero tests.**
8. **Shell sourcing integrity** — zsh/bash profile.d never verified to source without errors.
9. **Bazaar /etc/bazaar/ YAML configs** — curated.yaml, blocklist.yaml: YAML syntax errors crash the app store silently.

**System integrity (silent regression risks):**
10. **Polkit rules** — never tested; breakage hangs first-login or creates privilege escapes.
11. **udev rules** — 16 custom rules (Framework, ASUS, game controllers, Apple SuperDrive, ZSA, Wooting, Titan); syntax errors silently not applied.
12. **XDG portals** — xdg-desktop-portal service never health-checked.
13. **Container runtime** — podman socket, containerd health: only Podman Desktop GUI is tested.

**Desktop coverage gaps:**
14. **Bluefin desktop identity** — Dash-to-Dock, system tray, custom menu: zero coverage.
15. **Accessibility (a11y)** — zero. Every mature Linux QA suite has this.
16. **Power management** — power-profiles-daemon, upower: zero.
17. **Custom systemd services** — 10 shipped, none checked by name.

**Industry benchmark gaps (longer term):**
- Suspend/resume: untested
- GDM login flow: bypassed by autologin
- Localization/i18n: zero
- Multi-monitor: zero
- XDG portal interactions: zero
- Visual regression: zero (AT-SPI is blind to rendering)

**Current suite posture:** 287 scenarios / 242 active in CI / 30 quarantined / 15 future-blocked.

---

## Work Items (priority order)

### ITEM -1 — fix/471 (DONE)

PR #472 merged/queued: `fix(e2e): hard-fail when bootc install produces empty deployment`
Unblocks `run_e2e: true` across all repos.

---

### ITEM 0a — DNS health check uses `_run_host()` (DONE)

**Branch**: `fix/smoke/dns-check-runner-vs-vm`  
**File**: `tests/smoke/features/steps/system_health_steps.py`  
**Severity**: High (test passes even when VM has no DNS)

The DNS step runs `getent hosts ghcr.io` on the **test runner**, not the VM. Any VM network regression is invisible.

```python
# WRONG — runs locally in test runner
result = _run("getent hosts ghcr.io")

# CORRECT — runs inside the booted VM
result = _run_host("getent hosts ghcr.io")
```

One-line fix. No feature file changes. No behave dry-run needed. Ruff lint still required.

---

### ITEM 0b — Strengthen dconf value assertions (DONE)

**Branch**: `fix/common/dconf-expected-values`  
**File**: `tests/common/features/common_dconf.feature`

Currently asserts only "non-empty" for `color-scheme`, `clock-format`, `font-name`, `show-battery-percentage`. Reverts to upstream defaults pass silently.

Assert the **expected Bluefin values**:

```gherkin
Scenario: GNOME color scheme is set to prefer-dark
  * Run SSH command: "gsettings get org.gnome.desktop.interface color-scheme"
  * SSH command output contains "prefer-dark"

Scenario: GNOME clock format is 24h
  * Run SSH command: "gsettings get org.gnome.desktop.interface clock-format"
  * SSH command output contains "24h"
```

Check the actual shipped dconf defaults in `projectbluefin/common` before asserting values — use `system_files/bluefin/etc/dconf/db/distro.d/` as the source of truth.

---

### ITEM 1 — fix/bootc-install-silent-failure (DONE)

**Status**: completed  
**Branch**: `fix/bootc-install-silent-failure`  
**Files**: `.github/workflows/e2e.yml` and/or `.github/actions/gnome-e2e/action.yml`

**What to do:**
Find the `|| echo "bootc install exited..."` pattern around `bootc install to-disk --via-loopback`. The fix has two parts:

1. Capture and print the real exit code + stderr before the `|| echo` silences it:
```bash
set +e
sudo podman run ... bootc install to-disk --via-loopback /data/disk.raw ...
BOOTC_RC=$?
set -e
if [ $BOOTC_RC -ne 0 ]; then
  echo "bootc install exited $BOOTC_RC — checking if bootupd-only failure..."
fi
```

2. Post-install deployment guard — hard-fail if ostree deployment is empty:
```bash
DEPLOY=$(sudo ls /mnt/root/ostree/deploy/default/deploy/ 2>/dev/null | head -1)
if [ -z "$DEPLOY" ]; then
  echo "ERROR: ostree deployment missing after bootc install — real failure, not bootupd"
  exit 1
fi
echo "Deployment present: $DEPLOY"
```

**PR requirements:**
- Title: `fix(e2e): hard-fail when bootc install produces empty deployment`
- References issue #471 in body
- No emojis, plain text body
- Both AI trailers
- Do NOT post comments on issue #471

---

### ITEM 2 — bluefin_extensions.feature (DONE)

**Branch**: `feat/smoke/bluefin-extensions`  
**File**: `tests/smoke/features/bluefin_extensions.feature`  
**Steps**: `tests/smoke/features/steps/steps.py` (add extension-check steps there or in a new `tests/smoke/features/steps/extension_steps.py`)

**Pattern to follow**: `tests/bazzite/features/bazzite_extensions.feature`

**Important**: Smoke suite runs LOCAL inside the VM via qecore-headless. Steps use `subprocess.run`, NOT SSH. See `docs/skills/index.md` rule 5.

**Scenarios to write:**

```gherkin
Feature: Bluefin GNOME extensions
  Bluefin ships seven GNOME Shell extensions by default.
  Verify each is installed and enabled.

  Background:
    * GNOME Shell is accessible via AT-SPI

  @smoke @bluefin_only
  Scenario: Dash to Dock extension is installed
    * GNOME extension "dash-to-dock@micxgx.gmail.com" is installed

  @smoke @bluefin_only
  Scenario: Dash to Dock extension is enabled
    * GNOME extension "dash-to-dock@micxgx.gmail.com" is enabled

  @smoke @bluefin_only
  Scenario: AppIndicator extension is installed
    * GNOME extension "appindicatorsupport@rgcjonas.gmail.com" is installed

  @smoke @bluefin_only
  Scenario: AppIndicator extension is enabled
    * GNOME extension "appindicatorsupport@rgcjonas.gmail.com" is enabled

  @smoke @bluefin_only
  Scenario: Blur My Shell extension is installed
    * GNOME extension "blur-my-shell@aunetx" is installed

  @smoke @bluefin_only
  Scenario: Blur My Shell extension is enabled
    * GNOME extension "blur-my-shell@aunetx" is enabled

  @smoke @bluefin_only
  Scenario: GSConnect extension is installed
    * GNOME extension "gsconnect@andyholmes.github.io" is installed

  @smoke @bluefin_only
  Scenario: GSConnect extension is enabled
    * GNOME extension "gsconnect@andyholmes.github.io" is enabled

  @smoke @bluefin_only
  Scenario: Search Light extension is installed
    * GNOME extension "search-light@icedman.github.com" is installed

  @smoke @bluefin_only
  Scenario: Custom Command Menu extension is installed
    * GNOME extension "custom-command-list@storageb.github.com" is installed

  @smoke @bluefin_only
  Scenario: Custom Command Menu extension is enabled
    * GNOME extension "custom-command-list@storageb.github.com" is enabled

  @smoke @bluefin_only
  Scenario: No gnome-shell crash on Bluefin extension load
    * Run command: "journalctl -b --no-pager -p err -g 'gnome-shell' | grep -v '^$' || true"
    * No gnome-shell coredump after session start
```

**Step implementation** (add to steps.py):
```python
@step('GNOME extension "{ext_uuid}" is installed')
def step_extension_installed(context, ext_uuid):
    result = subprocess.run(
        ["gsettings", "get", "org.gnome.shell", "installed-extensions"],
        capture_output=True, text=True
    )
    assert ext_uuid in result.stdout, (
        f"Extension {ext_uuid} not in installed-extensions: {result.stdout}"
    )

@step('GNOME extension "{ext_uuid}" is enabled')
def step_extension_enabled(context, ext_uuid):
    result = subprocess.run(
        ["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
        capture_output=True, text=True
    )
    assert ext_uuid in result.stdout, (
        f"Extension {ext_uuid} not in enabled-extensions: {result.stdout}"
    )
```

**After writing:**
- `ruff check tests/ --select E,F,W --ignore E501`
- `behave --dry-run tests/smoke/`
- Update `QA-REVIEW.md` and `docs/skills/suite-map.md` scenario counts (+12 to smoke)
- Update `docs/skills/coverage-sprint-2026-06-21.md` (this file) to mark item done

---

### ITEM 3 — bluefin_desktop.feature (DONE)

**Branch**: `feat/smoke/bluefin-desktop` (or same branch as extensions)  
**File**: `tests/smoke/features/bluefin_desktop.feature`  
**Depends on**: Item 2 (extensions must land first for dock visibility step)

**Scenarios to write:**

```gherkin
Feature: Bluefin desktop identity
  Verify Bluefin-specific desktop layout and session quality.

  Background:
    * GNOME Shell is accessible via AT-SPI

  @smoke @bluefin_only
  Scenario: Wayland session is active
    * Run command: "echo $XDG_SESSION_TYPE"
    * Command output contains "wayland"

  @smoke @bluefin_only
  Scenario: No software rendering fallback
    * Run command: "echo ${LIBGL_ALWAYS_SOFTWARE:-unset}"
    * Command output contains "unset"

  @smoke @bluefin_only
  Scenario: Dash to Dock actor is visible on screen
    * Shell.Eval "Main.overview.dash.actor.visible" returns true

  @smoke @bluefin_only
  Scenario: System tray has at least one indicator
    * Shell.Eval "Main.panel.statusArea.aggregateMenu._indicators.get_n_children() > 0" returns true
```

**Shell.Eval pattern** (use `_eval_bool` helper from steps.py):
```python
@step('Shell.Eval "{js}" returns true')
def step_shell_eval_true(context, js):
    result = _eval_bool(js)
    assert result, f"Shell.Eval({js!r}) returned false"
```

---

### ITEM 4 — bctl suite (BLOCKED)

**Branch**: `feat/bctl/smoke`  
**Files**: `tests/bctl/features/bctl.feature`, `tests/bctl/features/steps/steps.py`, `tests/bctl/environment.py`  
**Depends on**: Homebrew must be available (Item 1 unblocks this path)

**Infrastructure note**: bctl is installed via Homebrew → `brew-setup.service` must NOT be masked for this suite to run. Either:
- Add a new e2e.yml job that does NOT mask brew-setup (preferred: pre-warmed image with Homebrew already initialized)
- OR tag scenarios `@requires_brew` and skip in environment.py when `shutil.which("bctl") is None`

**Feature file:**

```gherkin
Feature: bctl (bluefinctl) control panel
  bctl is the default-installed CLI/TUI for Bluefin system management.
  All safe read-only subcommands are verified here.

  @bctl
  Scenario: bctl is on PATH
    * Run SSH command: "command -v bctl"
    * SSH command output contains "bctl"

  @bctl
  Scenario: bctl status exits cleanly and reports image reference
    * Run SSH command: "bctl status"
    * SSH command exit code is 0
    * SSH command output contains "ghcr.io"

  @bctl
  Scenario: bctl update --check reports update state without modifying system
    * Run SSH command: "bctl update --check"
    * SSH command exit code is 0

  @bctl
  Scenario: bctl focus on enables focus mode
    * Run SSH command: "bctl focus on"
    * SSH command exit code is 0

  @bctl
  Scenario: bctl focus status reports active after enabling
    * Run SSH command: "bctl focus status"
    * SSH command output contains "active"

  @bctl
  Scenario: bctl focus off disables focus mode
    * Run SSH command: "bctl focus off"
    * SSH command exit code is 0

  @bctl
  Scenario: bctl changelogs exits cleanly with non-empty output
    * Run SSH command: "bctl changelogs 2>&1 | head -20"
    * SSH command exit code is 0
    * SSH command output is not empty

  @bctl
  Scenario: bctl TUI launches and exits in headless mode
    * Run SSH command: "timeout 5 bctl --help || true"
    * SSH command output contains "Usage"
```

**Note on bctl suite vs smoke**: bctl uses SSH (runs in the container, accesses VM over SSH), not local subprocess. Use `tests/shared/ssh_steps.py` patterns. See `docs/skills/index.md` rule 5.

**e2e.yml integration**: Add `bctl` to the `suites` input enum and the resolve-shard step. Wire it to run only on images where Homebrew completes (non-masked job variant).

---

### ITEM 5 — Named systemd service health checks (DONE)

**Branch**: `feat/common/service-health`  
**File**: `tests/common/features/common_scripts.feature` (add new scenarios) or new `tests/common/features/common_services.feature`

**Scenarios:**

```gherkin
@common
Scenario: dconf-update service ran at boot
  * Run SSH command: "systemctl is-enabled dconf-update.service"
  * SSH command output contains "static"
  * Run SSH command: "systemctl show dconf-update.service --property=ActiveState"
  * SSH command output contains "ActiveState=inactive"

@common
Scenario: ublue-system-setup service completed at boot
  * Run SSH command: "systemctl show ublue-system-setup.service --property=ActiveState"
  * SSH command output contains "ActiveState=inactive"

@common
Scenario: bazaar user service is active
  * Run SSH command: "systemctl --user show bazaar.service --property=ActiveState"
  * SSH command output contains "ActiveState=active"
```

**Note**: `dconf-update` and `ublue-system-setup` are oneshot — ActiveState will be `inactive` (exited cleanly) not `active`. Use `SubState=exited` to confirm they ran rather than failed.

---

### ITEM 6 — flatpak_firstboot.feature (DONE)

**Branch**: `feat/common/flatpak-firstboot`  
**File**: `tests/common/features/flatpak_firstboot.feature`

**Note**: `flatpak-preinstall.service` is masked in CI — these scenarios will fail unless that masking is lifted OR tests are written against what survives masking (i.e., the Flathub remote config from the image itself, which is baked in, not runtime-installed).

**Safe scenarios (work even with masking):**

```gherkin
@common
Scenario: Fedora flatpak remote is absent
  * Run SSH command: "flatpak remotes --show-disabled | grep -c fedora || echo 0"
  * SSH command output is "0"

@common
Scenario: Flathub is the only configured remote
  * Run SSH command: "flatpak remotes --columns=name | grep -v '^Name'"
  * SSH command output contains "flathub"

@common
Scenario: Bazaar Flatpak preinstall file is present
  * Run SSH command: "test -f /usr/share/ublue-os/homebrew/system-flatpaks.Brewfile && echo present"
  * SSH command output contains "present"
```

**Needs masking lifted** (mark `@quarantine` until flatpak-preinstall is unmasked):

```gherkin
@common @quarantine
Scenario: Firefox Flatpak system config overlay is present
  * Run SSH command: "test -d /var/lib/flatpak/extension/org.mozilla.firefox.systemconfig/ && echo present"
  * SSH command output contains "present"
```

---

### ITEM 7 — ujust safe recipe smoke tests (DONE)

**Branch**: can be same as Item 5 or 6  
**File**: `tests/common/features/common_scripts.feature`

**Add to existing common_scripts.feature:**

```gherkin
@common
Scenario: ujust check-local-overrides runs without error
  * Run SSH command: "ujust check-local-overrides"
  * SSH command exit code is 0

@common
Scenario: ujust logs-this-boot produces output
  * Run SSH command: "ujust logs-this-boot 2>&1 | head -5"
  * SSH command exit code is 0
  * SSH command output is not empty
```

---

### ITEM 8 — docs/skills update (DONE)

Every PR that adds scenarios must update:
1. `QA-REVIEW.md` — total scenario count
2. `docs/skills/suite-map.md` — per-suite row counts, variant matrix
3. `docs/skills/coverage-sprint-2026-06-21.md` — mark items done

---

## PR sequencing

PRs can be opened in parallel. Merge order:

```
fix-471 (ASAP — unblocks run_e2e across all repos)
  └── bctl-suite (needs brew unmasked, coordinate with fix-471 branch)

bluefin-extensions
  └── bluefin-desktop (dock visibility depends on extensions landing)

service-health, flatpak-firstboot, ujust-smoke  (parallel, independent)

docs-skill-update  (after all above are open, one cleanup PR)
```

---

## Mandatory checks before each PR

```bash
# Lint
ruff check tests/ --select E,F,W --ignore E501

# Dry run (for any .feature change)
behave --dry-run tests/<suite>/

# Step uniqueness
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d
# must be empty
```

## Commit trailer template

```
feat(smoke): add Bluefin extension named scenarios

Assisted-by: Claude Sonnet 4.6 via GitHub Copilot
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

Both trailers required. One without the other is a convention violation.

---

## Key file locations for this sprint

| What | Where |
|---|---|
| Bazzite extension pattern to copy | `tests/bazzite/features/bazzite_extensions.feature` |
| Bazzite shell pattern | `tests/bazzite/features/bazzite_shell.feature` |
| Shell.Eval helpers | `tests/smoke/features/steps/steps.py` (`_eval_bool`, `_shell_eval`) |
| SSH step patterns | `tests/shared/ssh_steps.py` |
| GNOME AT-SPI patterns | `docs/skills/gnome.md` |
| Suite-map to update | `docs/skills/suite-map.md` |
| QA review to update | `QA-REVIEW.md` |
| e2e.yml (suite wiring + masking) | `.github/workflows/e2e.yml` |
| gnome-e2e action | `.github/actions/gnome-e2e/action.yml` |
| Bluefin /etc configs | `projectbluefin/common:system_files/shared/etc/` |
| udev rules | `projectbluefin/common:system_files/shared/usr/lib/udev/rules.d/` |
| Polkit rules | `projectbluefin/common:system_files/shared/usr/share/polkit-1/rules.d/` |
| AI stack Brewfile | `projectbluefin/common:system_files/shared/usr/share/ublue-os/homebrew/ai-tools.Brewfile` |
| Bazaar configs | `projectbluefin/common:system_files/shared/etc/bazaar/` |
| zshrc | `projectbluefin/common:system_files/bluefin/etc/zsh/zshrc` |

---

## New work items found in second research pass

### ITEM A — AI/ML stack tests (`tests/ai/`)

Bluefin is an "AI-native OS" shipping `ramalama`, `ollama` (sysext), `goose`, `llmfit`, `ai-tools.Brewfile`, `claude-code`, `codex`. **Zero tests exist.** Silent failures here are high-profile.

**Branch**: `feat/ai/smoke`  
**Requires**: Homebrew initialized (brew not masked)

```gherkin
Feature: Bluefin AI stack
  @ai @requires_brew
  Scenario: ramalama is on PATH
    * Run SSH command: "command -v ramalama"
    * SSH command exit code is 0

  @ai @requires_brew
  Scenario: ramalama list exits cleanly
    * Run SSH command: "ramalama list 2>&1 | head -5"
    * SSH command exit code is 0

  @ai @requires_brew
  Scenario: ai-tools Brewfile is present
    * Run SSH command: "test -f /usr/share/ublue-os/homebrew/ai-tools.Brewfile && echo present"
    * SSH command output contains "present"

  @ai @requires_brew
  Scenario: llmfit is on PATH
    * Run SSH command: "command -v llmfit && echo found"
    * SSH command output contains "found"

  @ai @requires_brew
  Scenario: bctl ai list exits cleanly
    * Run SSH command: "bctl ai list"
    * SSH command exit code is 0
```

GPU scenarios tag `@requires_gpu` (blocked until Epic E08).

---

### ITEM B — Shell sourcing integrity (`tests/common/features/common_shell.feature`)

A zshrc syntax error crashes every developer terminal silently.

```gherkin
@common
Scenario: zsh sources system zshrc without errors
  * Run SSH command: "zsh -c 'exit 0' 2>&1"
  * SSH command exit code is 0
  * SSH command output does not contain "error"

@common
Scenario: bash sources profile.d scripts without errors
  * Run SSH command: "bash -l -c 'exit 0' 2>&1"
  * SSH command exit code is 0

@common
Scenario: starship prompt initializes in bash
  * Run SSH command: "bash -c 'eval \"$(starship init bash)\" && echo ok'"
  * SSH command output contains "ok"
```

---

### ITEM C — Bazaar config YAML integrity (`tests/software/features/`)

```gherkin
@software
Scenario: Bazaar YAML configs are syntactically valid
  * Run SSH command: "python3 -c \"import yaml, glob; [yaml.safe_load(open(f)) for f in glob.glob('/etc/bazaar/*.yaml')]; print('ok')\""
  * SSH command output contains "ok"

@software
Scenario: Bazaar blocklist file is present
  * Run SSH command: "test -f /etc/bazaar/blocklist.yaml && echo present"
  * SSH command output contains "present"
```

---

### ITEM D — Polkit rules validation (`tests/security/features/`)

```gherkin
@security
Scenario: ublue privileged setup polkit action is defined
  * Run SSH command: "pkaction --action-id org.ublue.privileged.user.setup --verbose 2>&1 | grep -c 'org.ublue'"
  * SSH command output contains "1"

@security
Scenario: polkit rules directory contains ublue rules
  * Run SSH command: "test -f /usr/share/polkit-1/rules.d/20-privileged-user-setup.rules && echo present"
  * SSH command output contains "present"
```

---

### ITEM E — udev rules syntax check (`tests/hardware/features/`)

```gherkin
@hardware
Scenario: Custom udev rules pass syntax validation
  * Run SSH command: "udevadm verify /usr/lib/udev/rules.d/50-framework16.rules 2>&1 | tail -1"
  * SSH command exit code is 0

@hardware
Scenario: Game device udev rules are installed
  * Run SSH command: "test -f /usr/lib/udev/rules.d/71-game-devices.rules && echo present"
  * SSH command output contains "present"
```

For a full sweep: `udevadm verify /usr/lib/udev/rules.d/*.rules` — but that may hit unrelated system rules; scope to Bluefin-specific ones by name.

---

### ITEM F — XDG portals and container runtime (`tests/common/`)

```gherkin
@common
Scenario: xdg-desktop-portal user service is active
  * Run SSH command: "systemctl --user is-active xdg-desktop-portal"
  * SSH command output contains "active"

@common
Scenario: xdg-desktop-portal-gnome user service is active
  * Run SSH command: "systemctl --user is-active xdg-desktop-portal-gnome"
  * SSH command output contains "active"

@common
Scenario: podman socket is active
  * Run SSH command: "systemctl --user is-active podman.socket"
  * SSH command output contains "active"

@common
Scenario: podman info exits cleanly
  * Run SSH command: "podman info --format json | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['version']['Version'])\""
  * SSH command exit code is 0
```

---

### ITEM G — Accessibility smoke tests (`tests/smoke/features/`)

Minimal cost, high signal. Does not require audio loopback.

```gherkin
@smoke @bluefin_only
Scenario: High contrast mode can be enabled via gsettings
  * Run command: "gsettings set org.gnome.desktop.a11y.interface high-contrast true"
  * Run command: "gsettings get org.gnome.desktop.a11y.interface high-contrast"
  * Command output contains "true"
  * Run command: "gsettings set org.gnome.desktop.a11y.interface high-contrast false"

@smoke
Scenario: Keyboard accessibility settings are readable
  * Run command: "gsettings get org.gnome.desktop.a11y.keyboard enable"
  * Command exit code is 0
```

---

### ITEM H — Power management (`tests/hardware/features/`)

```gherkin
@hardware
Scenario: power-profiles-daemon is active
  * Run SSH command: "systemctl is-active power-profiles-daemon"
  * SSH command output contains "active"

@hardware
Scenario: upower daemon responds to queries
  * Run SSH command: "upower --dump 2>&1 | head -5"
  * SSH command exit code is 0
  * SSH command output is not empty

@hardware
Scenario: Active power profile is readable
  * Run SSH command: "powerprofilesctl get"
  * SSH command exit code is 0
```

---

## Industry benchmark gaps (future sprints, not tonight)

These require infrastructure changes beyond this sprint:

| Gap | What's needed | Effort |
|---|---|---|
| GDM login flow | Boot without autologin, QEMU screendump comparison | High |
| Suspend/resume | QEMU ACPI injection, post-resume health check | High |
| Localization/i18n | Multi-locale VM variants | High |
| Multi-monitor | QEMU multi-head, virtio-gpu-gl | Medium |
| Visual regression | openQA needle library or pixel-diff tooling | Very high |
| Wayland protocol (clipboard, screencast) | XDG portal interaction harness | Medium |
| Printer/scanner | Virtual CUPS PDF printer in QEMU | Medium |

---

## Known hard constraints

- Smoke steps: **LOCAL subprocess** (not SSH). See `docs/skills/index.md` rule 5.
- bctl steps: **SSH** (bctl runs in the VM, tests run in container).
- `findChild` API: never pass `requireResult`. See `docs/skills/gnome.md`.
- `gdbus Shell.Eval`: success flag always `true`; extract JS result from second tuple element. See `docs/skills/gnome.md`.
- No WIP PRs. Each PR is ready to review when opened.
- Max 4 open PRs per agent (castrojo is admin — this limit is waived for this sprint).
- No comments on GitHub issues without explicit permission.
