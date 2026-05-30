# testsuite

Canonical home for **Bluefin GUI/system test content** (behave + qecore-headless + dogtail) and shared step libraries.

## Repository split (normalized)

| Concern | Canonical repo |
|---|---|
| Hardware/lab infrastructure (ghost, exo-1, ArgoCD, KubeVirt, manifests, CronWorkflows) | `projectbluefin/testing-lab` |
| Test framework and suite content (feature files, steps, qecore/dogtail patterns) | `projectbluefin/testsuite` |

## Test stack

| Layer | Tool | Purpose |
|---|---|---|
| BDD runner | behave | Gherkin scenarios and step binding |
| Session bridge | qecore-headless | Wayland/DBus session bootstrap |
| GUI automation | dogtail (AT-SPI) | Accessibility-tree interactions |
| Wayland bridge | gnome-ponytail-daemon | Coordinate injection support |
| Shell bridge | `org.gnome.Shell.Eval` | GNOME 50+ top-bar fallback path |

## Working in this repo

```bash
just lint        # validate Argo manifests
just list-stubs  # inspect not-yet-implemented scenarios
```

Authoring rules, patterns, and skill docs → **`docs/skills/`**  
Start with `docs/skills/index.md`.

## Image tags

| Tag | Image |
|---|---|
| `latest` | `ghcr.io/ublue-os/bluefin:latest` |
| `lts` | `ghcr.io/ublue-os/bluefin:lts` |

`gts` and `lts-hwe` are invalid for Bluefin.

