---
name: skill-drift
description: "How the skill-drift CI check works in testsuite — when it fires, what it validates, which skill to update for each code path, and how to request a waiver. Load when the skill-drift check is failing on a PR or when deciding whether a change needs a skill update."
metadata:
  type: procedure
---

# Skill Drift

`skill-drift.yml` warns when a PR changes implementation files without updating the matching skill documentation. The goal: keep agent-facing docs in sync with real repo behavior while the implementation context is still fresh.

The mandate for *why* you must write skill updates is in [`skill-improvement.md`](./skill-improvement.md).

---

## How it works

```
PR opened
  └─ extract changed files
       ├─ match against code-paths
       └─ if code-paths hit and no skill-paths hit → WARN
```

Currently advisory (warns but does not block merge). Treat warnings as hard requirements — the check is expected to harden into a block.

Calls the reusable `projectbluefin/actions/.github/workflows/skill-drift-check.yml` at a pinned SHA.

---

## Path mapping for this repo

| code-paths | skill-paths |
|---|---|
| `.github/workflows/**` | `docs/skills/**`, `docs/*.md`, `AGENTS.md` |
| `.github/actions/**` | `docs/skills/**`, `docs/*.md`, `AGENTS.md` |
| `tests/**` | `docs/skills/**`, `docs/*.md`, `AGENTS.md` |
| `scripts/**` | `docs/skills/**`, `docs/*.md`, `AGENTS.md` |
| `Justfile` | `docs/skills/**`, `docs/*.md`, `AGENTS.md` |

---

## Code path → skill file mapping

Use this when the check fires and you need to know which skill to update:

| Changed path | Update this skill |
|---|---|
| `tests/smoke/**` | `gnome.md` (AT-SPI patterns) or `behave.md` (step structure) |
| `tests/lifecycle/**` | `bootc.md` |
| `tests/shared/**` | `behave.md` (shared helper conventions) |
| `tests/unit/**` | No skill update required — unit tests are internal quality tools |
| `.github/workflows/e2e.yml`, `e2e-*.yml` | `e2e-workflow.md` |
| `.github/workflows/skill-drift.yml` | `skill-drift.md` (this file) |
| `.github/actions/gnome-e2e/**` | `e2e-workflow.md` |
| `scripts/parse_results.py` | `e2e-workflow.md` (results persistence section) |
| `Justfile` | whichever skill owns the changed recipe |

Not sure? Check `docs/skills/index.md` for the full routing table.

---

## What counts as a satisfying update

A passing update must:
- Name the file, workflow, step, or path that changed
- State the new rule, behavior, or expectation
- Explain what an agent should now do differently

**Passing:** "Added a new `test_ref` input to `manual.yml` so dispatches can run branch-local test content. Documented the new input and when to use it in `e2e-workflow.md`."

**Failing:** rewrapping text, adding unrelated notes, or touching any markdown file without explaining the implementation change.

---

## Waiver process

For refactoring changes with no functional impact:

1. Add to your PR description:
   ```markdown
   ## Skill drift waiver
   Changed: `tests/unit/test_gnome_files_steps.py`
   Reason: Unit test file only — no step logic change, no operator-facing behavior change.
   ```
2. A maintainer can override the check. Do not self-waive for functional changes.

Unit test files (`tests/unit/**`) are the most common case for a waiver — they test internal logic and don't change agent-facing step behavior.

---

## Common failure modes

- Changing a workflow and forgetting to update docs
- Updating the wrong skill file for the behavior that changed
- Adding a placeholder doc that does not explain the change
- Assuming advisory = optional
