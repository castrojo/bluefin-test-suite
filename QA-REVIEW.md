# testsuite QA review snapshot

> Last updated: 2026-05-27

This file tracks the current QA posture of `projectbluefin/testsuite` after repo-boundary normalization.

## What this repo is responsible for

- Behave suite coverage and quality
- qecore + dogtail integration patterns
- shared step/harness reuse across suites
- reliable scenario-level validation logic

## What this repo is not responsible for

- Lab hardware operations (ghost/exo)
- ArgoCD ownership and cluster reconciliation
- persistent titan VM lifecycle and CronWorkflow policy

Those are owned by `projectbluefin/testing-lab`.

## Coverage summary

| Suite | Status |
|---|---|
| smoke | active |
| developer | active |
| software | active |
| flatcar | active |
| lifecycle | present (expanding) |
| security | present (expanding) |
| dx | present (expanding) |
| nvidia | present (expanding) |
| hardware | present (expanding) |
| vanilla-gnome | present (expanding) |

## Highest-risk test correctness areas

1. GNOME Shell 50+ top-bar AT-SPI gaps (must use Shell.Eval fallback where needed)
2. Dogtail API misuse (`requireResult` on `findChild`) causing runtime errors
3. Step-definition collisions in suites where multiple step files are loaded
4. Duplicated SSH logic instead of shared helper reuse

## Review gate for testsuite PRs

1. Are new scenarios added in the correct suite?
2. Are shared helpers reused where applicable?
3. Are step phrases unique within each loaded suite?
4. Is dogtail usage compatible with current API behavior?
5. Do docs (`README.md`, `RUNBOOK.md`) still match behavior?
