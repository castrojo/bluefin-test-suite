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

**Submit to lab → wait for `ghost-lab` → merge on pass, fix on fail.**

`ghost-lab` **is** posted on testsuite PRs and **must be green before merging**.
It was dead for a long stretch: every testsuite lab workflow was rejected at
Argo admission in 0s because `bluefin-qa-pipeline`'s `pipeline` template
declared `image-digest` required with no default while `pr-poller` emitted it as
an empty string, and Argo normalises an empty string to absent.
`projectbluefin/lab#606` fixed that; `#607`/`#608`/`#610`/`#611` fixed
nested-target provisioning. Statuses post reliably since (observed on testsuite
`#724`, `#726`, `#727`, `#729`). Ignore any older "nothing will arrive" note.

### The gate to apply

1. **GitHub Actions CI green** — the five required checks below.
2. **`ghost-lab` green** — not optional, and not implied by (1). See below.
3. **Human approval to merge.** Merging is a human gate; an agent prepares the
   PR and asks. See `docs/skills/meta/human-gates/SKILL.md`.

| Check | Workflow | Trigger |
|---|---|---|
| `Lint & syntax` | `pr-validate.yml` | `pull_request`, `merge_group`, `push: main` |
| `Behave dry-run` | `pr-validate.yml` | same |
| `Quarantine age` | `pr-validate.yml` | same |
| `pytest` | `unit-tests.yml` | `pull_request`, `merge_group`, `push: main` |
| `docs-validate` | `docs-validate.yml` | `pull_request`, `merge_group`, `push: main` |

These are the required status checks configured on the `main — merge queue`
repository **ruleset** (which also enables the merge queue, squash method, and
`ALLGREEN` grouping). `gh api repos/projectbluefin/testsuite/branches/main/protection`
returns `404 Branch not protected` — expected, because the configuration lives
in a ruleset. Verify with `gh api repos/projectbluefin/testsuite/rulesets`.

Once CI and `ghost-lab` are green and a human has approved, enqueue with:

```bash
gh pr merge <NUMBER> --repo projectbluefin/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue re-runs the required checks
on the merge commit and lands to `main` automatically on green. Do not attempt
`--admin` bypasses.

### The five GHA checks are not sufficient

**GHA CI does not boot a real VM.** Lint, behave dry-run, quarantine age,
pytest, and docs-validate verify syntax, step-name resolution, doc structure,
and helper unit behaviour only. Real-VM regressions — GNOME Shell/AT-SPI
timing, GDM state, bootc upgrade/rollback, oomd kills — are invisible to all
five. `ghost-lab` runs the `smoke,common` suites on a real KubeVirt VM and is
the only pre-merge signal that catches them. A PR that is "5/5 green" has had
**no** runtime coverage.

Still say so explicitly in the PR description when a change has had no real-VM
coverage (for example when `ghost-lab` is red for an unrelated repo-wide
blocker and a human waives it).

### Reading and re-running `ghost-lab`

**It is a commit status, not a check run.** It does not appear in the
check-runs API, so tooling that only reads check runs will show it as missing.
Query the status API against the PR head SHA:

```bash
gh api repos/projectbluefin/testsuite/commits/$(gh pr view <N> \
  --repo projectbluefin/testsuite --json headRefOid --jq .headRefOid)/status \
  --jq '.statuses[] | {context, state}'
```

**Dispatch is automatic for testsuite.** The `pr-label-poller` CronWorkflow in
`projectbluefin/lab` runs every 5 minutes and auto-dispatches for every repo in
`AUTO_REPOS` (`common`, `knuckle`, `testsuite`). You do **not** need to add a
label: `test-on-lab` is only a Pass-2 catch-all for repos outside `AUTO_REPOS`,
and that label does not exist in this repository. Pushing a new commit is
enough; the poller picks up the new head SHA within 5 minutes.

**Dedup is by label.** The poller keys off `bluefin.io/pr-number` and
`bluefin.io/pr-sha` on the Argo workflow, so it will not re-dispatch for a SHA
it has already run. To force a re-run at the same SHA, delete the workflow and
wait for the next poll:

```bash
kubectl delete workflow -n argo -l bluefin.io/pr-number=<N>
```

**There is a `MAX_DISPATCH` rate cap.** A large batch of open PRs will not all
dispatch in one poll cycle; they drain over successive 5-minute runs. A PR
sitting without a `ghost-lab` status for a few minutes is normal backlog, not a
broken gate.

### Lesson: a merged fix is not a working fix

Verify a gate by observing a real signal end to end. Never conclude a gate works
because a fix for it merged: three consecutive fixes to this reporter each
merged green, and each left the gate posting nothing. The fix that finally
worked (`lab#606`) was confirmed by observing `ghost-lab` statuses on four
separate PRs, not by reading the diff. Reporting is a leg of the pipeline that
no upstream test exercises — an unauthenticated request or a rejected payload
fails silently from the PR's point of view. This is the same failure class as a
test suite that reports green while silently skipping every scenario.

**Counted-evidence rule for token plumbing.** Token-like strings are redacted in
command and log output, so you can never confirm an `Authorization` header by
reading it — a working header and an uninterpolated placeholder look identical.
Compare occurrence counts against a known-working file instead:

```bash
grep -c GITHUB_TOKEN <template>.yaml   # must match the working reporter's count
```

A template that defines the token but never interpolates it into the request
shows a lower count than the reference. Counts survive redaction; rendered text
does not.

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
