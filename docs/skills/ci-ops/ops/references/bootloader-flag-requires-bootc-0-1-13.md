---
name: bootloader-flag-requires-bootc-0-1-13
description: "Deep dive: --bootloader flag requires bootc >= 0.1.13"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Bootloader Flag Requires Bootc 0 1 13

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
