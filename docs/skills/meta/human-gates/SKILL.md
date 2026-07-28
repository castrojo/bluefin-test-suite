---
name: human-gates
description: "When to stop and ask a human for input. Load before making design, security, breakage, or merge decisions."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

# Human Decision Gates

Four situations require stopping and requesting human input. Never guess past them.

| Gate | Stop when |
|---|---|
| **Design** | Architecture change, new test infrastructure, user-visible CI behavior change, changing what suites an image runs |
| **Security** | Secrets in CI, cosign/signing changes, any `<readonly-upstream>/*` interaction, any KDE property interaction beyond read-only, COPR sources in runner |
| **Breakage** | Removing or renaming a reusable workflow input that consuming repos depend on (e2e.yml inputs, action inputs) |
| **Merge** | PR is ready — requires CI green + human approval; the `ghost-lab` lab gate is currently unavailable (see below) |

---

## Design gate — examples

Stop before acting on any of these:

- Adding a new test suite (new directory under `tests/`) — affects the variant matrix, runner image, and coverage docs
- Changing which suites run for a given image in the variant matrix — affects coverage expectations for that image
- Changing the `e2e.yml` reusable workflow interface (adding/removing inputs, changing defaults) — consuming repos call this workflow
- Migrating from one test tool to another (e.g. adding playwright alongside behave)
- Adding a new QEMU boot mode or VM configuration

**Signal:** open an issue with `kind/design` label; describe the proposed change and ask for approval.

---

## Security gate — examples

Stop before acting on any of these:

- Adding `secrets:` to any workflow or composite action
- Changing cosign signing steps or supply chain verification
- Adding a new third-party composite action not already in the repo
- Changing `permissions:` blocks to grant write access beyond `contents: read` + `packages: write`
- Any change that could affect the runner container's trust boundary

**Signal:** stop immediately, describe what you found, and ask the human to review before proceeding.

---

## Breakage gate — examples

Stop before acting on any of these:

- Removing an input from `e2e.yml` that `<image-org>/bluefin`, `<image-org>/actions`, or other repos pass in their workflows
- Renaming the `suites` input or changing its format
- Changing the artifact schema output by `e2e.yml` (artifact names, JSON structure)
- Modifying the `gnome-e2e` composite action interface

**How to check:** search for callers before removing anything:
```bash
gh search code "testsuite/.github/workflows/e2e.yml" --repo projectbluefin --json repository,path
```

**Signal:** open a breakage issue listing every affected repo before making the change.

---

## Merge gate

> **The `ghost-lab` commit status is NOT currently posted on testsuite PRs.** Do not wait for it — nothing will ever arrive. Tracking issue: [`projectbluefin/lab#471`](https://github.com/projectbluefin/lab/issues/471).

**Effective gate today:**

1. GitHub Actions CI green — `Lint & syntax` and `Behave dry-run` (`pr-validate.yml`), `pytest` (`unit-tests.yml`). These are the required status checks on the `main — merge queue` ruleset.
2. Human approval to merge. Prepare the PR, then ask; do not merge on your own judgement.

Once CI is green and a human has approved, enqueue via:
```bash
gh pr merge <NUMBER> --repo <image-org>/testsuite --squash --auto
```

The merge queue re-runs the required GHA checks on the merge commit and lands automatically on green. Human `lgtm` is not required for normal test/docs/fix PRs — only for:

- PRs touching `.github/workflows/e2e.yml` (reusable workflow interface)
- PRs touching `AGENTS.md` (behavioral directive changes)
- PRs touching `CODEOWNERS`

**Warning — reduced assurance.** GHA CI does **not** boot a real VM. Real-VM regressions (GNOME Shell/AT-SPI timing, GDM, bootc upgrade/rollback, oomd) are currently uncaught before merge. This is a known gap, not permission to skip verification: for changes to runtime step behaviour, environment hooks, or bootc flows, request a manual lab run and record the result in the PR before asking for merge approval.

**Target state (currently broken).** The intended workflow is: submit to lab → wait for results → merge on pass, fix on fail. The `pr-label-poller` in `<image-org>/testing-lab` auto-runs `smoke,common` on every open testsuite PR every 5 minutes; in the target state its result is published on the PR SHA and reviewers wait for it to be green before enqueuing. The poller is healthy and testsuite is in its `AUTO_REPOS` list, but testsuite is only half-enrolled — it gets no check reporter, no dispatch, and has no `.github/workflows/lab-check.yml` — so results are computed and discarded. Restore this as the gate when lab#471 lands. Full evidence: `docs/skills/ci-ops/contributing/references/reviewing-and-merging.md`.

---

## Upstream namespace prohibition (read-only)

**NEVER** create issues, PRs, comments, forks, or any other programmatic write to any
`<readonly-upstream>/*` repository. Read-only `gh api` calls are permitted. If a task requires
writing to `ublue-os`, stop and tell the human to report it manually.

### KDE properties — strictly read-only, no exceptions

All KDE-owned properties are read-only for every agent and every automated process:

- `invent.kde.org` (GitLab) and `invent-registry.kde.org`
- `bugs.kde.org`, `discuss.kde.org`, `community.kde.org`
- KDE Matrix rooms (`#kde-qa:kde.org`, `#plasma:kde.org`, `#kde-linux:kde.org`) and mailing lists
- The `KDE/*` GitHub mirrors

**Permitted:** read-only HTTP GET, read-only API calls, `git clone`, `git fetch`, reading source
and documentation.

**Forbidden — no exceptions, and no "draft it for review" carve-out:**

- Creating or editing issues, merge requests, pull requests, comments, reviews, snippets, wiki
  pages, forks, branches, tags, or releases
- Any authenticated write, push, or `POST`/`PUT`/`PATCH`/`DELETE` to a KDE host
- Posting to KDE Matrix rooms, forums, mailing lists, or bug trackers
- Registering accounts or requesting access

This applies to sub-agents, background agents, and scheduled jobs, not only the primary session.
When work identifies a genuine upstream contribution, **produce the patch or report locally and
hand it to a human to submit.** Describe it as a recommendation, never as an action taken or
authorized.

Rationale: KDE is an upstream community this project actively wants to collaborate with. A
single unauthorized automated write would cost more trust than any test contribution could earn.
