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

**Runtime skipping covers three tags.** `tests/shared/quarantine.py` skips `@quarantine`,
`@pending` and `@future`, and every suite's `before_scenario` hook calls it. The `--tags
~quarantine` filter only covers `@quarantine`, so `@pending` and `@future` scenarios rely
entirely on that helper. If you remove a tag from `_SKIP_TAGS`, dozens of intentionally
skipped scenarios start executing and failing.

---
