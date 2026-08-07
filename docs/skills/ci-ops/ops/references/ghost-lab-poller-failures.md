---
name: ghost-lab-poller-failures
description: "Diagnosing ghost-lab status failures on testsuite PRs — poller dedup, Argo template bugs, and the GNOME 50 AT-SPI lab-image blocker."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# ghost-lab poller failure signatures

When `ghost-lab` is failing or missing on many testsuite PRs at once, it is almost
always **infra-caused, not PR-caused**. Diagnose before blocking any PR on it.

## Signature A — workflow never runs, no status posted

The `pr-label-poller` CronWorkflow (namespace `argo`, `*/5 * * * *`) dispatches a
`bluefin-qa-pipeline` workflow per open PR. If the `bluefin-qa-pipeline` WorkflowTemplate
requires a parameter the poller doesn't pass (e.g. `image-digest`), the workflow dies
instantly with `invalid spec: ... templates.pipeline inputs.parameters.X was not supplied`
**before the send-status step runs** — so no `ghost-lab` status is ever posted.

The poller dedups on `pr-number + head-sha` labels, so a PR whose only workflow died
this way is **never re-dispatched automatically**. To re-trigger after the template is
fixed, either delete the stale failed workflow CRs, push a new commit, or use the
poller's `REFRESH_EXISTING=true` mode:

```bash
kubectl delete workflow -n argo -l bluefin.io/pr-number=<N>
```

## Signature B — workflow runs but both lanes die at AT-SPI readiness

Smoke + common lanes both fail after ~2 min at:

```
GNOME Shell AT-SPI readiness failed after 30 attempts (Shell.Eval … ServiceUnknown/not activatable)
```

with only a `gdm-greeter` session present and zero scenarios executed (`results.json not
found`). This is a **lab/`bluefin:testing` image-level** issue, not the PR. Confirm by
checking whether `nightly-smoke` (no PR involved) fails identically — if so, no PR change
will fix it. See `smoke-suite-pre-existing-lab-failures-gnome-50-at-spi.md`.

## How to confirm infra-caused vs PR-caused

1. `argo-mcp-list_workflows` / `kubectl get workflows -n argo` — find the PR's workflow.
2. `argo-mcp-get_workflow` + `argo-mcp-logs_workflow` — read the failure.
3. Instant `invalid spec` death → Signature A (template/poller). AT-SPI readiness timeout
   → Signature B (lab image). Anything inside an actual behave scenario → maybe PR-caused.
4. Cross-check against `nightly-smoke`: if the scheduled no-PR run fails the same way, it
   is infra.

## Merge-gate interaction

Per `docs/skills/meta/human-gates/SKILL.md`, the `ghost-lab` gate is currently a no-op —
do not block ready PRs on it. The required checks are the GHA trio (`Lint & syntax`,
`Behave dry-run`, `pytest`) plus `Coverage snapshot fresh`. Only restore the lab-first
gate when `ghost-lab` starts posting `success` again.
