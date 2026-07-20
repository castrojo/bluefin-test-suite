# developer test suite

Bluefin developer tooling — Ptyxis terminal, Podman, and Homebrew.

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
