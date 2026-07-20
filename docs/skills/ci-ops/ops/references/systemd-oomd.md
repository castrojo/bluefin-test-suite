---
name: systemd-oomd
description: "Why systemd-oomd fails in QEMU and the workaround."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## systemd-oomd: both .service AND .socket fail in QEMU

`systemd-oomd` monitors PSI files under `/proc/pressure/` which QEMU VMs don't expose. Both `systemd-oomd.service` **and** `systemd-oomd.socket` are in `IGNORED_FAILED_UNITS_IN_VM`. When adding entries to the allowlist, always check if both the `.service` and its companion `.socket` need ignoring.

---
