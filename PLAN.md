# testsuite normalization plan

> Last updated: 2026-05-27

Goal: keep `testsuite` focused on test framework/content and move hardware/lab orchestration ownership to `testing-lab`.

## Target end state

| Concern | Canonical repo |
|---|---|
| Ghost/exo hardware ops, ArgoCD, KubeVirt resources, workflow orchestration | `projectbluefin/testing-lab` |
| Behave features/steps, dogtail/qecore patterns, shared SSH helpers | `projectbluefin/testsuite` |

## Milestones

1. **Boundary docs aligned** ✅  
   README + RUNBOOK now reflect normalized ownership.

2. **Execution contract formalized** 🔄  
   `testing-lab` workflows should consume tests from pinned `testsuite` refs.

3. **Infra content drain from testsuite** 🔄  
   Legacy infra/manifests remain temporarily for compatibility; new infra changes should not be authored here.

4. **Parity and cutover** ⏳  
   Run dual-path validation, then retire duplicate infra docs/entrypoints from testsuite after cutover is stable.

## Near-term tasks

- Keep test authoring guidance in this repo authoritative.
- Keep lab operations guidance authoritative in `testing-lab`.
- Prevent regressions by rejecting PRs that add new hardware/lab ownership into testsuite.
