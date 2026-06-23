# testsuite — Agent & Copilot Instructions

> **You are part of an agentic operating system, built by agentic workflows.**
> Every session produces two outputs: the work AND the learning. See [Self-Improvement Loop](#self-improvement-loop).

**projectbluefin/testsuite** owns Bluefin's QA pipeline — behave + qecore-headless + dogtail AT-SPI tests running in GNOME-on-QEMU.

## Where This Repo Fits

```
projectbluefin/bluefin   ──┐
projectbluefin/bluefin-lts ┼──▶ images ──▶ testsuite (e2e gate) ──▶ promotion
projectbluefin/dakota    ──┘
```

New test content → this repo.
New infrastructure (Argo templates, VM specs, KubeVirt manifests) → `projectbluefin/testing-lab`.
Shared CI composite actions → `projectbluefin/actions`.
When a PR touches two repos, split it.

## Agent fast path

> **Before using any library or tool: look up its docs via Context7 first. Always.**
> qecore, dogtail, behave, gi.repository, AT-SPI — all have live, authoritative docs.
> Pattern: `resolve-library-id` → `get-library-docs` → implement → cite the section.
> Guessing at API, flag-hunting, and trial-and-error are banned. The docs exist. Read them.

```
1. docs/skills/index.md          # hard rules + skill routing table
2. Context7: resolve the library's ID, read its docs, then act
3. docs/skills/<area>.md         # load only the skill for your task
4. ruff check tests/ --select E,F,W --ignore E501  # before every commit
5. behave --dry-run              # before pushing any .feature change
```

**Cross-repo work:** repos are on disk at `~/src/`. Never clone into `/tmp`. Use `git worktree add ../repo-desc -b branch` for parallel branches. See `docs/skills/contributing.md` — Git worktree hygiene.

## GNOME 50 Crowdsourcing

This repo is **agent-first** — agents are the primary maintainers of GNOME 50 test coverage. No human gating required to file issues or submit PRs (within the gates below).

### What needs coverage

Run `just list-stubs` to see `@future` scenarios waiting for implementation. Current known gaps beyond `@future` tags:

| Area | Suite | Gap | Priority |
|---|---|---|---|
| OOBE / first-boot | smoke | Initial user setup flow | Low |
| Flatpak permissions | software | Flatseal per-app permissions | Low |

### How agents contribute

1. **Pick a gap** — from the table above, `just list-stubs`, or file a new issue
2. **Write the scenario** — add a `.feature` file entry in the appropriate suite
3. **Implement the steps** — add to the suite's `steps.py`; reuse `docs/skills/gnome.md` patterns
4. **Update the matching skill** — see [Self-Improvement Loop](#self-improvement-loop)
5. **Run lint locally** — `ruff check tests/ --select E,F,W --ignore E501`
6. **File a PR** — branch format: `feat/<suite>/<short-desc>`
7. **Update counts** — bump scenario count in `QA-REVIEW.md` and `docs/skills/suite-map.md`

### Testing your scenario

```yaml
# In any fork/branch workflow:
- uses: projectbluefin/testsuite/.github/actions/gnome-e2e@main
  with:
    image: ghcr.io/ublue-os/bluefin:latest
    suite: smoke
```

Or trigger manually: Actions → "Manual Test Run" (requires ghost runner access).

## Migration testing — manual only

`migration-test.yml` runs on `workflow_dispatch` only — there is no automated schedule trigger.
Changes to bootc version pins, image base digests, OCI layer compression format, or `ostree-ext`
carry **invisible migration risk**. Before promoting, manually trigger the migration test workflow
if your change could affect upgrade paths from `ublue-os/bluefin` → `projectbluefin/bluefin`.

Issue [#232](https://github.com/projectbluefin/testsuite/issues/232) (UEFI-boot 3-lane workflow)
is on `queue/hold` — do not attempt to implement the UEFI lane without checking hold criteria.

## Self-Improvement Loop

Every session that changes this repo produces two outputs:

1. **The work** — the PR, fix, or test coverage improvement
2. **The learning** — what a future agent should know

Output 1 without Output 2 leaves the factory no smarter. **The loop only compounds if agents write back.**

```
Agent works on task
  └─ discovers pattern / workaround / convention
       └─ writes it to the relevant skill file in docs/skills/
            └─ commits in the same PR (never a follow-up)
                 └─ next agent starts smarter → loop
```

### Before marking work complete — checklist

- [ ] Did I discover any workaround, non-obvious pattern, or convention?
- [ ] Is there a skill file for the area I worked in?
- [ ] If yes — did I update it?
- [ ] If no — did I create one in `docs/skills/`?
- [ ] Is the skill file committed in **this same PR**?

For the full mandate, routing table, and what counts as a learning: [`docs/skills/skill-improvement.md`](docs/skills/skill-improvement.md)

The skill-drift CI check warns when implementation changes land without a skill update. Treat warnings as hard requirements.

## Skills

**Start here:** `docs/skills/index.md` — hard rules + load-on-demand table for all sub-skills.

| Task | Load |
|---|---|
| Any test authoring task | `docs/skills/index.md` |
| Variant matrix, coverage snapshot, @future gaps | `docs/skills/suite-map.md` |
| Submitting improvements, PRs, doc fixes | `docs/skills/contributing.md` |
| Infra gotchas (GDM autologin, Argo mutex, systemd-oomd.socket, bazzite extension state) | `docs/skills/ops.md` |
| When to stop and ask a human | `docs/skills/human-gates.md` |
| Skill update mandate, which file to update | `docs/skills/skill-improvement.md` |
| Skill-drift CI check path mapping, waiver | `docs/skills/skill-drift.md` |

Sub-skills are indexed in `docs/skills/index.md` — load them from there on demand.

## Commit Format

[Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <description>`

Common types: `feat` `fix` `docs` `ci` `refactor` `test`

Every AI-authored commit **must** include both trailers:

```
feat(smoke): add Nautilus sidebar navigation steps

Assisted-by: Claude Sonnet 4.6 via GitHub Copilot
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

Both trailers must appear together. One without the other is a convention violation.

## Mandatory Gates

- Ruff lint must pass before every commit: `ruff check tests/ --select E,F,W --ignore E501`
- Behave dry-run must pass before pushing `.feature` changes
- PR title: Conventional Commits format
- Both AI attribution trailers on every AI-authored commit
- **SHA pinning** — all `uses:` references to external GitHub Actions must be pinned to a full commit SHA with a version comment. Never use floating tags (`@main`, `@latest`, `@v*`).
- Max 4 open PRs at a time per agent
- No WIP PRs — open PRs are ready to review and merge
- One PR per logical change — never batch unrelated fixes

## Human Decision Gates

Stop and request human input at these four gates. See [`docs/skills/human-gates.md`](docs/skills/human-gates.md) for details.

| Gate | Stop when |
|---|---|
| **Design** | New suite, new infra, changing e2e.yml interface, changing which suites run for an image |
| **Security** | Secrets in CI, cosign changes, new third-party actions, expanded `permissions:` |
| **Breakage** | Removing/renaming e2e.yml inputs that consuming repos depend on |
| **Merge** | PR is ready — merge queue + green CI always required |

## Verification Requirements

Do not enqueue a PR without:

- [ ] All three CI checks green (Lint & syntax, Behave dry-run, pytest)
- [ ] Skill file update committed in **this same PR** (not a follow-up)
- [ ] PR title follows Conventional Commits format
- [ ] Both AI attribution trailers on every AI-authored commit
- [ ] Scenario count updated in `QA-REVIEW.md` and `docs/skills/suite-map.md` if scenarios changed

## 🚫 ublue-os Prohibition

**NEVER** create issues, PRs, comments, forks, or any other programmatic write to any `ublue-os/*` repository. Read-only `gh api` calls are permitted. If a task requires writing to `ublue-os`, stop and tell the human to report it manually.

