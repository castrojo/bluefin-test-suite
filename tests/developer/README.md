# developer test suite

Tests for Bluefin developer tooling — Ptyxis terminal, micro editor, Podman, and Homebrew.

## Coverage

| Feature file | Coverage |
|---|---|
| `ptyxis.feature` | Ptyxis terminal opens, accepts input, renders output |
| `podman.feature` | Podman CLI available, `podman run hello-world` |
| `brew.feature` | Homebrew (`brew`) in PATH, `brew --version` |

## Image

| Variant | Image ref |
|---|---|
| Bluefin (latest) | `ghcr.io/ublue-os/bluefin:latest` |
| Bluefin (GTS) | `ghcr.io/ublue-os/bluefin:gts` |
| Bluefin (LTS) | `ghcr.io/ublue-os/bluefin:lts` |

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bluefin:latest
  suites: developer
```

## Prerequisites

- `gnome-ponytail-daemon` must be in the image
- Image must be a bootc/ostree image

## Desktop Screenshot

After every run, a fastfetch screenshot is pushed to GHCR as an OCI artifact:

```sh
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:developer-latest
```

This is the canonical example desktop screenshot for Bluefin images tested by this suite.
