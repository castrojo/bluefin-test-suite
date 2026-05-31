# testsuite QA review

> Last updated: 2026-05-31

Coverage snapshot and known gaps live in `docs/skills/suite-map.md`.
Current audit: 255 scenarios across 29 feature files (last audit: 2026-05-31).

## What this repo is responsible for

- Behave suite coverage and quality
- qecore + dogtail integration patterns
- shared step/harness reuse across suites
- reliable scenario-level validation logic

What it is **not** responsible for: lab hardware ops, ArgoCD, persistent titan VM lifecycle → `projectbluefin/testing-lab`.

## Highest-risk test correctness areas

1. GNOME Shell 50+ top-bar AT-SPI gaps (must use Shell.Eval fallback where needed)
2. dogtail API misuse (`requireResult` on `findChild`) causing runtime errors
3. Step-definition collisions in suites where multiple step files are loaded
4. Duplicated SSH logic instead of shared helper reuse

## Review gate for testsuite PRs

1. Are new scenarios added in the correct suite?
2. Are shared helpers reused where applicable?
3. Are step phrases unique within each loaded suite?
4. Is dogtail usage compatible with current API behavior?
5. Do docs (`README.md`, `RUNBOOK.md`, `docs/skills/`) still match behavior?
6. Are new pytest files being added? (Legacy pytest removed 2026-05-28 — all new tests must use behave.)
7. If scenario count changed, is `docs/skills/suite-map.md` updated?

## Current stub posture

- `flatcar/lifecycle`: partially active — knuckle install, update channel, and afterburn are implemented; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future`.
- `security/selinux`: still `@future` until Bluefin test images stop booting with `selinux=0`.
- `nvidia`: still `@future` / `@hardware_blocked` until GPU passthrough exists in the lab.

