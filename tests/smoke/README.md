# smoke test suite

Core Bluefin GNOME Shell smoke tests — runs on every Bluefin image variant.

## Coverage

| Feature file | Coverage |
|---|---|
| `gnome_shell.feature` | Panel, Logo Menu, Quick Settings, overview |
| `gnome_extensions.feature` | All enabled extensions present and loaded |
| `gnome_apps.feature` | Core GNOME apps launch and render |
| `gnome_calculator.feature` | Calculator arithmetic and keyboard input |
| `gnome_files.feature` | Files (Nautilus) open, navigate |
| `gnome_notifications.feature` | Notification banners and Do Not Disturb |
| `gnome_settings.feature` | Settings app opens, panels accessible |
| `gnome_text_editor.feature` | Text Editor opens and accepts input |
| `firefox.feature` | Firefox launches (Flatpak) |
| `system_health.feature` | No failed systemd units, journal errors |

## Image

| Variant | Image ref |
|---|---|
| Bluefin (latest) | `ghcr.io/ublue-os/bluefin:latest` |
| Bluefin (GTS) | `ghcr.io/ublue-os/bluefin:gts` |
| Bluefin (LTS) | `ghcr.io/ublue-os/bluefin:lts` |
| Bluefin DX | `ghcr.io/ublue-os/bluefin-dx:latest` |
| Bluefin NVIDIA | `ghcr.io/ublue-os/bluefin-nvidia-open:latest` |

## Run via GitHub Action

```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/ublue-os/bluefin:latest
  suites: smoke
```

## Prerequisites

- `gnome-ponytail-daemon` must be in the image (Wayland coordinate bridge)
- Image must be a bootc/ostree image

## Desktop Screenshot

After every run, a fastfetch screenshot is pushed to GHCR as an OCI artifact:

```sh
oras pull ghcr.io/projectbluefin/testsuite/desktop-screenshot:smoke-latest
```

This is the canonical example desktop screenshot for Bluefin images tested by this suite.
