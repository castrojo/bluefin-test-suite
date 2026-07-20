---
name: results-json-captures-first-pass-only
description: "Deep dive: results.json captures first-pass only"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## results.json captures first-pass only

`behave_retry.py` runs behave up to 3 times. `results.json` is written after the **first pass** and is not overwritten by retries. Always grep the job log for the true final count:
```bash
gh api "repos/org/repo/actions/jobs/$JOB_ID/logs" | grep "scenarios passed" | tail -3
```

---
