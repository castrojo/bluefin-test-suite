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

## Worktree policy

All isolated work happens in **`.worktrees/<short-desc>` at the repository root**.
This directory is already listed in `.gitignore`; never remove that entry.

### Before creating anything — detect existing isolation

You may already be inside a linked worktree. Creating another one nests state
that nobody can find later.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
git rev-parse --show-superproject-working-tree 2>/dev/null   # non-empty = submodule, not a worktree
```

If `GIT_DIR != GIT_COMMON` and you are not in a submodule, you are already
isolated. Use it. Do not create another worktree.

### Creating a worktree

Always branch from `origin/main`, never from whatever happens to be checked out:

```bash
cd ~/src/testsuite
git fetch origin
git worktree add .worktrees/<short-desc> -b <branch-name> origin/main
cd .worktrees/<short-desc>
git branch --show-current    # confirm before your first commit
```

If a native worktree tool is available in your harness (`EnterWorktree`,
`/worktree`, a `--worktree` flag), prefer it — it owns placement, branching, and
cleanup. Falling back to raw `git worktree add` when a native tool exists
creates state the harness cannot see or clean up.

### Rules

- **`.worktrees/` at the repo root is the only sanctioned location.** Not
  `/tmp`, not `/var/tmp`, not sibling directories under `~/src/`. Temp
  directories are wiped unpredictably and lose pre-commit hooks, git config, and
  branch context.
- **Never clone** — the repos are already on disk under `~/src/`. A worktree
  shares the object store; a clone does not.
- **One worktree per branch, named after the work**, e.g.
  `.worktrees/quarantine-fix`, `.worktrees/factory-onboard`.
- **Never commit from a branch you did not create for the current task.** Run
  `git branch --show-current` before every commit.
- **Never touch another worktree's branch or working tree.** A dirty tree
  elsewhere belongs to someone else's in-flight task.
- **Verify `.worktrees/` is ignored** before first use:
  `git check-ignore -q .worktrees`. An unignored worktree directory commits the
  entire tree into the repository.

### Dispatching agents

Every agent that will make commits gets its own worktree. Never let an agent run
`git checkout -b` in a working tree you are also using — you will land on the
wrong branch and commits will go to the wrong place.

```bash
git worktree add .worktrees/<agent-task> -b <branch-name> origin/main
# then instruct the agent: work only in .worktrees/<agent-task>
```

Tell the agent explicitly which worktree is its own, and that the main checkout
may be dirty with unrelated work it must not touch.

### Cleanup — run after every merge

```bash
cd ~/src/testsuite
git fetch origin
git worktree remove .worktrees/<short-desc>   # fails safely if the tree is dirty
git branch -d <branch-name>                   # -D if the PR was squash-merged
git worktree prune
```

`git worktree remove` refuses to delete a worktree with uncommitted changes.
That refusal is a signal to inspect, not to force with `--force`.

### Auditing

```bash
git worktree list                # all worktrees, branches, prunable status
git worktree prune --dry-run     # refs that can be cleaned up
```

A worktree is stale when any of these hold:

- Its PR is merged (`gh pr list --head <branch> --state all --json number,state`)
- It is marked `prunable` in `git worktree list`
- It has zero commits ahead of `origin/main`
  (`git rev-list --count origin/main..<branch>` returns `0`) and no open PR
- The work it existed for was superseded by another PR

Squash-merged branches do **not** appear in `git branch --merged origin/main`.
Check PR state rather than merge-base when deciding whether a branch is done.

## Cross-repo work

Other factory repos are already on disk under `~/src/`. Use the same
`.worktrees/` convention inside each repo:

```bash
cd ~/src/common
git worktree add .worktrees/fix-e2e -b fix/e2e-foo origin/main
```

Confirm the target repo ignores `.worktrees/` before the first commit. Never
write to `ublue-os/*`; read-only API calls there are fine.
