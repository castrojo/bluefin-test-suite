---
name: nvidia-services-always-fail-in-qemu
description: "Deep dive: NVIDIA services always fail in QEMU"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## NVIDIA services always fail in QEMU

`nvidia-persistenced.service` and `ublue-nvctk-cdi.service` require a physical GPU. Both are in `IGNORED_FAILED_UNITS_IN_VM` in `system_health_steps.py`. Do not remove them.

---
