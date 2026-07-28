---
name: kde-session-preconditions
description: "Contract for KDE/Plasma session preconditions: SDDM autologin, wizard suppression, determinism drop-ins, home seeding, and readiness polling."
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

## Capability model

All helpers follow the Tast `SoftwareDeps` pattern: a missing KDE capability
produces a **skip**, not a failure. The main entry point is
`apply_kde_session_preconditions(context)`, which returns a `KDEResult`.

| Probe | Meaning when false |
|---|---|
| `is_kde_session()` | DUT is not running `kwin_wayland` → skip the whole KDE suite. |
| `has_sddm()` | Display manager is not SDDM → skip SDDM autologin step only. |
| `has_kwriteconfig6()` | KDE 6 config tools are absent → skip wizard suppression only. |

## SDDM autologin

Drop-in file: `/etc/sddm.conf.d/99-testsuite-autologin.conf`

```ini
[Autologin]
User=bluefin-test
Session=plasmawayland.desktop
```

The session name must match a desktop file under `/usr/share/wayland-sessions/`;
upstream Plasma 6 ships `plasmawayland.desktop`.  If SDDM is not the active
display manager the step is skipped cleanly.

## First-run / welcome wizard suppression

- `kwriteconfig6 --file plasma-welcomerc --group General --key ShowOnStartup false`
- `kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0`
- Sentinel files are touched for known distro wizards; add more as variants are
discovered.

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
units when the display manager starts the user session via systemd.

## Home seeding

`seed_home()` removes `.cache`, `.config`, and `.local` under the test user's
home, recreates the expected directories, and fixes ownership. Scenarios must
not depend on leftover state from earlier runs.

## Readiness waiter

`wait_for_plasma_session(context, timeout=120)` polls with exponential backoff
until all three signals are true in a single SSH round-trip:

1. `kwin_wayland` process exists.
2. `plasmashell` process exists.
3. `gdbus call --session --dest org.a11y.Bus ... Ping` succeeds.

The command sources `/tmp/session.env` first, matching the GNOME smoke-suite
pattern for forwarding the session bus address inside an SSH connection.

## Verification

- [ ] `ruff check tests/ --select E,F,W --ignore E501` passes.
- [ ] `python3 -m pytest tests/unit/test_kde_preconditions.py -q` passes.
- [ ] Skill file or reference updated when `tests/shared/kde_preconditions.py`
      changes.
