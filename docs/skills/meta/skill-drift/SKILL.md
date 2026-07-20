---
name: skill-drift
description: "How the skill-drift CI check works and how to keep skills synchronized with implementation changes. Load when a PR touches both code and docs."
metadata:
  type: pattern
  audience: agents
  maturity: stable
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

Calls the reusable `<image-org>/actions/.github/workflows/skill-drift-check.yml` at a pinned SHA. See `.github/workflows/skill-drift.yml`.

---

## Path mapping for this repo

| code-paths | skill-paths |
|---|---|
| `.github/workflows/**` | `docs/**/*.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` |
| `.github/actions/**` | `docs/**/*.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` |
| `tests/**` | `docs/**/*.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` |
| `scripts/**` | `docs/**/*.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` |
| `Justfile` | `docs/**/*.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` |

---

## Code path → skill file mapping

Use this when the check fires and you need to know which skill to update:

| Changed path | Update this skill |
|---|---|
| `tests/smoke/**` | `test-authoring/gnome/SKILL.md` (AT-SPI patterns) or `test-authoring/behave/SKILL.md` (step structure) |
| `tests/lifecycle/**` | `test-authoring/bootc/SKILL.md` |
| `tests/shared/**` | `test-authoring/behave/SKILL.md` (shared helper conventions) |
| `tests/unit/**` | No skill update required — unit tests are internal quality tools |
| `.github/workflows/e2e.yml`, `e2e-*.yml` | `ci-ops/e2e-workflow/SKILL.md` |
| `.github/workflows/skill-drift.yml` | `meta/skill-drift/SKILL.md` (this file) |
| `.github/workflows/docs-validate.yml` | `meta/skill-drift/SKILL.md` or `meta/writing-skills/SKILL.md` |
| `.github/actions/gnome-e2e/**` | `ci-ops/e2e-workflow/SKILL.md` |
| `scripts/parse_results.py` | `ci-ops/e2e-workflow/SKILL.md` |
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
