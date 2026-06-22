---
name: suite-map
description: "Suite map and coverage snapshot for projectbluefin/testsuite — variant matrix, suite-to-image mapping, PR gate model, @future gaps, and active/quarantined scenario counts."
metadata:
  type: reference
---

# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

> Coverage snapshot here and in `QA-REVIEW.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which image. Any bootc/ostree GNOME image can run via the GitHub Action.

| Suite | `bluefin` | `bluefin-gdx` | `bluefin-nvidia-open` | `dakota` | `bazzite` | `gnomeos` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | ✅ | — | — | — | Core GNOME smoke; automatically sharded into `smoke-a` + `smoke-b` parallel jobs |
| `vanilla-gnome` | — | — | — | — | — | ✅ | — | Upstream GNOME baseline; `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` |
| `bazzite` | — | — | — | — | ✅ | — | — | Bazzite extensions + shell behaviour |
| `developer` | ✅ | ✅ | — | — | — | — | — | Homebrew/Ptyxis |
| `software` | — | — | — | — | — | ✅ | — | Bazaar launch, search, Flathub remote, permissions DB, and Bazaar CLI presence/info/remote active; upstream GNOME Software navigation scenarios remain quarantined (#176) |
| `common` | ✅ | ✅ | ✅ | ✅ | — | — | — | dconf, scripts, desktop entries, shell env, signing/security invariants |
| `lifecycle` | ✅ | — | ✅ | ✅ `@homed_migration` | — | — | — | bootc upgrade/rollback; SSH-mode; dakota: homed migration only |
| `security` | ✅ | — | ✅ | — | — | — | — | cosign + SELinux; SSH-mode |
| `hardware` | ✅ | — | — | — | — | — | — | Emulated peripherals; SSH-mode |
| `dx` | — | ✅ | — | — | — | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | — | — | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | — | — | — | ✅ | Flatcar OS boot and lifecycle |

**GitHub Action consumers**:
```yaml
uses: projectbluefin/testsuite/.github/workflows/e2e.yml@main
with:
  image: <your-bootc-image>
  suites: smoke          # or vanilla-gnome, bazzite, developer, dx, software, common, lifecycle
