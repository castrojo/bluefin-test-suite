---
name: reviewing-and-merging
description: "Detailed guidance for testsuite contributors: load when the core contributing skill routes you here."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

# Reviewing PRs before merging

## Reviewing PRs before merging

Before enqueuing any PR, read the diff (`gh pr diff <N> --repo <image-org>/testsuite`). Check:

1. **Correctness** — step names in `.feature` files have matching `@step` implementations; new steps don't duplicate existing ones.
2. **Not superseded** — compare the PR's changes against `git show origin/main:<file>` for each modified file. If the core change is already in main (landed via another PR), close the PR with a comment explaining which commit superseded it.
3. **Contributor PRs** — check `maintainerCanModify` before deciding to fix vs close:
   ```bash
   gh pr view <N> --repo <image-org>/testsuite --json maintainerCanModify,headRepositoryOwner,headRefName
   ```
   If `maintainerCanModify: true`, check out and push fixes directly to the contributor's branch rather than opening a new PR.

### Resolving count conflicts when rebasing

PRs that update `docs/qa-review.md` or `docs/skills/test-authoring/suite-map/SKILL.md` counts frequently conflict when rebased. Resolve by recalculating from main's current counts plus the PR's delta — never blindly accept either side:

```
# Identify what the PR changes (e.g. removes 8 @quarantine tags)
# Start from main's numbers and apply the delta:
#   main:  268 total / 30 quarantined / 217 active / 21 stubs
#   PR:    removes 8 quarantine tags
#   result: 268 / 22 quarantined / 225 active / 21 stubs
```

The suite table row for the affected suite must also be updated to reflect the correct active/quarantined split.

### Merge queue dependency ordering

If PR B depends on step functions added by PR A (e.g. B's `.feature` uses `Switch to migration target` defined in A's `steps.py`), enqueue A first. The merge queue tests each entry against all preceding entries in the queue, so B will see A's steps in CI even before A merges to `main`.

Corollary: do not close or skip enqueuing a "dependency" PR just because its CI ran against an older `main` — re-enqueue both in order.

## Merging PRs — the effective gate today

