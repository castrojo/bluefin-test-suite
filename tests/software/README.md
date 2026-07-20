# software test suite

GNOME Software and Bazaar (Bluefin software center) coverage.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/<image-org>/bluefin:testing
  suites: software
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/behave/SKILL.md`
- `test-authoring/gnome/SKILL.md`
