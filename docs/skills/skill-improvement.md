---
name: skill-improvement
description: "The skill-improvement mandate — every agent session must produce a skill file update alongside the work. Use when completing a task and deciding whether to write a skill update, or when creating or updating a skill file."
metadata:
  type: procedure
---

# Skill Improvement Mandate

Every agent session that changes this repo produces two outputs:

1. **The work** — the PR, fix, or test coverage improvement
2. **The learning** — what a future agent should know

Output 1 without Output 2 leaves the factory no smarter. The loop only compounds if agents write back.

## Before You Mark Work Complete

Run this checklist before enqueuing any PR:

- [ ] Did I discover any workaround, non-obvious pattern, or convention?
- [ ] Is there a skill file for the area I worked in?
- [ ] If yes — did I update it?
- [ ] If no — did I create one in `docs/skills/`?
- [ ] Is the skill file committed in **this same PR**? (Not a follow-up. Same PR.)

If all five are checked, you're done. If any are unchecked, finish them first.

The skill-drift CI check will warn if you modify `tests/**`, `.github/workflows/**`, or `scripts/**` without touching a skill file. Treat warnings as hard requirements.

## What Counts as a Learning Worth Writing Back

**Write it:**

| Category | Example |
|---|---|
| Upstream bug workaround | "GNOME 50 removed `list item` role in Nautilus sidebar — use `button` role instead" |
| Non-obvious correctness requirement | "behave dry-run must pass before pushing — CI runs it in a Fedora 41 container with the full dogtail stack" |
| Convention not obvious from code | "Smoke suite uses subprocess, not SSH — never import `tests.shared.ssh_steps` into smoke environment" |
| Trial-and-error discovery | "dogtail 4.16 removed `requireResult` from `findChild` — use `findChildren(pred)` for no-raise behavior" |
| AT-SPI / GNOME version quirk | "Shell.Eval check via D-Bus requires `unsafe_mode=true` — set before any Shell.Eval call" |

**Do NOT write:**

| Category | Example |
|---|---|
| One-off task note | "Use commit message `fix(smoke): revert sidebar step` for this PR" |
| Obvious developer knowledge | "Run git status to see changed files" |
| Ephemeral state | "bazzite extensions are currently all in ERROR state due to upstream regression" |
| Contradiction of another skill | Update the skill to reflect the new reality — don't add a competing note |

## Where to Write It

| Working in... | Write to |
|---|---|
| `tests/smoke/**` | `docs/skills/gnome.md` (AT-SPI patterns) or `docs/skills/behave.md` (step structure) |
| `tests/lifecycle/**` | `docs/skills/bootc.md` |
| `tests/shared/**` | `docs/skills/behave.md` (shared helper patterns) |
| `.github/workflows/**` | `docs/skills/e2e-workflow.md` or `docs/skills/suite-map.md` |
| `.github/actions/**` | `docs/skills/e2e-workflow.md` |
| `scripts/**` | `docs/skills/e2e-workflow.md` |
| New domain entirely | Create `docs/skills/<area>.md` |
| Cross-cutting (affects `projectbluefin/testsuite` + other repos) | Update local skill first, then open a propagation issue in `projectbluefin/actions` |

## Which Skill File to Update

| Changed area | Update this skill |
|---|---|
| GNOME AT-SPI step, dogtail pattern | `gnome.md` |
| behave scaffolding, step structure, shared helpers | `behave.md` |
| bootc upgrade / rollback / migration | `bootc.md` |
| e2e workflow inputs, QEMU pipeline, reusable action | `e2e-workflow.md` |
| Suite coverage, variant matrix, @future gaps | `suite-map.md` |
| VM boot, GDM, Argo, systemd-oomd, infra gotcha | `ops.md` |
| UEFI boot, OVMF, systemd-boot | `uefi-boot.md` |
| PR process, merge queue, Renovate | `contributing.md` |
| Hard rules for all agents | `index.md` (rules section only) |
| Skill file format, skill update mandate | `skill-improvement.md` (this file) |
| skill-drift CI check behavior | `skill-drift.md` |

When in doubt, update the closest existing skill rather than creating a new file.

## How to Commit It

The skill update goes in the **same commit or same PR** as the implementation. Not a follow-up PR.

```bash
# Stage both the implementation and the skill update together
git add tests/smoke/features/steps/gnome_files_steps.py docs/skills/gnome.md
git commit -m "feat(smoke): add Nautilus sidebar navigation steps

Update gnome.md: document GNOME 50 sidebar item role change
(list item → button) and URI fallback pattern for AT-SPI action failures.

Assisted-by: Claude Sonnet 4.6 via GitHub Copilot
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

The skill-drift CI gate will warn if you forget. See `docs/skills/skill-drift.md` for the full path mapping and waiver process.
