# testsuite — Agent instructions

You are an agent working in **testsuite**, the GNOME bootc image end-to-end test repository. This repo owns the behave/qecore/dogtail test suites, shared helpers, and reusable GitHub Actions used to validate GNOME-based bootc images.

## Start here

1. Read `docs/skills/index.md` next. It contains the hard rules and a task → skill map.
2. Load only the skill file(s) matching your current task. Do not read every skill.
3. Before using any library (qecore, dogtail, behave, gi.repository, AT-SPI), look up its current docs via Context7.

## Build / test / lint commands

Run these before every change:

```bash
# Lint
ruff check tests/ --select E,F,W --ignore E501

# BDD dry-run (run only if you touched .feature files)
behave --dry-run tests/<suite>/features

# Unit tests
python3 -m pytest tests/unit/ -q

# List unimplemented scenarios
just list-stubs
```

## Navigation quick-reference

| Task | Load |
|---|---|
| Writing behave tests or step definitions | `docs/skills/test-authoring/behave/SKILL.md` |
| GNOME Shell / AT-SPI / dogtail interactions | `docs/skills/test-authoring/gnome/SKILL.md` |
| bootc upgrade/rollback/migration tests | `docs/skills/test-authoring/bootc/SKILL.md` |
| UEFI/OVMF reboot testing | `docs/skills/test-authoring/uefi-boot/SKILL.md` |
| Reusable e2e workflow inputs and debugging | `docs/skills/ci-ops/e2e-workflow/SKILL.md` |
| Lab/infra gotchas (GDM, oomd, Argo mutex) | `docs/skills/ci-ops/ops/SKILL.md` |
| Coverage matrix and @future gaps | `docs/skills/test-authoring/suite-map/SKILL.md` |
| Writing or updating a skill file | `docs/skills/meta/writing-skills/SKILL.md` |
| Knowing when to stop and ask a human | `docs/skills/meta/human-gates/SKILL.md` |
| Operational commands (manual runs, merge queue, diagnostics) | `docs/runbook.md` |
| Release-trust / audit posture | `docs/qa-review.md` |

## Hard boundaries

- **Test content → this repo.** Infrastructure (VM specs, KubeVirt manifests, workflow orchestration) belongs in the separate [`projectbluefin/lab`](https://github.com/projectbluefin/lab) repo. Split PRs that touch both.
- **Never create issues, PRs, comments, forks, or writes in read-only upstream namespaces.** Read-only API calls are allowed; see `docs/skills/meta/human-gates/SKILL.md` for the prohibition details. **This explicitly includes all KDE properties (`invent.kde.org`, `bugs.kde.org`, KDE Matrix rooms, `KDE/*` mirrors) — read-only, no exceptions, for sub-agents and scheduled jobs too.**
- **Workflow action references must be pinned.** External `uses:` must be a full commit SHA with a version comment. Never use floating tags.
- **No WIP PRs.** Open PRs must be ready to merge.
- Keep open PRs scoped and mergeable; there is no artificial cap on the number of open PRs.

## Mandatory gates before enqueuing any PR

- [ ] `ruff check tests/ --select E,F,W --ignore E501` passes.
- [ ] `behave --dry-run` passes if any `.feature` file changed.
- [ ] `python3 -m pytest tests/unit/ -q` passes.
- [ ] A matching skill file in `docs/skills/` is updated in the same PR if you changed `tests/**`, `.github/workflows/**`, `.github/actions/**`, or `scripts/**`.
- [ ] Scenario counts are updated in `docs/skills/test-authoring/suite-map/SKILL.md` and `docs/qa-review.md` if totals changed.
- [ ] PR title follows Conventional Commits (`feat`, `fix`, `docs`, `ci`, `refactor`, `test`, `build`, `chore`).
- [ ] Every AI-authored commit includes both attribution trailers:

```text
Assisted-by: <Model> via <runtime>
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## Human decision gates

Stop and request human input when you are:

- Creating a new suite or changing CI interfaces/inputs.
- Touching secrets in CI, cosign, new third-party actions, or expanded `permissions:`.
- Removing or renaming `e2e.yml` inputs that downstream repos depend on.
- Ready to merge (always use merge queue + green CI).

See `docs/skills/meta/human-gates/SKILL.md` for full examples.
