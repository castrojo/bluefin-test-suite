---
name: triage
version: "1.0"
last_updated: "2026-07-20"
id: triage
one_line_purpose: Triage testsuite issues and pull requests with the canonical label workflow.
entry_point: docs/skills/meta/triage/SKILL.md
category: meta
mcp_compliance_level: partial
status: active
dependencies: []
tags: [triage, labels, issues]
description: "Issue triage rules and lifecycle labels for this repo. Load when triaging open issues or backlog PRs."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---
# Triage — testsuite backlog hygiene

`projectbluefin/testsuite` uses the canonical factory label contract from
[`common/docs/skills/label-workflow.md`](https://github.com/projectbluefin/common/blob/main/docs/skills/label-workflow.md).
That document is authoritative; this skill only covers what is specific to
testsuite. Good triage means every open issue carries exactly one numbered
workflow label, stale work is closed, and agents never waste time on blocked or
already-finished items.

**Trust the machines: workflows own state, humans provide intent.** Do not
invent a second state machine with comments, custom labels, or local scripts.

## When to Use

- A user asks you to "review open issues and PRs"
- You need to classify issues after a filing session
- You are deciding what to claim next
- You are closing out a session and leaving the backlog in a clean state

## When NOT to Use

- You are writing implementation code (use the relevant test-authoring skill)
- The issue needs a human design/security/breakage decision (use `docs/skills/meta/human-gates/SKILL.md`)
- The work belongs in `projectbluefin/lab` or another repo (file/link there)

## Canonical queue source

Do not reconstruct the actionable queue by grepping labels. The Hive exposes
the single source of truth:

```bash
~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --summary
~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --top 20
~/.agents/skills/hive-todos/scripts/hive-todos.sh --repo testsuite --queued --top 10
~/.agents/skills/hive-todos/scripts/hive-todos.sh --prs --top 10
```

Combine filters freely (`--repo`, `--label`, `--top`, `--json`).

## Labels

Check current labels before editing:

```bash
gh label list --repo projectbluefin/testsuite
```

The seven canonical workflow labels are the only lifecycle state:

| Label | Meaning |
|---|---|
| `1-triage` | New work awaiting triage |
| `2-discussing` | Discussion or design clarification needed |
| `3-human-queue` | Admitted to the human-maintained queue |
| `3-clanker-queue` | Admitted to the agent-maintained queue — this is what agents claim |
| `4-review` | Pull request awaiting review |
| `blocked` | Waiting on human input or an external dependency (overlay) |
| `hold` | Intentionally paused (overlay) |

Exactly one numbered label per issue, with `blocked` or `hold` as an optional
overlay. testsuite additionally carries repository-local, non-lifecycle labels
(`kde`, `runner`, `dependencies`, `javascript`) applied by automation; they
describe scope, not state.

> Older testsuite docs referenced `status/queued`, `status/triage`,
> `status/hold`, `status/claimed`, `pr/needs-review`, `automerge`,
> `test-quality`, `coverage-gap`, `structural`, and `source:*`. **None of these
> exist on the repository.** Do not create them — adding a label is a
> governance action requiring human sign-off. Record classification detail in
> the issue body or project fields instead.

## Core triage workflow

1. **Read the queue.** Use the Hive summary plus raw GitHub lists:
   ```bash
   gh issue list --repo projectbluefin/testsuite --state open --limit 200
   gh pr list --repo projectbluefin/testsuite --state open --limit 200
   ```

2. **Inspect stale issues.** For anything older than a few weeks, read the body,
   recent comments, and linked commits/PRs. Verify against the repo:
   ```bash
   git log --oneline -- tests/<suite>/features/<feature>.feature
   git show <commit> -- tests/<suite>/features/steps/steps.py
   ```

3. **Apply exactly one numbered label per issue.** An issue should not sit
   unlabeled. Use `1-triage`, `2-discussing`, `3-human-queue`, or
   `3-clanker-queue`, plus `blocked`/`hold` as an overlay when applicable.
   Classification detail (test quality, coverage gap, structural) belongs in the
   issue body, not in a new label.

4. **Close completed/duplicate issues.** Use evidence from code or comments.
   Close quietly — labels and git history are the audit trail.
   ```bash
   GH_REPO=projectbluefin/testsuite gh issue close <number>
   ```
   Remove queue labels from closed issues so the Hive stays accurate:
   ```bash
   GH_REPO=projectbluefin/testsuite gh issue edit <number> --remove-label "3-clanker-queue"
   ```

5. **Triage PRs.**
   - Mergeable and not reviewed → `4-review`
   - Approved and green → enqueue via the merge queue; there is no `automerge` label
   - Conflicting dependency update → leave for Renovate; do not hand-rebase
   - Two open PRs touching the same file → flag the overlap; one of them should
     fold into the other (see the disjointness rule in `AGENTS.md`)

6. **Re-check the queue.** Run the Hive summary again and confirm the counts
   match your changes.

## Classification guide

| Situation | Label | Notes |
|---|---|---|
| Fix is in testsuite, clear next step, no human gate | `3-clanker-queue` | Ready for an agent to claim |
| Missing scenario or `@future` stub | `3-clanker-queue` | Update `suite-map.md` and `docs/qa-review.md` when implemented |
| Broken step/assertion | `3-clanker-queue` | Reference the failing step in the body |
| Harness/CI issue | `3-clanker-queue` or `3-human-queue` | May need a split PR to `projectbluefin/lab` |
| Upstream image regression (bazzite extensions, composefs caps, MIME defaults) | `blocked` | Do not fix in testsuite; link the tracking issue |
| Needs design or cross-repo decision | `2-discussing` | Wait for the human decision |
| Migration/UEFI workflow paused by policy | `hold` | Blocked by maintainer policy or spike |
| Human should do it | `3-human-queue` | Not agent-claimable |

## Things to avoid

- **Do not post explanatory comments** for label or close actions. Labels are
  the audit trail; comments are for humans asking questions.
- **Do not close issues without verifying** they are actually resolved. Check
  the test file or a confirming comment first.
- **Do not route design-gate issues to `3-clanker-queue`.** If a human must
  decide, use `2-discussing` or `3-human-queue`.
- **Do not create new labels.** Label changes are a governance action; propose
  them to a human instead.
- **Do not change labels to manufacture progress.**
- **Do not file upstream issues** on `ublue-os/*`, `cncf/*`, or `homebrew/*`.

## Verification

At the end of a triage session:

- [ ] Every open issue carries exactly one numbered workflow label
- [ ] No closed issue still carries `3-clanker-queue` or `3-human-queue`
- [ ] `gh label list --repo projectbluefin/testsuite` shows only the seven
      canonical labels plus repository-local automation labels
- [ ] `hive-todos --repo testsuite --summary` reflects the expected queue
- [ ] Every open PR is labeled `4-review` or has a known blocker
- [ ] No upstream issues were filed on prohibited orgs
