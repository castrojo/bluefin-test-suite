---
name: composite-actions-vs-checkout-for-cross-repo-scripts
description: "Deep dive: Composite actions vs checkout for cross-repo scripts"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Composite Actions Vs Checkout For Cross Repo Scripts

## Composite actions vs checkout for cross-repo scripts

**Never** check out `projectbluefin/actions` into the caller repo workspace to run a script.
Placing a nested git repo in the workspace causes `git add -A` to capture it as an
undeclared gitlink (mode 160000 with no `.gitmodules` entry). That gitlink ends up in
squash commits and breaks any consumer build using `submodules: recursive`:

```
fatal: No url found for submodule path '.workflow-scripts' in .gitmodules
```

**Fix:** Wrap the script as a composite action. Composite actions get `$GITHUB_ACTION_PATH`
pointing at the action's own directory — the script is accessible with no checkout:

```yaml
runs:
  using: composite
  steps:
    - shell: bash
      run: python3 "$GITHUB_ACTION_PATH/my_script.py" ...
```

Call it from a reusable workflow with `uses: projectbluefin/actions/.github/actions/my-action@v1`.
GitHub checks out the actions repo to a runner cache path, never inside the caller workspace.

Also: `.gitignore` rules without a leading `/` match anywhere in the tree.
`actions/` ignores `.github/actions/` too. Use `/actions/` to scope to the repo root.

---
