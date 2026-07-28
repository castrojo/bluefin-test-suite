---
name: kde-session-preconditions
description: "Contract for KDE/Plasma session preconditions: display manager detection (SDDM/PLM), autologin, wizard suppression, determinism drop-ins, home seeding, and readiness polling."
metadata:
  type: reference
  audience: agents
  maturity: draft
---

# KDE Session Preconditions

## Why this exists

No KDE GUI scenario can pass until the session reliably reaches a stable,
automatable desktop. This reference documents the contract implemented by
`tests/shared/kde_preconditions.py`.

## Lifecycle phases

Operations are split into two phases to match how bootc/ostree images work:

### Disk-prep (before first boot)

Entry point: **`apply_disk_prep(context, username)`**

These write to `/etc` and `/home` and only take effect after a reboot.  They
require `sudo -n` because `/etc` is not writable by the unprivileged SSH user
on immutable images.

| Step | What it does |
|---|---|
| `configure_autologin()` | Detect DM → write autologin drop-in to correct dir |
| `emit_determinism_dropin()` | Write `/etc/environment.d/99-testsuite-kde.conf` |
| `seed_home()` | Reset `$HOME` to a clean state |
| `suppress_welcome_wizard()` | Touch sentinels + set kwriteconfig6 defaults |

### Runtime (after boot, live session)

Entry points:
- **`ensure_kde_session(context)`** — preferred for new code; used by
  `tests/kde-smoke/features/environment.py`
- **`apply_kde_session_preconditions(context)`** — legacy orchestrator, kept
  for backwards compatibility

These only run operations safe on a live session: wait for Plasma readiness
and suppress the welcome wizard.  They do NOT attempt autologin or determinism
drop-in writes (those are next-boot-only).

## Capability model

All helpers follow the Tast `SoftwareDeps` pattern: a missing KDE capability
produces a **skip**, not a failure. The runtime entry point is
`apply_kde_session_preconditions(context)`, which returns a `KDEResult`.

| Probe | Meaning when false |
|---|---|
| `is_kde_session()` | DUT is not running `kwin_wayland` → skip the whole KDE suite. |
| `is_kde_image(ref)` | Image ref is not a KDE variant (string check, no SSH). |
| `detect_display_manager()` | Returns `"sddm"`, `"plm"`, or `"unknown"`. |
| `has_sddm()` | Display manager is not SDDM. |
| `has_plm()` | Display manager is not PLM (Plasma Login Manager). |
| `has_kwriteconfig6()` | KDE 6 config tools are absent → skip wizard suppression only. |

## Display manager detection (SDDM vs PLM)

**Fedora 44 / Plasma 6.7** introduces **Plasma Login Manager (PLM)** as a
replacement for SDDM.  Aurora may ship either one depending on the image
generation.

Detection strategy: read the `display-manager.service` symlink under
`/etc/systemd/system/`.  This is the most robust check because it reflects
what systemd will actually start, regardless of which packages happen to be
installed.

- SDDM → config dir: `/etc/sddm.conf.d/`
- PLM → config dir: `/etc/plasmalogin.conf.d/`
- Unknown → hard failure with actionable message (never silent)

The `[Autologin]` INI syntax is identical for both.

## Autologin configuration

Drop-in file: `99-testsuite-autologin.conf` (under the detected DM's conf.d)

```ini
[Autologin]
User=bluefin-test
Session=plasmawayland.desktop
```

### The `plasmawayland.desktop` vs `plasma.desktop` trap

⚠️ **`plasmawayland.desktop`** in `/usr/share/wayland-sessions/` = Plasma 6
**Wayland** session.  This is what we want.

**`plasma.desktop`** in `/usr/share/xsessions/` = the **X11** session.  Using
it would silently start an X11 session, which breaks Wayland-dependent tests.

The correct value is exported as the module constant `KDE_WAYLAND_SESSION`.

### Drop-in filename and precedence

The filename `99-testsuite-autologin.conf` uses a `99-` prefix.  SDDM/PLM
read drop-ins in lexical order, so `99-` intentionally wins over any
lower-numbered defaults (e.g. `00-ci-autologin.conf` from the e2e workflow).
This precedence is deliberate: the testsuite's autologin must be the final
word.  The filename is exported as `AUTOLOGIN_DROPIN_FILENAME`.

## Determinism drop-in

File: `/etc/environment.d/99-testsuite-kde.conf`

```text
KWIN_WAYLAND_NO_PERMISSION_CHECKS=1
KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
QT_QPA_PLATFORM=wayland
LIBGL_ALWAYS_SOFTWARE=1
KWIN_NO_ANIMATIONS=1
QT_NO_ANIMATIONS=1
MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
LANG=C.UTF-8
```

This drop-in is read by `systemd --user` and propagated to graphical session
units when the display manager starts the user session via systemd.  It is a
**disk-prep** operation: it only takes effect on the next boot.

All writes to `/etc` use `sudo -n` because the unprivileged SSH test user
cannot write to `/etc` on immutable bootc/ostree images.

## Home seeding

`seed_home()` removes `.cache`, `.config`, and `.local` under the test user's
home, recreates the expected directories, and fixes ownership. Scenarios must
not depend on leftover state from earlier runs.

## First-run / welcome wizard suppression

- `kwriteconfig6 --file plasma-welcomerc --group General --key ShowOnStartup false`
- `kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0`
- Sentinel files are touched for known distro wizards; add more as variants are
  discovered.

## Readiness waiter

`wait_for_plasma_session(context, timeout=120)` polls with exponential backoff
until all three signals are true in a single SSH round-trip:

1. `kwin_wayland` process exists.
2. `plasmashell` process exists.
3. `gdbus call --session --dest org.a11y.Bus ... Ping` succeeds.

The command sources `/tmp/session.env` first, matching the GNOME smoke-suite
pattern for forwarding the session bus address inside an SSH connection.

## Public API summary

| Function | Phase | Purpose |
|---|---|---|
| `apply_disk_prep()` | disk-prep | Full pre-boot setup |
| `ensure_kde_session()` | runtime | Wait + wizard suppression (for kde-smoke) |
| `apply_kde_session_preconditions()` | runtime | Legacy orchestrator |
| `configure_autologin()` | disk-prep | DM-aware autologin drop-in |
| `configure_sddm_autologin()` | disk-prep | Compat wrapper (deprecated) |
| `emit_determinism_dropin()` | disk-prep | `/etc/environment.d/` drop-in |
| `seed_home()` | disk-prep | Reset test user's `$HOME` |
| `suppress_welcome_wizard()` | both | Wizard sentinels + kwriteconfig6 |
| `is_kde_image()` | — | Pure string check for image family |

## Verification

- [ ] `ruff check tests/ --select E,F,W --ignore E501` passes.
- [ ] `python3 -m pytest tests/unit/test_kde_preconditions.py -q` passes.
- [ ] Skill file or reference updated when `tests/shared/kde_preconditions.py`
      changes.
