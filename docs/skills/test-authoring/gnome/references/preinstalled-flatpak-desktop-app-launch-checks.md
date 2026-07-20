---
name: preinstalled-flatpak-desktop-app-launch-checks
description: "Deep dive: Preinstalled Flatpak desktop app launch checks"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Preinstalled Flatpak desktop app launch checks

For smoke tests that only need to prove a preinstalled Flatpak desktop app
launches, reuse the `gnome_apps.feature` pattern: launch, wait for one visible
top-level frame in the AT-SPI tree, send `<Alt><F4>`, then assert the frame is
gone.

Use `app_support.launch_background()` with **desktop-first** targets and a
Flatpak fallback:

```python
LAUNCH_TARGETS = (
    ("desktop", "io.missioncenter.MissionCenter.desktop"),
    ("flatpak", "io.missioncenter.MissionCenter"),
)
```

Why: in CI/container runs the helper resolves desktop files from Flatpak export
dirs (`/var/lib/flatpak/exports/...`) and launches them on the VM via SSH, so
you should not hardcode `/usr/share/applications/<app>.desktop` for Flatpak-only
apps.