```
Passing `suites: smoke` automatically expands to two parallel jobs (`smoke-a` and `smoke-b`), cutting smoke wall time by ~50%. Both shards push screenshots to `smoke-latest` (last writer wins).

GitHub Action suites (`smoke`, `vanilla-gnome`, `bazzite`, `developer`, `dx`, `software`, `common`, `lifecycle`) run on `ubuntu-latest`.
`security` and `hardware` (SSH-mode) are not yet in the GHA action (epics #43/#44).

## PR gate model

- All consumer repos should gate on the `smoke` suite only.
- Nightly CI is gone; PR gates are now the only CI signal for promotion decisions.
- `e2e.yml` now caches OCI layers by image digest to speed repeated runs.
- For workflow internals, cache behavior, and troubleshooting, see [`docs/skills/e2e-workflow.md`](e2e-workflow.md).


**Trigger a lifecycle run manually**:
Go to **[projectbluefin/actions → Actions → bootc Upgrade and Rollback Test → Run workflow](https://github.com/projectbluefin/actions/actions/workflows/upgrade-test.yml)**.
Set `image` (e.g. `ghcr.io/ublue-os/bluefin:latest`), `suites: lifecycle`, `chunked_enabled: false`.
Set `chunked_enabled: true` once `ghcr.io/projectbluefin/bluefin:latest` ships zstd:chunked layers.

> **For lifecycle runs, use `upgrade-test.yml` in `projectbluefin/actions`** — it
> calls `e2e.yml` cross-repo and exposes the lifecycle-specific inputs (`chunked_enabled`,
> `test_ref`). `manual.yml` in this repo works for non-lifecycle suites (startup_failure
> was fixed in PR #245 by removing the `@main` ref suffix from the `uses:` line — the
> bare local path `uses: ./.github/workflows/e2e.yml` is fine). For lifecycle, prefer
> `upgrade-test.yml` because it has the richer input set lifecycle needs.

**Registry split:** `bluefin`, `bluefin-nvidia-open`, `dakota` → `ghcr.io/projectbluefin`. `bluefin-gdx`, `bazzite-gnome` → `ghcr.io/ublue-os`.

**Tag notes:**
- `bluefin`: `testing` (pre-release) + `stable` + `lts-testing` + `lts`
- `bluefin-gdx`: `stream10` = lts equivalent; `stream10-testing` = pre-release
- `bluefin-nvidia-open` / `bazzite-gnome`: `testing` + `stable`
- `dakota`: `testing` + `latest`

**Why these assignments:**
- `bluefin` does not ship GNOME Software (it ships Bazaar — `io.github.kolunmi.Bazaar`, a Flatpak software center) → the GNOME Software navigation scenarios stay quarantined (#176); Bazaar CLI presence/info/remote coverage is active in `bazaar.feature`
- `bazzite` is not vanilla GNOME → only the bazzite suite runs against it (no vanilla-gnome)
- `bluefin-nvidia-open` is used because nvidia-open is built daily; nvidia services (`nvidia-persistenced`, `ublue-nvctk-cdi`) are in `IGNORED_FAILED_UNITS_IN_VM` — they always fail in QEMU without a physical GPU

## Scenario tags

| Tag | Meaning |
|---|---|
| `@smoke_suite` | Runs as part of the standard Bluefin smoke suite |
| `@dx_only` / `@developer_suite` | DX variant only |
| `@nvidia_only` | NVIDIA variant only |
| `@flatcar_suite` | Flatcar OS only |
| `@hardware_emulation` | Requires full-hw VM spec (TPM, audio, watchdog) |
| `@pending` | Placeholder coverage gap; intentionally skipped until a valid harness exists |
| `@future` | Not yet implemented or blocked on infra |
| `@homed_migration` | systemd-homed migration scenarios; dakota lifecycle; SSH-mode; skip-safe when homed absent |

## Coverage snapshot

277 scenarios across 34 feature files (last audit: 2026-06-22). 30 quarantined, 244 active, 3 @future stubs.

| Suite | Scenarios | Active | Quarantined | Notes |
|---|---|---|---|---|
| smoke | 87 | 86 | 1 | 1 quarantined: `ujust report` just parse error (common main fixed, rebuilding) |
| developer | 19 | 7 | 12 | 6 brew + 6 ptyxis (AT-SPI restart issue #368) — `brew-setup.service` masked in CI |
| software | 15 | 7 | 8 | Bazaar launch + search + CLI presence/info/remote active on bluefin; CLI (Flathub remote + permissions DB) active on all images; Bazaar scenarios skipped on gnomeos via image guard |
| common | 38 | 36 | 2 | custom-command-list dconf checks active; signing-policy/runtime security assertions |
| vanilla-gnome | 12 | 12 | 0 | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 21 | 19 | 2 | bootc upgrade / rollback / migration; pin + switch quarantined |
| hardware | 10 | 10 | 0 | Driven by shared SSH steps |
| security | 15 | 15 | 0 | cosign verify: projectbluefin (bluefin, lts, dakota) + ublue-os (latest, LTS, DX, nvidia, GTS, DX-nvidia, negative) |
| bazzite | 20 | 20 | 0 | Extension presence + shell behaviour |
| dx | 15 | 10 | 5 | distrobox enter, JupyterLab, brew, mise×2 — infra gaps |
| nvidia | 12 | 12 | 0 | Enabled after GPU passthrough work |
| flatcar | 13 | 10 | 0 | boot (7 active) + lifecycle (3 active); 3 `@future` (Ignition, boot-order, update_strategy=off) |

### Remaining quarantine breakdown

| Scenario | Suite | Blocked by |
|---|---|---|
| brew (×6) | developer | `brew-setup.service` masked in CI (`kernel_args` in e2e.yml) |
| ptyxis: `@brew` | developer | same — brew must be initialized first |
| ptyxis: `@input`, `@podman`, `@regression`, `@new_tab`, `@close` (×5) | developer | AT-SPI restart issue in CI — ptyxis reopens between scenarios but the new process isn't reliably accessible (issue #368) |
| VS Code extensions via Marketplace | dx | Flatpak marketplace not in RPM-installed VS Code |
| distrobox enter | dx | pulls `fedora:latest`; no pre-pull in CI, times out |
| JupyterLab | dx | not preinstalled in DX image |
| mise (×2) | dx | `brew-setup.service` masked — mise uses brew-installed shims |
| ujust report (×1) | smoke | `just` version change parses `{{.Repository}}` as template; common main fixed, awaiting image rebuild |
| software GNOME Software scenarios (×8) | software | Bluefin uses Bazaar, so upstream GNOME Software coverage is quarantined until issue #419 lands Bazaar coverage |
| common signing (×2) | common | pending signing policy enforcement |
| bootc pin | lifecycle | pin not supported on all images (race condition in some test environments) |
| bootc switch | lifecycle | switch target requires a valid alternate image ref in CI |

## Known coverage gaps

| Area | Priority | Status | Notes |
|---|---|---|---|
| Bazaar / Flatpak management on Bluefin | High | Open | `@pending` placeholder exists; current `common` suite is SSH-only with no GNOME session (issue #419) |
| Common shell tools (zsh, fish, fzf, bat, eza, fd, ripgrep, starship) | Medium | Fixed | Resolved by installing tools in CI workflow step before common suite runs (issue #210) |
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
