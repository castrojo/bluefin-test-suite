# testsuite

A cloud-native QA pipeline for [Project Bluefin](https://projectbluefin.io) desktops and [Flatcar Container Linux](https://www.flatcar.org).

Runs on a home-lab k3s cluster (**ghost**), driven by **Argo Workflows**, booting images as **KubeVirt VMs** from BIB golden disks (btrfs reflink clones), and executing GUI tests via **behave + qecore-headless + Dogtail (AT-SPI)** — no ISO installer, no pixel matching.

---

## Architecture

```
GitHub webhook / just run-tests / just run-titan-smoke
        │
        ▼
  Argo Workflow (argo namespace)
        │
        ├─ ensure-disk ───────────► BIB build golden disk (idempotent)
        │                           /var/tmp/bluefin-golden/<tag>/disk.raw
        │
        ├─ provision-bluefin-vm ──► btrfs reflink clone (~24ms CoW)
        │                           KubeVirt VM with hostDisk
        │                           namespace: bluefin-test | bluefin-lts-test
        │
        ├─ run-gnome-tests ───────► Fedora runner pod
        │                           git-sync → SSH → VM pod IP
        │                           qecore-headless + behave + dogtail
        │
        └─ teardown (onExit) ─────► delete VM + hostDisk clone
```

## Test stack

| Layer | Tool | Purpose |
|---|---|---|
| BDD runner | behave | Gherkin `.feature` files, step definitions |
| Session bridge | qecore-headless | Sets DBUS/Wayland env, starts gnome-ponytail-daemon |
| GUI automation | dogtail (AT-SPI) | Accessibility tree interaction — no pixels |
| AT-SPI on Wayland | gnome-ponytail-daemon | Coordinate injection bridge |
| Shell scripting | Shell.Eval (gdbus) | GNOME 50+ workaround for top-bar menus |

## Test phases

| Phase | Plan | Runs on |
|---|---|---|
| 1 — Golden Path smoke | `/smoke` | Every PR |
| 2 — Developer tooling | `/developer-tools` | Every merge |
| 3 — Software management | `/software-management` | Nightly |
| Flatcar | `/flatcar` | On demand |

## Quick start

```bash
# One-time cluster setup (CDI + RBAC + templates + SSH secret)
just setup-cluster

# Run smoke tests against latest Bluefin
source .env.test-pubkey
just run-tests

# Run against persistent titan VMs (instant, no BIB build)
just run-titan-smoke

# Run against a specific image
just run-tests-image ghcr.io/ublue-os/bluefin:lts lts

# Run the full matrix (latest + lts in parallel)
just run-tests-matrix

# Run Flatcar smoke tests
just run-flatcar-smoke

# Apply WorkflowTemplates to the cluster
just apply-templates

# Watch logs from most recent workflow
just logs

# Lint all Argo YAML
just lint
```

## Repository layout

```
testsuite/
├── Justfile                              # all commands live here
├── PLAN.md                               # implementation plan + architecture notes
├── RUNBOOK.md                            # operational runbook for agents + humans
├── argocd/
│   └── application.yaml                  # Argo CD auto-sync for WorkflowTemplates
├── container/
│   └── Containerfile                     # tmt SSH runner image (legacy)
├── exo-1/
│   └── just/99-local.just                # ujust recipe for exo-1 k8s-mode
├── manifests/
│   ├── cdi-insecure-registry.yaml        # CDI config for ghost:5000 (legacy)
│   └── flatcar-test-namespace.yaml       # namespace manifest
├── plans/
│   ├── main.fmf                          # tmt metadata
│   ├── plan.fmf                          # test plans (smoke / developer / software)
│   └── flatcar.fmf                       # Flatcar test plan
├── tests/
│   ├── smoke/                            # Phase 1: GNOME Shell boot, panel, extensions
│   │   ├── features/                     # behave .feature + steps + environment.py
│   │   ├── test_gnome_shell.py           # pytest alternative (not used in pipeline)
│   │   └── test_notifications.py         # notification tests
│   ├── developer/                        # Phase 2: Ptyxis, brew, podman, micro, dakota
│   │   ├── features/                     # behave BDD tests
│   │   ├── conftest.py                   # shared pytest fixtures
│   │   ├── test_ptyxis_term.py           # Ptyxis terminal tests
│   │   ├── test_dakota_terminal.py       # Dakota/Ghostty terminal tests
│   │   ├── test_micro_editor.py          # micro editor tests
│   │   └── test_podman_desktop.py        # Podman Desktop tests
│   ├── software/                         # Phase 3: GNOME Software, Flatpak
│   │   └── features/                     # behave BDD tests
│   └── flatcar/                          # Flatcar OS: systemd, containerd, networking
│       ├── features/                     # behave BDD tests
│       ├── test_flatcar_boot.py          # pytest boot tests
│       └── test_flatcar_knuckle.py       # knuckle installer tests
└── argo/
    ├── bluefin-smoke-test.yaml           # single-image smoke workflow
    ├── bluefin-test-matrix.yaml          # multi-channel matrix (latest + lts)
    ├── flatcar-smoke-test.yaml           # Flatcar smoke workflow
    ├── deprecated/                       # old workflow versions (reference only)
    └── workflow-templates/
        ├── bib-build-and-push.yaml       # BIB golden disk builder
        ├── bluefin-qa-pipeline.yaml      # full multi-phase pipeline
        ├── bluefin-titan-smoke.yaml      # persistent titan VM smoke runner
        ├── provision-vm.yaml             # btrfs reflink + KubeVirt VM boot
        ├── provision-flatcar-vm.yaml     # Flatcar disk prep + VM boot
        ├── run-gnome-tests.yaml          # qecore-headless + behave runner
        ├── run-tmt.yaml                  # tmt SSH runner (legacy)
        ├── run-flatcar-tests.yaml        # Flatcar behave runner
        ├── teardown-vm.yaml              # VM + hostDisk cleanup
        └── teardown-flatcar-vm.yaml      # Flatcar VM cleanup
```

## Cluster topology

| Host | Role | IP |
|---|---|---|
| ghost | control-plane + KubeVirt compute | 192.168.1.102 |
| exo-1 | worker node (workflow pods only) | 192.168.1.239 |

- **Argo UI:** http://192.168.1.102:2746
- **Namespaces:** `argo`, `bluefin-test`, `bluefin-lts-test`, `flatcar-test`
- **KubeVirt VMs** pinned to ghost via `nodeSelector`

## Prerequisites

- k3s + KubeVirt running on ghost
- Argo Workflows in `argo` namespace
- `bluefin-test`, `bluefin-lts-test`, `flatcar-test` namespaces
- Secret `bluefin-test-ssh-key` in `argo` namespace (ed25519)
- Golden disks at `/var/tmp/bluefin-golden/{latest,lts}/disk.raw`

### First-time setup

```bash
# 1. Apply RBAC + templates + SSH secret
just setup-cluster
source .env.test-pubkey

# 2. Build golden disk (BIB, ~100s cold)
just ensure-disk

# 3. Run smoke tests
just run-tests
```

## Writing new tests

1. Add a `.feature` file in the appropriate `tests/<phase>/features/` directory
2. Write step definitions in `tests/<phase>/features/steps/steps.py`
3. Use `context.sandbox.shell` (qecore) to access GNOME Shell via AT-SPI
4. For top-bar interactions on GNOME 50+, use `Shell.Eval` via gdbus (see `steps.py`)
5. Use `dogtail.findChildren(predicate)` — **never** pass `requireResult` (broken in dogtail 4.16)
6. Each scenario must be self-contained — clean up after itself
7. Use `retry=False` in `findChild()` for presence checks to avoid 20s waits
8. Run `just lint` before opening a PR

## Valid image tags

| Tag | Image | Notes |
|---|---|---|
| `latest` | `ghcr.io/ublue-os/bluefin:latest` | Bleeding edge |
| `lts` | `ghcr.io/ublue-os/bluefin:lts` | Long-term support |

**`gts` does NOT exist. `lts-hwe` does NOT exist.** Do not use these tags.
