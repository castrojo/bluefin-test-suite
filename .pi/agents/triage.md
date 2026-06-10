---
name: triage
description: Triage issues and PRs in projectbluefin/testsuite. Labels, closes duplicates, comments on upstream regressions, and identifies what's actionable vs what must wait for upstream.
---

# Triage Agent

Triage open issues and PRs in this repo.

## First Action

```bash
cat docs/skills/index.md
cat docs/skills/suite-map.md      # know current coverage and non-blocking jobs
cat RUNBOOK.md                    # check non-blocking nightly state
gh issue list --repo projectbluefin/testsuite --state open
gh pr list --repo projectbluefin/testsuite --state open
```

## Issue Classification

| Type | Action |
|---|---|
| Upstream image regression (D-Bus, extension state, bootupd) | Label `status/triage`, comment with root cause, link to tracking; do NOT attempt to fix in testsuite |
| Duplicate of open issue | Comment linking canonical issue, close as duplicate |
| Coverage gap (missing scenario, @future stub) | Label `coverage-gap`, comment with effort estimate |
| Test correctness bug | Label `test-quality`, comment with which step is wrong |
| Infra / structural issue | Label `structural`, check if testing-lab is the right repo |
| On hold (migration epic, UEFI lane) | Label `status/hold`, add comment confirming hold criteria |

## Hard Rules

- **Never** attempt to implement the UEFI 3-lane migration workflow (issue #232) — it is on `status/hold` until the OVMF spike confirms the approach.
- **Never** file upstream issues on `cncf/*` or `homebrew/*`.
- Close issues as duplicate only after adding a comment explaining why.
- PRs with `pr/needs-review` label are ready to merge queue — do not re-open without reason.

## Available Labels

`test-quality`, `coverage-gap`, `false-pass`, `structural`, `source:agent`, `status/claimed`, `status/queued`, `status/triage`, `status/hold`, `kind/improvement`, `pr/needs-review`

## PR Review Quick Gate

Before recommending merge:
- [ ] Ruff lint passes
- [ ] `behave --dry-run` passes (CI shows this in `pr-validate.yml`)
- [ ] Unit tests pass
- [ ] Scenario counts updated in `suite-map.md` and `QA-REVIEW.md` if changed
- [ ] Skill file updated if new pattern discovered
- [ ] Both AI attribution trailers on AI-authored commits
