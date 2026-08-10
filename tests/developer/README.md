# developer test suite

Bluefin developer tooling — Ptyxis terminal and Podman Desktop.

Brew and bctl (bluefinctl) coverage moved to the dedicated
[`homebrew`](../homebrew/README.md) suite, which is active rather than
`@pending`: it targets a systemd-booted image with Homebrew actually
provisioned instead of the QEMU CI lane where `e2e.yml` masks
`brew-setup.service` (#487). The remaining `@pending` count in this suite is
Ptyxis-only, blocked on the AT-SPI restart issue tracked in #368.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/ublue-os/bluefin:latest
  suites: developer
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/gnome/SKILL.md`
- `test-authoring/behave/SKILL.md`
