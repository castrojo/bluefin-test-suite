---
name: testsuite-skills
description: Entry point for projectbluefin/testsuite skill tree. Load this for any test authoring task; load sub-skills on demand.
---

# testsuite skill index

## Ownership boundary

| This repo owns | Belongs elsewhere |
|---|---|
| Behave features/steps, dogtail/qecore patterns, shared SSH helpers | Hardware ops, ArgoCD, KubeVirt, CronWorkflows → `projectbluefin/testing-lab` |

New suites → this repo. New infra (Argo templates, VM specs, manifests) → testing-lab. PRs touching both must be split.

## Hard rules (single source of truth)

1. **Shared SSH steps** — always import from `tests/shared/ssh_steps.py`. Never duplicate `_ssh()` or generic step defs in suite-specific files. Exception: `dx/steps.py` uses a local `_ssh()` deliberately (qecore phrase collision — document if you change it).
2. **No ambiguous steps** — all step files under a suite are loaded together by behave. Step phrases must be unique within each loaded set. Check before committing: `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d`
3. **dogtail 4.16** — never pass `requireResult` to `findChild`. Use `findChildren(pred)` for no-raise; `findChild(pred, retry=False)` for fast-fail.
4. **GNOME Shell 50+ top-bar** — AT-SPI click on clock/system-status is unreliable. Use `Shell.Eval` path. Set `unsafe_mode=true` first.
5. **Smoke suite is local, not SSH** — smoke runs inside the VM via qecore-headless. Steps use `subprocess.run`, not `context.vm_ip`. Never import `tests.shared.ssh_steps` into smoke environment.
6. **All new tests must use behave** — legacy pytest was removed 2026-05-28. No new pytest files.

## Load on demand

| Task | Load |
|---|---|
| Writing behave tests, scaffolding suites, debugging step resolution | `docs/skills/behave.md` |
| GNOME Shell / AT-SPI / dogtail interactions | `docs/skills/gnome.md` |
| bootc lifecycle, upgrade, rollback tests | `docs/skills/bootc.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Infra gotchas (GDM autologin, Argo mutex) | `docs/skills/ops.md` |
| Submitting improvements, PRs, doc updates | `docs/skills/contributing.md` |
| Full PR review gate, coverage posture | `QA-REVIEW.md` |
| Commands, operational guidance | `RUNBOOK.md` |
