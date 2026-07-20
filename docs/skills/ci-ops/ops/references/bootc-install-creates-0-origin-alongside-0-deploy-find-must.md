---
name: bootc-install-creates-0-origin-alongside-0-deploy-find-must
description: "Deep dive: bootc install creates .0.origin alongside .0 — DEPLOY find must use -type d"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## bootc install creates .0.origin alongside .0 — DEPLOY find must use -type d

**Symptom:** `Install OCI image and configure disk` fails with:
```
ls: cannot access '/mnt/root/ostree/deploy/default/deploy/<hash>.0.origin/usr/lib/modules/': Not a directory
deploy=<hash>.0.origin  kver=
ERROR: vmlinuz not found in deployment or boot partition
```

**Cause:** `bootc install to-disk` writes two entries in the deploy directory:
- `<hash>.0` — the actual deployment directory (correct)
- `<hash>.0.origin` — a small metadata file (NOT a directory)

Without `-type d`, `find -printf '%f\n' | head -1` may return `.0.origin` before `.0` depending on filesystem ordering. Setting `DEPLOY` to a file path causes `ls $D/usr/lib/modules/` to fail with "Not a directory", leaving `KVER` empty.

**Fix (in e2e.yml):** Ensure the `DEPLOY=` assignment uses `-type d`:
```bash
DEPLOY=$(sudo find /mnt/root/ostree/deploy/default/deploy/ -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | head -1)
```

Without `-type d`, `find` may return the `.0.origin` metadata file before the `.0` deployment directory, causing `ls $D/usr/lib/modules/` to fail. The `-type d` flag is required on the `DEPLOY=` assignment; later `for DEP in` loops in the same file already include it.

---
