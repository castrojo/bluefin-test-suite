---
name: polkit-rules-path-check-both-directories
description: "Deep dive: Polkit rules path — check both directories"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Polkit Rules Path Check Both Directories

## Polkit rules path — check both directories

**Symptom:** `common_polkit.feature` "polkit rules directory has Bluefin rules"
returns zero even though Bluefin ships polkit rules.

**Cause:** Bluefin ships polkit rules under `/usr/share/polkit-1/rules.d/` (immutable
layer, read-only). The test was only checking `/etc/polkit-1/rules.d/` (mutable
override path, empty on a stock Bluefin install).

**Fix:** Scan both paths:

```bash
ls /etc/polkit-1/rules.d/*.rules /usr/share/polkit-1/rules.d/*.rules 2>/dev/null | wc -l
```

This returns a non-zero count as long as rules exist in either location.

---
