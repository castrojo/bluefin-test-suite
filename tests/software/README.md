# software test suite

Tests for GNOME Software (`org.gnome.Software`) and the Bluefin Bazaar coverage gap.

Runs on `gnomeos` (upstream GNOME OS) where `gnome-software` ships as an RPM. Bluefin ships
Bazaar (`io.github.kolunmi.Bazaar`) instead, so the GNOME Software scenarios are quarantined and
Bazaar coverage stays `@pending` until issue #419 has a Bluefin-valid harness.

## Coverage

| Feature file | Coverage |
|---|---|
| `flatpak.feature` | Quarantined upstream GNOME Software smoke coverage kept for GNOME OS only |
| `bazaar.feature` | Pending placeholder for Bluefin Bazaar Flatpak management coverage |

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
