---
name: arc-ghost-runners-local-dev-routing
description: "Deep dive: ARC ghost runners — local dev routing"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## ARC ghost runners — local dev routing

The testsuite can run on the ghost k3s cluster's ARC runners instead of GitHub-hosted runners. ARC replicates the `ubuntu-latest` GHA environment exactly, which is required for reliable debugging.

### How it works

A global pre-push hook (`~/.git-hooks/pre-push`) intercepts pushes to `<image-org>/*` repos and:
1. Creates `ghost/<branch>` with `ubuntu-latest` → `ghost-runners` patched in workflow files
2. Pushes the ghost branch, triggering push-based workflows automatically
3. Auto-dispatches `workflow_dispatch` workflows (skips `manual.yml`)

### Running the full matrix manually on ghost

```bash
GHOST_REF="ghost/<your-branch>"
SUITES="smoke,developer,dx,software,vanilla-gnome,bazzite,lifecycle"

for image in \
  "ghcr.io/<image-org>/bluefin:testing" \
  "ghcr.io/<image-org>/bluefin:stable" \
  "ghcr.io/<image-org>/bluefin-lts:testing" \
  "ghcr.io/<image-org>/bluefin-lts:stable" \
  "ghcr.io/<image-org>/bluefin-lts-hwe:testing" \
  "ghcr.io/<image-org>/bluefin-lts-hwe:stable" \
  "ghcr.io/<image-org>/dakota:testing" \
  "ghcr.io/<image-org>/dakota:stable"; do
  gh workflow run manual.yml \
    --repo <image-org>/testsuite \
    --ref "${GHOST_REF}" \
    --field image="${image}" \
    --field suites="${SUITES}"
done
```

### ARC health check

```bash
kubectl get pods -n arc-systems

kubectl get ephemeralrunners -n arc-runners

kubectl logs -f -n arc-runners -l actions.github.com/scale-set-name=ghost-runners
```

### Ghost branch cleanup

Ghost branches auto-delete after 2 hours via the hook's background process. Manual cleanup:
```bash
git push origin :ghost/<branch-name>
```

---
