---
name: user-bootstrap-primary-group-bug-on-fresh-boots
description: "Deep dive: User Bootstrap primary group bug on fresh boots"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## User Bootstrap primary group bug on fresh boots

**Symptom:** `run-gnome-tests` fails during bluefin-test user bootstrap with:
```
useradd: group '1001' does not exist
exit status 6
```

**Cause:** On first boot, the primary group `1001` (bluefin-test) doesn't exist, causing `useradd -u 1001 -g 1001` to exit with code 6.

**Fix:** Create the primary group first, ignoring duplicates:
```bash
groupadd -g 1001 bluefin-test 2>/dev/null || true
useradd -m -u 1001 -g 1001 -G wheel -s /bin/bash ...
```

---
