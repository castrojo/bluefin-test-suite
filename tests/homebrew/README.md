# homebrew test suite

Active native-systemd lane for Bluefin's managed Homebrew stack: Brew CLI
operations, bluefinctl (`bctl`) headless subcommands, and ChairLift's managed
cask, desktop integration, and configured UI. All scenarios in this suite are
active — unlike `developer`, this suite does not carry `@pending` Brew/bctl
coverage.

## Why this suite is separate from `developer`

Brew and bctl scenarios were originally written in `developer` but stayed
`@pending` there because `e2e.yml` masks `brew-setup.service` in the QEMU CI
lane for boot speed (#487). This suite targets a systemd-booted target where
Homebrew is actually provisioned and `qecore` runs as `bluefin-test` — the
Brew/bctl scenarios are unchanged from `developer`, just active here instead
of pending.

## Scenario groups

- **Brew CLI** (`@brew`, 6 scenarios) — `brew --version`, `list`, `info`,
  `search`, `doctor`, and an install/uninstall round-trip, driven through
  Ptyxis terminal typing.
- **bctl (bluefinctl)** (`@bctl`, 4 scenarios) — `bctl status`, `update
  --check`, `devmode status`, and `--help`, driven the same way.
- **ChairLift** (`@chairlift`, 5 scenarios) — the managed Homebrew cask state,
  the user-scoped desktop/icon integration the cask installs, the UI ChairLift
  renders for Bluefin's maintainer `config.yml`, and the authenticated,
  download-only bootc staging contract. Only the two `@chairlift_ui` scenarios
  launch the app; the cask, desktop-file, and bootc-helper scenarios assert
  files and services directly so a launch failure cannot mask a packaging
  regression. When a UI step cannot find ChairLift's AT-SPI root, the failure
  message and the `after_scenario` hook both list the application names that
  *are* registered on the bus, so "never launched" is distinguishable from a
  real UI regression. See
  [`docs/skills/test-authoring/behave/references/homebrew-chairlift.md`](../../docs/skills/test-authoring/behave/references/homebrew-chairlift.md)
  for the accessible-label evidence and what upstream ChairLift already
  covers on its own.

## Lane contract

This suite runs **only** through the lab's `run-systemd-container-tests`
Argo WorkflowTemplate — a privileged, disposable Pod with systemd as PID 1,
not a VM and not the QEMU `e2e.yml` lane. `e2e.yml` masks
`brew-setup.service`, so Homebrew is never provisioned there and this suite
would fail on preconditions; do not add `suites: homebrew` to that workflow.

The lane must provide:

| Requirement | Why |
|---|---|
| `brew-setup.service` unmasked and started | provisions `/var/home/linuxbrew/.linuxbrew/bin/brew` |
| lingering enabled for the test user and its systemd user manager started | `brew-preinstall.service` is a **user** unit |

`before_all` verifies each of those instead of trusting them: it probes the
systemd user manager (`systemctl --user show --property=Version`), requires
`/var/home/linuxbrew/.linuxbrew/bin/brew` to exist and be executable (naming
`brew-setup.service` when it doesn't), then starts `brew-preinstall.service`
and asserts it actually completed (`active`/`exited`/`success`) rather than
just returning 0. It covers the shipped user unit rather than calling
`/usr/bin/brew-preinstall` directly.

`XDG_RUNTIME_DIR` is read for diagnostics but never rewritten — the suite
uses whatever the session already set, because relocating it would move the
accessibility and session bus out from under qecore.

Every one of those preconditions **fails the run with a nonzero exit** — a
missing cask, desktop file, or service is the regression under test, so
nothing here degrades into a skipped-green scenario.

## Run via the lab

> **Not runnable yet.** `run-systemd-container-tests.yaml` in
> `projectbluefin/lab` guards on `smoke|common|developer|software|system` in
> both of its suite `case` statements, so `suite=homebrew` exits 2 today, and
> the template does not unmask `brew-setup.service` or start the test user's
> systemd user manager. The lab-side change that adds `homebrew` to both
> allowlists and provisions Homebrew for this lane only must land before the
> submission below does anything.

```bash
: "${COMMON_PR:?export COMMON_PR to the common pull request number}"
IMAGE_TAG="$(gh api \
  'orgs/projectbluefin/packages/container/common/versions?per_page=50' \
  --jq '.[].metadata.container.tags[]?' \
  | grep "^e2e-pr-${COMMON_PR}-" \
  | head -1)"
argo submit -n argo \
  --from workflowtemplate/run-systemd-container-tests \
  -p image=ghcr.io/projectbluefin/common \
  -p image-tag="${IMAGE_TAG}" \
  -p suite=homebrew \
  -p variant=bluefin \
  -p testsuite-branch=main
```

`testsuite-branch=main` is the default: the lane runs the merged suite.
Override it with a feature branch (`-p testsuite-branch=test/<branch>`) only
to validate suite changes that are not on `main` yet — for example while
reviewing this suite's own PR. Reach for the override deliberately; a green
run against an unmerged branch does not tell you `main` is green.

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/behave/SKILL.md`
- `test-authoring/behave/references/homebrew-chairlift.md`
- `test-authoring/gnome/SKILL.md`
- `projectbluefin/lab`: `docs/skills/test-authoring/systemd-container-tests.md`
  and `docs/reference/WORKFLOWS.md` for the lane's own contract.
