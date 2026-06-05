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

## Migration testing — manual only

`migration-test.yml` runs on `workflow_dispatch` only — there is no automated schedule trigger.
Changes to bootc version pins, image base digests, OCI layer compression format, or `ostree-ext`
carry **invisible migration risk**. Before promoting, manually trigger the migration test workflow
if your change could affect upgrade paths from `ublue-os/bluefin` → `projectbluefin/bluefin`.

Issue [#232](https://github.com/projectbluefin/testsuite/issues/232) (UEFI-boot 3-lane workflow)
is on `queue/hold` — do not attempt to implement the UEFI lane without checking hold criteria.

## Skills

**Start here:** `docs/skills/index.md` — hard rules + load-on-demand table for all sub-skills.

| Task | Load |
|---|---|
| Any test authoring task | `docs/skills/index.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Submitting improvements, PRs, doc fixes | `docs/skills/contributing.md` |
| Infra gotchas (GDM autologin, Argo mutex, systemd-oomd.socket, bazzite extension state) | `docs/skills/ops.md` |

Sub-skills are indexed in `docs/skills/index.md` — load them from there on demand.

## Ownership constraint

New test suites → this repo.  
New infrastructure (Argo templates, VM specs, manifests) → `projectbluefin/testing-lab`.  
When a PR touches both, split into two PRs.
