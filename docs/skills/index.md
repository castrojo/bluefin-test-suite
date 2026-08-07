---
name: testsuite-skills
description: "testsuite skill manifest — hard rules and task → skill routing. Load this first in every session, then load sub-skills on demand."
metadata:
  type: manifest
  audience: agents
  maturity: stable
---

# testsuite skill index

## Hard rules

1. **Context7 before any library** — resolve qecore, dogtail, behave, gi.repository, AT-SPI docs via Context7; never guess API from training data.
2. **Shared SSH steps** — import from `tests/shared/ssh_steps.py`; never duplicate `_ssh()` in suite files.
3. **No ambiguous steps** — `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d` must be empty.
4. **dogtail 4.16** — never pass `requireResult` to `findChild`; use `findChildren(pred)` for no-raise.
5. **GNOME Shell 50+ top-bar** — use `Shell.Eval`, not AT-SPI clicks; set `unsafe_mode=true` first.
6. **Smoke suite is local, not SSH** — smoke runs inside the VM via qecore-headless; never import `tests.shared.ssh_steps` there.
7. **Behave only** — no new pytest files; legacy pytest was removed 2026-05.
8. **Fedora 41 for test container** — qecore/dogtail/GObject stack runs in `registry.fedoraproject.org/fedora:41`.
9. **Dry-run before push** — run `behave --dry-run tests/<suite>/features` after touching `.feature` files.
10. **Update skills in the same PR** — any code change that surfaces a convention must update the matching skill file.
11. **Isolated work lives in `.worktrees/<short-desc>`** — branch from `origin/main` at the repo root; never `/tmp`, `/var/tmp`, or sibling directories, and never touch another worktree's branch or working tree. See `ci-ops/contributing/references/branch-and-worktree.md`.

## Load on demand

| Task | Load |
|---|---|
| Writing behave scenarios / steps | `test-authoring/behave/SKILL.md` |
| GNOME Shell / AT-SPI / dogtail interactions | `test-authoring/gnome/SKILL.md` |
| KDE/Plasma / selenium-webdriver-at-spi / Gamescope CDP | `test-authoring/kde/SKILL.md` |
| bootc upgrade / rollback / migration tests | `test-authoring/bootc/SKILL.md` |
| UEFI/OVMF reboot testing | `test-authoring/uefi-boot/SKILL.md` |
| Variant matrix, coverage gaps, `@future` stubs | `test-authoring/suite-map/SKILL.md` |
| Quarantine expiry and policy | `test-authoring/quarantine-age/SKILL.md` |
| Reusable e2e workflow / consumer wiring | `ci-ops/e2e-workflow/SKILL.md` |
| Lab gotchas (GDM, oomd, Argo, runners) | `ci-ops/ops/SKILL.md` |
| Dashboard metrics / Astro site | `ci-ops/dashboard-metrics/SKILL.md` |
| Contribution mechanics / PR checklist | `ci-ops/contributing/SKILL.md` |
| Flatpak screenshot gallery (app authors) | `flatpak-screenshots/SKILL.md` |
| When to stop and ask a human | `meta/human-gates/SKILL.md` |
| Triage issues and label hygiene | `meta/triage/SKILL.md` |
| Update cadence / promotion-gate research | `../update-cadence-research.md` |
| Skill update mandate | `meta/skill-improvement/SKILL.md` |
| How to write or maintain a skill | `meta/writing-skills/SKILL.md` |

## Project agents

Local agents live in `.pi/agents/`. Use them for scoped work.

| Agent | Purpose |
|---|---|
| `test-author` | Implement `@future` scenarios and fill coverage gaps |
| `triage` | Label, close duplicates, classify regressions |
| `pr-reviewer` | Review PRs against contribution gates |

## Improving these docs

Any session that discovers a workaround or convention must write it back. See `meta/skill-improvement/SKILL.md` for the checklist and `meta/writing-skills/SKILL.md` for format rules.
