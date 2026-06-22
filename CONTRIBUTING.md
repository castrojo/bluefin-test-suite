# Contributing to testsuite

This is the test framework and suite for GNOME-based bootc images. It runs headless GNOME automation using behave + qecore + dogtail, plus SSH-based system health checks.

**358 scenarios across 48 feature files.** This repo is agent-first — AI agents are primary contributors. See the [agentic factory section in README.md](README.md#agentic-factory).

## Where things live

| Concern | Repo |
|---|---|
| Test content (feature files, step definitions, shared helpers) | `projectbluefin/testsuite` (this repo) |
| Infrastructure (ArgoCD, KubeVirt, cluster manifests) | `projectbluefin/testing-lab` |

## Suites at a glance

| Suite | Mode | Purpose |
|---|---|---|
| `smoke` | GUI (qecore/dogtail) | Core GNOME functionality, MIME handlers, accessibility, desktop identity |
| `common` | SSH | Portable system health: Flatpak, portals, polkit, shell, ujust, immutability |
| `vanilla-gnome` | GUI | Upstream GNOME OS baseline for comparison |
| `developer` | GUI | Homebrew/Ptyxis on developer variant |
| `dx` | SSH+GUI | VS Code, distrobox, JupyterLab, mise |
| `software` | SSH+GUI | Bazaar app store health and config integrity |
| `lifecycle` | SSH | bootc upgrade/rollback/migration |
| `security` | SSH | cosign signature verification |
| `hardware` | SSH | udev rules syntax, emulated peripherals |
| `bazzite` | GUI | Bazzite-specific extensions and shell |
| `flatcar` | SSH | Flatcar OS boot and lifecycle |

The `smoke` and `common` suites are suitable for any GNOME bootc image — no Bluefin-specific knowledge required.

## Local setup

```bash
pip install behave qecore dogtail
```

> `qecore-headless` is the runner binary installed by the `qecore` package — do not install it separately.

Full end-to-end GUI runs require a live **Wayland + AT-SPI** session, which is not feasible on most contributor workstations. SSH-based suites (`common`, `security`, `hardware`, `lifecycle`) can be run manually against a VM you control. For most changes, use the GitHub Action reusable workflow (see README).

[`gnome-ponytail-daemon`](https://github.com/dogtail/gnome-ponytail-daemon) is a Wayland coordinate bridge that must be **baked into the image under test** — it is not a local pip install. Only required for GUI suites.

## Validation (run before every PR)

```bash
ruff check tests/ --select E,F,W --ignore E501   # lint
just list-stubs                                    # check for unimplemented @future scenarios
```

CI runs `ruff check` and `behave --dry-run` across all suites. If you add a step phrase to a `.feature` file you **must** implement the `@step` before pushing.

## Full contributing guide

Authoring patterns, step conventions, skill docs, and the full contributor guide are in **[`docs/skills/`](docs/skills/)** — start with [`docs/skills/index.md`](docs/skills/index.md).

## PRs target `main`

The `main` branch is protected. Open a PR with a descriptive title following [Conventional Commits](https://www.conventionalcommits.org/) format; CI must be green before merge.
