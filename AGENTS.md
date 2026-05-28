# testsuite — Agent Instructions

This repo owns **Bluefin test content** (behave + qecore-headless + dogtail).  
Lab infrastructure (ghost, exo, ArgoCD, KubeVirt, CronWorkflows) belongs to `projectbluefin/testing-lab`.

## Skills

| Task | Load |
|---|---|
| Any test authoring in this repo | `docs/SKILL.md` |
| GNOME Shell / AT-SPI / dogtail details | `docs/gnome-testing.md` |
| behave scaffolding, step patterns, SSH helpers | `docs/behave-patterns.md` |
| bootc lifecycle / upgrade / rollback tests | `docs/bootc-lifecycle.md` |
| PR review gate, coverage posture | `QA-REVIEW.md` |
| Commands, suite layout, operational guidance | `RUNBOOK.md` |

Start with `docs/SKILL.md`. Load reference docs only when the task touches that area.

## Ownership constraint

New test suites → this repo.  
New infrastructure (Argo templates, VM specs, manifests) → `projectbluefin/testing-lab`.  
When a PR touches both, split into two PRs.
