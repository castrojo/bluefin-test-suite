---
name: xdg-desktop-portal-and-graphical-session-target
description: "Deep dive: xdg-desktop-portal and graphical-session.target"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## xdg-desktop-portal and graphical-session.target

`xdg-desktop-portal` 1.22.0 (shipped in Fedora 42 / Bluefin mid-2026) added `Requisite=graphical-session.target` to its user-session service unit. If `graphical-session.target` is not active, the portal fails immediately with:

```
xdg-desktop-portal.service: Job failed with result 'dependency'
```

This silently breaks dark mode (Settings portal), file choosers, screenshots, and all Flatpak sandbox bridging, because `systemctl --user status` may still show `inactive` rather than `failed`.

**Root cause:** GNOME activates `graphical-session.target` via GDM + gnome-session. If GDM autologin is broken, or if the session manager does not reach `graphical-session.target`, portals will never start.

**Regression guards** (in `common_portals.feature`):
- `graphical-session.target is active in the user session` — asserts the target reached active state
- `xdg-desktop-portal did not fail due to missing session target` — asserts `Result=success`

If these fail: check GDM autologin config (section above), then check `journalctl --user -u graphical-session.target` for activation order issues. Reference: https://bbs.archlinux.org/viewtopic.php?id=313883

---
