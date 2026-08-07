# developer test suite

Bluefin developer tooling — Ptyxis terminal, Podman, Homebrew, and bctl (bluefinctl).

`bctl.feature` scenarios are `@pending`: bctl is installed via Homebrew, and
`e2e.yml` masks `brew-setup.service` in CI, so bctl is never provisioned there
today. See `projectbluefin/testsuite#487`.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/<readonly-upstream>/bluefin:latest
  suites: developer
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/gnome/SKILL.md`
- `test-authoring/behave/SKILL.md`
