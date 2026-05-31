# testsuite runbook

> Last updated: 2026-05-29

This runbook covers **operational commands** for `projectbluefin/testsuite`.  
Authoring rules, patterns, and skill docs live in `docs/skills/` — load from there.

## Ownership boundary

| Area | Owner |
|---|---|
| Test suites (`tests/**`), step definitions, shared test helpers | `testsuite` |
| Workflow templates, manifests, persistent VMs, CronWorkflows, host operations | `projectbluefin/testing-lab` |

If a change touches both repos, split into two PRs.

## Commands

```bash
# List @future / not-yet-implemented scenarios
just list-stubs
```

## Vanilla GNOME baseline comparison

The `vanilla-gnome` suite runs against an unmodified GNOME OS disk to establish
a comparison baseline:

- **Failures on vanilla-gnome** → likely upstream GNOME issue
- **Failures on Bluefin but not vanilla** → likely Bluefin-specific regression

Currently this comparison is manual. Procedure:

1. Wait for both nightly runs to complete (Argo Workflows in `testing-lab`)
2. Compare results for the 7 overlapping scenarios between `smoke` and `vanilla-gnome`:
   - `gnome_calculator` — launch and basic interaction
   - `gnome_text_editor` — launch and typing
   - `gnome_files_browse_dir` — Nautilus directory listing
   - `gnome_settings_about_display` — Settings → About rendering
   - `firefox_launch_and_close` — Firefox launch via Flatpak
   - `system_monitor_app_list` — System Monitor process table
   - `app_grid_search` — GNOME Shell app search
3. Flag scenarios that fail on Bluefin but pass on vanilla as Bluefin regressions
4. Record findings in the relevant issue

Future: automated diff via `just compare-results` (see #22).

## Update checklist for docs + tests

| Result | Interpretation |
|---|---|
| `smoke=failed`, `vanilla-gnome=passed` | ⚠ Bluefin regression |
| `smoke=failed`, `vanilla-gnome=failed` | ↑ Upstream GNOME issue |
| all other combinations | Informational |

Results are visible in the GitHub Actions job summary and as 30-day artifacts.

