> **Archived** — This plan was written in 2026-05. Milestones 1-2 were completed; milestones 3-5 were superseded by later work. Kept for historical context only.

# testsuite normalization plan

> Last updated: 2026-05-29

Goal: keep `testsuite` focused on test framework/content and move hardware/lab orchestration ownership to `testing-lab`.

## Target end state

| Concern | Canonical repo |
|---|---|
| Ghost/exo hardware ops, ArgoCD, KubeVirt resources, workflow orchestration | `projectbluefin/testing-lab` |
| Behave features/steps, dogtail/qecore patterns, shared SSH helpers | `projectbluefin/testsuite` |

## Milestones

1. **Boundary docs aligned** ✅  
   README + RUNBOOK reflect normalized ownership.

2. **Agent skill tree** ✅  
   `docs/skills/` created with consolidated rules, contributing guide, suite map, ops gotchas. Single source of truth for all agent-facing guidance.

3. **Execution contract formalized** 🔄  
   `testing-lab` workflows should consume tests from pinned `testsuite` refs.

4. **Infra content drain from testsuite** 🔄  
   Legacy `argo/`, `manifests/`, `argocd/`, `exo-1/` remain temporarily for compatibility. New infra changes must not be authored here.

5. **Parity and cutover** ⏳  
   Run dual-path validation, then retire duplicate infra entrypoints from testsuite after cutover is stable.

