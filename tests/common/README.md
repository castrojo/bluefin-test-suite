# common test suite

SSH-mode portable health gate for any GNOME bootc image — Flatpak, portals, polkit, shell, and immutability.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/<image-org>/bluefin:latest
  suites: common
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/behave/SKILL.md`
