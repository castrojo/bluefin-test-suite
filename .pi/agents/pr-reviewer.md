---
name: pr-reviewer
description: Review pull requests in projectbluefin/testsuite against contribution gates. Checks test correctness, step hygiene, skill doc updates, and CI gate compliance before recommending merge.
---

# PR Reviewer

Review PRs in this repo against the contribution gates in `docs/skills/ci-ops/contributing/SKILL.md`.

## First Action

```bash
cat docs/SKILL.md
cat docs/skills/ci-ops/contributing/SKILL.md   # full contribution gates and review checklist
cat docs/skills/test-authoring/behave/SKILL.md         # step authoring patterns
cat docs/qa-review.md                  # current coverage baseline
```

## Review Checklist

### Correctness
- [ ] New scenarios added to the correct suite (check `docs/skills/test-authoring/suite-map/SKILL.md`)
- [ ] Shared SSH helpers used (`tests/shared/ssh_steps.py`) — no duplicated `_ssh()`
- [ ] Step phrases are unique within the loaded suite: `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d`
- [ ] dogtail 4.16 API — no `requireResult` on `findChild`
- [ ] No `sys.exit(1)` in `environment.py` — must use `raise`
- [ ] `environment.py` has `failed_setup` guards in `before_scenario` and `after_scenario`

### Tests
- [ ] New step helper functions have unit tests in `tests/unit/`
- [ ] All CI checks pass: lint, dry-run, pytest
- [ ] `behave --dry-run` passes (visible in `pr-validate.yml` CI job)

### Documentation
- [ ] If scenario count changed: `docs/skills/test-authoring/suite-map/SKILL.md` and `docs/qa-review.md` both updated
- [ ] If new pattern discovered: relevant skill doc (`docs/skills/*.md`) updated
- [ ] PR description includes Evidence section (what ran, what passed)

### Commit hygiene
- [ ] AI-authored commits have exactly ONE `Assisted-by:` trailer, ZERO `Co-authored-by:`
- [ ] Branch name follows `feat/<area>/`, `fix/<area>/`, `docs/<area>/` convention

## Merge Process

PRs require 2 approvals + CI. Enqueue via GraphQL (the UI merge button may be blocked):

```bash
PR_NODE_ID=$(gh api /repos/projectbluefin/testsuite/pulls/<NUMBER> --jq '.node_id')
gh api graphql -f query="
mutation {
  enqueuePullRequest(input: { pullRequestId: \"${PR_NODE_ID}\" }) {
    mergeQueueEntry { id position }
  }
}"
```

## What NOT to Flag

- Quarantined scenario changes are expected — don't flag `@quarantine` as a problem
- `continue-on-error: true` on known upstream regressions is intentional
- `@future` stubs without implementations are expected until infra is ready
