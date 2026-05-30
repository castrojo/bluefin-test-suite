# testsuite runbook

> Last updated: 2026-05-28

This runbook covers **test-content operations** for `projectbluefin/testsuite`.
Lab infrastructure operations (cluster topology, ArgoCD ownership, ghost/exo lifecycle) are owned by `projectbluefin/testing-lab`.

## Ownership boundary

| Area | Owner |
|---|---|
| Test suites (`tests/**`), step definitions, shared test helpers | `testsuite` |
| Workflow templates, manifests, persistent VMs, CronWorkflows, host operations | `testing-lab` |

If a change touches both, split it into two PRs (one per repo) and keep the contract explicit (`testing-lab` runs tests from `testsuite`).

## Hard rules

1. **No node SSH for cluster operations.** Use MCP/kubectl/Argo workflows from approved control paths.
2. **Reuse shared SSH steps** from `tests/shared/ssh_steps.py` for non-GUI suites.
3. **Avoid ambiguous behave steps** in `tests/smoke/features/steps/` (all step modules are loaded together).
4. **Dogtail 4.16 compatibility:** never pass `requireResult` to `findChild`.

## Dogtail and qecore guidance

### Required patterns

- Use `context.sandbox.shell` when interacting with GNOME Shell under qecore.
- Presence checks:
  - `findChildren(predicate)` for no-raise checks
  - `findChild(predicate, retry=False)` for fast-fail
- Use `Shell.Eval` path for top-bar flows where GNOME 50+ does not expose expected AT-SPI nodes.

### Anti-patterns to avoid

- `findChild(..., requireResult=...)` (invalid in dogtail 4.16)
- duplicate step texts across multiple step files in the same suite
- suite-specific SSH logic duplicated instead of calling shared helpers

## Suite layout

### Variant matrix

| Suite | `bluefin` (latest/lts) | `bluefin-dx` | `bluefin-nvidia` | `flatcar` | Notes |
|-------|:---:|:---:|:---:|:---:|-------|
| `smoke` | ✅ | ✅ | ✅ | — | Core GNOME smoke; runs on all Bluefin variants |
| `vanilla-gnome` | ✅ | — | — | — | Baseline comparison; latest only |
| `developer` | ✅ | ✅ | — | — | Homebrew/Ptyxis; DX adds extra tools |
| `software` | ✅ | — | — | — | Bazaar/Flatpak; standard variant only |
| `lifecycle` | ✅ | ✅ | ✅ | — | bootc upgrade/rollback; all Bluefin variants |
| `security` | ✅ | ✅ | ✅ | — | cosign + SELinux; all Bluefin variants |
| `hardware` | ✅ | — | — | — | Emulated peripherals; standard VM spec |
| `dx` | — | ✅ | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | ✅ | Flatcar OS boot and lifecycle |

**Variant tags** used in feature files:

| Tag | Meaning |
|-----|---------|
| `@smoke_suite` | Runs as part of the standard Bluefin smoke suite |
| `@dx_only` / `@developer_suite` | DX variant only |
| `@nvidia_only` | NVIDIA variant only |
| `@flatcar_suite` | Flatcar OS only |
| `@hardware_emulation` | Requires full-hw VM spec (TPM, audio, watchdog) |
| `@nightly` | Runs nightly; may be slow or destructive |
| `@future` | Not yet implemented or blocked |

Current test suites:

- `smoke`
- `developer`
- `software`
- `flatcar`
- `lifecycle`
- `security`
- `dx`
- `nvidia`
- `hardware`
- `vanilla-gnome`

Shared utilities:

- `tests/shared/ssh_steps.py`

## Useful commands

```bash
# lint Argo YAML in this repo
just lint

# list stubs / @future scenarios
just list-stubs
```

For lab execution commands (`run-tests`, matrix runs, titan paths, nightly/manual automation), prefer the canonical entrypoints in `testing-lab`.

## Vanilla-GNOME comparison procedure

`tests/vanilla-gnome/` exists as a GNOME upstream baseline for the `tests/smoke/` scenarios. If smoke fails while vanilla-gnome passes, treat that as a likely Bluefin regression. If both suites fail on the same scenario, treat it as a likely upstream GNOME issue until proven otherwise.

Use the comparison helper after a run finishes:

```bash
# compare the newest run on ghost
just compare-results

# compare a specific workflow UID
just compare-results <run-uid>
```

Interpret the output as follows:

- `⚠ Bluefin regression` → `smoke=failed` and `vanilla-gnome=passed`
- `↑ Upstream GNOME issue` → `smoke=failed` and `vanilla-gnome=failed`
- all other rows are informational (for example `passed/passed`, `skipped/skipped`, or other mixed states)

If you need to inspect a specific scenario manually:

1. Run `just results` to find the workflow UID you care about.
2. Open `/var/tmp/bluefin-results/<workflow-uid>/smoke/results.json` and `/var/tmp/bluefin-results/<workflow-uid>/vanilla-gnome/results.json`.
3. Find the scenario name in both files and compare the per-scenario `status` values.
4. Use the suite-specific logs or workflow artifacts for deeper debugging once you know whether the failure reproduces on vanilla GNOME.

## Update checklist for docs + tests

When changing testsuite behavior:

1. Update `README.md` if suite ownership, scope, or usage changed.
2. Update this runbook if authoring rules or operational constraints changed.
3. Update `PLAN.md` if normalization milestones shifted.
4. Keep cross-repo boundaries consistent with `testing-lab` docs.
