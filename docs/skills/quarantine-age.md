---
name: quarantine-age
description: "Quarantine-age CI enforcement for feature scenarios. Load when changing scripts/check_quarantine_age.py or the quarantine-age job in pr-validate.yml."
metadata:
  type: reference
---

# Quarantine age enforcement

## What it does

`scripts/check_quarantine_age.py` scans current `.feature` files for `@quarantine` scenarios, walks `git log --follow` history for each feature file, and records the first commit where each scenario appears with the `@quarantine` tag.

The script fails when a quarantine age exceeds the configured threshold:

```text
effective threshold = --max-days + --grace-days
default threshold   = 30 + 0 = 30 days
CI rollout threshold = 30 + 30 = 60 days
```

## Workflow requirements

- The `quarantine-age` job lives in `.github/workflows/pr-validate.yml`.
- That job must check out the repository with `fetch-depth: 0`; shallow history breaks age detection.
- The rollout job currently runs `python3 scripts/check_quarantine_age.py --grace-days 30` to avoid blocking PRs immediately while still aging out stale quarantines.

## Operator expectations

- If a quarantine ages out, fix the scenario or convert it to `@future`/`@pending` when it represents planned coverage rather than flaky regression coverage.
- Keep the script dependency-free so it can run on `ubuntu-latest` with only checkout + Python setup.
- Prefer snapshot-based history checks (`git show <sha>:<path>`) over fragile diff hunk matching; the goal is stable CI enforcement, not perfect archeology.
