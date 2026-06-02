# vanilla-gnome — upstream GNOME baseline suite

Tests for stock GNOME Shell with no distro customisation. Designed to run on
**any** bootc/ostree GNOME image — Fedora Silverblue, GNOME OS, or any upstream spin.

## Purpose

Acts as the upstream comparison baseline:

| Result | Meaning |
|---|---|
| `smoke` fails, `vanilla-gnome` passes | Downstream (Bluefin/Bazzite) regression |
| `smoke` fails, `vanilla-gnome` fails | Upstream GNOME issue |
| `vanilla-gnome` fails on Silverblue | Bug in this test suite |

## Run via GitHub Action

```yaml
# On Fedora Silverblue
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: quay.io/fedora/fedora-bootc:latest
  suites: vanilla-gnome

# On Bazzite (verify extensions don't break core GNOME)
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bazzite:latest
  suites: vanilla-gnome

# On Bluefin
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bluefin:latest
  suites: vanilla-gnome
```

## Silverblue / Fedora bootc

`vanilla-gnome` is the upstream GNOME baseline for any bootc GNOME image, including
`quay.io/fedora/fedora-bootc:latest`. Use it to validate Fedora Silverblue-style
GNOME behaviour without Bluefin customisation, then compare against downstream suites.

## Prerequisites

- `gnome-ponytail-daemon` must be in the image
- Image must be a bootc/ostree image

## Tracking

Epic: projectbluefin/testsuite#41
