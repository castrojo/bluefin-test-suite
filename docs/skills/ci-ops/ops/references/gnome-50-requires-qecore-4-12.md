---
name: gnome-50-requires-qecore-4-12
description: "Deep dive: GNOME 50 requires qecore >= 4.12"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## GNOME 50 requires qecore >= 4.12

**Symptom:** `GetWindows` returns `AccessDenied`; `unsafe_mode` never set; `Shell.Eval` returns `""`.

**Cause:** qecore < 4.12 uses a unit name pattern that never matched GNOME 50's gnome-shell unit.

**Fix:** `e2e.yml` pins `qecore>=4.12`. Do not downgrade.

---
