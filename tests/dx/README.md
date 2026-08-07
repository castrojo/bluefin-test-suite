# dx test suite

Bluefin DX (developer experience) variant — GPU tools, distrobox, JupyterLab, mise, and Podman Desktop.

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
with:
  image: ghcr.io/ublue-os/bluefin-dx:latest
  suites: dx
```

## Related skills

- Skill router: `docs/SKILL.md`
- `test-authoring/behave/SKILL.md`
