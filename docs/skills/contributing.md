# Agent Contribution Guide

Load when: you found a bug, gap, or improvement while working in this repo.

This is an agent-first repo — agents MAY file issues and PRs directly. No human gating required.

## Decision: which repo?

| Found in | Fix goes in |
|---|---|
| Feature files, step defs, qecore/dogtail patterns, shared SSH helpers | `projectbluefin/testsuite` (this repo) |
| Argo templates, VM specs, CronWorkflows, cluster manifests | `projectbluefin/testing-lab` |

If a fix touches both repos, split into two PRs — one per repo.

## When to contribute

Contribute when you encounter any of the following mid-task:
- A skill doc that describes wrong behavior (wrong API, stale path, incorrect command)
- A missing pattern you had to figure out from scratch (add it so the next agent doesn't)
- A new operational gotcha (failed workflow, unexpected infra behavior)
- A step that's broken or uses a deprecated API
- A coverage gap that's now worth tracking

Don't defer. File the PR as part of your current working session.

## Branch naming

```
feat/<area>/<short-desc>    # new scenarios, new step files
fix/<area>/<short-desc>     # broken steps, wrong docs, stale patterns
docs/<area>/<short-desc>    # doc-only updates
```

Areas: `smoke`, `lifecycle`, `gnome`, `bootc`, `behave`, `security`, `dx`, `hardware`, `flatcar`, `ops`, `skills`

Examples:
```
fix/gnome/update-shell50-eval-pattern
docs/skills/add-contributing-guide
feat/smoke/add-calendar-scenario
```

## Pre-PR validation checklist

### CI checks (`.github/workflows/pr-validate.yml` — must pass)

```bash
# Ruff lint
ruff check tests/ --select E,F,W --ignore E501

# Python syntax
python3 -m py_compile $(find tests/ -name '*.py' | tr '\n' ' ')

# YAML lint (relaxed mode)
yamllint -d relaxed argo/

# YAML parse check
for f in argo/*.yaml; do python3 -c "import yaml; yaml.safe_load(open('$f'))"; done
```

### Recommended local checks (not in CI but catch common mistakes)

```bash
# Argo workflow lint
just lint

# Duplicate step patterns (replace <suite> with the suite you touched)
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d

# @future inventory (verify no accidental tag changes)
just list-stubs
```

All CI checks must pass cleanly before pushing. Local checks should also be clean.

## What to update in the PR

| Change | Files to update |
|---|---|
| New scenario in any suite | Feature file + steps file |
| Scenario count changes | `QA-REVIEW.md` coverage table + `docs/skills/suite-map.md` coverage snapshot |
| New suite or variant-matrix change | `docs/skills/suite-map.md` variant matrix + `RUNBOOK.md` suite layout table |
| New step pattern discovered | `docs/behave-patterns.md` |
| New dogtail / GNOME anti-pattern | `docs/gnome-testing.md` |
| New bootc JSON path or gotcha | `docs/bootc-lifecycle.md` |
| Infra gotcha (GDM, Argo, VM) | `docs/skills/ops.md` |
| New hard rule for all agents | `docs/skills/index.md` (rules section) |
| Behavior or command change | `README.md` and/or `RUNBOOK.md` if agent-facing docs describe the old behavior |
| @future scenario now implemented | Remove `@future` tag; update `QA-REVIEW.md` + `docs/skills/suite-map.md` status |
| Coverage gap resolved | Update `QA-REVIEW.md` known gaps + `docs/skills/suite-map.md` known gaps |

## PR description format

```markdown
## What

One sentence: what changed and why.

## Evidence

- [ ] Ruff passes
- [ ] py_compile passes
- [ ] Argo YAML lint passes
- [ ] No duplicate step phrases

## Scenario count (if changed)

Before: N  After: M  (+/- delta)
```

## Improving skill docs

If a skill doc (`docs/skills/*.md`) is wrong or incomplete:

1. Edit the relevant file in `docs/skills/`
2. Branch: `docs/skills/<what-changed>`
3. In the PR description, quote the old incorrect text and explain what you found
4. No need for the scenario count section if it's docs-only

**Do not add hard rules to individual skill docs** — rules go in `docs/skills/index.md` (single source). Skill docs hold patterns and examples only.

## After the PR merges

- If you changed `QA-REVIEW.md`, verify the scenario count is still accurate
- If you resolved a `@future` scenario, confirm `just list-stubs` no longer lists it
- If you added a new operational gotcha to `docs/skills/ops.md`, check `docs/skills/index.md`'s rules section doesn't already cover it (avoid duplication)
