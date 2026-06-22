# software test suite

Tests for GNOME Software (`org.gnome.Software`) and Bluefin's Bazaar coverage.

Runs on `gnomeos` (upstream GNOME OS) where `gnome-software` ships as an RPM and on Bluefin
images where Bazaar (`io.github.kolunmi.Bazaar`) is the software center. The old GNOME Software
widget expectations remain quarantined while Bluefin-valid Bazaar coverage lives in dedicated
Bazaar feature files.

## Coverage

| Feature file | Coverage |
|---|---|
| `flatpak.feature` | Quarantined upstream GNOME Software smoke coverage kept for GNOME OS only |
| `bazaar.feature` | Active Bluefin Bazaar Flatpak presence / info / remote coverage |
| `bazaar_ui.feature` | Active Bluefin Bazaar UI launch / navigation / close coverage |

## Image

| Variant | Image ref |
|---|---|
| Bluefin | `ghcr.io/projectbluefin/bluefin:testing` |
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
