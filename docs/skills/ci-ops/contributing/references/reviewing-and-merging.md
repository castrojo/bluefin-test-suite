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

Before enqueuing any PR, read the diff (`gh pr diff <N> --repo projectbluefin/testsuite`). Check:

1. **Correctness** — step names in `.feature` files have matching `@step` implementations; new steps don't duplicate existing ones.
2. **Not superseded** — compare the PR's changes against `git show origin/main:<file>` for each modified file. If the core change is already in main (landed via another PR), close the PR with a comment explaining which commit superseded it.
3. **Contributor PRs** — check `maintainerCanModify` before deciding to fix vs close:
   ```bash
   gh pr view <N> --repo projectbluefin/testsuite --json maintainerCanModify,headRepositoryOwner,headRefName
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

## Merging PRs — the effective gate

> **The `ghost-lab` lab status is not posted on testsuite PRs. Do not wait for it — you will block forever.**
> All live state (current status, the PRs attempting a fix, dates) belongs in the tracking issue:
> [`projectbluefin/lab#471`](https://github.com/projectbluefin/lab/issues/471). Do not copy it back into this file.

### The gate to apply

1. **GitHub Actions CI green** — the three required checks below must pass.
2. **Human approval to merge.** Merging is a human gate; an agent prepares the PR and asks. See `docs/skills/meta/human-gates/SKILL.md`.

| Check | Workflow | Trigger |
|---|---|---|
| `Lint & syntax` | `pr-validate.yml` | `pull_request`, `merge_group`, `push: main` |
| `Behave dry-run` | `pr-validate.yml` | same |
| `pytest` | `unit-tests.yml` | `pull_request`, `merge_group`, `push: main` |

These three are the required status checks configured on the `main — merge queue` repository **ruleset** (which also enables the merge queue, squash method, `ALLGREEN` grouping). Note that `gh api repos/projectbluefin/testsuite/branches/main/protection` returns `404 Branch not protected` — that is expected, because the configuration lives in a ruleset rather than legacy branch protection. Verify with:

```bash
gh api repos/projectbluefin/testsuite/rulesets
```

Once CI is green and a human has approved the merge, enqueue with:

```bash
gh pr merge <NUMBER> --repo projectbluefin/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue re-runs the required checks on the merge commit and lands to `main` automatically on green.

Do not attempt `--admin` bypasses.

### Known reduction in assurance

**GHA CI does not boot a real VM.** Lint, behave dry-run, and pytest verify syntax, step-name resolution, and helper unit behaviour only. Real-VM regressions — GNOME Shell/AT-SPI timing, GDM state, bootc upgrade/rollback, oomd kills — are **currently uncaught before merge**.

This is a known gap, not a licence to skip verification. While it persists:

- Prefer changes that are verifiable by dry-run and unit tests.
- For anything touching runtime step behaviour, environment hooks, or bootc flows, request a manual lab run and paste the result in the PR before asking for merge approval (see `docs/runbook.md` for manual run commands).
- Say so explicitly in the PR description when a change has had no real-VM coverage.

### How to tell whether the lab gate is live

The intended workflow is **submit to lab → wait for results → merge on pass, fix on fail**: the `pr-label-poller` CronWorkflow in `projectbluefin/lab` runs the `smoke,common` suites on a real KubeVirt VM for every open testsuite PR and publishes the result as a `ghost-lab` commit status on the PR head SHA. The poller runs; the reporting leg is what has been broken.

The only trustworthy check is an observed status. Run:

```bash
gh api repos/projectbluefin/testsuite/commits/$(gh pr view <N> --repo projectbluefin/testsuite --json headRefOid --jq .headRefOid)/status \
  --jq '.statuses[].context'
```

- **`ghost-lab` appears** → the gate is live. Restore the lab-first gate (`ghost-lab: success` on the PR SHA required before enqueuing), and update this file and `docs/skills/meta/human-gates/SKILL.md` in the same PR. Do not leave both framings in place.
- **Nothing printed** → the gate is still dead and the GHA-only gate above applies.

### Lesson: a merged fix is not a working fix

Verify a gate by observing a real signal end to end. Never conclude a gate works because a fix for it merged: three consecutive fixes to this reporter each merged green, and each left the gate posting nothing. Reporting is a leg of the pipeline that no upstream test exercises — an unauthenticated request or a rejected payload fails silently from the PR's point of view. This is the same failure class as a test suite that reports green while silently skipping every scenario.

**Counted-evidence rule for token plumbing.** Token-like strings are redacted in command and log output, so you can never confirm an `Authorization` header by reading it — a working header and an uninterpolated placeholder look identical. Compare occurrence counts against a known-working file instead:

```bash
grep -c GITHUB_TOKEN <template>.yaml   # must match the working reporter's count
grep -c Bearer       <template>.yaml
```

A template that defines the token but never interpolates it into the request shows a lower count than the reference. Counts survive redaction; rendered text does not.

## Dependency updates (Renovate / mergeraptor)

Dependency updates for this repo and `projectbluefin/bluefin` are managed by Renovate (bot login: `app/mergeraptor`). No manual action is required from agents.

**Automerge policy (configured in `renovate.json`):**

| Update type | Action |
|---|---|
| `digest`, `pin`, `patch`, `minor` | Automerged when CI passes (squash) |
| `major` | Opens a PR — requires manual review |

**Triggering Renovate manually** (e.g. after config changes):

1. Open the [Dependency Dashboard](https://github.com/projectbluefin/testsuite/issues) issue (titled "Dependency Dashboard")
2. Check the **"rebase all open PRs"** checkbox — Renovate will pick up the updated config and rebase all open dep PRs

Or edit the checkbox directly via gh:
```bash
gh issue view <dashboard-issue-number> --repo projectbluefin/testsuite --json body --jq '.body' | \
  sed 's/ - \[ \] <!-- rebase-all-open-prs -->/ - [x] <!-- rebase-all-open-prs -->/' | \
  gh issue edit <dashboard-issue-number> --repo projectbluefin/testsuite --body-file -
```

**bluefin-specific:** `renovate.json` in `projectbluefin/bluefin` sets `"baseBranches": ["testing"]` — all Renovate PRs there target the `testing` branch, not `main`.

## After the PR merges

- If you changed `docs/qa-review.md`, verify the scenario count is still accurate
- If you resolved a `@future` scenario, confirm `just list-stubs` no longer lists it
- If you added a new operational gotcha to `docs/skills/ci-ops/ops/SKILL.md`, check `docs/SKILL.md`'s rules section doesn't already cover it (avoid duplication)
