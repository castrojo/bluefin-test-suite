---
name: workflows-without-a-pull-request-trigger-break-main-silently
description: "Deep dive: workflows with no pull_request trigger break main silently"
metadata:
  type: reference
  audience: agents
  maturity: stable
  context7-sources:
    - /actions/checkout
---
# Workflows Without A Pull Request Trigger Break Main Silently

## Schedule-only workflows have no PR safety net

`.github/workflows/publish-to-pages.yml` builds the dashboard and runs on `schedule`,
`push` to `main` (paths-filtered), and `workflow_dispatch` — never on `pull_request`.
Nothing validates the dashboard build while a PR is open, so a dependency bump can be
merged fully green and only fail afterwards, on a schedule tick that no human is
watching. The classic signature is an `npm ci` `ERESOLVE` peer-dependency conflict
introduced by an automated dependency-update PR: the lockfile resolves locally, the PR
checks are all unrelated, and the workflow then fails on every scheduled run until
someone happens to open the Actions tab.

**Rule: when a workflow validates an artifact that PRs can break, it needs a
PR-triggered counterpart.** Otherwise its first red run is on `main`, after the
breaking change is already merged. Either add `pull_request` (with the same paths
filter) to the workflow, or add an equivalent build job to `pr-validate.yml`. Check
this whenever you add a schedule-only or push-only workflow, and whenever you add a
new buildable artifact directory to the repo.

The corollary applies to the paths filter too: a `push`-on-`main` trigger scoped to
`dashboard/**` does not fire when the break comes from a lockfile or config file
outside that path.

## Triage: find the first failing run, not the newest merge

A schedule-only workflow can be red for many consecutive runs before it is noticed, so
the most recent merge is almost never the cause. Get the run history and find the
boundary between the last green run and the first red one, then diff the two commits:

```bash
gh run list --workflow "Publish QA Dashboard & Screenshots to Pages" \
  --limit 60 --json conclusion,createdAt,headSha,databaseId

# then diff the last green head against the first red head
git log --oneline <last-green-sha>..<first-red-sha>
```

The change that lands in that range is the breaking one. Reading the newest failing
log alone tells you the symptom but not which merge introduced it.

---
