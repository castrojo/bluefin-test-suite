# software test suite

Tests for GNOME Software (`org.gnome.Software`) — Flatpak browsing, install/remove, and update flows.

Runs on `gnomeos` (upstream GNOME OS) where `gnome-software` ships as an RPM. Bluefin ships
Bazaar (`io.github.kolunmi.Bazaar`) instead; this suite is intentionally upstream-only.

## Coverage

| Feature file | Coverage |
|---|---|
| `flatpak.feature` | Browse, install, and remove a Flatpak via gnome-software |

## Image

| Variant | Image ref |
|---|---|
| GNOME OS (nightly) | `ghcr.io/gnomeos/os:nightly` |

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/gnomeos/os:nightly
  suites: software
```

## Prerequisites

- `gnome-ponytail-daemon` must be in the image
- Image must be a bootc/ostree image

## Desktop Screenshot

After every run, a fastfetch screenshot is pushed to GHCR as an OCI artifact:

```sh
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:software-latest
```

This is the canonical example desktop screenshot for GNOME OS images tested by this suite.
