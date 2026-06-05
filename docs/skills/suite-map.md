# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

> Coverage snapshot here and in `QA-REVIEW.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which image. Any bootc/ostree GNOME image can run via the GitHub Action.

| Suite | `bluefin` | `bluefin-gdx` | `bluefin-nvidia-open` | `dakota` | `bazzite` | `gnomeos` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | ✅ | — | — | — | Core GNOME smoke; all Bluefin variants |
| `vanilla-gnome` | — | — | — | — | — | ✅ | — | Upstream GNOME baseline; `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` |
| `bazzite` | — | — | — | — | ✅ | — | — | Bazzite extensions + shell behaviour |
| `developer` | ✅ | ✅ | — | — | — | — | — | Homebrew/Ptyxis |
| `software` | — | — | — | — | — | ✅ | — | Bazaar launch, search, Flathub remote, and permissions DB are active; upstream GNOME Software scenarios quarantined (Bluefin ships Bazaar `io.github.kolunmi.Bazaar`); `@pending` Bazaar placeholder tracks issue #419 |
| `common` | ✅ | ✅ | ✅ | ✅ | — | — | — | dconf, scripts, desktop entries, shell env, signing/security invariants |
| `lifecycle` | ✅ | — | ✅ | — | — | — | — | bootc upgrade/rollback; SSH-mode |
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
GitHub Action suites (`smoke`, `vanilla-gnome`, `bazzite`, `developer`, `dx`, `software`, `common`, `lifecycle`) run on `ubuntu-latest`.
`security` and `hardware` (SSH-mode) are not yet in the GHA action (epics #43/#44).

**Trigger a lifecycle run manually** (preferred — same code path as nightly):
Go to **[projectbluefin/actions → Actions → bootc Upgrade and Rollback Test → Run workflow](https://github.com/projectbluefin/actions/actions/workflows/upgrade-test.yml)**.
Set `image` (e.g. `ghcr.io/ublue-os/bluefin:latest`), `suites: lifecycle`, `chunked_enabled: false`.
Set `chunked_enabled: true` once `ghcr.io/projectbluefin/bluefin:latest` ships zstd:chunked layers.

> **For lifecycle runs, use `upgrade-test.yml` in `projectbluefin/actions`** — it
> calls `e2e.yml` cross-repo and exposes the lifecycle-specific inputs (`chunked_enabled`,
> `test_ref`). `manual.yml` in this repo works for non-lifecycle suites (startup_failure
> was fixed in PR #245 by removing the `@main` ref suffix from the `uses:` line — the
> bare local path `uses: ./.github/workflows/e2e.yml` is fine). For lifecycle, prefer
> `upgrade-test.yml` because it has the richer input set lifecycle needs.

## Nightly CI job matrix

The `nightly.yml` workflow runs 14 named jobs (plus `persist-results`). Each job name is visible in the Actions UI.

| Job name | Image | Suites |
|---|---|---|
| `bluefin:testing` | `ghcr.io/projectbluefin/bluefin:testing` | smoke, developer, common |
| `bluefin:stable` | `ghcr.io/projectbluefin/bluefin:stable` | smoke, developer, common |
| `bluefin:lts-testing` | `ghcr.io/projectbluefin/bluefin:lts-testing` | smoke, developer, common |
| `bluefin:lts` | `ghcr.io/projectbluefin/bluefin:lts` | smoke, developer, common |
| `bluefin-gdx:stream10-testing` | `ghcr.io/ublue-os/bluefin-gdx:stream10-testing` | smoke, developer, dx, common |
| `bluefin-gdx:stream10` | `ghcr.io/ublue-os/bluefin-gdx:stream10` | smoke, developer, dx, common |
| `bluefin-nvidia-open:testing` | `ghcr.io/projectbluefin/bluefin-nvidia-open:testing` | smoke, common |
| `bluefin-nvidia-open:stable` | `ghcr.io/projectbluefin/bluefin-nvidia-open:stable` | smoke, common |
| `dakota:testing` | `ghcr.io/projectbluefin/dakota:testing` | smoke, common |
| `dakota:latest` | `ghcr.io/projectbluefin/dakota:latest` | smoke, common |
| `bazzite-gnome:testing` | `ghcr.io/ublue-os/bazzite-gnome:testing` | bazzite |
| `bazzite-gnome:stable` | `ghcr.io/ublue-os/bazzite-gnome:stable` | bazzite |
| `gnomeos` | `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` | vanilla-gnome, software |
| `bluefin:lifecycle` | `ghcr.io/ublue-os/bluefin:latest` | lifecycle (via `upgrade-test.yml`) |
| `persist-results` | n/a | Downloads nightly result artifacts and publishes `data/results-YYYY-MM-DD.jsonl` to `gh-pages` |

**Registry split:** `bluefin`, `bluefin-nvidia-open`, `dakota` → `ghcr.io/projectbluefin`. `bluefin-gdx`, `bazzite-gnome` → `ghcr.io/ublue-os`.

**Tag notes:**
- `bluefin`: `testing` (pre-release) + `stable` + `lts-testing` + `lts`
- `bluefin-gdx`: `stream10` = lts equivalent; `stream10-testing` = pre-release
- `bluefin-nvidia-open` / `bazzite-gnome`: `testing` + `stable`
- `dakota`: `testing` + `latest`

**Why these assignments:**
- `bluefin` does not ship GNOME Software (it ships Bazaar — `io.github.kolunmi.Bazaar`, a Flatpak software center) → the GNOME Software suite stays quarantined and Bazaar coverage is tracked separately until issue #419 is implemented
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
| `@nightly` | Runs nightly; may be slow or destructive |
| `@pending` | Placeholder coverage gap; intentionally skipped until a valid harness exists |
| `@future` | Not yet implemented or blocked on infra |

## Coverage snapshot

268 scenarios across 32 feature files (last audit: 2026-06-05). 22 quarantined, 225 active, 21 @future/@pending stubs.

| Suite | Scenarios | Active | Quarantined | Notes |
|---|---|---|---|---|
| smoke | 82 | 82 | 0 | All active |
| developer | 19 | 12 | 7 | 6 brew + 1 ptyxis@brew — `brew-setup.service` masked in CI |
| software | 13 | 4 | 8 | Bazaar launch + search + Flathub remote + permissions DB are active; GNOME Software scenarios quarantined (Bluefin uses Bazaar); 1 `@pending` Bazaar placeholder tracks issue #419 |
| common | 37 | 37 | 0 | Shell tools (zsh, fish, fzf, bat, eza, fd, rg, starship) installed in CI via e2e workflow step; adds signing-policy/runtime security assertions |
| vanilla-gnome | 12 | 12 | 0 | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 20 | 18 | 2 | bootc upgrade / rollback / migration; pin + switch quarantined |
| hardware | 10 | 10 | 0 | Driven by shared SSH steps |
| security/image_provenance | 10 | 10 | 0 | cosign verify: projectbluefin (bluefin, lts, dakota) + ublue-os (latest, LTS, DX, nvidia, GTS, DX-nvidia, negative) |
| bazzite | 20 | 20 | 0 | Extension presence + shell behaviour |
| dx | 15 | 10 | 5 | distrobox enter, JupyterLab, brew, mise×2 — infra gaps |
| flatcar/boot | 7 | 7 | 0 | systemd, containerd, networking |
| flatcar/lifecycle | 6 | 3 | 0 | knuckle install, update channel, and afterburn are active; boot-order swap, Ignition config-drive, and `update_strategy=off` remain `@future` |
| security/selinux | 5 | 0 | 0 | `@future` Feature-level — needs `selinux=0` removed from golden disk (Epic E04, PR #280 in merge queue) |
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
| software GNOME Software scenarios (×8) | software | Bluefin uses Bazaar, so upstream GNOME Software coverage is quarantined until issue #419 lands Bazaar coverage |
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
