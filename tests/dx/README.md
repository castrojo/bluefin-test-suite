# dx test suite

Tests for Bluefin DX (developer experience) variant — GPU tools, distrobox, JupyterLab, mise, and Podman Desktop.

## Coverage

| Feature file | Coverage |
|---|---|
| `dx_tools.feature` | distrobox, mise, JupyterLab, Podman Desktop (Flatpak) |

## Image

| Variant | Image ref |
|---|---|
| Bluefin DX (latest) | `ghcr.io/ublue-os/bluefin-dx:latest` |
| Bluefin DX (GTS) | `ghcr.io/ublue-os/bluefin-dx:gts` |
| Bluefin DX (LTS) | `ghcr.io/ublue-os/bluefin-dx:lts` |

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bluefin-dx:latest
  suites: dx
```

## Prerequisites

- `gnome-ponytail-daemon` must be in the image
- Image must be a bootc/ostree image

## Desktop Screenshot

After every run, a fastfetch screenshot is pushed to GHCR as an OCI artifact:

```sh
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:dx-latest
```

This is the canonical example desktop screenshot for Bluefin DX images tested by this suite.
