# testsuite runbook

> Last updated: 2026-05-29

This runbook covers **operational commands** for `projectbluefin/testsuite`.  
Authoring rules, patterns, and skill docs live in `docs/skills/` — load from there.

## Ownership boundary

| Area | Owner |
|---|---|
| Test suites (`tests/**`), step definitions, shared test helpers | `testsuite` |
| Workflow templates, manifests, persistent VMs, CronWorkflows, host operations | `projectbluefin/testing-lab` |

If a change touches both repos, split into two PRs.

## Commands

```bash
# List @future / not-yet-implemented scenarios
just list-stubs
```

## Vanilla-GNOME comparison

`tests/vanilla-gnome/` is a GNOME upstream baseline for `tests/smoke/`.

| Result | Interpretation |
|---|---|
| `smoke=failed`, `vanilla-gnome=passed` | ⚠ Bluefin regression |
| `smoke=failed`, `vanilla-gnome=failed` | ↑ Upstream GNOME issue |
| all other combinations | Informational |

Results are visible in the GitHub Actions job summary and as 30-day artifacts.

