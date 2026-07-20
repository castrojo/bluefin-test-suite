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

## Merging PRs — lab test first, then merge queue

**The review workflow is: submit to lab → wait for results → merge on pass, fix on fail.**

The `pr-label-poller` CronWorkflow in `<image-org>/testing-lab` automatically picks up every open testsuite PR every 5 minutes and runs `smoke,common` suites on a real KubeVirt VM. It posts a `ghost-lab` commit status on the PR SHA.

Wait for the `ghost-lab` status to be `success` before enqueuing. If it is `failure`, fix the PR and let the poller re-run.

**Do not enqueue before the lab result is posted.** GHA CI (lint, dry-run, pytest) passing is necessary but not sufficient — those checks do not boot a real VM.

Once `ghost-lab` is green, enqueue with:

```bash
gh pr merge <NUMBER> --repo <image-org>/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue runs all required CI checks on the merge commit and lands to `main` automatically on green.

| Check | Workflow | Trigger |
|---|---|---|
| `Lint & syntax` | `pr-validate.yml` | `pull_request`, `merge_group`, `push: main` |
| `Behave dry-run` | `pr-validate.yml` | same |
| `pytest` | `unit-tests.yml` | `pull_request`, `merge_group`, `push: main` |

Do not attempt `--admin` bypasses.

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
