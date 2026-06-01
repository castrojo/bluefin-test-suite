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
| `software` | — | — | — | — | ✅ | — | GNOME Software/Flatpak; gnomeos only — Bluefin ships Bazaar (`io.github.kolunmi.Bazaar`), not GNOME Software |
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

The `nightly.yml` workflow runs 9 named jobs. Each job name is visible in the Actions UI:

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

**Why these assignments:**
- `bluefin` does not ship GNOME Software (it ships Bazaar — `io.github.kolunmi.Bazaar`, a Flatpak software center) → software suite is gnomeos-only
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

255 scenarios across 29 feature files (last audit: 2026-06-01). 20 quarantined (down from 42), 235 active.

| Suite | Scenarios | Active | Quarantined | Notes |
|---|---|---|---|---|
| smoke | 81 | 81 | 0 | dogtail 4.16 API correct throughout |
| developer | 19 | 12 | 7 | 6 brew + 1 ptyxis@brew — `brew-setup.service` masked in CI |
| software | 12 | 4 | 8 | 4 navigation/regression/close scenarios need live gnomeos run to verify GNOME 50 AT-SPI names |
| common | 32 | 32 | 0 | dconf (+clock/font/color-scheme), scripts (+bootc/just/ublue-update), desktop entries (+MIME/icons/Nautilus/Settings), shell + modern CLI tools |
| vanilla-gnome | 12 | 12 | 0 | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 13 | 13 | 0 | bootc upgrade / rollback / switch / version tracking / idempotence |
| hardware | 10 | 10 | 0 | Driven by shared SSH steps |
| security/image_provenance | 10 | 10 | 0 | cosign verify: projectbluefin (bluefin, lts, dakota) + ublue-os (latest, LTS, DX, nvidia, GTS, DX-nvidia, negative) |
| bazzite | 20 | 20 | 0 | Extension presence + shell behaviour |
| dx | 15 | 10 | 5 | distrobox enter, JupyterLab, brew, mise×2 — infra gaps |
| flatcar/boot | 7 | 7 | 0 | systemd, containerd, networking |
| flatcar/lifecycle | 6 | 4 | 0 | knuckle install, update channel, and afterburn are active; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future` |
| security/selinux | 5 | 0 | 0 | `@future` — needs `selinux=0` removed from golden disk (Epic E04) |
| nvidia | 12 | 0 | 0 | `@future`/`@hardware_blocked` — needs GPU passthrough (Epic E08) |

### Remaining quarantine breakdown

| Scenario | Suite | Blocked by |
|---|---|---|
| brew (×6) | developer | `brew-setup.service` masked in CI (`kernel_args` in e2e.yml) |
| ptyxis: `@brew` | developer | same — brew must be initialized first |
| VS Code extensions via Marketplace | dx | Flatpak marketplace not in RPM-installed VS Code |
| distrobox enter | dx | pulls `fedora:latest`; no pre-pull in CI, times out |
| JupyterLab | dx | not preinstalled in DX image |
| mise (×2) | dx | `brew-setup.service` masked — mise uses brew-installed shims |
| software navigation (Explore/Installed tabs) | software | GNOME 50 AT-SPI element names in gnome-software changed; needs live gnomeos run |
| software regressions (×2) | software | same |
| software close | software | same |
| software flatpak CLI (×2) | software | same |

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
