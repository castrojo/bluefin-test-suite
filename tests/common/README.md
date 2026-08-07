# common test suite

SSH-mode portable health gate for any GNOME bootc image — Flatpak, portals, polkit, shell, and immutability.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/projectbluefin/bluefin:latest
  suites: common
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/behave/SKILL.md`
