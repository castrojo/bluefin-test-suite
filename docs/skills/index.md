---
name: testsuite-skills
description: Entry point for projectbluefin/testsuite skill tree. Load this for any test authoring task; load sub-skills on demand.
---

# testsuite skill index

## Ownership boundary

| This repo owns | Belongs elsewhere |
|---|---|
| Behave features/steps, dogtail/qecore patterns, shared SSH helpers | VM specs, cluster manifests, CronWorkflows → `projectbluefin/testing-lab` |

**`projectbluefin/testsuite` is the single source of truth for all Bluefin image tests.**
Tests run in two places from this repo:
- **GitHub Actions** (`e2e.yml`) — QEMU-based, on every PR and image publish
- **KubeVirt lab** (`run-gnome-tests` WorkflowTemplate in testing-lab) — clones this repo and runs against a real VM

New test scenarios → this repo. New infra (VM specs, manifests, Argo templates) → testing-lab. PRs touching both must be split.

## Hard rules (single source of truth)

1. **Context7 before any library** — before using qecore, dogtail, behave, gi.repository, or any other library: resolve its docs via Context7 (`resolve-library-id` → `get-library-docs`). Never guess API from training data. The docs are open source and live.
2. **Shared SSH steps** — always import from `tests/shared/ssh_steps.py`. Never duplicate `_ssh()` or generic step defs in suite-specific files. Exception: `dx/steps.py` uses a local `_ssh()` deliberately (qecore phrase collision — document if you change it).
2. **No ambiguous steps** — all step files under a suite are loaded together by behave. Step phrases must be unique within each loaded set. Check before committing: `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d`
3. **dogtail 4.16** — never pass `requireResult` to `findChild`. Use `findChildren(pred)` for no-raise; `findChild(pred, retry=False)` for fast-fail.
4. **GNOME Shell 50+ top-bar** — AT-SPI click on clock/system-status is unreliable. Use `Shell.Eval` path. Set `unsafe_mode=true` first.
5. **Smoke suite is local, not SSH** — smoke runs inside the VM via qecore-headless. Steps use `subprocess.run`, not `context.vm_ip`. Never import `tests.shared.ssh_steps` into smoke environment.
6. **All new tests must use behave** — legacy pytest was removed 2026-05-28. No new pytest files.
7. **CI containers: upstream only, never `ubuntu-latest` for test jobs** — use the container the upstream ecosystem targets. qecore/dogtail/GObject stack → `registry.fedoraproject.org/fedora:41`. Pure lint/yaml-only jobs may use `ubuntu-latest`. Never fight PyGObject ABI on Ubuntu.
8. **Feature files and step files must stay in sync** — every step phrase used in a `.feature` file must have a matching `@step` decorator. Run `behave --dry-run` locally before pushing. The CI dry-run job catches any mismatch.

## Load on demand

| Task | Load |
|---|---|
| Writing behave tests, scaffolding suites, debugging step resolution | `docs/skills/behave.md` |
| MIME handler verification, xdg-open patterns | `docs/skills/behave.md` |
| GNOME Shell / AT-SPI / dogtail interactions | `docs/skills/gnome.md` |
| GNOME extension testing patterns | `docs/skills/gnome.md` |
| bootc lifecycle, upgrade, rollback tests | `docs/skills/bootc.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Flatpak remote state, portal health | `docs/skills/suite-map.md` |
| Infra gotchas (GDM autologin, systemd-oomd.socket, bazzite extension state, GVariant quoting) | `docs/skills/ops.md` |
| Reusable e2e workflow (calling from another repo, debugging QEMU pipeline) | `docs/skills/e2e-workflow.md` |
| Modifying, compiling, and deploying the Astro QA Dashboard and data pipelines | `docs/skills/dashboard-metrics.md` |
| Quarantine expiry CI (`scripts/check_quarantine_age.py`, `pr-validate.yml`) | `docs/skills/quarantine-age.md` |
| UEFI boot via OVMF + systemd-boot (migration reboot testing) | `docs/skills/uefi-boot.md` |
| Flatpak screenshot gallery (screenshot_flatpaks input, GHCR artifact tags) | `docs/flatpak-screenshots.md` |
| Submitting improvements, PRs, doc updates | `docs/skills/contributing.md` |
| Triage issues/PRs, stale-issue detection, label hygiene | `docs/skills/triage.md` |
| When to stop and request human input (design/security/breakage gates) | `docs/skills/human-gates.md` |
| What counts as a skill update, how to write and commit it | `docs/skills/skill-improvement.md` |
| How the skill-drift CI check works, path mapping, waiver process | `docs/skills/skill-drift.md` |
| Full PR review gate, coverage posture | `QA-REVIEW.md` |
| Commands, operational guidance | `RUNBOOK.md` |

## Project agents

Project-local agents live in `.pi/agents/`. Load with `agentScope: "project"` or `"both"`.

| Agent | Purpose |
|---|---|
| `test-author` | Write behave scenarios for coverage gaps, implement @future stubs |
| `triage` | Label issues, close duplicates, classify upstream regressions vs testsuite bugs |
| `pr-reviewer` | Review PRs against contribution gates before merge queue |

## Improving skill docs

All files in `docs/skills/` are community-maintained operational knowledge. Any agent or contributor can update them.

**When to update a skill:** any time a session surfaces a workaround, non-obvious pattern, or convention while working in this repo. See [`docs/skills/skill-improvement.md`](skill-improvement.md) for the full mandate and checklist.

The skill-drift CI check (`skill-drift.yml`) warns when implementation changes land without a matching skill update. Treat warnings as hard requirements.
