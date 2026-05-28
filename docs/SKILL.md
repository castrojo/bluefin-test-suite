---
name: testsuite
description: Entry point for projectbluefin/testsuite — behave/qecore/dogtail test content. Load this first; load reference docs on demand.
---

# testsuite skill

## Ownership boundary

| This repo owns | Belongs elsewhere |
|---|---|
| Behave features/steps, dogtail/qecore patterns, shared SSH helpers | Hardware ops, ArgoCD, KubeVirt, CronWorkflows → `projectbluefin/testing-lab` |

## Hard rules

1. **Shared SSH steps** — always import from `tests/shared/ssh_steps.py`. Never duplicate `_ssh()` or generic step defs in suite-specific files.
2. **No ambiguous steps** — all step files under a suite are loaded together by behave. Step phrases must be unique within each loaded set.
3. **dogtail 4.16** — never pass `requireResult` to `findChild`. Use `findChildren(pred)` for no-raise, `findChild(pred, retry=False)` for fast-fail.
4. **GNOME Shell 50+ top-bar** — AT-SPI click on clock/system-status is unreliable. Use `Shell.Eval` path. Set `unsafe_mode=true` first.

## Load on demand

| Task | Reference |
|---|---|
| GNOME Shell / AT-SPI / dogtail | `docs/gnome-testing.md` |
| behave scaffolding, step patterns, SSH helpers | `docs/behave-patterns.md` |
| bootc lifecycle tests, ostree parsing | `docs/bootc-lifecycle.md` |
| PR review gate, coverage posture | `QA-REVIEW.md` |
| Commands, suite layout, operational guidance | `RUNBOOK.md` |
