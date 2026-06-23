# testsuite
[![codecov](https://codecov.io/gh/projectbluefin/testsuite/branch/main/graph/badge.svg)](https://codecov.io/gh/projectbluefin/testsuite)

> Enslave the oppressors

Automated behave + qecore-headless + dogtail and shared libraries for testing GNOME-based bootc images. Totally headless, Kubernetes-friendly.

**386 scenarios across 52 feature files.** Covers GUI automation, SSH-based health checks, and system integrity assertions for any GNOME bootc image.

- GNOME 50+
- Image-specific suites: Bluefin, Bazzite, Dakota, vanilla GNOME OS, Flatcar
- Any GNOME-based bootc image can use the `common` and `smoke` suites as a portable health gate
- Agent-first: autonomous AI agents are primary contributors to GNOME 50 test coverage

## Where this repo fits

```
projectbluefin/bluefin   ──┐
projectbluefin/bluefin-lts ┼──▶ images ──▶ testsuite (e2e gate) ──▶ promotion
projectbluefin/dakota    ──┘

Any GNOME bootc image ──────────────────▶ testsuite (smoke + common)
```

| Concern | Canonical repo |
|---|---|
| Infrastructure (ArgoCD, KubeVirt, manifests, CronWorkflows) | `projectbluefin/testing-lab` |
| Test framework and suite content (feature files, steps, qecore/dogtail patterns) | `projectbluefin/testsuite` |

## Test stack

| Layer | Tool | Purpose |
|---|---|---|
| BDD runner | behave | Gherkin scenarios and step binding |
| Session bridge | qecore-headless | Wayland/DBus session bootstrap |
| GUI automation | dogtail (AT-SPI) | Accessibility-tree interactions |
| Wayland bridge | gnome-ponytail-daemon | Coordinate injection support |
| Shell bridge | `org.gnome.Shell.Eval` | GNOME 50+ top-bar fallback path |
| SSH bridge | shared SSH steps | Out-of-VM system health assertions |

## What is tested

### Smoke suite (GUI — runs inside the VM via qecore-headless)
Core GNOME functionality verified visually against a live Wayland session:
- GNOME Shell, Settings panels, Notifications, Calculator, Text Editor, Files (Nautilus)
- Firefox launch via Flatpak
- MIME handler registration — HTML → Firefox, PDF → Papers, PNG → Loupe, video → Totem
- GNOME Accessibility infrastructure (AT-SPI daemon, high-contrast toggle, a11y Settings panel)
- Bluefin desktop identity — Wayland session, hardware acceleration, Dash to Dock, system tray
- GNOME extensions presence

### Common suite (SSH — runs against the VM over SSH)
Portable health checks suitable for any GNOME bootc image:
- **Flatpak model**: Flathub-only remote, no Fedora remote, required system apps present
- **Flatpak state**: correct remote configuration after first boot
- **XDG portal health**: `xdg-desktop-portal`, `xdg-desktop-portal-gnome` active; D-Bus interface reachable
- **XDG portal integration**: FileChooser, Screenshot, OpenURI, Notification interfaces introspectable
- **Container runtime**: podman available, storage driver set, rootless socket active, can run a container
- **Polkit rules**: custom rules present and parseable, daemon running, no syntax errors
- **Shell environment**: `/etc/environment` present, modern CLI tools (zsh, fish, fzf, bat, eza, starship)
- **Shell sourcing**: shell rc files source cleanly without errors
- **System scripts**: `ujust`, `ublue-image-info`, `ublue-system-setup`, `ublue-user-setup`, `bootc`
- **ujust recipes**: non-destructive recipe smoke tests (check-local-overrides, logs-this-boot, bios-info, changelogs)
- **GSettings/dconf defaults**: custom-command-list extension in defaults, locked keys enforced, keybindings configured
- **Immutable OS integrity**: no layered RPMs, `/usr` mounted read-only, bootc status reports a pinned image
- **Desktop entries**: no graphical RPM apps pointing to `/usr/bin` (Flatpak-only model)
- **Signing and security**: image signing policy assertions

### Other suites
- **hardware**: udev rules syntax validation, emulated peripherals
- **software**: Bazaar app store launch, search, config YAML integrity, Flatpak CLI health
- **developer**: Homebrew/Ptyxis on Bluefin developer variant
- **dx**: VS Code, distrobox, JupyterLab, mise on DX variant
- **lifecycle**: bootc upgrade / rollback / migration
- **security**: cosign signature verification
- **vanilla-gnome**: upstream GNOME OS baseline (comparison against Bluefin smoke)
- **bazzite**: Bazzite-specific extensions and shell behavior
- **flatcar**: Flatcar OS boot and lifecycle

## Working in this repo

```bash
just lint        # validate Argo manifests
just list-stubs  # inspect not-yet-implemented scenarios
```

Authoring rules, patterns, and skill docs → **`docs/skills/`**  
Start with `docs/skills/index.md`.

## Agentic factory

This repo is **agent-first**: AI agents are the primary authors of GNOME 50 test coverage. Every agent session produces two outputs — the work (PR) and the learning (skill doc update). The skill docs in `docs/skills/` are the institutional memory that makes each agent session start smarter than the last.

Agents can file issues and submit PRs directly without human gating (within the gates defined in `docs/skills/human-gates.md`). The `@future` tag marks scenarios awaiting implementation — run `just list-stubs` to see the current list. The `docs/skills/` tree routes each task type to the right patterns and avoids re-discovering the same gotchas.

## Local development

- CI uses **Python 3.14** (`actions/setup-python` in `.github/workflows/pr-validate.yml` and `.github/workflows/unit-tests.yml`), so use Python 3.14 locally as well.
- Install the local Python pieces with `pip install behave qecore dogtail` (`qecore-headless` is the runner binary installed by the `qecore` package, not a separate pip package).
- [`gnome-ponytail-daemon`](https://github.com/dogtail/gnome-ponytail-daemon) is **not** a local pip install; it must already be baked into the image under test.
- Full end-to-end runs still require a live **Wayland + AT-SPI** session, so they are not feasible for most contributors on a normal workstation. For most changes, the recommended execution path is the GitHub Action workflow below.

## Using as a GitHub Action

Any GNOME-based OS built as a **bootc/ostree image** can run this test suite as a PR gate on standard `ubuntu-latest` runners — no self-hosted hardware, no Argo, no ghost required.

### For other bootc image maintainers

If you are building a GNOME-based bootc image and want to add automated testing, the `common` and `smoke` suites are designed to work against any GNOME bootc image. The `common` suite runs entirely over SSH and validates system invariants that any well-formed immutable GNOME image should satisfy:

- Flathub is the only Flatpak remote
- XDG portals are healthy
- Container runtime is functional (podman)
- Polkit rules are present and parseable
- The OS is truly immutable (no layered RPMs, `/usr` read-only)
- Standard system scripts are present and executable
- bootc reports a pinned image

The `smoke` suite runs GUI automation over a live Wayland session and validates core GNOME functionality. Both suites are safe to run against any GNOME bootc image without Bluefin-specific knowledge.

**Minimum image requirements:**
- `bootc install to-disk` compatible OCI image
- `gnome-ponytail-daemon` baked in (for smoke suite; Wayland coordinate bridge)
- GNOME 40+ with GDM autologin support

### Quick start — reusable workflow

Add to your repo's `.github/workflows/e2e.yml`:

```yaml
name: E2E Tests
on:
  pull_request:

jobs:
  test:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@v1
    with:
      image: ghcr.io/myorg/myimage:latest   # your bootc OCI image
      suites: smoke,common                   # smoke | common | developer | dx | software | vanilla-gnome
```

**Pin to `@v1`** — testsuite auto-updates the `v1` tag on every merge to `main`. Renovate does not need to manage this pin.

If you wrap the reusable workflow in a `workflow_dispatch` to test an unreleased testsuite branch, resolve `test_ref` in the wrapper (`${{ github.event.inputs.test_ref || github.ref_name }}`) and pass it through. Do **not** rely on `github.ref_name` inside `e2e.yml`; in `workflow_call` it resolves to `main`.

### Advanced — composite action directly

For full control over artifact naming, concurrency, or triggering:

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - name: Run GNOME e2e
        id: test
        uses: projectbluefin/testsuite/.github/actions/gnome-e2e@v1
        with:
          image: ghcr.io/myorg/myimage:latest
          suite: smoke

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results-${{ github.run_id }}
          path: results/

      - name: Fail on test failures
        if: steps.test.outputs.behave-rc != '0'
        run: exit 1
```

### Suite sharding

`suites: smoke` and `suites: common` each automatically expand into two parallel jobs (`smoke-a` + `smoke-b`, `common-a` + `common-b`), cutting wall time roughly in half. New `.feature` files added to these suites are picked up automatically — no manual shard configuration needed.

### Requirements

- OCI image must be a **bootc/ostree** image (uses `bootc install to-disk`)
- **`gnome-ponytail-daemon`** must be baked into the image for smoke suite (Wayland coordinate bridge)
- Supported suites via GHA: `smoke`, `common`, `developer`, `dx`, `software`, `vanilla-gnome`, `bazzite`, `lifecycle`
- `security` and `hardware` (SSH-only mode) are not yet in the GHA action

### Inputs

| Input | Default | Description |
|---|---|---|
| `image` | — | OCI image ref to test (required) |
| `suites` | `smoke` | Comma-separated suite names |
| `test_ref` | `main` | `projectbluefin/testsuite` git ref for test content |
| `skip_native_apps` | `false` | Skip `@native_app` scenarios (apps not in all variants) |
| `screenshot_flatpaks` | `""` | Flatpak app IDs to launch-and-screenshot after the test run |
| `chunked_enabled` | `false` | Enable `@zstd_chunked` lifecycle scenarios |
| `memory` | `4096` | VM RAM in MB |
| `cpus` | `4` | VM CPU count |
| `free-disk-space` | `true` | Run disk cleanup before provisioning |

## Image tags

| Tag | Image |
|---|---|
| `latest` | `ghcr.io/ublue-os/bluefin:latest` |
| `lts` | `ghcr.io/ublue-os/bluefin:lts` |

`gts` and `lts-hwe` are invalid for Bluefin.

## Local development

- CI uses **Python 3.14** (`actions/setup-python` in `.github/workflows/pr-validate.yml` and `.github/workflows/unit-tests.yml`), so use Python 3.14 locally as well.
- Install the local Python pieces with `pip install behave qecore dogtail` (`qecore-headless` is the runner binary installed by the `qecore` package, not a separate pip package).
- [`gnome-ponytail-daemon`](https://github.com/dogtail/gnome-ponytail-daemon) is **not** a local pip install; it must already be baked into the image under test.
- Full end-to-end runs still require a live **Wayland + AT-SPI** session, so they are not feasible for most contributors on a normal workstation. For most changes, the recommended execution path is the GitHub Action workflow above.

