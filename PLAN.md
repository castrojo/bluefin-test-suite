# Bluefin Test Lab — Implementation Plan

## Timing: how long does provisioning take?

| Scenario | Time |
|---|---|
| BIB build (cold, image not cached) | ~100s |
| BIB build (warm, image in containerd cache) | ~60s |
| hostDisk reflink clone from golden disk | ~24ms |
| VM boot to GNOME Shell ready | ~3-4 min |
| **Total cold (new image tag)** | **~8-10 min** |
| **Total warm (golden disk already present)** | **~4-5 min** |

No `bootc install to-disk` at test time. BIB runs once per image tag and writes
a golden disk to `/var/tmp/bluefin-golden/<tag>/disk.raw`. Each test run
reflinks that golden disk into a per-run `hostDisk`, then boots the VM from it.

## Architecture

```
Argo Workflow / bluefin-qa-pipeline
  ├── ensure-disk (bib-build-and-push)
  │     ├── check-golden-disk   → test -f /var/tmp/bluefin-golden/<tag>/disk.raw
  │     └── bib-build           → BIB privileged pod writes golden disk on hostPath
  │                               (skipped if exists)
  │
  ├── provision-vm (provision-bluefin-vm)
  │     ├── reflink-golden-disk → cp --reflink=auto to per-run hostDisk
  │     ├── relabel-hostdisk    → chcon -t svirt_sandbox_file_t
  │     ├── create-vm           → KubeVirt VM with hostDisk root disk + cloud-init
  │     └── wait-for-vm-ready   → polls pod Ready, emits pod IP
  │
  ├── run-tests (run-tmt-tests)
  │     └── tmt SSH runner pod  → SSHes to pod IP
  │                               ~/.ssh/environment has AT-SPI vars
  │                               Dogtail works via gnome-ponytail-daemon
  │
  └── cleanup (onExit, always)
        ├── delete VM
        └── delete hostDisk clone
```

## Iteration 1 Fixes (2026-05-25)

Three root causes fixed after 20 failed matrix runs:

| Bug | Fix | Template |
|---|---|---|
| tmt runner SIGTERM (exit 143) — SSH wait 180s < VM boot time 3-4min | SSH wait 180s→600s; activeDeadlineSeconds:3600 added | run-tmt-tests |
| LTS hostDisk Permission Denied — SVirt SELinux label missing | Added `chcon -t svirt_sandbox_file_t` after reflink | provision-bluefin-vm |
| reflink-disk exit 1 — `cp --reflink=always` transient failure | Changed to `cp --reflink=auto` | provision-bluefin-vm |

Also applied: `bluefin-qa-pipeline` WorkflowTemplate (was missing from cluster).
Issues filed: castrojo/copilot-config #329–332.

## Prerequisites: what's on the cluster vs what's needed

| Item | Status |
|---|---|
| Argo Workflows | ✅ running |
| KubeVirt | ✅ running |
| RBAC: argo-kubevirt-manager ClusterRole + Binding | ✅ applied |
| WorkflowTemplate: bib-build-and-push | ✅ live |
| WorkflowTemplate: provision-bluefin-vm | ✅ live (updated) |
| WorkflowTemplate: run-tmt-tests | ✅ live |
| WorkflowTemplate: teardown-bluefin-vm | ✅ live (updated, cleans hostDisk) |
| WorkflowTemplate: bluefin-qa-pipeline | ✅ live |
| CDI | ✅ not used — hostDisk + reflink replaced CDI |
| CDI insecure registry config | ✅ not applicable — no CDI/PVC path |
| SSH secret `bluefin-test-ssh-key` | ✅ exists |
| tmt runner image | ✅ at `192.168.1.102:5000/bluefin-tmt-runner:latest` |
| First golden disk | ✅ at `/var/tmp/bluefin-golden/{latest,lts}/disk.raw` |

## Execution order (first run)

```bash
# 1. Apply/refresh WorkflowTemplates (includes bluefin-qa-pipeline)
just apply-templates

# 2. SSH secret (idempotent)
just setup-ssh-secret
source .env.test-pubkey

# 3. Build + push tmt runner image
just build-runner
just push-runner

# 4. Pre-build golden disk for latest tag (~100s BIB if missing)
just ensure-disk

# 5. Run smoke tests
just run-tests
```

## Subsequent runs (warm)

```bash
source .env.test-pubkey
just run-tests          # ~4-5 min total, golden disk already present
```

## Open questions for iteration

- **gnome-ponytail-daemon COPR** *(status: under investigation)*: If a COPR
  package exists for Fedora 41, the prepare block simplifies to
  `dnf install -y gnome-ponytail-daemon`. Check: `dnf search gnome-ponytail`
  inside the VM before the build-from-source path.

- **Session timing** *(resolved)*: SSH wait increased from 180s to 600s in
  `run-tmt-tests`, which covers the observed 3-4 minute VM boot time.

- **CDI pullMethod** *(resolved)*: Not applicable. CDI is no longer used;
  provisioning now uses golden disks + per-run `hostDisk` reflinks.

- **local-path + WaitForFirstConsumer** *(resolved)*: Not applicable. There is
  no CDI/PVC provisioning path in the current architecture.
