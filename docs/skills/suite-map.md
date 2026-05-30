# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

> Coverage snapshot here and in `QA-REVIEW.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which Bluefin variant:

| Suite | `bluefin` (latest/lts) | `bluefin-dx` | `bluefin-nvidia` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | — | Core GNOME smoke; all Bluefin variants |
| `vanilla-gnome` | ✅ | — | — | — | GNOME upstream baseline; latest only |
| `developer` | ✅ | ✅ | — | — | Homebrew/Ptyxis; DX adds extra tools |
| `software` | ✅ | — | — | — | Bazaar/Flatpak; standard variant only |
| `lifecycle` | ✅ | ✅ | ✅ | — | bootc upgrade/rollback; all Bluefin variants |
| `security` | ✅ | ✅ | ✅ | — | cosign + SELinux; all Bluefin variants |
| `hardware` | ✅ | — | — | — | Emulated peripherals; standard VM spec |
| `dx` | — | ✅ | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | ✅ | Flatcar OS boot and lifecycle |

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

162 scenarios across 20 feature files (last audit: 2026-05-28).

| Suite | Scenarios | Status | Notes |
|---|---|---|---|
| smoke | 68 | ✅ active | dogtail 4.16 API correct throughout |
| developer | 16 | ✅ active | brew, podman, ptyxis covered |
| software | 10 | ✅ active | Bazaar/gnome-software + Flathub |
| vanilla-gnome | 8 | ✅ active | Baseline GNOME Shell parity check |
| lifecycle | 7 | ✅ active | bootc upgrade / rollback / switch / /etc merge |
| hardware | 10 | ✅ active | Driven by shared SSH steps |
| security/image_provenance | 5 | ✅ active | cosign verify steps fully implemented |
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

## Comparing smoke vs vanilla-gnome

If smoke fails while vanilla-gnome passes → likely Bluefin regression.  
If both fail → likely upstream GNOME issue.

```bash
just compare-results          # newest run
just compare-results <uid>    # specific workflow UID
```
