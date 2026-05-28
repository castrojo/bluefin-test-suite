# testsuite

Canonical home for **Bluefin GUI/system test content** (behave + qecore-headless + dogtail) and shared step libraries.

## Repository split (normalized)

| Concern | Canonical repo |
|---|---|
| Hardware/lab infrastructure (ghost, exo-1, ArgoCD, KubeVirt, manifests, CronWorkflows) | `projectbluefin/testing-lab` |
| Test framework and suite content (feature files, steps, qecore/dogtail patterns) | `projectbluefin/testsuite` |

This repo keeps some infra files for transition compatibility, but **new infrastructure work belongs in `testing-lab`**.

## Test stack

| Layer | Tool | Purpose |
|---|---|---|
| BDD runner | behave | Gherkin scenarios and step binding |
| Session bridge | qecore-headless | Wayland/DBus session bootstrap |
| GUI automation | dogtail (AT-SPI) | Accessibility-tree interactions |
| Wayland bridge | gnome-ponytail-daemon | Coordinate injection support |
| Shell bridge | `org.gnome.Shell.Eval` | GNOME 50+ top-bar fallback path |

## Current suite map

`tests/` currently contains:
- `smoke`, `developer`, `software`, `flatcar`
- `lifecycle`, `security`, `dx`, `nvidia`, `hardware`, `vanilla-gnome`
- shared step utilities in `tests/shared/`

## Working in this repo

```bash
# Validate Argo manifests in this repo
just lint

# Inspect not-yet-implemented scenarios
just list-stubs
```

Execution against lab hardware is typically launched from `testing-lab` (or equivalent Argo submission path), which consumes tests from this repository.

## Authoring rules (important)

1. Non-GUI / SSH-driven suites should reuse shared SSH helpers from `tests/shared/ssh_steps.py`.
2. Under `tests/smoke/features/steps/`, avoid duplicate `@step()` patterns across files (behave loads all step modules together).
3. Dogtail 4.16: do not pass `requireResult` to `findChild`; use `findChildren` for no-raise checks and `findChild(..., retry=False)` for fast-fail.
4. For GNOME Shell 50+ top-bar interactions, use `Shell.Eval` path where AT-SPI nodes are not exposed.

## Image tags

| Tag | Image |
|---|---|
| `latest` | `ghcr.io/ublue-os/bluefin:latest` |
| `lts` | `ghcr.io/ublue-os/bluefin:lts` |

`gts` and `lts-hwe` are invalid for Bluefin.

## Related docs

- `RUNBOOK.md` — test authoring and operational guidance for this repo
- `PLAN.md` — normalization plan/status for testsuite vs testing-lab boundaries
