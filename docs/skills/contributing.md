# Agent Contribution Guide

Load when: you found a bug, gap, or improvement while working in this repo.

This is an agent-first repo — agents MAY file issues and PRs directly. No human gating required.

## Decision: which repo?

| Found in | Fix goes in |
|---|---|
| Feature files, step defs, qecore/dogtail patterns, shared SSH helpers | `projectbluefin/testsuite` (this repo) |
| VM specs, CronWorkflows, cluster manifests, infra | `projectbluefin/testing-lab` |

If a fix touches both repos, split into two PRs — one per repo.

## When to contribute

Contribute when you encounter any of the following mid-task:
- A skill doc that describes wrong behavior (wrong API, stale path, incorrect command)
- A missing pattern you had to figure out from scratch (add it so the next agent doesn't)
- A new operational gotcha (failed workflow, unexpected infra behavior)
- A step that's broken or uses a deprecated API
- A coverage gap that's now worth tracking

Don't defer. File the PR as part of your current working session.

## Branch naming

```
feat/<area>/<short-desc>    # new scenarios, new step files
fix/<area>/<short-desc>     # broken steps, wrong docs, stale patterns
docs/<area>/<short-desc>    # doc-only updates
```

Areas: `smoke`, `lifecycle`, `gnome`, `bootc`, `behave`, `security`, `dx`, `hardware`, `flatcar`, `ops`, `skills`

Examples:
```
fix/gnome/update-shell50-eval-pattern
docs/skills/add-contributing-guide
feat/smoke/add-calendar-scenario
```

## Pre-PR validation checklist

### CI checks (`.github/workflows/pr-validate.yml` — must pass)

```bash
# Ruff lint
ruff check tests/ --select E,F,W --ignore E501

# Python syntax
python3 -m py_compile $(find tests/ -name '*.py' | tr '\n' ' ')
```

CI also runs `behave --dry-run` across all suites in a Fedora 41 container. This catches undefined step patterns (feature file uses a phrase with no matching `@step` decorator). **If you add a step phrase to a `.feature` file you must implement the `@step` before pushing.**

To replicate locally (requires Fedora or the runner container `ghcr.io/projectbluefin/testsuite:runner`):
```bash
for suite in tests/*/features/; do
  PYTHONPATH=. python3 -m behave "$suite" --dry-run --no-capture
done
```

### Recommended local checks (not in CI but catch common mistakes)

```bash
# Duplicate step patterns (replace <suite> with the suite you touched)
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d

# @future inventory (verify no accidental tag changes)
just list-stubs
```

All CI checks must pass cleanly before pushing. Local checks should also be clean.

## What to update in the PR

| Change | Files to update |
|---|---|
| New scenario in any suite | Feature file + steps file |
| Scenario count changes | `QA-REVIEW.md` coverage table + `docs/skills/suite-map.md` coverage snapshot |
| New suite or variant-matrix change | `docs/skills/suite-map.md` variant matrix + `RUNBOOK.md` suite layout table |
| New step pattern discovered | `docs/skills/behave.md` |
| New dogtail / GNOME anti-pattern | `docs/skills/gnome.md` |
| New bootc JSON path or gotcha | `docs/skills/bootc.md` |
| Infra gotcha (GDM, VM) | `docs/skills/ops.md` |
| New hard rule for all agents | `docs/skills/index.md` (rules section) |
| e2e workflow changes (inputs, stages, image requirements) | `docs/skills/e2e-workflow.md` |
| Behavior or command change | `README.md` and/or `RUNBOOK.md` if agent-facing docs describe the old behavior |
| @future scenario now implemented | Remove `@future` tag; update `QA-REVIEW.md` + `docs/skills/suite-map.md` status |
| Coverage gap resolved | Update `QA-REVIEW.md` known gaps + `docs/skills/suite-map.md` known gaps |

## PR description format

```markdown
## What

One sentence: what changed and why.

## Evidence

- [ ] Ruff passes
- [ ] py_compile passes
- [ ] No duplicate step phrases

## Scenario count (if changed)

Before: N  After: M  (+/- delta)
```

## Improving skill docs

If a skill doc (`docs/skills/*.md`) is wrong or incomplete:

1. Edit the relevant file in `docs/skills/`
2. Branch: `docs/skills/<what-changed>`
3. In the PR description, quote the old incorrect text and explain what you found
4. No need for the scenario count section if it's docs-only

**Do not add hard rules to individual skill docs** — rules go in `docs/skills/index.md` (single source). Skill docs hold patterns and examples only.

## Testing your changes with the GitHub Action

No cluster access needed. Add a workflow to your branch or fork:

```yaml
name: Test my scenario
on: push
jobs:
  e2e:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@<your-branch>
    with:
      image: ghcr.io/ublue-os/bluefin:latest
      suites: smoke
```

Or use the composite action directly for full control over artifact names and failure handling (see `README.md`).

For scenarios in the `developer` or `dx` suites, swap `bluefin:latest` for the appropriate DX image.

## Merging PRs — merge queue required

This repo uses a **merge queue** (ruleset `main — merge queue`, id 17074591). Enqueue with:

```bash
gh pr merge <NUMBER> --repo projectbluefin/testsuite --squash --auto
```

The `--auto` flag enqueues the PR; the merge queue runs all required CI checks on the merge commit and lands to `main` automatically on green.

| Check | Workflow | Trigger |
|---|---|---|
| `Lint & syntax` | `pr-validate.yml` | `pull_request`, `merge_group`, `push: main` |
| `Behave dry-run` | `pr-validate.yml` | same |
| `pytest` | `unit-tests.yml` | `pull_request`, `merge_group`, `push: main` |

**Prerequisites before enqueueing:** all 3 checks must be green on the PR head. If checks are still running, `--auto` will wait and enqueue once they pass.

Do not attempt `--admin` bypasses.

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

- If you changed `QA-REVIEW.md`, verify the scenario count is still accurate
- If you resolved a `@future` scenario, confirm `just list-stubs` no longer lists it
- If you added a new operational gotcha to `docs/skills/ops.md`, check `docs/skills/index.md`'s rules section doesn't already cover it (avoid duplication)
