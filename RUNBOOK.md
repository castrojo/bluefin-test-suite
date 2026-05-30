# testsuite runbook

> Last updated: 2026-05-29

This runbook covers **operational commands** for `projectbluefin/testsuite`.  
Authoring rules, patterns, and skill docs live in `docs/skills/` — load from there.

## Ownership boundary

| Area | Owner |
|---|---|
| Test suites (`tests/**`), step definitions, shared test helpers | `testsuite` |
| Workflow templates, manifests, persistent VMs, CronWorkflows, host operations | `testing-lab` |

If a change touches both repos, split into two PRs.

## Commands

```bash
# Lint Argo YAML
just lint

# List @future / not-yet-implemented scenarios
just list-stubs

# Show recent test results from ghost
just results

# Compare smoke vs vanilla-gnome for the newest run
just compare-results

# Compare a specific workflow UID
just compare-results <uid>
```

Lab execution commands (`run-tests`, matrix runs, titan paths) are in `testing-lab`.

## Vanilla-GNOME comparison

`tests/vanilla-gnome/` is a GNOME upstream baseline for `tests/smoke/`.

| Result | Interpretation |
|---|---|
| `smoke=failed`, `vanilla-gnome=passed` | ⚠ Bluefin regression |
| `smoke=failed`, `vanilla-gnome=failed` | ↑ Upstream GNOME issue |
| all other combinations | Informational |

Manual inspection:
1. `just results` → find the workflow UID
2. Open `/var/tmp/bluefin-results/<uid>/smoke/results.json` and `.../vanilla-gnome/results.json`
3. Compare per-scenario `status` values

