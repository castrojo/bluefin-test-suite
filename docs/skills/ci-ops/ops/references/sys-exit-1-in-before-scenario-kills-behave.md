---
name: sys-exit-1-in-before-scenario-kills-behave
description: "Deep dive: sys.exit(1) in before_scenario kills behave"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## sys.exit(1) in before_scenario kills behave

**Symptom:** All scenarios after the first failure appear to pass (not run). Behave exits non-zero but only shows the first failure.

**Cause:** `sys.exit(1)` inside `before_scenario` raises `SystemExit`, terminates the entire behave process.

**Fix:** Replace every `sys.exit(1)` with `raise`. Verify:
```bash
grep -r "sys.exit" tests/*/features/environment.py
```

---
