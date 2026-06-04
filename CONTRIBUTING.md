# Contributing to testsuite

This is the test framework and suite for Project Bluefin. It runs headless GNOME automation using behave + qecore + dogtail. **Help wanted!**

## Where things live

| Concern | Repo |
|---|---|
| Test content (feature files, step definitions, shared helpers) | `projectbluefin/testsuite` (this repo) |
| Infrastructure (ArgoCD, KubeVirt, cluster manifests) | `projectbluefin/testing-lab` |

## Local setup

```bash
pip install behave qecore dogtail
```

> `qecore-headless` is the runner binary installed by the `qecore` package — do not install it separately.

Full end-to-end runs require a live **Wayland + AT-SPI** session, which is not feasible on most contributor workstations. For most changes, use the GitHub Action reusable workflow instead (see README).

[`gnome-ponytail-daemon`](https://github.com/dogtail/gnome-ponytail-daemon) is a Wayland coordinate bridge that must be **baked into the image under test** — it is not a local pip install.

## Validation (run before every PR)

```bash
just lint        # validate Argo manifests
just list-stubs  # check for unimplemented @future scenarios
```

CI runs `ruff check` and `behave --dry-run` across all suites. If you add a step phrase to a `.feature` file you **must** implement the `@step` before pushing.

## Full contributing guide

Authoring patterns, step conventions, skill docs, and the full contributor guide are in **[`docs/skills/`](docs/skills/)** — start with [`docs/skills/index.md`](docs/skills/index.md).

## PRs target `main`

The `main` branch is protected. Open a PR with a descriptive title; CI must be green before merge.
