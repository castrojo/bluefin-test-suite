---
name: human-gates
description: "The four human decision gates for projectbluefin/testsuite — when to stop and request human input rather than proceeding autonomously. Load when uncertain whether a change requires human approval."
metadata:
  type: procedure
---

# Human Decision Gates

Four situations require stopping and requesting human input. Never guess past them.

| Gate | Stop when |
|---|---|
| **Design** | Architecture change, new test infrastructure, user-visible CI behavior change, changing what suites an image runs |
| **Security** | Secrets in CI, cosign/signing changes, any `ublue-os/*` interaction, COPR sources in runner |
| **Breakage** | Removing or renaming a reusable workflow input that consuming repos depend on (e2e.yml inputs, action inputs) |
| **Merge** | PR is ready — always requires merge queue entry and CI green; merge queue still requires the required checks to pass |

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

- Removing an input from `e2e.yml` that `projectbluefin/bluefin`, `projectbluefin/actions`, or other repos pass in their workflows
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

All PRs enter the merge queue via:
```bash
gh pr merge <NUMBER> --repo projectbluefin/testsuite --squash --auto
```

The merge queue runs required CI (lint, behave dry-run, pytest) on the merge commit and lands automatically on green. Human `lgtm` is not required for normal test/docs/fix PRs — only for:

- PRs touching `.github/workflows/e2e.yml` (reusable workflow interface)
- PRs touching `AGENTS.md` (behavioral directive changes)
- PRs touching `CODEOWNERS`

---

## ublue-os prohibition

**NEVER** create issues, PRs, comments, forks, or any other programmatic write to any `ublue-os/*` repository. Read-only `gh api` calls are permitted. If a task requires writing to `ublue-os`, stop and tell the human to report it manually.
