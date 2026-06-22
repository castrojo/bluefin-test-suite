# testsuite QA review

> Last updated: 2026-06-22

Coverage snapshot and known gaps live in `docs/skills/suite-map.md`.
Current audit: 309 scenarios across 40 feature files (last audit: 2026-06-22). 30 quarantined, 267 active, 3 @future stubs.

## Architecture changes (2026-06-21)

- Nightly removed — PR gates are now the sole CI mechanism.
- `e2e.yml` now uses OCI layer caching and a 45-minute timeout.
- `pr-validate.yml` now enforces 30-day quarantine expiry.
- Known infrastructure-flaky smoke scenarios now use `@retry`.
Current audit: 309 scenarios across 39 feature files (last audit: 2026-06-22). 30 quarantined, 276 active, 3 @future stubs.

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
6. Are new scenario tests being added as behave steps, with pytest reserved for `tests/unit/` helper coverage?
7. If scenario count changed, is `docs/skills/suite-map.md` updated?

## Unit test coverage

593 unit tests across 35 files (`tests/unit/`). Run with `python3 -m pytest tests/unit/ -q`.

| File | Tests | What it covers |
|---|---|---|
| `test_gnome_shell_steps.py` | 41 | Shell.Eval, AT-SPI step helpers, ShellEval bool variants |
| `test_gnome_settings_steps.py` | 20 | Settings panel navigation and toggle helpers |
| `test_lifecycle_steps.py` | 20 | bootc upgrade/rollback/migration step helpers |
| `test_ssh_steps.py` | 26 | `run_ssh()`, journal/coredump matchers, output assertions |
| `test_timing.py` | 13 | SLA tag thresholds and timing helpers |
| `test_screenshot.py` | 11 | Screenshot capture helpers |
| `test_shared.py` | 9 | Shared step utilities |
| `test_screenshot_cli.py` | 9 | `screenshot_cli.main()` argument parsing and dispatch |
| `test_security_steps.py` | 15 | `_cosign_entries()` JSON validation and `_collect_values()` recursive extraction |
| `test_quarantine.py` | 7 | `@quarantine` / `@pending` skip logic |
| `test_qemu_screendump.py` | 8 | `_ppm_to_png` conversion and `main()` entry point |
| `test_app_support.py` | 17 | `_desktop_path`, `_flatpak_available`, `launch_target_available`, `launch_background` |
| `test_system_health_steps.py` | 16 | `_has_image_reference`, `_running_in_vm`, `IGNORED_FAILED_UNITS_IN_VM` |
| `test_brew_steps.py` | 7 | Brew step helpers and formula detection |
| `test_gnome_notifications_steps.py` | 5 | Notification step helpers |
| `test_retry.py` | 4 | Behave retry harness, `sys.executable` fallback |
| `test_parse_results.py` | 1 | `scripts/parse_results.py` JSONL output |

The `pytest` CI check (`unit-tests.yml`) runs these on every PR and merge queue entry.

## Current stub posture

- `flatcar/lifecycle`: partially active — knuckle install, update channel, and afterburn are implemented; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future`.
- `security/selinux`: `@future` scenarios at Feature level — will activate when Bluefin test images stop booting with `selinux=0` (PR #280 in merge queue).
- `nvidia`: still `@future` / `@hardware_blocked` until GPU passthrough exists in the lab.
