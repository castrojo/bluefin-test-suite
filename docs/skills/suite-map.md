# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

> Coverage snapshot here and in `QA-REVIEW.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which image. Any bootc/ostree GNOME image can run via the GitHub Action.

| Suite | `bluefin` (latest/gts/lts) | `bluefin-dx` (latest/gts/lts) | `bluefin-nvidia` | `bazzite` | `gnomeos` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | — | — | — | Core GNOME smoke; all Bluefin variants |
| `vanilla-gnome` | — | — | — | — | ✅ | — | Upstream GNOME baseline; `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` |
| `bazzite` | — | — | — | ✅ | — | — | Bazzite extensions + shell behaviour; `bazzite-gnome:latest` only |
| `developer` | ✅ | ✅ | — | — | — | — | Homebrew/Ptyxis; DX adds extra tools |
| `software` | — | — | — | — | ✅ | — | Bazaar/Flatpak; gnomeos only — Bluefin ships Warehouse, not GNOME Software |
| `common` | ✅ | ✅ | ✅ | — | — | — | dconf, scripts, desktop entries, shell env |
| `lifecycle` | ✅ | ✅ | ✅ | — | — | — | bootc upgrade/rollback; SSH-mode |
| `security` | ✅ | ✅ | ✅ | — | — | — | cosign + SELinux; SSH-mode |
| `hardware` | ✅ | — | — | — | — | — | Emulated peripherals; SSH-mode |
| `dx` | — | ✅ | — | — | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | — | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | — | — | ✅ | Flatcar OS boot and lifecycle |

**GitHub Action consumers**:
```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: <your-bootc-image>
  suites: smoke          # or vanilla-gnome, bazzite, developer, dx, software, common
```
GitHub Action suites (`smoke`, `vanilla-gnome`, `bazzite`, `developer`, `dx`, `software`, `common`) run on `ubuntu-latest`.
SSH-mode suites (`lifecycle`, `security`, `hardware`) are not yet in the GHA action (epics #43/#44).

## Nightly CI job matrix

The `nightly.yml` workflow runs 10 named jobs. Each job name is visible in the Actions UI:

| Job name | Image | Suites |
|---|---|---|
| `bluefin:latest` | `ghcr.io/ublue-os/bluefin:latest` | smoke, developer, common |
| `bluefin:gts` | `ghcr.io/ublue-os/bluefin:gts` | smoke, developer, common |
| `bluefin:lts` | `ghcr.io/ublue-os/bluefin:lts` | smoke, developer, common |
| `bluefin-dx:latest` | `ghcr.io/ublue-os/bluefin-dx:latest` | smoke, developer, dx, common |
| `bluefin-dx:gts` | `ghcr.io/ublue-os/bluefin-dx:gts` | smoke, developer, dx, common |
| `bluefin-dx:lts` | `ghcr.io/ublue-os/bluefin-dx:lts` | smoke, developer, dx, common |
| `bluefin-nvidia-open:latest` | `ghcr.io/ublue-os/bluefin-nvidia-open:latest` | smoke, common |
| `bazzite-gnome:latest` | `ghcr.io/ublue-os/bazzite-gnome:latest` | bazzite |
| `gnomeos-latest` | `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` | vanilla-gnome, software |
| `persist-results` | n/a | Downloads nightly result artifacts and publishes `data/results-YYYY-MM-DD.jsonl` to `gh-pages` |

**Why these assignments:**
- `bluefin` does not ship GNOME Software (it ships Warehouse) → software suite is gnomeos-only
- `bazzite` is not vanilla GNOME → only the bazzite suite runs against it (no vanilla-gnome)
- `bluefin-nvidia-open` is used instead of `bluefin-nvidia` because nvidia-open is built daily; `bluefin-nvidia:latest` (Oct 2025) ships bootc too old to support `--bootloader`
- nvidia services (`nvidia-persistenced`, `ublue-nvctk-cdi`) are in the `IGNORED_FAILED_UNITS_IN_VM` allowlist because they always fail in QEMU without a physical GPU

## Scenario tags

| Tag | Meaning |
|---|---|
| `@smoke_suite` | Runs as part of the standard Bluefin smoke suite |
| `@dx_only` / `@developer_suite` | DX variant only |
| `@nvidia_only` | NVIDIA variant only |
| `@flatcar_suite` | Flatcar OS only |
| `@hardware_emulation` | Requires full-hw VM spec (TPM, audio, watchdog) |
| `@nightly` | Runs nightly; may be slow or destructive |
| `@future` | Not yet implemented or blocked on infra |

## Coverage snapshot

255 scenarios across 29 feature files (last audit: 2026-05-31).

| Suite | Scenarios | Status | Notes |
|---|---|---|---|
| smoke | 81 | ✅ active | dogtail 4.16 API correct throughout |
| developer | 19 | ✅ active | brew, podman Desktop (+Containers/Images/Volumes), ptyxis |
| software | 12 | ✅ active | Bazaar/gnome-software + Flathub + permissions DB |
| common | 32 | ✅ active | Bluefin common layer: dconf (+clock/font/color-scheme), scripts (+bootc/just/ublue-update), desktop entries (+MIME/icons/Nautilus/Settings), shell + modern CLI tools |
| vanilla-gnome | 12 | ✅ active | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 13 | ✅ active | bootc upgrade / rollback / switch / version tracking / idempotence |
| hardware | 10 | ✅ active | Driven by shared SSH steps |
| security/image_provenance | 10 | ✅ active | cosign verify: projectbluefin (bluefin, lts, dakota) + ublue-os (latest, LTS, DX, nvidia, GTS, DX-nvidia, negative) |
| bazzite | 20 | ✅ active | Extension presence + shell behaviour |
| dx | 15 | ✅ active | VS Code + CLI tools + brew |
| flatcar/boot | 7 | ✅ active | systemd, containerd, networking |
| flatcar/lifecycle | 6 | ⚠️ partially active | knuckle install, update channel, and afterburn are active; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future` |
| security/selinux | 5 | ⏳ @future | Needs `selinux=0` removed from golden disk (Epic E04) |
| nvidia | 12 | ⏳ @future/@hardware_blocked | Needs GPU passthrough (Epic E08); freedesktop tools (drm_info, vulkaninfo, glmark2) staged |

## Known coverage gaps

| Area | Priority | Status | Notes |
|---|---|---|---|
| Flatpak permission management | Low | Open | Flatseal / per-app permissions not exercised |
| OOBE / first-boot | Low | Open | Initial user setup flow not covered |

## @future inventory

Find remaining stubs:
```bash
just list-stubs
# or
grep -r "@future" tests/*/features/*.feature
```

Activate a `@future` scenario when all three conditions are met:
1. VM spec supports the required hardware/feature
2. Step implementations are complete
3. Suite runs cleanly via the GHA action

When activating: remove `@future`, update this file's coverage snapshot, update `QA-REVIEW.md`.

## smoke vs vanilla-gnome

`smoke=failed` + `vanilla-gnome=passed` → Bluefin regression.  
`smoke=failed` + `vanilla-gnome=failed` → upstream GNOME issue.  
`vanilla-gnome` runs exclusively against `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` — the official upstream GNOME OS bootc image — so results are directly comparable to what GNOME ships.  
Comparison commands and manual inspection procedure → `RUNBOOK.md`.
