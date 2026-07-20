---
name: branch-and-worktree
description: "Detailed guidance for testsuite contributors: load when the core contributing skill routes you here."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

# Branch naming

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

## Cross-repo work and worktree hygiene

### Starting a branch — always from main

Before creating any branch, verify you are on main and current:

```bash
cd ~/src/testsuite
git checkout main
git pull origin main
git branch --show-current   # must print "main" before proceeding
git checkout -b <branch-name>
```

**Never commit while on a branch you did not create for the current task.** Run `git branch --show-current` before every `git commit`. If the output is anything other than your intended branch, stop and fix it first.

### Background agents must use worktrees

When dispatching a background agent that will make commits, give it an isolated worktree — never have it `git checkout -b` in the same main worktree you are working in:

```bash
# WRONG — agent and orchestrator share the same working tree
# Agent does: git checkout -b docs/agent-branch origin/main
# Result: you land on the wrong branch, commits go to the wrong place

# CORRECT — agent gets its own worktree
cd ~/src/testsuite
git worktree add ../testsuite-agent-work -b docs/agent-branch origin/main
# Then tell the agent: work in /var/home/jorge/src/testsuite-agent-work
```

### After each PR merges — clean up

Run immediately after your PR is merged:
```bash
cd ~/src/testsuite
git checkout main && git pull origin main
git branch --merged origin/main | grep -v "^\* \|^  main$" | xargs -r git branch -d
git worktree prune
```

This keeps the local branch list short and avoids landing on stale branches next session.

### Cross-repo work

The factory pattern for cross-repo work is **sibling directories under `~/src/`**, named `<repo>-<short-desc>`. Do not clone into `/tmp` or create ad-hoc directories elsewhere.

```bash
# The repos you need are already on disk at ~/src/
ls ~/src/         # common, dakota, bluefin, bluefin-lts, testsuite, ...

# For a new branch on an existing repo, use a git worktree at the sibling location:
cd ~/src/common
git worktree add ../common-fix-e2e -b fix/e2e-foo

# Work in the sibling dir; it's a full working tree
cd ~/src/common-fix-e2e
# ... make changes, pre-commit, push ...

# Remove when done
cd ~/src/common
git worktree remove ../common-fix-e2e
git worktree prune
```

Rules agents must follow:
- **Never clone into `/tmp`** — the repos are already on disk. Cloning wastes time and loses pre-commit hooks, git config, and branch context.
- Sibling dirs are named `<repo>-<short-desc>`, e.g. `dakota-fix-sync-next`, `common-fix-e2e`.
- Remove the worktree immediately after the PR merges or you abandon the branch.
- `git worktree prune` after removal to clean stale refs.

To audit live worktrees:
```bash
git worktree list                     # shows all worktrees with branch and prunable status
git worktree prune --dry-run          # lists refs that can be cleaned up
```

A worktree is stale when:
- Its branch has been squash-merged into main (check: `git log --oneline origin/main.. 2>/dev/null` returns empty)
- It is marked `prunable` in `git worktree list` output
- The feature it was created for was superseded by another PR
