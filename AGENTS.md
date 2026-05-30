# testsuite — Agent Instructions

This repo owns **Bluefin test content** (behave + qecore-headless + dogtail).  
Lab infrastructure (ghost, exo, ArgoCD, KubeVirt, CronWorkflows) belongs to `projectbluefin/testing-lab`.

## Skills

**Start here:** `docs/skills/index.md` — hard rules + load-on-demand table for all sub-skills.

| Task | Load |
|---|---|
| Any test authoring task | `docs/skills/index.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Submitting improvements, PRs, doc fixes | `docs/skills/contributing.md` |
| Infra gotchas (GDM autologin, Argo mutex) | `docs/skills/ops.md` |

Sub-skills are indexed in `docs/skills/index.md` — load them from there on demand.

## Ownership constraint

New test suites → this repo.  
New infrastructure (Argo templates, VM specs, manifests) → `projectbluefin/testing-lab`.  
When a PR touches both, split into two PRs.
