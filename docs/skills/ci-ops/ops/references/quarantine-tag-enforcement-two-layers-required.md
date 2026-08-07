---
name: quarantine-tag-enforcement-two-layers-required
description: "Deep dive: non-runnable scenario tag enforcement — two runner layers required"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Non-Runnable Tag Enforcement Requires Two Runner Layers

## Filter non-runnable scenarios before hooks

**Symptom:** Scenarios tagged `@quarantine`, `@pending`, or `@future` run and fail.

**How it works (two required layers):**
1. `behave_retry.py` calls `with_skip_filters()` and appends one negative tag
   filter for each non-runnable classification to every behave invocation.
2. `e2e.yml` includes the same three negative filters in `BEHAVE_TAG_ARGS`
   before calling `behave_retry.py`.

Do not remove either layer.

Every suite's `before_scenario` hook also calls `tests/shared/quarantine.py`,
which skips the same tags for direct behave invocations that bypass the runner
filters. Keep the wrapper constant, workflow arguments, and runtime helper in
sync so no single regression activates intentionally disabled coverage.

---
