# homebrew test suite

Active native-systemd lane for Bluefin's managed Homebrew stack: Brew CLI
operations, bluefinctl (`bctl`) headless subcommands, and ChairLift's managed
cask, desktop integration, and configured UI. All scenarios in this suite are
active — unlike `developer`, this suite does not carry `@pending` Brew/bctl
coverage.

## Why this suite is separate from `developer`

Brew and bctl scenarios were originally written in `developer` but stayed
`@pending` there because `e2e.yml` masks `brew-setup.service` in the QEMU CI
lane for boot speed (#487). This suite targets a systemd-booted image where
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
  download-only bootc staging contract. See
  [`docs/skills/test-authoring/behave/references/homebrew-chairlift.md`](../../docs/skills/test-authoring/behave/references/homebrew-chairlift.md)
  for the accessible-label evidence and what upstream ChairLift already
  covers on its own.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/projectbluefin/bluefin:testing
  suites: homebrew
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/behave/SKILL.md`
- `test-authoring/behave/references/homebrew-chairlift.md`
- `test-authoring/gnome/SKILL.md`
