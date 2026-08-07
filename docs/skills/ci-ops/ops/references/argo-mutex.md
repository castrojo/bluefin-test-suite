---
name: argo-mutex
description: "ArgoCD timing and mutex behavior with projectbluefin/lab templates."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Argo Mutex

## projectbluefin/lab ArgoCD template resolution timing

Argo WorkflowTemplates are resolved at pod creation time from the current state of the
WorkflowTemplate object in the cluster. ArgoCD syncs `projectbluefin/lab` within ~2 minutes of
a push. If a workflow is submitted before ArgoCD syncs a new template version, the
running workflow pods will use the OLD template.

**Impact:** If you push a fix to run-gnome-tests.yaml, workflows already submitted will
use the old version. Wait for the current workflow to finish, then dispatch a new one.

**ArgoCD sync status:**
```bash
# List Applications first — the Application name is cluster-side and may differ from the repo name.
kubectl get applications -n argocd
kubectl get application <APP_NAME> -n argocd \
  -o jsonpath='{.status.sync.status} {.status.sync.revision}'
```
