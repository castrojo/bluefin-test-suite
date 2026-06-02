# Bazzite test suite

Tests for Bazzite-specific GNOME Shell behaviour and extensions.

## Image

| Variant | Image ref |
|---|---|
| Desktop (AMD/Intel) | `ghcr.io/ublue-os/bazzite:latest` |
| Desktop (NVIDIA) | `ghcr.io/ublue-os/bazzite-nvidia:latest` |

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bazzite:latest
  suites: bazzite
```

## Suites

| Feature file | Coverage |
|---|---|
| `bazzite_extensions.feature` | All 11 enabled extensions + 3 installed-not-enabled |
| `bazzite_shell.feature` | Logo Menu, Quick Settings, overview, coredump check |

## Prerequisites

- `gnome-ponytail-daemon` must be in the image (Wayland coordinate bridge)
- Image must be a bootc/ostree image (required by the `gnome-e2e` action)

## Enabled extensions (default)

```
logomenu@aryan_k
appindicatorsupport@rgcjonas.gmail.com
user-theme@gnome-shell-extensions.gcampax.github.com
gsconnect@andyholmes.github.io
blur-my-shell@aunetx
hotedge@jonathan.jdoda.ca
caffeine@patapon.info
add-to-steam@pupper.space
restartto@tiagoporsch.github.io
compiz-alike-magic-lamp-effect@hermes83.github.com
bazaar-integration@kolunmi.github.io
```

## Also installed (not default-enabled)

```
burn-my-windows@schneegans.github.com
desktop-cube@schneegans.github.com
compiz-windows-effect@hermes83.github.com
block-caribou-36@lxylxy123456.ercli.dev
```

## Desktop Screenshot

After every run, a fastfetch screenshot is pushed to GHCR as an OCI artifact:

```sh
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:bazzite-latest
```

This is the canonical example desktop screenshot for Bazzite images tested by this suite.

## Tracking

Epic: projectbluefin/testsuite#42
