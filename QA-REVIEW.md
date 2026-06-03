# testsuite QA review

> Last updated: 2026-06-02

Coverage snapshot and known gaps live in `docs/skills/suite-map.md`.
Current audit: 262 scenarios across 30 feature files (last audit: 2026-06-02). 20 quarantined (down from 42), 242 active.

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

## Unit test coverage

67 unit tests across 8 files (`tests/unit/`). Run with `python3 -m pytest tests/unit/ -q`.

| File | Tests | What it covers |
|---|---|---|
| `test_gnome_shell_steps.py` | 38 | Shell.Eval, AT-SPI step helpers, ShellEval bool variants |
| `test_ssh_steps.py` | 26 | `run_ssh()`, journal/coredump matchers, output assertions |
| `test_timing.py` | 13 | SLA tag thresholds and timing helpers |
| `test_shared.py` | 9 | Shared step utilities |
| `test_screenshot.py` | 9 | Screenshot capture helpers |
| `test_quarantine.py` | 6 | `@quarantine` skip logic |
| `test_retry.py` | 2 | Behave retry harness |
| `test_parse_results.py` | 1 | `scripts/parse_results.py` JSONL output |

The `pytest` CI check (`unit-tests.yml`) runs these on every PR and merge queue entry.

## Current stub posture

- `flatcar/lifecycle`: partially active — knuckle install, update channel, and afterburn are implemented; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future`.
- `security/selinux`: still `@future` until Bluefin test images stop booting with `selinux=0`.
- `nvidia`: still `@future` / `@hardware_blocked` until GPU passthrough exists in the lab.
- `lifecycle/migration` (3-lane: rechunker, zstd_chunked, unified_storage): `.github/workflows/migration-test.yml` added (epic #227). Uses UEFI boot (OVMF pflash) so VM reboots pick up the new deployment after `bootc switch`. Steps use 900s timeout and graceful `Check unified storage support and skip if unavailable`.

