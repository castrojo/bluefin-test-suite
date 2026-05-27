# Bluefin Test Suite — Senior QA Design Review & Epic Breakdown

## Executive Summary

This document is a production-grade gap analysis and implementation roadmap for the `projectbluefin/testsuite` repository. It assesses the current state, identifies coverage/infrastructure/tooling/security gaps, and decomposes the full test suite into implementation-ready epics suitable for direct SWE execution.

**Current state:** The testsuite is a functional but early-stage cloud-native QA pipeline running on a k3s/KubeVirt/Argo Workflows cluster. It tests Bluefin `latest` and `lts` variants plus Flatcar via behave+qecore+dogtail (AT-SPI) over SSH into KubeVirt VMs. Provisioning uses BIB golden disks with btrfs reflink cloning (~24ms per VM).

**Assessment:** The foundation is solid and opinionated (AT-SPI over pixel matching, immutable golden disks, Argo DAGs). However, coverage is shallow across variants, missing entire OS targets, has no security/compliance testing, no lifecycle testing, and lacks CI/CD integration. The following analysis addresses all of this systematically.

---

# Phase 1: Senior QA Design Review & Gap Analysis

## 1. Coverage Gaps Across Target OSes

### 1.1 Variant Coverage Matrix

| Target OS | Currently Tested | Gap |
|---|---|---|
| Bluefin standard (latest) | ✅ Smoke + Developer + Software | — |
| Bluefin standard (lts) | ✅ Smoke only | Developer + Software phases not run on LTS |
| Bluefin DX (Developer Experience) | ❌ Not tested | Entire DX variant missing — includes devcontainers, VS Code, additional tooling |
| Bluefin NVIDIA | ❌ Not tested | No GPU passthrough, no nvidia-smi validation, no CUDA stack tests |
| GNOME (vanilla/upstream Fedora) | ❌ Not tested | No baseline Fedora Workstation comparison tests |
| Fedora CoreOS / KnuckleOS | ⚠️ Minimal | Only dry-run unit tests for knuckle; boot.feature is basic |

### 1.2 Test Category Gaps

| Category | Status | Detail |
|---|---|---|
| Install/First-boot | ❌ Missing | No anaconda/OOBE tests; BIB skips installer entirely |
| Boot validation | ⚠️ Basic | No firmware (UEFI/SecureBoot), no grub menu tests, no multi-boot |
| Desktop session | ✅ Adequate | Good GNOME Shell AT-SPI coverage; extensions, panel, overview |
| Hardware emulation | ❌ Missing | No USB, audio, bluetooth, TPM emulation tests |
| GPU passthrough | ❌ Missing | Critical for NVIDIA variant — no vfio-pci, no nvidia-smi |
| Update/rebase lifecycle | ❌ Missing | No `bootc upgrade`, no `rpm-ostree rebase`, no rollback tests |
| Suspend/Resume | ❌ Missing | No ACPI S3/S4 testing in KubeVirt |
| Multi-display | ❌ Missing | Single-head only; no virtio-gpu multi-monitor |
| Disk encryption | ❌ Missing | No LUKS/clevis tests |
| Accessibility conformance | ⚠️ Incidental | AT-SPI used as tool but no A11y conformance validation |
| Flatpak sandboxing | ❌ Missing | No portal validation, no permission grant tests |

### 1.3 Flatcar/KnuckleOS Specific Gaps

- **No actual install test**: `test_flatcar_knuckle.py` only does `--dry-run`; never exercises real disk partition/install
- **No update channel test**: No Nebraska/Omaha protocol validation
- **No Ignition config testing**: Cloud-init is used but Ignition is the Flatcar-native method
- **No etcd/k8s bootstrap**: No validation of CoreOS role as K8s node
- **No afterburn testing**: No cloud metadata validation

## 2. Infrastructure Gaps

### 2.1 Display Server Access

| Concern | Current State | Gap |
|---|---|---|
| Wayland session | ✅ Working via qecore-headless + ponytail | — |
| VNC/RDP for debugging | ❌ Missing | No live session observation capability during test runs |
| Screenshot capture | ❌ Missing | No visual evidence collection on failures |
| Video recording | ❌ Missing | No session recording for failure post-mortem |
| X11 fallback | ❌ Missing | Cannot test X11 session type |

### 2.2 Persistent Storage for Artifacts

| Concern | Current State | Gap |
|---|---|---|
| Test result storage | ⚠️ Ephemeral | Results in pod `/tmp/` disappear on completion; titan VMs are the only persistent store |
| Artifact repository | ❌ Missing | No S3/MinIO/Argo Artifacts configuration |
| Historical trend data | ❌ Missing | No test result database; no flakiness tracking |
| Log aggregation | ⚠️ Basic | Loki exists at :30100 but not integrated into test reporting |
| Golden disk versioning | ❌ Missing | No content-addressable tracking of which image SHA produced which golden disk |

### 2.3 VM Lifecycle and Resource Management

