---
name: gdm-autologin
description: "Why GDM autologin is required and how to configure it."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## GDM autologin required

**Symptom:** VM boots but all scenarios fail — `gnome-ponytail-daemon` D-Bus name not activatable. Zero tests run.

**Cause:** `bib-disk-configure` did not write GDM autologin config. VM boots to GDM greeter; no graphical session starts.

**Required config** (must be on the golden disk image):
```ini
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=bluefin-test
```

Open an issue in the image repo referencing `bib-disk-configure`. Do not add this workaround to step code.

**GDM boot regression guard:** A `@health @gdm @regression` scenario in `system_health.feature` explicitly asserts `gdm.service` and `graphical.target` are both `active`. This catches the 2026-06-13 bluefin-lts emergency-console incident — if `gdm.service` fails, the VM boots to emergency console and all AT-SPI tests silently skip without a clear failure. If this scenario fails, check GDM autologin config above before investigating further.

---
