# vanilla gnome test suite

Upstream GNOME baseline suite for comparison against downstream images.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: quay.io/fedora/fedora-bootc:latest
  suites: vanilla-gnome
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/gnome/SKILL.md`