| Concern | Current State | Gap |
|---|---|---|
| Orphan cleanup | ⚠️ Manual | RUNBOOK documents manual `kubectl delete vm`; no automated GC |
| Resource limits | ❌ Missing | VMs get 4c/8Gi but no pod resource limits/requests for Argo pods |
| Parallel execution | ⚠️ Limited | Matrix runs 2 VMs in parallel; no fan-out for 5+ variants |
| VM health monitoring | ❌ Missing | No watchdog; VMs can silently hang with no detection |
| Network policies | ❌ Missing | No isolation between test namespaces |

### 2.4 Cluster Scalability

- **Single compute node (ghost)**: All KubeVirt VMs pinned to ghost. If the full matrix expands to 6+ variants, 64GB RAM and 16 cores become a bottleneck (each VM: 4c/8Gi = 32c/48Gi for 6 VMs)
- **No autoscaling**: No mechanism to schedule lower-priority variants when resources are available
- **Storage pressure**: Golden disks + reflink clones + BIB output compete for `/var/tmp` space

## 3. Tooling Gaps

### 3.1 Test Automation Framework

| Tool | Status | Gap |
|---|---|---|
| behave (BDD) | ✅ Primary runner | — |
| pytest | ⚠️ Secondary/unused in pipeline | Conftest exists but pipeline runs behave only |
| qecore-headless | ✅ Session bridge | — |
| dogtail (AT-SPI) | ✅ GUI automation | API migration issues (4.16) documented and addressed |
| Image comparison | ❌ Missing | No OpenCV/pixelmatch for visual regression |
| Performance profiling | ❌ Missing | No frame timing, startup latency measurement |
| Crash detection | ⚠️ Basic | `coredumpctl list` grep only; no ABRT/FAF integration |
| Journalctl analysis | ⚠️ Basic | Simple grep for error priority; no structured analysis |

### 3.2 CI/CD Integration

| Integration | Status | Gap |
|---|---|---|
| GitHub Actions trigger | ❌ Missing | README mentions "GitHub webhook" but no `.github/workflows/` exist |
| PR gating | ❌ Missing | No required status checks from test results |
| Argo Events (webhook) | ❌ Missing | No event source configuration for GitHub webhooks |
| Result reporting to PR | ❌ Missing | No GitHub Checks API integration |
| Slack/Discord notification | ❌ Missing | No alerting on test failures |
| Badge/status page | ❌ Missing | No public test status dashboard |

### 3.3 Test Data Management

| Concern | Status | Gap |
|---|---|---|
| Test user provisioning | ⚠️ Manual | `bluefin-test` user baked into golden disk; no parameterization |
| Fixture data | ❌ Missing | No test Flatpaks, no test extensions for controlled validation |
| Mock services | ❌ Missing | No mock GNOME Online Accounts, no mock update server |
| Seed data reset | ⚠️ Implicit | Reflink from golden disk provides clean state but no in-run reset |

## 4. Risk Areas: Immutable/Image-Based OSes

### 4.1 Atomic Update Lifecycle (Critical Gap)

The testsuite does **not** test the most critical user journey for immutable OS users:
- `bootc upgrade` — the primary update mechanism
- `bootc switch` — variant/channel switching
- Rollback after failed upgrade
- Staged deployments pending reboot
- `rpm-ostree` compatibility layer

**Risk:** A broken upgrade path ships to users with zero automated gate.

### 4.2 OSTree/bootc Transitions

- No test validates that `ostree admin status` reports correct deployments
- No test validates that `bootc status` reports expected image reference
- No test validates that the boot loader entries are correct after upgrade
- No test validates that `/etc` merge conflicts are handled during upgrade

### 4.3 Layering and Overlay

- `ostree admin unlock` is used in the test runner to install dependencies — this is correct but means tests run on a modified (unlocked) filesystem
- No validation that the unlock does not persist across reboots
- No test for user-initiated layering (`rpm-ostree install`)

### 4.4 Image Signing and Provenance

- Container images are pulled from GHCR without cosign verification
- No SBOM validation
- No attestation checking in the test pipeline
- Golden disk provenance is not tracked (which image SHA → which disk)

## 5. Security and Compliance Gaps

### 5.1 Container Image Signing (cosign)

| Requirement | Status | Gap |
|---|---|---|
| Verify `ghcr.io/ublue-os/bluefin:*` signatures before BIB build | ❌ Missing | Images pulled unsigned |
| Verify runner container images (Fedora, chainguard) | ❌ Missing | No signature verification |
| Sign test result artifacts | ❌ Missing | No provenance chain |
| Sigstore verification policy | ❌ Missing | No ClusterImagePolicy or admission controller |

### 5.2 SELinux Policy Validation

| Concern | Status | Gap |
|---|---|---|
| SELinux enforcing in test VMs | ❌ **Disabled** | `selinux=0` in BLS entries — all tests run with SELinux OFF |
| SELinux denials as test failures | ❌ Missing | No AVC denial checking |
| Custom policy validation | ❌ Missing | Bluefin ships custom SELinux policies; never tested |
| relabeling after unlock | ❌ Missing | `ostree admin unlock` may create mislabeled files |

