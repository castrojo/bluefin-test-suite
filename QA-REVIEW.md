# testsuite QA review snapshot

> Last updated: 2026-05-28

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

158 scenarios across 20 feature files (last full-audit: 2026-05-28).

| Suite | Scenarios | Status | Notes |
|---|---|---|---|
| smoke | 68 | ✅ active | dogtail 4.16 API correct throughout |
| developer | 16 | ✅ active | brew, podman, ptyxis fully covered |
| software | 10 | ✅ active | Bazaar/gnome-software + Flathub |
| vanilla-gnome | 8 | ✅ active | Baseline GNOME Shell parity check |
| lifecycle | 7 | ✅ active | bootc upgrade / rollback / switch / /etc merge |
| hardware | 10 | ✅ active | Fully driven by shared SSH steps |
| security/image_provenance | 5 | ✅ active | cosign verify steps fully implemented |
| dx | 8 | 🔄 expanding | VS Code + CLI tools; `_ssh()` local by design (qecore collision) |
| flatcar/boot | 7 | ✅ active | systemd, containerd, networking |
| flatcar/lifecycle | 6 | ⏳ @future | Needs dual-disk VM + boot-order swap (Epic E09) |
| security/selinux | 5 | ⏳ @future | Needs `selinux=0` removed from golden disk (Epic E04) |
| nvidia | 8 | ⏳ @future/@hardware_blocked | Needs GPU passthrough (Epic E08) |

## Known coverage gaps

| Area | Priority | Notes |
|---|---|---|
| `ujust` commands | Medium | No scenario exercises user-facing `ujust` scripts |
| Auto-update service | Medium | No test that `bootc-fetch-apply-updates.timer` is active |
| `bootc pin/unpin` | Low | Lifecycle covers upgrade/rollback but not image pinning |
| Flatpak permission management | Low | Flatseal / per-app permissions not exercised |
| Brew on DX | Low | `brew` tested in developer suite but not dx suite |
| OOBE / first-boot | Low | Initial user setup flow not covered |

## Known deferred suites

- **nvidia** (`@future @hardware_blocked`): all steps stubbed; `NotImplementedError` on connectivity. Activate after GPU passthrough is wired in testing-lab (Epic E08).
- **security/selinux** (`@future`): steps defined, blocked on golden disk change (Epic E04).
- **flatcar/lifecycle** (`@future`): partial stubs; scenarios 2+3 need VM boot-order swap infrastructure (Epic E09).
- **dx/steps.py `_ssh()`**: duplicates `shared/ssh_steps.run_ssh` intentionally — `qecore.common_steps` wildcard import collides with shared step phrases. If shared SSH logic changes, sync dx manually.

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
5. Do docs (`README.md`, `RUNBOOK.md`) still match behavior?
6. Are new pytest files being added? (Legacy pytest files were removed 2026-05-28 — all new tests must use behave.)
