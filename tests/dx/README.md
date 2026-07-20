# dx test suite

Bluefin DX (developer experience) variant — GPU tools, distrobox, JupyterLab, mise, and Podman Desktop.

## Run via GitHub Action

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/<readonly-upstream>/bluefin-dx:latest
  suites: dx
```

## Related skills

- Skill index: `docs/skills/index.md`
- `test-authoring/behave/SKILL.md`