> **The `ghost-lab` commit status is NOT currently posted on testsuite PRs. Do not wait for it — you will block forever.**
> Tracking issue: [`projectbluefin/lab#471`](https://github.com/projectbluefin/lab/issues/471).
> Fix in flight: [`projectbluefin/lab#474`](https://github.com/projectbluefin/lab/pull/474) — **open, not merged** as of 2026-07-28.

### ⚠️ This section expires — check before you trust it

[`projectbluefin/lab#474`](https://github.com/projectbluefin/lab/pull/474) ("fix: report testsuite lab status directly", `Fixes #471`) adds `argo/workflow-templates/github-status-reporter.yaml` and modifies `argo/workflow-templates/pr-poller.yaml` so testsuite child workflows report a **direct `ghost-lab` commit status**, while the fully-enrolled repos (`bluefin`, `bluefin-lts`, `dakota`) keep their detailed Check Runs. When it lands, the lab gate becomes live again and everything below about the gate being unavailable becomes wrong.

**Before relying on this section, verify whether the gate is live:**

```bash
# 1. Is the fix merged?
gh pr view 474 --repo projectbluefin/lab --json state,mergedAt

# 2. Is a ghost-lab status actually being posted on a testsuite PR?
gh api repos/<image-org>/testsuite/commits/$(gh pr view <N> --repo <image-org>/testsuite --json headRefOid --jq .headRefOid)/status \
  --jq '.statuses[].context'
```

If step 2 prints `ghost-lab` for a recent PR, **the gate is live again**: revert to the lab-first gate documented under "Target state" below — wait for `ghost-lab: success` on the PR SHA before enqueuing — demote this "current gate" text to a historical note, and update `docs/skills/meta/human-gates/SKILL.md` in the same PR. Do not leave both framings in place.

If step 2 prints nothing, the gate is still dead and this section still applies.

### Current gate (what to actually do, while the lab gate is dead)

1. **GitHub Actions CI green** — the three required checks below must pass.
2. **Human approval to merge.** Merging is a human gate; an agent prepares the PR and asks. See `docs/skills/meta/human-gates/SKILL.md`.

| Check | Workflow | Trigger |
|---|---|---|
| `Lint & syntax` | `pr-validate.yml` | `pull_request`, `merge_group`, `push: main` |
| `Behave dry-run` | `pr-validate.yml` | same |
| `pytest` | `unit-tests.yml` | `pull_request`, `merge_group`, `push: main` |

These three are the required status checks configured on the `main — merge queue` repository **ruleset** (which also enables the merge queue, squash method, `ALLGREEN` grouping). Note that `gh api repos/<image-org>/testsuite/branches/main/protection` returns `404 Branch not protected` — that is expected, because the configuration lives in a ruleset rather than legacy branch protection. Verify with:

```bash
gh api repos/<image-org>/testsuite/rulesets
```

Once CI is green and a human has approved the merge, enqueue with:

```bash
gh pr merge <NUMBER> --repo <image-org>/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue re-runs the required checks on the merge commit and lands to `main` automatically on green.

Do not attempt `--admin` bypasses.

### Known reduction in assurance

**GHA CI does not boot a real VM.** Lint, behave dry-run, and pytest verify syntax, step-name resolution, and helper unit behaviour only. Real-VM regressions — GNOME Shell/AT-SPI timing, GDM state, bootc upgrade/rollback, oomd kills — are **currently uncaught before merge**.

This is a known gap, not a licence to skip verification. While it persists:

- Prefer changes that are verifiable by dry-run and unit tests.
- For anything touching runtime step behaviour, environment hooks, or bootc flows, request a manual lab run and paste the result in the PR before asking for merge approval (see `docs/runbook.md` for manual run commands).
- Say so explicitly in the PR description when a change has had no real-VM coverage.

### Target state (currently broken — restore when lab#471/#474 land)

The intended workflow is: **submit to lab → wait for results → merge on pass, fix on fail.**

The `pr-label-poller` CronWorkflow in `<image-org>/testing-lab` picks up every open testsuite PR every 5 minutes and runs the `smoke,common` suites on a real KubeVirt VM. In the target state it publishes that result back to the PR SHA, and reviewers wait for it to be `success` before enqueuing; on `failure` the PR is fixed and the poller re-runs. GHA CI passing is necessary but not sufficient.

Why it does not work today (verified 2026-07-28):

- `gh api repos/<image-org>/testsuite/commits/<sha>/status` returns **zero** statuses for every open testsuite PR (re-checked 2026-07-28 against #656, #653, #651, #652, #654, #648 — all empty). The only `ghost-lab` status anywhere in the repo is on PR #609, state `error`, dated 2026-07-20. PR #616 merged after that date with no lab status at all.
- The poller itself is healthy and not suspended (schedule `*/5 * * * *`, recent runs `Succeeded`), and `testsuite` is in its `AUTO_REPOS` list — the QA workflows genuinely run. The results are computed and then discarded.
- Root cause: in the lab repo's `argo/workflow-templates/pr-poller.yaml`, only `bluefin`, `bluefin-lts`, and `dakota` get the `report-start` / `onExit: report-final` (`github-check-reporter`) and `dispatch_lab_check` steps. `testsuite` falls through to a bare `kubectl create` branch with no reporter and no dispatch. The string `ghost` does not appear in that file at all: the old direct commit-status path was replaced by `testing-lab / <repo>` Check Runs and testsuite was never migrated.
- `.github/workflows/lab-check.yml` does not exist in this repo, so testsuite is "half-enrolled" in the poller. [`lab#474`](https://github.com/projectbluefin/lab/pull/474) addresses this without requiring that workflow: it routes testsuite child workflows to a new `github-status-reporter.yaml` template that posts the `ghost-lab` commit status directly, leaving the Check Run path for the fully-enrolled repos.

When [`projectbluefin/lab#474`](https://github.com/projectbluefin/lab/pull/474) merges (it closes [`lab#471`](https://github.com/projectbluefin/lab/issues/471)) **and** you have observed a `ghost-lab` status on a testsuite PR head SHA with the verification command above, re-enable this section as the gate: wait for `ghost-lab` on the PR SHA to be green before enqueuing, move the "current gate" text back under it as a historical note ("`ghost-lab` was not posted between 2026-07-20 and the day lab#474 landed"), and make the matching edit to `docs/skills/meta/human-gates/SKILL.md`.

Do not restore it on the strength of the merge alone — lab#474 changes the poller template, and a template change is only effective once the CronWorkflow picks it up. Confirm an actual status exists first.

## Dependency updates (Renovate / mergeraptor)

Dependency updates for this repo and `<image-org>/bluefin` are managed by Renovate (bot login: `app/mergeraptor`). No manual action is required from agents.

**Automerge policy (configured in `renovate.json`):**

| Update type | Action |
|---|---|
| `digest`, `pin`, `patch`, `minor` | Automerged when CI passes (squash) |
| `major` | Opens a PR — requires manual review |

**Triggering Renovate manually** (e.g. after config changes):

1. Open the [Dependency Dashboard](https://github.com/<image-org>/testsuite/issues) issue (titled "Dependency Dashboard")
2. Check the **"rebase all open PRs"** checkbox — Renovate will pick up the updated config and rebase all open dep PRs

Or edit the checkbox directly via gh:
```bash
gh issue view <dashboard-issue-number> --repo <image-org>/testsuite --json body --jq '.body' | \
  sed 's/ - \[ \] <!-- rebase-all-open-prs -->/ - [x] <!-- rebase-all-open-prs -->/' | \
  gh issue edit <dashboard-issue-number> --repo <image-org>/testsuite --body-file -
```

**bluefin-specific:** `renovate.json` in `<image-org>/bluefin` sets `"baseBranches": ["testing"]` — all Renovate PRs there target the `testing` branch, not `main`.

## After the PR merges

- If you changed `docs/qa-review.md`, verify the scenario count is still accurate
- If you resolved a `@future` scenario, confirm `just list-stubs` no longer lists it
- If you added a new operational gotcha to `docs/skills/ci-ops/ops/SKILL.md`, check `docs/skills/index.md`'s rules section doesn't already cover it (avoid duplication)
