# bluefin-test-suite

A cloud-native QA pipeline for [Project Bluefin](https://projectbluefin.io) desktops.

Runs inside Kubernetes on [ghost](https://github.com/castrojo/utah), driven by **Argo Workflows**, booting Bluefin directly as a **KubeVirt `containerDisk`** VM, and executing GUI tests via **tmt + Dogtail (AT-SPI)** — no ISO installer, no pixel matching.

---

## Architecture

```
GitHub webhook / just run-tests
        │
        ▼
  Argo Workflow (argo ns)
        │
        ├─ provision-bluefin-vm ──► KubeVirt VM (containerDisk)
        │                           namespace: bluefin-test
        │                           image: ghcr.io/ublue-os/bluefin:latest
        │
        ├─ run-tmt-tests ──────────► tmt runner pod
        │                           SSH → VM pod IP
        │                           pytest + Dogtail (AT-SPI)
        │
        └─ teardown (onExit) ──────► delete VM
```

## Test phases

| Phase | Plan | Runs on |
|---|---|---|
| 1 — Golden Path smoke | `/smoke` | Every PR |
| 2 — Developer tooling | `/developer-tools` | Every merge |
| 3 — Software management | `/software-management` | Nightly |

## Quick start

```bash
# Run smoke tests against latest Bluefin
just run-tests

# Run against a specific image
just run-tests-image ghcr.io/ublue-os/bluefin:gts

# Run the full matrix (latest + lts)
just run-tests-matrix

# Apply WorkflowTemplates to the cluster
just apply-templates

# Watch logs
just logs
```

## Repository layout

```
bluefin-test-suite/
├── Justfile                          # all commands live here
├── container/
│   └── Containerfile                 # tmt runner image
├── plans/
│   ├── main.fmf                      # tmt metadata
│   └── plan.fmf                      # test plans (smoke / developer / software)
├── tests/
│   ├── test_gnome_shell.py           # Phase 1: boot, Activities, extensions
│   ├── test_ptyxis_term.py           # Phase 2: terminal, brew, podman, micro
│   └── test_flatpak_ui.py            # Phase 3: GNOME Software, Flatpak install
└── argo/
    ├── bluefin-smoke-test.yaml       # single-image workflow
    ├── bluefin-test-matrix.yaml      # multi-channel matrix workflow
    └── workflow-templates/
        ├── provision-vm.yaml         # KubeVirt containerDisk VM provisioning
        ├── run-tmt.yaml              # tmt SSH runner
        └── teardown-vm.yaml         # VM cleanup (onExit)
```

## Prerequisites

- k3s + KubeVirt running on ghost (`192.168.1.102`)
- Argo Workflows installed in `argo` namespace
- `bluefin-test` and `bluefin-lts-test` namespaces exist
- Secret `bluefin-test-ssh-key` in `argo` namespace with an `id_ed25519` key

### Create the SSH secret

```bash
ssh-keygen -t ed25519 -f /tmp/bluefin-test-key -N ""
kubectl create secret generic bluefin-test-ssh-key \
    --from-file=id_ed25519=/tmp/bluefin-test-key \
    --from-file=id_ed25519.pub=/tmp/bluefin-test-key.pub \
    -n argo
# The public key goes into cloud-init via workflow parameter:
PUBKEY=$(cat /tmp/bluefin-test-key.pub)
just run-tests   # edit Justfile to pass -p ssh-pubkey="$PUBKEY"
```

## Writing new tests

1. Add a `test_<feature>.py` to `tests/`
2. Use `from dogtail.tree import root` — interact with GNOME via AT-SPI, not pixels
3. Use `dogtail-sniff` on a live Bluefin desktop to explore the accessibility tree
4. Each test must be atomic — one behaviour per function
5. Every fixture that opens an app must close it in the `yield` teardown block
6. Run `just lint` before opening a PR
