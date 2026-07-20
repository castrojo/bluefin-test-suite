---
name: quarantine-tag-enforcement-two-layers-required
description: "Deep dive: @quarantine tag enforcement — two layers required"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Quarantine Tag Enforcement Two Layers Required

## @quarantine tag enforcement — two layers required

**Symptom:** Scenarios tagged `@quarantine` run and fail.

**How it works (two required layers):**
1. `behave_retry.py` calls `with_quarantine_filter()` — appends `--tags ~@quarantine` to every behave invocation.
2. `e2e.yml` sets `BEHAVE_TAG_ARGS="--tags ~@quarantine"` before calling `behave_retry.py`.

Do not remove either layer.

---
