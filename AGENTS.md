# testsuite — Agent Instructions

This repo owns **Bluefin test content** (behave + qecore-headless + dogtail).  
Infrastructure (ArgoCD, KubeVirt, CronWorkflows) belongs to `projectbluefin/testing-lab`.

## GNOME 50 Crowdsourcing

This repo is **agent-first** — agents are the primary maintainers of GNOME 50 test coverage. No human gating required to file issues or submit PRs.

### What needs coverage

Run `just list-stubs` to see `@future` scenarios waiting for implementation. Current known gaps beyond `@future` tags:

| Area | Suite | Gap | Priority |
|---|---|---|---|
| OOBE / first-boot | smoke | Initial user setup flow | Low |
| Flatpak permissions | software | Flatseal per-app permissions | Low |

### How agents contribute

1. **Pick a gap** — from the table above, `just list-stubs`, or file a new issue
2. **Write the scenario** — add a `.feature` file entry in the appropriate suite
3. **Implement the steps** — add to the suite's `steps.py`; reuse `docs/skills/gnome.md` patterns
4. **Run lint locally** — `ruff check tests/ --select E,F,W --ignore E501`
5. **File a PR** — branch format: `feat/<suite>/<short-desc>`
6. **Update counts** — bump scenario count in `QA-REVIEW.md` and `docs/skills/suite-map.md`

Load `docs/skills/contributing.md` for the full PR checklist.

### Testing your scenario

Run via the GitHub Action (no ghost required):

```yaml
# In any fork/branch workflow:
- uses: projectbluefin/testsuite/.github/actions/gnome-e2e@main
  with:
    image: ghcr.io/ublue-os/bluefin:latest
    suite: smoke
```

Or trigger manually: Actions → "Manual Test Run" (requires ghost runner access).

## Skills

**Start here:** `docs/skills/index.md` — hard rules + load-on-demand table for all sub-skills.

| Task | Load |
|---|---|
| Any test authoring task | `docs/skills/index.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Submitting improvements, PRs, doc fixes | `docs/skills/contributing.md` |
| Infra gotchas (GDM autologin, Argo mutex) | `docs/skills/ops.md` |

Sub-skills are indexed in `docs/skills/index.md` — load them from there on demand.

## Ownership constraint

New test suites → this repo.  
New infrastructure (Argo templates, VM specs, manifests) → `projectbluefin/testing-lab`.  
When a PR touches both, split into two PRs.

## CI gates

- **`skill-drift.yml`** — advisory PR gate: warns when `tests/**`, `scripts/**`, or workflow changes land without a docs/skills update.
- **`nightly.yml`** — runs the full matrix nightly. The `bluefin-gdx:stream10*` jobs were replaced with `bluefin:lts-testing` (PR#384) after the upstream gdx images dropped Homebrew and caused permanent common-suite failures. Do not re-add `ublue-os/bluefin-gdx` refs without verifying Homebrew is restored upstream.

## Mandatory gates

- `ruff check tests/ --select E,F,W --ignore E501` before every commit
- `python3 -m py_compile <changed step files>` before every commit
- PR title: Conventional Commits format
- Attribution on every AI-authored commit: `Assisted-by: <Model> via <Tool>`
