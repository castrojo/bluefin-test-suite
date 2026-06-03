# testsuite
> Enslave the oppressors

Automated behave + qecore-headless + dogtail and shared libraries for testing GNOME. Totally headless, k8s friendly. Help wanted!

- GNOME 50 
- Individual image tests for: Bazzite, Bluefin ... you?
- End Goal: GNOME 51 and autonomous agent maintenance of this testsuite

## Repository split (normalized)

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

## Working in this repo

```bash
just lint        # validate Argo manifests
just list-stubs  # inspect not-yet-implemented scenarios
```

Authoring rules, patterns, and skill docs → **`docs/skills/`**  
Start with `docs/skills/index.md`.

## Local development

- CI uses **Python 3.14** (`actions/setup-python` in `.github/workflows/pr-validate.yml` and `.github/workflows/unit-tests.yml`), so use Python 3.14 locally as well.
- Install the local Python pieces with `pip install behave qecore dogtail` (`qecore-headless` is the runner binary installed by the `qecore` package, not a separate pip package).
- [`gnome-ponytail-daemon`](https://github.com/dogtail/gnome-ponytail-daemon) is **not** a local pip install; it must already be baked into the image under test.
- Full end-to-end runs still require a live **Wayland + AT-SPI** session, so they are not feasible for most contributors on a normal workstation. For most changes, the recommended execution path is the GitHub Action workflow below.

## Using as a GitHub Action

Any GNOME-based OS built as a **bootc/ostree image** can run this test suite as a PR gate on standard `ubuntu-latest` runners — no self-hosted hardware, no Argo, no ghost required.

### Quick start — reusable workflow

Add to your repo's `.github/workflows/e2e.yml`:

```yaml
name: E2E Tests
on:
  pull_request:

jobs:
  test:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
    with:
      image: ghcr.io/myorg/myimage:latest   # your bootc OCI image
      suites: smoke                          # smoke | developer | dx | software | vanilla-gnome
```

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
        uses: projectbluefin/testsuite/.github/actions/gnome-e2e@main
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

### Requirements

- OCI image must be a **bootc/ostree** image (uses `bootc install to-disk`)
- **`gnome-ponytail-daemon`** must be baked into the image (Wayland coordinate bridge)
- Supported GUI suites: `smoke`, `developer`, `dx`, `software`, `vanilla-gnome`
- `lifecycle`, `security`, `hardware` use a different SSH-only mode (not yet in this action)

### Inputs

| Input | Default | Description |
|---|---|---|
| `image` | — | OCI image ref to test (required) |
| `suite` | `smoke` | Test suite name |
| `testsuite-ref` | action ref | `projectbluefin/testsuite` git ref for test content |
| `memory` | `4096` | VM RAM in MB |
| `cpus` | `4` | VM CPU count |
| `free-disk-space` | `true` | Run disk cleanup before provisioning |

## Image tags

| Tag | Image |
|---|---|
| `latest` | `ghcr.io/ublue-os/bluefin:latest` |
| `lts` | `ghcr.io/ublue-os/bluefin:lts` |

`gts` and `lts-hwe` are invalid for Bluefin.

