---
name: triage
description: >-
  Triage open issues and PRs in projectbluefin/testsuite. Use when asked to
  review the backlog, classify stale work, apply lifecycle labels, close
  completed/duplicate issues, or decide what is ready for an agent to claim.
metadata:
  canonical: /addyosmani/agent-skills
---

# Triage Agent

Triage open issues and PRs in `projectbluefin/testsuite`.

## When to Use

- A user asks to "review open issues and PRs"
- A user asks what is actionable, blocked, or stale
- You need to label newly-filed issues with one of the seven canonical workflow labels
- You are closing the loop on a session and want to leave the backlog correctly classified
- You need to decide whether an issue is testsuite-fixable or blocked on another repo

## When NOT to Use

- You are about to write implementation code (switch to `test-author` or the relevant implementation skill)
- The issue requires a human design, security, or breakage gate decision → route to `docs/skills/meta/human-gates/SKILL.md`
- You are tempted to file issues on `ublue-os/*`, `cncf/*`, or `homebrew/*` — stop and tell the human
- The issue is #232 (UEFI 3-lane migration workflow) while it is on `hold`

## Core Process

1. **Pull the canonical queue.**
   The Hive is the single source of truth; do not reconstruct the queue from labels.
   ```bash
   ~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --summary
   ~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --top 20
   ~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --prs --top 10
   ```

2. **List raw open work.**
   ```bash
   gh issue list --repo projectbluefin/testsuite --state open --limit 200
   gh pr list --repo projectbluefin/testsuite --state open --limit 200
   ```

3. **Inspect before classifying.** Read the issue body, recent comments, and linked PRs. For stale issues, verify against the current codebase:
   ```bash
   git log --oneline -- tests/path/feature.feature
   git show <commit> -- tests/path/feature.feature
   ```

4. **Classify and label.** Verify label names first:
   ```bash
   gh label list --repo projectbluefin/testsuite
   ```
   The only lifecycle labels are `1-triage`, `2-discussing`, `3-human-queue`,
   `3-clanker-queue`, `4-review`, plus the `blocked`/`hold` overlays. Exactly one
   numbered label per issue. Do not create new labels — that is a governance action.

5. **Close stale/resolved issues.** Use evidence (merged commit, existing test file, comment confirming completion). Prefer closing quietly — labels already describe the state.
   ```bash
   GH_REPO=projectbluefin/testsuite gh issue close <number>
   ```
   Use `gh issue edit <n> --remove-label "3-clanker-queue"` on closed issues so the queue stays clean.

6. **Triage PRs.**
   - Mergeable + no review → add `4-review`
   - Approved and green → enqueue via the merge queue (there is no `automerge` label)
   - Conflicting dependency PRs → leave for Renovate; do not hand-rebase

## Issue Classification

| Type | Label | Notes |
|---|---|---|
| Ready to claim | `3-clanker-queue` | Clear spec, fix is in testsuite, no human gate |
| Missing scenario / coverage gap | `3-clanker-queue` | Add scenario; update `suite-map.md` and `docs/qa-review.md` |
| Test correctness bug | `3-clanker-queue` | Point to the broken step or assertion |
| Infrastructure / structural | `3-clanker-queue` or `3-human-queue` | Check if the real fix belongs in `projectbluefin/lab` |
| Upstream image regression | `blocked` | bazzite extensions, composefs caps, MIME defaults, etc. |
| Design / human gate | `2-discussing` | e2e.yml changes, OOBE first-boot, cross-repo recipe changes |
| On hold | `hold` | Migration workflow, UEFI lane, explicit maintainer pause |

## Hard Rules

- **Never** implement issue #232 (UEFI 3-lane migration workflow) while it is on `hold`.
- **Never** file upstream issues on `ublue-os/*`, `cncf/*`, or `homebrew/*`.
- **Never** post explanatory comments just to describe a label or close action — the labels and git history are the audit trail.
- Verify an issue is actually resolved before closing it; grep the relevant feature/step file or read the merged commit.
- Do not apply `3-clanker-queue` to issues whose first step requires a human decision (use `2-discussing` or `3-human-queue`).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I should comment explaining every label/close." | Testsuite uses labels as the audit trail. Extra comments create noise for human maintainers. |
| "This old issue is probably done." | "Probably" is not enough. Verify with `git log` or the test file before closing. |
| "I need to implement the fix before I can triage the issue." | Triage is classification, not implementation. Set the label and move on. |
| "The Hive count is wrong; I can ignore it." | The Hive is the single source of truth. If it disagrees with your labels, fix your labels. |

## Red Flags

- An issue is closed but still carries `3-clanker-queue`
- A design-gate issue is labeled `3-clanker-queue`
- Triage actions are accompanied by explanatory comments
- Issues are closed without checking code or comment evidence
- Conflicting Renovate PRs are manually rebased

## Verification

Before ending a triage session:

- [ ] Every open issue has at least one status or source label
- [ ] No closed issue still carries `3-clanker-queue` or `3-human-queue`
- [ ] `hive-todos --repo testsuite --summary` reflects the intended queue
- [ ] Open PRs have `4-review` or a known blocker noted
- [ ] No `ublue-os/*`, `cncf/*`, or `homebrew/*` issues were filed