**Critical finding:** SELinux is explicitly disabled in the golden disks (`selinux=0` in BLS boot entries). This means:
1. No test ever validates that Bluefin runs correctly with SELinux enforcing
2. Any SELinux regression ships completely undetected
3. The `chcon` commands in provisioning are cosmetic when SELinux is off

### 5.3 Additional Security Concerns

- **SSH key rotation**: No automated reconciliation when secret is rotated (documented in RUNBOOK but not automated)
- **Privileged pods**: BIB builder and disk operations run `privileged: true` with no PodSecurity restriction
- **hostPath volumes**: Extensive use of hostPath with no admission policy
- **No network policies**: Test VMs can reach the internet and each other unrestricted

---

# Phase 2: Epic Breakdown for SWE Implementation

## Epic Dependency Graph

```
E01 (Artifact Storage) ─────────────────────────────────────────┐
E02 (CI/CD Integration) ────────────────────────────────────────┤
E03 (Cosign Verification) ──────────────────────────────────────┤
                                                                 │
E04 (SELinux Enforcing) ────────────────────────────────────────┤
E05 (Variant Matrix: DX + NVIDIA) ─── depends on E01, E03 ─────┤
E06 (Update Lifecycle) ─── depends on E04, E05 ─────────────────┤
E07 (Vanilla GNOME Baseline) ─── depends on E01 ───────────────┤
E08 (GPU/NVIDIA Passthrough) ─── depends on E05 ────────────────┤
E09 (KnuckleOS Full Install) ─── depends on E01 ────────────────┤
E10 (Visual Evidence & Recording) ─── depends on E01 ───────────┤
E11 (Performance SLAs & Reporting) ─── depends on E01, E02 ─────┤
E12 (Hardware Emulation) ─── depends on E05 ────────────────────┤
E13 (Security Hardening) ─── depends on E03, E04 ───────────────┘
```

---

## E01: Persistent Artifact Storage & Test Result Database

**Objective:** Establish a durable, queryable artifact storage system so test results, screenshots, logs, and trend data survive workflow completion and support historical analysis.

**Targets:** All OS variants and test categories (cross-cutting infrastructure)

**Acceptance Criteria:**
- [ ] MinIO (S3-compatible) deployed in the cluster with retention policy (90 days)
- [ ] Argo Workflows configured with `artifactRepository` pointing to MinIO
- [ ] All test templates emit artifacts (results.json, junit.xml, logs, screenshots) to S3
- [ ] PostgreSQL or SQLite database stores structured test results (suite, variant, scenario, pass/fail, duration, timestamp)
- [ ] `just results` command queries and displays recent results from the database
- [ ] Historical trend visible via Grafana dashboard connected to the results DB
- [ ] Golden disk provenance tracking: image digest → disk hash → test run ID

**Implementation Notes:**
- Deploy MinIO via Helm chart (`minio/minio`) with hostPath PV on ghost
- Use Argo's native `artifactRepository.s3` configuration
- Results ingestion: add a `finalize` step to all pipelines that POSTs structured JSON to a results API or writes to DB directly
- Consider TimescaleDB for time-series queries on test durations (flakiness detection)
- Red Hat pattern: follow OpenShift CI's `artifacts/` convention for directory layout

**Performance SLA:** Artifact upload must not add >30s to any workflow; query latency <2s for last 30 days

**Dependencies:** None (foundational)

**Estimated effort:** 2 sprints (1 for MinIO/Argo config, 1 for DB + Grafana)

---

## E02: CI/CD Integration — GitHub Actions + Argo Events

**Objective:** Wire the test suite into the Bluefin PR/merge lifecycle so tests are triggered automatically and results gate merges.

**Targets:** All Bluefin variants (latest, lts); triggered by bluefin repo PRs

**Acceptance Criteria:**
- [ ] GitHub Actions workflow in `projectbluefin/bluefin` triggers test run on PR open/sync
- [ ] Argo Events `EventSource` (GitHub webhook) receives PR events and submits workflows
- [ ] Argo `Sensor` maps PR metadata (SHA, branch, PR number) to workflow parameters
- [ ] Test results posted back to PR as GitHub Check Run with summary (X/Y passed, link to full report)
- [ ] Failed tests block merge (required status check)
- [ ] Matrix of (latest, lts) runs per PR; DX/NVIDIA on nightly schedule
- [ ] `just trigger-pr <owner/repo> <pr-number>` for manual re-trigger
- [ ] Webhook secret stored in k8s Secret, rotated quarterly

