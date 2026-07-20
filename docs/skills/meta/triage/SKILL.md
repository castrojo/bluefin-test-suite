---
name: triage
description: "Issue triage rules and lifecycle labels for this repo. Load when triaging open issues or backlog PRs."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

# Triage — testsuite backlog hygiene

`<image-org>/testsuite` uses a small set of lifecycle labels to keep the
agent queue readable. Good triage means every open issue has a clear
classification, stale work is closed, and agents never waste time on blocked or
already-finished items.

## When to Use

- A user asks you to "review open issues and PRs"
- You need to classify issues after a filing session
- You are deciding what to claim next
- You are closing out a session and leaving the backlog in a clean state

## When NOT to Use

- You are writing implementation code (use the relevant test-authoring skill)
- The issue needs a human design/security/breakage decision (use `docs/skills/human-gates.md`)
- The work belongs in `<image-org>/testing-lab` or another repo (file/link there)

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

## Status labels

Check current labels before editing:

```bash
gh label list --repo <image-org>/testsuite
```

The triage-relevant labels are:

| Label | Meaning |
|---|---|
| `status/queued` | Ready to claim — clear spec, fix is in testsuite, no human gate |
| `status/triage` | Needs human review/design/cross-repo decision before work starts |
| `status/hold` | Intentionally paused: migration lane, external image fix, maintainer hold |
| `status/claimed` | Someone is actively working on it |
| `test-quality` | Test correctness or reliability concern |
| `coverage-gap` | Missing test coverage (scenario, unit test, or @future stub) |
| `structural` | Suite architecture or CI harness issue |
| `source:agent` / `source:gha` / `source:manual` | Who/what filed the issue |
| `pr/needs-review` | PR is ready for maintainer review |
| `automerge` | PR is approved and can merge when CI is green |

## Core triage workflow

1. **Read the queue.** Use the Hive summary plus raw GitHub lists:
   ```bash
   gh issue list --repo <image-org>/testsuite --state open --limit 200
   gh pr list --repo <image-org>/testsuite --state open --limit 200
   ```

2. **Inspect stale issues.** For anything older than a few weeks, read the body,
   recent comments, and linked commits/PRs. Verify against the repo:
   ```bash
   git log --oneline -- tests/<suite>/features/<feature>.feature
   git show <commit> -- tests/<suite>/features/steps/steps.py
   ```

3. **Apply one status label per issue.** An issue should not sit unlabeled. Use
   `status/queued`, `status/triage`, or `status/hold`. Add type labels
   (`test-quality`, `coverage-gap`, `structural`) when they clarify the work.

4. **Close completed/duplicate issues.** Use evidence from code or comments.
   Close quietly — labels and git history are the audit trail.
   ```bash
   GH_REPO=<image-org>/testsuite gh issue close <number>
   ```
   Remove active-work labels from closed issues so the Hive stays accurate:
   ```bash
   GH_REPO=<image-org>/testsuite gh issue edit <number> --remove-label "status/queued"
   ```

5. **Triage PRs.**
   - Mergeable and not reviewed → `pr/needs-review`
   - Approved and green → `automerge`
   - Conflicting dependency update → leave for Renovate; do not hand-rebase

6. **Re-check the queue.** Run the Hive summary again and confirm the counts
   match your changes.

## Classification guide

| Situation | Labels | Notes |
|---|---|---|
| Fix is in testsuite, clear next step | `status/queued` (+ `test-quality`/`coverage-gap`/`structural`) | Ready to claim |
| Missing scenario or `@future` stub | `coverage-gap` + `status/queued` | Update `suite-map.md` and `QA-REVIEW.md` when implemented |
| Broken step/assertion | `test-quality` + `status/queued` | Reference the failing step |
| Harness/CI issue | `structural` + `status/queued` | May need a split PR to `<image-org>/testing-lab` |
| Upstream image regression (e.g. bazzite extensions, composefs caps, MIME defaults) | `status/hold` | Do not fix in testsuite; link tracking issue |
| Needs design or cross-repo recipe change | `status/triage` | Wait for human decision |
| Migration/UEFI workflow | `status/hold` | Blocked by maintainer policy or spike |

## Things to avoid

- **Do not post explanatory comments** for label or close actions. Labels are
  the audit trail; comments are for humans asking questions.
- **Do not close issues without verifying** they are actually resolved. Check
  the test file or a confirming comment first.
- **Do not label design-gate issues as `status/queued`.** If a human must
  decide, use `status/triage`.
- **Do not file upstream issues** on `<readonly-upstream>/*`, `cncf/*`, or `homebrew/*`.

## Verification

At the end of a triage session:

- [ ] Every open issue has at least one status or source label
- [ ] No closed issue still carries `status/queued` or `status/claimed`
- [ ] `hive-todos --repo testsuite --summary` reflects the expected queue
- [ ] Every open PR is labeled `pr/needs-review`, `automerge`, or has a known blocker
- [ ] No upstream issues were filed on prohibited orgs
