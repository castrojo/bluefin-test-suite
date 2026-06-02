# common test suite

SSH-mode behave suite for validating the `projectbluefin/common` OCI layer as shipped in Bluefin images.

## Coverage

- dconf / GSettings defaults and locked keys
- `ujust`, `ublue-system-setup`, `ublue-user-setup`, `ublue-image-info.sh`
- Desktop entry and MIME integration smoke
- Shell availability (`zsh`, `fish`) and `/etc/environment`

## Image

Run against any Bluefin image that includes the common layer, for example:

- `ghcr.io/projectbluefin/bluefin:latest`
- `ghcr.io/projectbluefin/bluefin-dx:latest`
- `ghcr.io/projectbluefin/bluefin-nvidia:latest`

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/projectbluefin/bluefin:latest
  suites: common
```

## Relationship to `projectbluefin/common`

`projectbluefin/common` builds the shared OCI layer; this suite validates that the layer's user-facing artifacts are actually present and functional once composed into a Bluefin image.