**Implementation Notes:**
- Argo Events: deploy `EventSource` (type: github) + `Sensor` + `EventBus` (NATS or jetstream)
- GitHub App (preferred over webhook) for Check Run write access and fine-grained permissions
- Workflow receives: `image` (from PR's build artifact), `image-tag`, `pr-number`, `commit-sha`
- Result callback: use `gh` CLI or GitHub API from a finalize step to update Check Run status
- Rate limiting: debounce rapid pushes (only test latest push per PR within 5-min window)
- Red Hat pattern: mirrors how OpenShift CI (Prow) handles PR triggers → test → report

**Performance SLA:** Time from PR push to first test result visible: <15 minutes (smoke only)

**Dependencies:** E01 (results must be stored to generate summary for PR comment)

**Estimated effort:** 2 sprints

---

## E03: Cosign Signature Verification Tests

**Objective:** Validate that Bluefin images are correctly signed by upstream build systems. The signing infrastructure lives in the Bluefin CI — this epic only verifies the signatures are present, valid, and match expected identity constraints.

**Targets:** All Bluefin images (`ghcr.io/ublue-os/bluefin:*`, DX, NVIDIA variants)

**Acceptance Criteria:**
- [ ] Test scenario: `cosign verify` succeeds against every image tag in the matrix
- [ ] Test scenario: Verification uses correct OIDC issuer + identity regexp for ublue-os
- [ ] Test scenario: `bootc status` inside booted VM shows a signed image digest
- [ ] Test scenario: Signature verification fails gracefully with clear error on tampered/unsigned image
- [ ] `just verify-images` command runs cosign verify against all active image tags
- [ ] Verification runs as a pre-flight check in the pipeline (before BIB build)

**Implementation Notes:**
- ublue-os uses Sigstore keyless signing via GitHub Actions OIDC — verify with:
  ```bash
  cosign verify --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
    --certificate-identity-regexp='https://github.com/ublue-os/.*' \
    ghcr.io/ublue-os/bluefin:latest
  ```
- This is a validation-only epic — do NOT replicate signing infra or admission controllers
- Cosign binary: install in a lightweight verification step or use `cgr.dev/chainguard/cosign`

**Performance SLA:** Verification step must complete in <30s per image

**Dependencies:** None (can be implemented immediately)

**Estimated effort:** 0.5 sprint

---

## E04: SELinux Enforcing Mode & Policy Validation

**Objective:** Remove the `selinux=0` kernel parameter from golden disks and run all tests with SELinux enforcing, adding AVC denial detection as a test quality signal.

**Targets:** All Bluefin variants (standard, DX, NVIDIA); Flatcar (where applicable)

**Acceptance Criteria:**
- [ ] Golden disk BLS entries no longer contain `selinux=0`
- [ ] All existing smoke/developer/software tests pass with SELinux enforcing
- [ ] New test scenario: "No SELinux AVC denials in journal" (per-scenario `ausearch` check)
- [ ] New test scenario: "SELinux mode is Enforcing" (`getenforce` returns `Enforcing`)
- [ ] `ostree admin unlock` overlay is properly labeled (no `restorecon` failures)
- [ ] Test dependencies installed via `pip install --user` don't trigger AVC denials
- [ ] Known-acceptable denials documented and allowlisted (e.g., test-specific uinput access)
- [ ] `selinux_allowlist.yaml` configuration for denials that are Bluefin bugs (filed upstream) vs test infrastructure noise

**Implementation Notes:**
- Remove `selinux=0` sed from `bib-disk-configure` template
- The existing `chcon -t svirt_sandbox_file_t` on hostDisks is already correct
- The existing `chcon -t uinput_device_t /dev/uinput` will become REQUIRED (currently cosmetic)
- Add `after_scenario` hook to behave that runs:
  ```bash
  ausearch -m avc -ts recent --raw 2>/dev/null | grep -v 'type=AVC.*denied.*{.*}.*tcontext=.*bluefin_test_t'
  ```
- Expect breakage: investigate and fix before declaring done
- This is the highest-risk epic — expect 1-2 weeks of iterative fixing
- Red Hat pattern: mirrors RHEL CI which gates on zero AVCs per test

**Performance SLA:** AVC check adds <5s per scenario; no overall suite time impact >10%

**Dependencies:** None (should be done early as it may break everything)

**Estimated effort:** 3 sprints (expect significant debugging)

---

## E05: Variant Matrix Expansion — DX and NVIDIA Images

**Objective:** Extend the test matrix to cover Bluefin DX (Developer Experience) and NVIDIA variants with variant-specific test scenarios.

**Targets:** `ghcr.io/ublue-os/bluefin-dx:latest`, `ghcr.io/ublue-os/bluefin-dx:lts`, `ghcr.io/ublue-os/bluefin-nvidia:latest`

**Acceptance Criteria:**
- [ ] Golden disks built and cached for DX and NVIDIA variants
- [ ] Variant-specific test suites:
  - DX: VS Code/Codium launch + accessibility, devcontainer CLI, podman-compose, distrobox
  - NVIDIA: `nvidia-smi` reports GPU (or graceful skip if no GPU), Vulkan validation, `vainfo`
- [ ] Matrix workflow expanded: `bluefin-test-matrix.yaml` fans out to 4-6 variants
- [ ] Variant parameter flows through all templates (used in labels, annotations, result grouping)
- [ ] Per-variant golden disk management: `just ensure-disk-all` builds all variants
- [ ] Shared smoke scenarios run identically across all variants (regression gate)
- [ ] Variant-specific scenarios tagged: `@dx_only`, `@nvidia_only`

**Implementation Notes:**
- DX images include additional packages: verify their presence without testing upstream functionality
- NVIDIA without physical GPU: use `--vgpu` or virtio-gpu with `nouveau` driver; tests should handle "no GPU" gracefully
- BIB must handle larger DX images (~4GB vs ~2.5GB for standard)
- Resource allocation: DX VMs may need more RAM (devcontainers); NVIDIA VMs need GPU passthrough resources
- Use Argo `withItems` for matrix fan-out instead of duplicating workflow steps:
  ```yaml
  - - name: test-variant
      withItems:
        - {image: "bluefin:latest", tag: "latest", ns: "bluefin-test"}
        - {image: "bluefin-dx:latest", tag: "dx-latest", ns: "bluefin-test"}
      templateRef: ...
  ```

**Performance SLA:** Each variant's smoke suite: <15 minutes. Full matrix (all variants, all phases): <3 hours

**Dependencies:** E01 (artifact storage for expanded matrix), E03 (verify new images)

**Estimated effort:** 2 sprints

---

## E06: Atomic Update & Rebase Lifecycle Tests

**Objective:** Test the complete update lifecycle for immutable/image-based OSes: upgrade, switch, rollback, and staged deployment verification.

**Targets:** All Bluefin variants (bootc-based), Flatcar (Nebraska/Omaha updates)

**Acceptance Criteria:**
- [ ] Scenario: `bootc upgrade` downloads new deployment, stages it, VM reboots into new deployment
- [ ] Scenario: `bootc rollback` reverts to previous deployment after upgrade
- [ ] Scenario: `bootc switch ghcr.io/ublue-os/bluefin-dx:latest` successfully transitions standard→DX
- [ ] Scenario: Post-upgrade desktop session starts (GNOME Shell accessible via AT-SPI)
- [ ] Scenario: `/etc` customizations survive upgrade (merge works correctly)
- [ ] Scenario: `bootc status` shows correct image reference and digest after upgrade
- [ ] Scenario: Failed upgrade (corrupt image) is detected and does not brick the system
- [ ] Flatcar: Nebraska update protocol mock validates channel switching
- [ ] All lifecycle tests use a dedicated golden disk (not shared with smoke tests) to avoid pollution
- [ ] Total lifecycle test execution: <45 minutes per variant

**Implementation Notes:**
- Lifecycle tests need a **second image** to upgrade to — use `bluefin:latest` → `bluefin:latest-YYYYMMDD` (pinned digest) or a test-specific tag
- Requires two-phase test: (1) boot baseline, (2) trigger upgrade, (3) reboot VM (ACPI shutdown + KubeVirt restart), (4) validate new state
- KubeVirt VM reboot: `virtctl restart <vm>` or guest-initiated `systemctl reboot`
- For rollback: boot upgraded, then `bootc rollback`, reboot, validate original deployment
- Mock upgrade server: serve a modified OCI image from local zot registry to avoid network dependency
- Red Hat pattern: mirrors `bootc-image-builder` upstream testing which validates upgrade→rollback cycles

**Performance SLA:** Single upgrade+reboot+validate cycle: <15 minutes. Full lifecycle suite: <45 minutes

**Dependencies:** E04 (SELinux must be enforcing to catch relabeling bugs during upgrade), E05 (need variant images to test switch)

**Estimated effort:** 3 sprints

---

## E07: Vanilla GNOME/Upstream Fedora Baseline Tests

**Objective:** Establish a Fedora Workstation (vanilla GNOME) test target as a comparison baseline, allowing detection of Bluefin-specific regressions versus upstream GNOME issues.

**Targets:** Fedora Workstation latest (vanilla GNOME)

**Acceptance Criteria:**
- [ ] Golden disk built from `quay.io/fedora/fedora-bootc:latest` or Fedora Workstation bootc image
- [ ] Shared smoke scenarios (top bar, Activities, Quick Settings) pass on vanilla GNOME
- [ ] Comparison report: "Scenario X passes on vanilla, fails on Bluefin" → Bluefin-specific bug
- [ ] Vanilla GNOME run scheduled nightly (not per-PR — too expensive)
- [ ] Results tagged as `baseline` in the results database
- [ ] Extension-free GNOME validates that test infrastructure works without Bluefin customizations
- [ ] New namespace: `gnome-baseline-test`

**Implementation Notes:**
- Use `quay.io/fedora/fedora-bootc:41` as the bootc base image for BIB
- This image has vanilla GNOME (no Bluefin extensions, no Ptyxis, no brew)
- Only `smoke` suite runs on vanilla — `developer` and `software` have Bluefin-specific scenarios
- Test tagging: scenarios marked `@bluefin_specific` are skipped on vanilla; `@gnome_core` runs everywhere
- Provides invaluable debugging signal: if a test fails on both vanilla and Bluefin, it's upstream

**Performance SLA:** Vanilla smoke suite: <15 minutes

**Dependencies:** E01 (store comparison results)

**Estimated effort:** 1 sprint

---

## E08: GPU Passthrough & NVIDIA Validation

**Objective:** Enable GPU passthrough testing for the Bluefin NVIDIA variant, validating driver stack, CUDA availability, and Vulkan rendering.

**Targets:** Bluefin NVIDIA variant

**Acceptance Criteria:**
- [ ] KubeVirt VM spec supports GPU passthrough via `hostDevices` (VFIO-PCI) or mediated devices (vGPU)
- [ ] Test scenario: `nvidia-smi` returns valid output showing GPU model and driver version
- [ ] Test scenario: `vulkaninfo` reports NVIDIA Vulkan ICD
- [ ] Test scenario: No Vulkan validation errors in journal (regression from bluefin#4620)
- [ ] Test scenario: CUDA sample (`vectorAdd`) executes successfully
- [ ] Test scenario: `vainfo` shows hardware video decode/encode capabilities
- [ ] Graceful skip: If ghost has no NVIDIA GPU, tests are skipped with `@requires_gpu` tag
- [ ] NVIDIA driver version pinning: test validates that running driver matches expected version from image

**Implementation Notes:**
- **Hardware dependency:** ghost has AMD Ryzen AI MAX+ — confirm if discrete NVIDIA GPU is present
- If no NVIDIA hardware: use `vfio-pci` mediated device or accept that this epic produces the test structure + skip logic, with GPU tests activated when hardware is available
- KubeVirt GPU passthrough requires:
  1. IOMMU enabled in BIOS/kernel
  2. GPU bound to `vfio-pci` driver
  3. KubeVirt `permittedHostDevices` configuration
  4. VM spec `hostDevices` section
- Alternative: Use virtio-gpu with Mesa software rendering to validate the Vulkan/VA-API plumbing without physical hardware
- Red Hat pattern: OpenShift Virtualization GPU passthrough documentation

**Performance SLA:** GPU-specific tests: <10 minutes (or instant skip)

**Dependencies:** E05 (NVIDIA variant golden disk)

**Estimated effort:** 2 sprints (1 for infrastructure, 1 for tests; blocked on hardware availability)

---

## E09: KnuckleOS Full Installation & Lifecycle Tests

**Objective:** Validate the complete KnuckleOS/Flatcar installation flow from knuckle installer through first boot, including real disk writes (not just dry-run).

**Targets:** Flatcar Container Linux via knuckle installer

**Acceptance Criteria:**
- [ ] Test scenario: `knuckle headless --config <file>` installs Flatcar to a second virtio disk
- [ ] Test scenario: VM reboots from installed disk and reaches `multi-user.target`
- [ ] Test scenario: Installed system has correct hostname, timezone, SSH keys from config
- [ ] Test scenario: Network configuration (DHCP or static) is applied correctly
- [ ] Test scenario: `update_strategy: off` is honored (no automatic update)
- [ ] Test scenario: Ignition transpilation produces valid config
- [ ] Test scenario: etcd bootstrap (if applicable for KnuckleOS k8s mode)
- [ ] Two-disk VM: rootdisk (Flatcar live) + targetdisk (install target) already supported
- [ ] Post-install validation runs automatically after reboot

**Implementation Notes:**
- Current `provision-flatcar-vm.yaml` already creates two disks (`rootdisk` + `targetdisk`) — leverage this
- Extend `test_flatcar_knuckle.py` beyond dry-run: actually invoke `knuckle headless` against `/dev/vdb`
- Two-phase test flow:
  1. Boot from `rootdisk`, run `knuckle headless` targeting `targetdisk`
  2. Delete VM, recreate with `targetdisk` as boot disk (swap boot order)
  3. Validate installed system
- Alternative: Use `virtctl console` to change boot order without VM recreation
- Knuckle binary: build from source in a prep step or include in golden disk

**Performance SLA:** Full install + reboot + validate: <20 minutes

**Dependencies:** E01 (store install logs as artifacts)

**Estimated effort:** 2 sprints

---

## E10: Visual Evidence Collection — Screenshots & Video Recording

**Objective:** Capture screenshots on test failure and optional video recording of entire test sessions, providing visual evidence for debugging GUI test failures.

**Targets:** All GNOME-based variants (Bluefin standard, DX, NVIDIA, vanilla GNOME)

**Acceptance Criteria:**
- [ ] Screenshot captured automatically on any scenario failure (saved as artifact)
- [ ] Screenshot method: `gnome-screenshot` CLI or PipeWire screencopy via script
- [ ] Video recording: opt-in per-run via parameter (adds overhead); uses `wf-recorder` or PipeWire
- [ ] Screenshots uploaded to artifact store (MinIO) with workflow/scenario metadata
- [ ] Failed PR comments include inline screenshot preview (linked from artifact store)
- [ ] VNC/SPICE access: `virtctl vnc` or VNC service exposed for live debugging
- [ ] `just vnc <vm-name>` command opens VNC session to a running test VM
- [ ] Video files capped at 100MB per scenario (auto-truncate older frames)

**Implementation Notes:**
- `gnome-screenshot --file=/tmp/results/screenshot_<scenario>.png` via SSH after failure
- For PipeWire/Wayland-native: `grim` (wlroots) won't work on Mutter; use `gnome-screenshot` or:
  ```bash
  gdbus call --session --dest org.gnome.Shell.Screenshot \
    --object-path /org/gnome/Shell/Screenshot \
    --method org.gnome.Shell.Screenshot.Screenshot \
    true true '/tmp/results/screenshot.png'
  ```
- Add to `after_scenario` hook in `environment.py`: if scenario.status == 'failed', capture screenshot
- VNC: KubeVirt provides VNC console natively — just expose via `virtctl vnc` or Service
- Video: `wf-recorder` in Flatpak or compiled; start at scenario begin, stop+save at end

**Performance SLA:** Screenshot capture: <3s. Video recording overhead: <10% of scenario duration

**Dependencies:** E01 (artifact storage for screenshots/video)

**Estimated effort:** 1.5 sprints

---

## E11: Performance SLAs, Timing, & Flakiness Tracking

**Objective:** Instrument the test suite with timing gates, track test flakiness over time, and enforce per-image execution budgets.

**Targets:** All variants and suites (cross-cutting)

**Acceptance Criteria:**
- [ ] Every workflow step has `activeDeadlineSeconds` matching SLA (smoke: 900s, full pipeline: 10800s)
- [ ] Per-scenario duration recorded in results DB; outliers flagged
- [ ] Flakiness score: scenario with >10% failure rate over 20 runs marked as flaky
- [ ] Flaky tests reported separately from genuine failures in PR comments
- [ ] Grafana dashboard shows: avg suite duration (7-day rolling), P95 scenario time, flakiness heatmap
- [ ] Performance regression alert: if smoke suite exceeds 20 min average, notify via webhook
- [ ] `just flaky` command shows top-10 flakiest scenarios
- [ ] VM boot time tracked: from `create-vm` to SSH ready (target: <5 min)
- [ ] BIB build time tracked: warm cache target <60s, cold target <120s

**Performance SLA Targets (enforced):**
| Suite | Per-image Target | Full Matrix Target |
|---|---|---|
| Smoke | 15 min | 45 min (3 variants parallel) |
| Developer | 20 min | 60 min |
| Software | 10 min | 30 min |
| Lifecycle | 45 min | 2 hr |
| Full pipeline | 45 min/image | 3-4 hr total |

**Implementation Notes:**
- Argo Workflows has built-in duration metrics — scrape via Prometheus
- Add `pytest-json-report` or parse behave JSON output for per-scenario timing
- Flakiness detection: same scenario, same variant, different outcomes over N runs
- Use Argo's `metrics` template field to emit custom Prometheus metrics
- Alert via Alertmanager → webhook → Discord/Slack/GitHub Issue

**Dependencies:** E01 (results database), E02 (CI integration for continuous data)

**Estimated effort:** 2 sprints

---

## E12: Hardware Emulation — USB, Audio, TPM, Watchdog

**Objective:** Extend KubeVirt VM specs to include emulated hardware peripherals and add tests validating GNOME's interaction with them.

**Targets:** All Bluefin variants (standard, DX, NVIDIA)

**Acceptance Criteria:**
- [ ] USB device emulation: `virtio-usb` or `qemu-xhci` + mass storage device attached
- [ ] Test scenario: GNOME Files shows USB device in sidebar when emulated device attached
- [ ] Audio: `ich9-hda` or `virtio-snd` audio device; PulseAudio/PipeWire reports output device
- [ ] Test scenario: `pactl list sinks` shows at least one audio output
- [ ] TPM 2.0: `swtpm` device attached; `tpm2_getcap` reports TPM presence
- [ ] Test scenario: `systemd-cryptenroll --tpm2-device=auto` enrollment possible (dry-run)
- [ ] Watchdog: `i6300esb` watchdog device; `wdctl` reports device
- [ ] All hardware tests tagged `@hardware_emulation` for selective execution
- [ ] VM spec variants: `standard` (no extras), `full-hw` (all emulated devices)

**Implementation Notes:**
- KubeVirt supports:
  - `devices.sound`: `{name: audio, model: ich9}` 
  - `devices.tpm`: `{}` (uses swtpm emulator)
  - `devices.watchdog`: `{model: i6300esb, action: poweroff}`
  - USB: via `devices.inputs` or custom QEMU args
- These don't require physical hardware — purely emulated
- Run as a nightly job (not per-PR) to manage total execution time
- Red Hat pattern: libvirt-tck hardware validation suite

**Performance SLA:** Hardware emulation tests: <15 minutes per variant

**Dependencies:** E05 (variant golden disks)

**Estimated effort:** 2 sprints

---

## E13: Security Hardening — Pipeline & Runtime

**Objective:** Harden the test pipeline itself against supply-chain attacks and validate the security posture of tested images.

**Targets:** Pipeline infrastructure + all Bluefin variants

**Acceptance Criteria:**
- [ ] Pod Security Standards: `restricted` profile applied to test namespaces (except KubeVirt which needs `privileged`)
- [ ] Network Policies: test VMs can reach DNS/GHCR but not other cluster services
- [ ] RBAC audit: `argo` ServiceAccount has minimum required permissions (document in runbook)
- [ ] SSH key rotation: automated workflow that rotates key, re-patches golden disks, verifies SSH
- [ ] Secrets scanning: pre-commit hook prevents committing secrets to repo
- [ ] Image pinning: all workflow template images pinned to digest (not `:latest`)
- [ ] Vulnerability scanning: Trivy scan on golden disk rootfs, fail on critical CVEs
- [ ] Admission controller: Kyverno or OPA Gatekeeper enforcing image signing + resource limits
- [ ] Supply-chain attestation: SLSA Level 2 provenance for test artifacts

**Implementation Notes:**
- Image pinning: use `crane digest` to resolve tags to SHA256 and store in a `images.lock` file
- Network Policies: allow egress to `ghcr.io` (443), cluster DNS (53), deny everything else
- Trivy: run as an Argo step after BIB build, scanning the golden disk rootfs
- Key rotation workflow:
  1. Generate new ed25519 key
  2. Update k8s Secret
  3. Re-run `bib-disk-configure` on all golden disks
  4. Verify SSH connectivity
  5. Delete old key
- Red Hat pattern: OpenShift compliance-operator approach

**Performance SLA:** Security scans: <5 minutes. Key rotation: <10 minutes (automated)

**Dependencies:** E03 (cosign verification), E04 (SELinux)

**Estimated effort:** 3 sprints

---

## Priority & Sequencing Recommendation

### Sprint 1-2 (Immediate — Foundation)
1. **E03: Cosign Verification** — Quick win, high impact, no dependencies
2. **E01: Artifact Storage** — Unlocks all other epics that need result persistence

### Sprint 3-4 (Critical Path)
3. **E04: SELinux Enforcing** — Highest risk; start early to absorb debugging time
4. **E02: CI/CD Integration** — Unlocks automated triggering

### Sprint 5-6 (Variant Expansion)
5. **E05: DX + NVIDIA Variants** — Expands coverage to all required targets
6. **E07: Vanilla GNOME Baseline** — Quick, high diagnostic value

### Sprint 7-8 (Lifecycle & Security)
7. **E06: Update Lifecycle** — Tests the most critical user journey
8. **E13: Security Hardening** — Comprehensive pipeline security

### Sprint 9-10 (Full Coverage)
9. **E09: KnuckleOS Install** — Completes OS target coverage
10. **E10: Visual Evidence** — Debugging multiplier

### Sprint 11-12 (Polish & Performance)
11. **E11: Performance SLAs** — Enforces quality gates on timing
12. **E08: GPU Passthrough** — Hardware-dependent; may be blocked
13. **E12: Hardware Emulation** — Nice-to-have; nightly-only tests

---

## Full Suite Runtime Budget (Target Architecture)

| Pipeline | Variants | Parallel Lanes | Per-Lane Time | Total Wall Clock |
|---|---|---|---|---|
| PR Smoke | latest + lts | 2 | 15 min | 15 min |
| PR Full (smoke + developer) | latest + lts | 2 | 35 min | 35 min |
| Nightly Full | standard + DX + NVIDIA + vanilla | 4 | 45 min | 45 min |
| Nightly Lifecycle | standard + DX | 2 | 45 min | 45 min |
| Weekly Complete | All variants, all suites | 6 | 60 min | 2.5 hr |

**Total weekly test hours consumed:** ~8-10 hours of compute (within single-node budget with scheduling)

---

## Architecture Decision Records

### ADR-1: AT-SPI over Pixel Matching
**Decision:** Retained. AT-SPI provides semantic interaction that is resilient to theme changes, resolution changes, and rendering differences across variants. Pixel matching is reserved only for visual regression (E10) as a supplementary signal, never as a primary assertion mechanism.

### ADR-2: Argo Workflows over Tekton
**Decision:** Retained. Argo is already deployed, understood, and has native DAG/matrix support. Tekton would require migration with no clear benefit. GitHub Actions triggers Argo (not replaces it).

### ADR-3: BIB Golden Disks over Live Install
**Decision:** Retained for CI speed. Live install testing (anaconda/OOBE) is explicitly out of scope; the knuckle installer flow (E09) is the only install-path test.

### ADR-4: SELinux Enforcing as Default
**Decision:** New. All tests must pass with SELinux enforcing. `selinux=0` is a testing anti-pattern that hides real production bugs. The transition will be painful but is non-negotiable for a production-grade test suite.

### ADR-5: Cosign Verification as Pipeline Gate
**Decision:** New. No image enters the test pipeline without signature verification. This includes the Bluefin images under test AND the infrastructure images (Fedora, chainguard) used by the pipeline itself.
