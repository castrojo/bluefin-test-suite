# smoke test suite

Core GNOME Shell smoke tests — runs on every Bluefin image variant.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/<readonly-upstream>/bluefin:latest
  suites: smoke
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/gnome/SKILL.md`
