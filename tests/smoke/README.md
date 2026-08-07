# smoke test suite

Core GNOME Shell smoke tests — runs on every Bluefin image variant.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/ublue-os/bluefin:latest
  suites: smoke
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/gnome/SKILL.md`
