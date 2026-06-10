# testsuite runbook

> Last updated: 2026-05-31

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

## Nightly CI

The nightly is driven by `.github/workflows/nightly.yml` (GitHub Actions, no self-hosted runners).

```bash
# Trigger a nightly run manually
gh workflow run nightly.yml --repo projectbluefin/testsuite --ref main

# Check latest nightly status
gh run list --repo projectbluefin/testsuite --workflow nightly.yml --limit 3

# View job-level results for a specific run
gh run view <RUN_ID> --repo projectbluefin/testsuite

# Tail logs for a failing job
gh run view --job=<JOB_ID> --log-failed --repo projectbluefin/testsuite
```

**10 named jobs** (see `docs/skills/suite-map.md` for the full matrix):

| Job | Image | Suites |
|---|---|---|
| `bluefin:latest/gts/lts` | `ghcr.io/ublue-os/bluefin:{tag}` | smoke, developer, common |
| `bluefin-dx:latest/gts/lts` | `ghcr.io/ublue-os/bluefin-dx:{tag}` | smoke, developer, dx, common |
| `bluefin-nvidia-open:latest` | `ghcr.io/ublue-os/bluefin-nvidia-open:latest` | smoke, common |
| `bazzite-gnome:latest` | `ghcr.io/ublue-os/bazzite-gnome:latest` | bazzite |
| `gnomeos-latest` | `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` | vanilla-gnome, software |
| `persist-results` | n/a | Downloads nightly result artifacts and publishes `data/results-YYYY-MM-DD.jsonl` to `gh-pages` |

**Diagnosing failures** — check `docs/skills/ops.md` for the most common causes.

## Merge queue

PRs require 2 approvals + CI. Enqueue via GraphQL (the UI merge button is blocked):

```bash
PR_NODE_ID=$(gh api /repos/projectbluefin/testsuite/pulls/<NUMBER> --jq '.node_id')
gh api graphql -f query="
mutation {
  enqueuePullRequest(input: { pullRequestId: \"${PR_NODE_ID}\" }) {
    mergeQueueEntry { id position }
  }
}"
```

## Vanilla GNOME baseline comparison

The `vanilla-gnome` suite runs against an unmodified GNOME OS disk to establish
a comparison baseline:

- **Failures on vanilla-gnome** → likely upstream GNOME issue
- **Failures on Bluefin but not vanilla** → likely Bluefin-specific regression

Currently this comparison is manual. Procedure:

1. Wait for the nightly run to complete (GitHub Actions — `nightly.yml`)
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

Results are visible in the GitHub Actions job summary, as 30-day artifacts, and as persisted JSONL snapshots on the `gh-pages` branch under `data/results-YYYY-MM-DD.jsonl`.


## Non-blocking nightly jobs

Some nightly jobs run with `continue-on-error: true` to track upstream image regressions outside the testsuite's control. A failing non-blocking job turns orange (⚠️) but does not fail the overall nightly run.

Check current non-blocking state in `nightly.yml` (`continue_on_error: true` in the matrix). When an upstream fix ships and the nightly passes cleanly for two consecutive runs, remove the flag and close the tracking issue.

```bash
# Check which jobs are currently non-blocking
grep -A3 "continue_on_error" .github/workflows/nightly.yml | grep -B1 "true"

# Watch a nightly run
gh run list --repo projectbluefin/testsuite --workflow nightly.yml --limit 1
```

## Update checklist for docs + tests

When scenario counts change, update both files (they are co-authoritative):
- `docs/skills/suite-map.md` — per-suite table
- `QA-REVIEW.md` — total line at the top
