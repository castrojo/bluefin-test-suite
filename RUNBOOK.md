# testsuite runbook

> Last updated: 2026-06-23

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

## Manual CI runs

PR validation is the only standing CI gate. For ad hoc image and suite runs, use `.github/workflows/manual.yml` (GitHub Actions, no self-hosted runners).

```bash
# Trigger a manual run (smoke suite, auto-shards into smoke-a + smoke-b)
gh workflow run manual.yml --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/bluefin:testing \
  -f suites=smoke

# Trigger common suite (auto-shards into common-a + common-b)
gh workflow run manual.yml --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/bluefin:testing \
  -f suites=common

# Multiple suites in one run
gh workflow run manual.yml --repo projectbluefin/testsuite --ref main \
  -f image=ghcr.io/projectbluefin/bluefin:testing \
  -f suites=smoke,common,vanilla-gnome

# Check recent manual runs
gh run list --repo projectbluefin/testsuite --workflow manual.yml --limit 3

# View job-level results for a specific run
gh run view <RUN_ID> --repo projectbluefin/testsuite

# Tail logs for a failing job
gh run view --job=<JOB_ID> --log-failed --repo projectbluefin/testsuite
```

**Diagnosing failures** — check `docs/skills/ops.md` for the most common causes.

**Suite sharding**: `suites: smoke` and `suites: common` each automatically expand into two parallel jobs. New `.feature` files are picked up automatically — no shard configuration needed.

## Merge queue

This repo uses a **merge queue** (ruleset `main — merge queue`). Enqueue with:

```bash
gh pr merge <NUMBER> --repo projectbluefin/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue runs all required CI checks on the merge commit and lands to `main` automatically on green. No manual approvals required — CI is the gate.

Required checks: `Lint & syntax`, `Behave dry-run`, `pytest` — all must be green before enqueueing.

## Vanilla GNOME baseline comparison

The `vanilla-gnome` suite runs against an unmodified GNOME OS disk to establish
a comparison baseline:

- **Failures on vanilla-gnome** → likely upstream GNOME issue
- **Failures on Bluefin but not vanilla** → likely Bluefin-specific regression

Currently this comparison is manual. Procedure:

1. Dispatch and wait for two manual runs to complete:
   - Bluefin baseline: `image=ghcr.io/projectbluefin/bluefin:testing`, `suites=smoke`
   - GNOME OS baseline: `image=quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest`, `suites=vanilla-gnome`
2. Compare results for the overlapping scenarios between `smoke` and `vanilla-gnome`:
   - `gnome_calculator` — launch and basic interaction
   - `gnome_text_editor` — launch and typing
   - `gnome_files_browse_dir` — Nautilus directory listing
   - `gnome_settings_about_display` — Settings → About rendering
   - `firefox_launch_and_close` — Firefox launch via Flatpak
   - `system_monitor_app_list` — System Monitor process table
   - `app_grid_search` — GNOME Shell app search
3. Flag scenarios that fail on Bluefin but pass on vanilla as Bluefin regressions
4. Record findings in the relevant issue

Future: automated diff via `just compare-results` (see #22).

## Update checklist for docs + tests

| Result | Interpretation |
|---|---|
| `smoke=failed`, `vanilla-gnome=passed` | ⚠ Bluefin regression |
| `smoke=failed`, `vanilla-gnome=failed` | ↑ Upstream GNOME issue |
| all other combinations | Informational |

Results are visible in the GitHub Actions job summary and as run artifacts.

## Update checklist for docs + tests

When scenario counts change, update both files (they are co-authoritative):
- `docs/skills/suite-map.md` — per-suite table
- `QA-REVIEW.md` — total line at the top
