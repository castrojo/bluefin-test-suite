# software test suite

GNOME Software and Bazaar (Bluefin software center) coverage.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/projectbluefin/bluefin:testing
  suites: software
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/behave/SKILL.md`
- `test-authoring/gnome/SKILL.md`
