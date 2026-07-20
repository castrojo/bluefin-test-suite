---
name: git-restore-vs-git-checkout-for-full-directory-reset
description: "Deep dive: git restore vs git checkout for full directory reset"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Git Restore Vs Git Checkout For Full Directory Reset

## git restore vs git checkout for full directory reset

When a branch-sync workflow merges main into another branch, the merge can pull in
new files under `.github/workflows/`. Pushing those changes requires `workflows: write`
which `GITHUB_TOKEN` does not have by default.

**Fix:** After the merge, fully reset the target directory to its pre-merge state with:

```bash
git restore --source='HEAD@{1}' --staged --worktree -- .github/workflows/
```

**Do NOT use** `git checkout HEAD@{1} -- .github/workflows/` — that command only restores
paths that existed before the merge. It will **not** delete files newly added by the merge.
`git restore --staged --worktree` makes the working tree and index exactly match the
pre-merge ref, including deletions.

After restoring, stage the directory before amending the merge commit:
```bash
git add .github/workflows/
git commit --amend --no-edit
git push origin <branch>
```
