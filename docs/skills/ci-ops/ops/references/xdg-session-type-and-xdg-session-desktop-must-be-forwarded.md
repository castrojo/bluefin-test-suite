---
name: xdg-session-type-and-xdg-session-desktop-must-be-forwarded
description: "Deep dive: XDG_SESSION_TYPE and XDG_SESSION_DESKTOP must be forwarded"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Xdg Session Type And Xdg Session Desktop Must Be Forwarded

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
