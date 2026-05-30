# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

> Coverage snapshot here and in `QA-REVIEW.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which image. Any bootc/ostree GNOME image can run via the GitHub Action.

| Suite | `bluefin` (latest/lts) | `bluefin-dx` | `bluefin-nvidia` | `bazzite` | `silverblue` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | — | — | — | Core GNOME smoke; all Bluefin variants |
| `vanilla-gnome` | ✅ | — | — | ✅ | ✅ | — | Upstream GNOME baseline; any GNOME image |
| `bazzite` | — | — | — | ✅ | — | — | Bazzite extensions + shell behaviour |
| `developer` | ✅ | ✅ | — | — | — | — | Homebrew/Ptyxis; DX adds extra tools |
| `software` | ✅ | — | — | — | — | — | Bazaar/Flatpak; standard variant only |
| `lifecycle` | ✅ | ✅ | ✅ | — | — | — | bootc upgrade/rollback; SSH-mode (ghost only for now) |
| `security` | ✅ | ✅ | ✅ | — | — | — | cosign + SELinux; SSH-mode (ghost only for now) |
| `hardware` | ✅ | — | — | — | — | — | Emulated peripherals; SSH-mode (ghost only for now) |
| `dx` | — | ✅ | — | — | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | — | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | — | — | ✅ | Flatcar OS boot and lifecycle |

**GitHub Action consumers** (no ghost/Argo needed):
```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: <your-bootc-image>
  suites: smoke          # or vanilla-gnome, bazzite, developer, dx, software
```
GUI suites (`smoke`, `vanilla-gnome`, `bazzite`, `developer`, `dx`, `software`) run on `ubuntu-latest`.  
SSH-mode suites (`lifecycle`, `security`, `hardware`) require the ghost/Argo stack until the SSH-mode action is built (see #43).

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

162 scenarios across 20 feature files (last audit: 2026-05-28). Bazzite suite adds 20 scenarios (pending PR).

| Suite | Scenarios | Status | Notes |
|---|---|---|---|
| smoke | 68 | ✅ active | dogtail 4.16 API correct throughout |
| developer | 16 | ✅ active | brew, podman, ptyxis covered |
| software | 10 | ✅ active | Bazaar/gnome-software + Flathub |
| vanilla-gnome | 8 | ✅ active | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 7 | ✅ active | bootc upgrade / rollback / switch / /etc merge |
| hardware | 10 | ✅ active | Driven by shared SSH steps |
| security/image_provenance | 5 | ✅ active | cosign verify steps fully implemented |
| bazzite | 20 | 🔄 new | Extension presence + shell behaviour; epic #42 |
| dx | 9 | 🔄 expanding | VS Code + CLI tools + brew |
| flatcar/boot | 7 | ✅ active | systemd, containerd, networking |
| flatcar/lifecycle | 6 | ⏳ @future | Needs dual-disk VM (Epic E09) |
| security/selinux | 5 | ⏳ @future | Needs `selinux=0` removed from golden disk (Epic E04) |
| nvidia | 8 | ⏳ @future/@hardware_blocked | Needs GPU passthrough (Epic E08) |

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
2. Argo template wires the suite
3. Step implementations are complete

When activating: remove `@future`, update this file's coverage snapshot, update `QA-REVIEW.md`.

## smoke vs vanilla-gnome

`smoke=failed` + `vanilla-gnome=passed` → Bluefin regression.  
`smoke=failed` + `vanilla-gnome=failed` → upstream GNOME issue.  
Comparison commands and manual inspection procedure → `RUNBOOK.md`.
