# Contributing to testsuite

This repo is the test framework and suite for GNOME-based bootc images. It runs headless GNOME automation with behave + qecore + dogtail, plus SSH-based system health checks.

| Concern | Repo |
|---|---|
| Test content (features, steps, helpers) | `testsuite` (this repo) |
| Infrastructure (ArgoCD, KubeVirt, manifests) | `testing-lab` |

## Suites at a glance

| Suite | Mode | Purpose |
|---|---|---|
| `smoke` | GUI (qecore/dogtail) | Core GNOME, MIME handlers, accessibility |
| `common` | SSH | Portable system health: Flatpak, portals, polkit, shell |
| `vanilla-gnome` | GUI | Upstream GNOME OS baseline |
| `developer` | GUI | Homebrew/Ptyxis on developer variant |
| `dx` | SSH+GUI | VS Code, distrobox, JupyterLab, mise |
| `software` | SSH+GUI | Bazaar app store and Flatpak CLI health |
| `lifecycle` | SSH | bootc upgrade/rollback/migration |
| `security` | SSH | cosign signature verification |
| `hardware` | SSH | udev rules, emulated peripherals |
| `bazzite` | GUI | Bazzite-specific extensions |
| `flatcar` | SSH | Flatcar OS boot and lifecycle |

## Local setup

```bash
pip install behave qecore dogtail
```

> `qecore-headless` is the runner binary installed by `qecore` — do not install it separately.

Full GUI runs require a live Wayland + AT-SPI session. For most changes, use the GitHub Action workflow.

## Validation (run before every PR)

```bash
ruff check tests/ --select E,F,W --ignore E501   # lint
behave --dry-run tests/<suite>/features           # if you touched .feature files
python3 -m pytest tests/unit/ -q                  # unit tests
just list-stubs                                    # unimplemented @future scenarios
```

## Agent rules and patterns

For the agent entry point, mandatory gates, and skill loading rules, see `AGENTS.md` and `docs/skills/index.md`.

## PRs target `main`

Open a PR with a [Conventional Commits](https://www.conventionalcommits.org/) title. CI must be green before enqueueing. This repo uses a merge queue; enqueue with:

```bash
gh pr merge <NUMBER> --repo <image-org>/testsuite --squash --auto
```
