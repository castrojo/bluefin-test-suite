---
name: flatpak-screenshots
description: "How to request and retrieve Flatpak app screenshots from the e2e workflow. Load when configuring screenshot_flatpaks or writing release workflows that consume screenshots."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

# Flatpak Screenshot Gallery

The `e2e.yml` reusable workflow can launch-and-screenshot any Flatpak app that is
installed in the test image. This is useful for **application authors** who want
visual evidence of their app running correctly on Bluefin, or who want a
ready-made desktop screenshot for release notes or changelogs.

## How it works

1. After the behave test suite completes, the workflow SSHes back into the VM.
2. For each requested app, it calls `screenshot_cli.py` inside the runner container
   (same GNOME session, same D-Bus access as the tests).
3. Each app is launched via `flatpak run <app-id>` (or `gtk-launch` for desktop apps),
   held open for a few seconds, then screenshotted via `GNOME Shell.Eval`.
4. PNGs land in the results artifact alongside test screenshots.
5. Each PNG is also pushed to GHCR as an OCI artifact with a stable per-app tag.

## Workflow input

```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@main
with:
  image: ghcr.io/<readonly-upstream>/bluefin:latest
  suites: smoke
  screenshot_flatpaks: "org.gnome.Calculator,io.github.kolunmi.Bazaar,org.mozilla.firefox"
```

`screenshot_flatpaks` is a **comma-separated list of Flatpak app IDs**. Apps that are
not installed in the image are skipped (the step continues with the next app).

## Pulling a screenshot

After a successful run, pull any app's screenshot with `oras`:

```sh
# Stable tag — updated on every passing run for this image
oras pull ghcr.io/<image-org>/testsuite/desktop-screenshot:flatpak-org-gnome-calculator-latest

# Or check the job summary for the immutable per-run ref
```

Tag format: `flatpak-<app-id-slug>-latest`
where `<app-id-slug>` is the app ID lowercased with dots/underscores replaced by dashes.

| App ID | Tag |
|--------|-----|
| `org.gnome.Calculator` | `flatpak-org-gnome-calculator-latest` |
| `io.github.kolunmi.Bazaar` | `flatpak-io-github-kolunmi-bazaar-latest` |
| `org.mozilla.firefox` | `flatpak-org-mozilla-firefox-latest` |

## Using in release workflows

```yaml
- name: Pull desktop screenshot
  run: |
    oras pull ghcr.io/<image-org>/testsuite/desktop-screenshot:flatpak-io-github-kolunmi-bazaar-latest
    mv desktop-screenshot.png bazaar-on-bluefin.png
```

The image registry is public-read; no authentication needed to pull.

## Customising wait time

Set the `SCREENSHOT_APP_WAIT` environment variable (seconds, default `4`) if your
app needs longer to render:

```yaml
# In the workflow that calls e2e.yml, set a repo-level or job-level env var
# (not yet exposed as a workflow input — open an issue if you need this)
```

## How the screenshot is taken

`screenshot_cli.py` uses `tests/shared/screenshot.py` which calls:

```
gdbus call --session \
  --dest org.gnome.Shell \
  --object-path /org/gnome/Shell \
  --method org.gnome.Shell.Eval \
  "Shell.Screenshot API JS snippet"
```

This is the same mechanism used by the behave suites for failure screenshots, so
the image quality and crop are identical.

## Job summary

The workflow job summary shows a **Flatpak Screenshot Gallery** table listing each
app and its `oras pull` command after a run that included `screenshot_flatpaks`.
