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
  the system-wide desktop/icon integration `projectbluefin/common` ships (the
  cask's own `~/.local/share` artifacts are first-user-wins, so they are not
  asserted), the UI ChairLift renders for Bluefin's maintainer `config.yml`,
  and the authenticated, stage-only bootc contract: the privileged helper runs
  plain `bootc upgrade` and must never pass `--apply`, `--soft-reboot`,
  `--download-only`, or `--from-downloaded`. Only the two `@chairlift_ui` scenarios
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

This suite targets the lab's `run-systemd-container-tests` Argo
WorkflowTemplate **only** — a privileged, disposable Pod with systemd as PID 1,
not a VM and not the QEMU `e2e.yml` lane. `e2e.yml` masks
`brew-setup.service`, so Homebrew is never provisioned there and this suite
would fail on preconditions; do not add `suites: homebrew` to that workflow.

The lane must provide:

| Requirement | Why |
|---|---|
| `brew-setup.service` unmasked and started | provisions `/var/home/linuxbrew/.linuxbrew/bin/brew` |
| a systemd user manager for the test user, reachable at the `XDG_RUNTIME_DIR` the behave process sees | `brew-preinstall.service` is a **user** unit |

`before_all` verifies each of those instead of trusting them: it probes the
systemd user manager (`systemctl --user show --property=Version`), requires
`/var/home/linuxbrew/.linuxbrew/bin/brew` to exist and be executable (naming
`brew-setup.service` when it doesn't), then starts `brew-preinstall.service`
and asserts it actually completed (`active`/`exited`/`success`) rather than
just returning 0. It covers the shipped user unit rather than calling
`/usr/bin/brew-preinstall` directly. Failures also report `ConditionResult`
and `ExecMainStatus`: the unit carries `ConditionUser=!@system` and
`ConditionPathExists=/var/home/linuxbrew/.linuxbrew/bin/brew`, so an unmet
condition makes systemd *skip* it — `start` exits 0, `ActiveState=inactive`,
`Result=success`, and only `ConditionResult=no` distinguishes "skipped" from
"never asked to run".

`XDG_RUNTIME_DIR` is read for diagnostics but never rewritten. `systemctl
--user` resolves the manager through it (local transport,
`$XDG_RUNTIME_DIR/systemd/private`), so rewriting it from the suite would
probe a different manager than the one the lane started. It would *not*
relocate the accessibility or session bus — the lane pins those with absolute
`DBUS_SESSION_BUS_ADDRESS`/`AT_SPI_BUS_ADDRESS` values that do not follow
`XDG_RUNTIME_DIR` — which is exactly why the two must be kept consistent by
the layer that owns them: the lab template, not this suite.

Every one of those preconditions **fails the run with a nonzero exit** — a
missing cask, desktop file, or service is the regression under test, so
nothing here degrades into a skipped-green scenario.

## What the lab lane must add before this suite can run

Read from `projectbluefin/lab`'s live
`argo/workflow-templates/run-systemd-container-tests.yaml` (commit
`3b46b76fc`); every value below is what the template does **today**, not a
proposal:

| Runtime fact | Current value | Lines |
|---|---|---|
| Suite allowlist (runner script) | `smoke\|common\|developer\|software\|system`, else `exit 2` | 155 |
| Suite allowlist (in-target `run-behave.sh`) | same list, checked again | 233 |
| Test user | `bluefin-test`, uid/gid 1000, appended to `/etc/passwd` with home `/home/bluefin-test` | 202–205 |
| Behave invocation | `runuser -u bluefin-test -- env … qecore-headless … /workspace/run-behave.sh` | 263–274 |
| `HOME` | `/home/bluefin-test` | 266 |
| `XDG_RUNTIME_DIR` | `/home/bluefin-test/run` (created by `mkdir -p`, `chown 1000:1000`) | 267, 211, 214 |
| `DBUS_SESSION_BUS_ADDRESS` | `unix:path=/home/bluefin-test/run/bus` | 268 |
| `AT_SPI_BUS_ADDRESS` | `unix:path=/home/bluefin-test/run/bus` | 269 |
| Homebrew provisioning | none — `brew-setup.service` is neither unmasked nor started | — |
| systemd user manager | none — `runuser` starts no PAM/logind session, no lingering, no `user@1000.service` | — |

So Task 6 owes three things:

1. **Add `homebrew` to both allowlists.** One is not enough; the second `case`
   lives inside the heredoc that writes `/workspace/run-behave.sh`, and a suite
   that passes the first and fails the second exits 2 after the target Pod is
   already up.
2. **Provision Homebrew for this lane only.** Unmask and start
   `brew-setup.service` (or otherwise populate the prefix) before behave;
   `before_all` fails on the brew binary, naming that unit, when it is absent.
3. **Reconcile the qecore a11y/session bus with the systemd user-manager
   connection.** These are two different lookups over the same directory and
   the template currently satisfies only the first:
   - qecore/dogtail use the **absolute** `DBUS_SESSION_BUS_ADDRESS` and
     `AT_SPI_BUS_ADDRESS` above; they are independent of `XDG_RUNTIME_DIR`.
   - `systemctl --user` ignores those and uses `XDG_RUNTIME_DIR` (verified on
     systemd 260.2: a bogus `DBUS_SESSION_BUS_ADDRESS` still works, a bogus
     `XDG_RUNTIME_DIR` fails with `Failed to connect to user scope bus via
     local transport`).

   **Do not assume a literal path.** A manager started as `user@1000.service`
   through logind gets the runtime dir logind assigns it; a manager started
   directly can be given `/home/bluefin-test/run`. Either is fine. The
   invariant Task 6 must hold is that the `XDG_RUNTIME_DIR` exported to
   `runuser`/`qecore-headless` is the *same* directory the user manager uses
   (its `systemd/private` socket must be inside it), **and** that the two bus
   addresses still point at a live session bus after that choice. Changing one
   without the other yields either an unreachable manager (`before_all` fails
   loudly, as designed) or a dead a11y bus (every UI step fails at
   `_chairlift_root`).

## Run via the lab

> **Not runnable yet.** The three items above must land in
> `projectbluefin/lab` first; until then `suite=homebrew` exits 2 and the
> submission below does nothing.

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
