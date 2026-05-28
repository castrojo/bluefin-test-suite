# testsuite runbook

> Last updated: 2026-05-27

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

## Update checklist for docs + tests

When changing testsuite behavior:

1. Update `README.md` if suite ownership, scope, or usage changed.
2. Update this runbook if authoring rules or operational constraints changed.
3. Update `PLAN.md` if normalization milestones shifted.
4. Keep cross-repo boundaries consistent with `testing-lab` docs.
