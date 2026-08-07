---
name: suite-map
description: "Authoritative coverage matrix and @future gap list. Load during planning, coverage reviews, or when adding a new suite."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

# Suite Map and Coverage

Load when: deciding which suite to add a test to, checking existing coverage, or reviewing @future gaps.

## When to Use

- Choosing the correct suite for new coverage
- Determining which image variants run a suite
- Updating scenario counts after feature-file changes
- Verifying variant-specific tag semantics such as `@bluefin` and `@dakota_only`

## When NOT to Use

- GNOME AT-SPI implementation details → use `gnome.md`
- Behave step-authoring patterns or collision avoidance → use `behave.md`
- CI workflow internals or reusable action behavior → use `e2e-workflow.md`

## Core Process

1. Identify the suite affected by the change.
2. Confirm the suite/image matrix before adding variant-specific coverage.
3. Verify the correct scenario tags for that image family.
4. Update the coverage snapshot and per-suite counts when scenario totals change.
5. Cross-check the same totals in `docs/qa-review.md` before opening the PR.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It is only one scenario, the counts can wait." | Coverage drift compounds quickly; `suite-map.md` and `docs/qa-review.md` are co-authoritative. |
| "The tag name is obvious." | Variant gating is implemented in suite hooks; confirm the actual tag semantics before writing image-specific scenarios. |
| "Another skill file already mentions this suite." | This file is the source for suite-to-image mapping and coverage totals. |

## Red Flags

- Scenario totals changed but `suite-map.md` was not updated
- A variant-specific scenario was added without checking whether the image actually runs that suite
- A new tag was used without documenting its meaning here
- `suite-map.md` and `docs/qa-review.md` disagree on counts

## Verification

- [ ] Suite/image matrix still matches the intended coverage
- [ ] Variant tag semantics match the actual suite hook behavior
- [ ] Scenario totals here match `docs/qa-review.md`
- [ ] Notes describe timeless operating rules, not session history

> Coverage snapshot here and in `docs/qa-review.md` are co-authoritative — update both when scenario counts or gap status change.

## Variant matrix

Which suites run on which image. Any bootc/ostree GNOME image can run via the GitHub Action.

| Suite | `bluefin` | `bluefin-gdx` | `bluefin-nvidia-open` | `dakota` | `bazzite` | `gnomeos` | `flatcar` | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `smoke` | ✅ | ✅ | ✅ | ✅ | — | — | — | Core GNOME smoke; automatically sharded into `smoke-a` + `smoke-b` parallel jobs |
| `vanilla-gnome` | — | — | — | — | — | ✅ | — | Upstream GNOME baseline; `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` |
| `bazzite` | — | — | — | — | ✅ | — | — | Bazzite extensions + shell behaviour |
| `developer` | ✅ | ✅ | — | — | — | — | — | Homebrew/Ptyxis |
| `software` | — | — | — | — | — | ✅ | — | Bazaar launch, search, config YAML validation, Flathub remote, permissions DB, and Bazaar CLI presence/info/remote active; upstream GNOME Software navigation scenarios remain quarantined (#176) |
| `common` | ✅ | ✅ | ✅ | ✅ | — | — | — | Flatpak model/state, XDG portals, container runtime, polkit, shell env/sourcing, system scripts, ujust recipes, GSettings/dconf, immutable OS integrity |
| `lifecycle` | ✅ | — | ✅ | ✅ `@homed_migration` | — | — | — | bootc upgrade/rollback; SSH-mode; dakota: homed migration only |
| `security` | ✅ | — | ✅ | — | — | — | — | cosign + SELinux; SSH-mode |
| `hardware` | ✅ | — | — | — | — | — | — | udev rules syntax validation + emulated peripherals; SSH-mode |
| `dx` | — | ✅ | — | — | — | — | — | DX-only tools (VS Code, distrobox, Jupyter) |
| `nvidia` | — | — | ✅ | — | — | — | — | GPU driver validation; NVIDIA variant only |
| `flatcar` | — | — | — | — | — | — | ✅ | Flatcar OS boot and lifecycle |
| `kde-smoke` | — | — | — | — | — | — | — | KDE Plasma harness proof-of-concept; Aurora-only, all scenarios `@informational` |

**GitHub Action consumers**:
```yaml
uses: <image-org>/testsuite/.github/workflows/e2e.yml@v1
with:
  image: <your-bootc-image>
  suites: smoke,common   # smoke and common each auto-shard into two parallel jobs
```
Passing `suites: smoke` expands to `smoke-a` + `smoke-b`, and `suites: common` expands to `common-a` + `common-b`. Both cut wall time by ~50%. New `.feature` files in these suites are picked up automatically.

GitHub Action suites (`smoke`, `vanilla-gnome`, `bazzite`, `developer`, `dx`, `software`, `common`, `lifecycle`) run on `ubuntu-latest`.
`security` and `hardware` (SSH-mode) are not yet in the GHA action (epics #43/#44).

Any bootc/ostree GNOME image can plug in `smoke` and `common` as a portable health gate — no Bluefin-specific knowledge required. See `README.md` → "For other bootc image maintainers" for minimum image requirements.

## PR gate model

- All consumer repos should gate on the `smoke` suite only.
- Nightly CI is gone; PR gates are now the only CI signal for promotion decisions.
- `e2e.yml` now caches OCI layers by image digest to speed repeated runs.
- For workflow internals, cache behavior, and troubleshooting, see [`docs/skills/ci-ops/e2e-workflow/SKILL.md`](../../ci-ops/e2e-workflow/SKILL.md).


**Trigger a lifecycle run manually**:
Go to **[<image-org>/actions → Actions → bootc Upgrade and Rollback Test → Run workflow](https://github.com/<image-org>/actions/actions/workflows/upgrade-test.yml)**.
Set `image` (e.g. `ghcr.io/<readonly-upstream>/bluefin:latest`), `suites: lifecycle`, `chunked_enabled: false`.
Set `chunked_enabled: true` once `ghcr.io/<image-org>/bluefin:latest` ships zstd:chunked layers.

> **For lifecycle runs, use `upgrade-test.yml` in `<image-org>/actions`** — it
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
- `bluefin` does not ship GNOME Software (it ships Bazaar — `io.github.kolunmi.Bazaar`, a Flatpak software center) → the GNOME Software navigation scenarios stay quarantined (#176); Bazaar CLI presence/info/remote coverage is active in `bazaar.feature` and Bazaar config integrity coverage is active in `bazaar_config.feature`
- `bazzite` is not vanilla GNOME → only the bazzite suite runs against it (no vanilla-gnome)
- `bluefin-nvidia-open` is used because nvidia-open is built daily; nvidia services (`nvidia-persistenced`, `ublue-nvctk-cdi`) are in `IGNORED_FAILED_UNITS_IN_VM` — they always fail in QEMU without a physical GPU

## Scenario tags

| Tag | Meaning |
|---|---|
| `@smoke_suite` | Runs as part of the standard smoke suite |
| `@bluefin` | Smoke scenario runs only when the image name contains `bluefin`; smoke `environment.py` skips it elsewhere |
| `@dakota_only` | Smoke scenario runs only when the image name contains `dakota`; smoke `environment.py` skips it elsewhere |
| `@dx_only` / `@developer_suite` | DX variant only |
| `@nvidia_only` | NVIDIA variant only |
| `@flatcar_suite` | Flatcar OS only |
| `@hardware_emulation` | Requires full-hw VM spec (TPM, audio, watchdog) |
| `@pending` | Placeholder coverage gap; intentionally skipped until a valid harness exists |
| `@future` | Not yet implemented or blocked on infra |
| `@homed_migration` | systemd-homed migration scenarios; dakota lifecycle; SSH-mode; skip-safe when homed absent |
| `@regression` | Anchors a known incident regression guard; must remain active indefinitely |
| `@kde_smoke` | KDE Plasma smoke-suite identifier; used by `e2e.yml` suite registration (#645) |
| `@informational` | Bake-period tier; scenario runs and reports results but does not gate promotion until promoted to `@critical` |

## Coverage snapshot

486 scenarios across 62 feature files (mechanical recount 2026-07-29; fractional scaling adds 2 and sudo-rs adds 5 smoke scenarios).

> **Count drift notice.** The previous snapshot claimed 427 scenarios across 52 files. A
> mechanical recount of `tests/*/features/**/*.feature` on `main` found **479 across 61** —
> the snapshot had drifted by ~39 scenarios before any KDE work began. The totals above and
> the Scenarios/Active/Quarantined columns below are now mechanically derived from
> `behave --dry-run` (bare, and with `--tags=quarantine`) per suite. The *Remaining
> quarantine breakdown* table further down is a non-exhaustive list of known blockers,
> inherited from the 2026-06-30 audit; it does not enumerate every quarantined scenario.

| Suite | Scenarios | Active | Quarantined | Notes |
|---|---|---|---|---|
| smoke | 187 | 142 | 45 | MIME handler coverage (Firefox/Papers/Loupe/Text Editor/video); GNOME accessibility (AT-SPI daemon, high-contrast toggle, a11y panel); display fractional/integer scaling via Mutter DisplayConfig; Bluefin desktop identity (Wayland, hardware accel, Dash to Dock); GNOME regression guards in gnome_regression.feature; Dakota sudo-rs privilege and PAM checks |
| developer | 19 | 7 | 12 | 6 brew + 6 ptyxis (AT-SPI restart issue #368) — `brew-setup.service` masked in CI |
| software | 23 | 15 | 8 | Bazaar launch + search + CLI presence/info/remote + config YAML validation active on bluefin; Bazaar UI tests rewritten for actual Bazaar layout; CLI (Flathub remote + permissions DB) active on all images; upstream GNOME Software scenarios quarantined |
| common | 116 | 98 | 18 | Flatpak model + state; XDG portal health + integration; container runtime (podman); polkit rules; shell env + sourcing; system scripts; ujust recipes; GSettings/dconf defaults; immutable OS integrity (no layered RPMs, /usr read-only, bootc status); desktop entries; signing assertions |
| vanilla-gnome | 13 | 13 | 0 | Baseline GNOME Shell parity check; runs on any GNOME image |
| lifecycle | 27 | 25 | 2 | bootc upgrade / rollback / migration; pin + switch quarantined |
| hardware | 13 | 13 | 0 | udev rules syntax validation (ZSA, Apple SuperDrive, Framework 16, AMD s2idle, Wooting, VIIA); emulated peripherals driven by shared SSH steps |
| security | 15 | 15 | 0 | cosign verify: projectbluefin (bluefin, lts, dakota) + ublue-os (latest, LTS, DX, nvidia, GTS, DX-nvidia, negative) |
| bazzite | 20 | 20 | 0 | Extension presence + shell behaviour |
| dx | 15 | 10 | 5 | distrobox enter, JupyterLab, brew, mise×2 — infra gaps |
| nvidia | 12 | 0 | 0 | `@future` / `@hardware_blocked` until GPU passthrough exists in the lab |
| flatcar | 13 | 10 | 0 | boot (7 active) + lifecycle (3 active); 3 `@future` (Ignition, boot-order, update_strategy=off) |
| kde-smoke | 13 | 13 | 0 | Plasma session, D-Bus services, AT-SPI tree, KWin output, one KCM, Dolphin, Konsole, Kickoff; all `@informational` |

## Known coverage gaps

| Area | Priority | Notes |
|---|---|---|
| Bazaar / Flatpak management GUI | High | Bazaar CLI/config integrity coverage active; GUI navigation pending GNOME 50 AT-SPI re-validation |
| Flatpak permission management | Low | Flatseal / per-app permissions not exercised |
| OOBE / first-boot | Low | Initial user setup flow not covered |
| `ujust toggle-updates` | Medium | Blocked upstream in `projectbluefin/common`. `update.just` declares `toggle-updates ACTION="prompt":` but never reads `ACTION`, so `gum choose` always prompts and there is no non-interactive entry point; on images with `bctl` the recipe `exec`s a GUI panel. Scenario stays `@pending @wip` in `common_ujust.feature`. Next step: `projectbluefin/common` must honour `ACTION`; tracked in `projectbluefin/testsuite#499`. |
| uupd conditional suppression | Medium | Battery and metered-network checks are not covered: uupd reads UPower and NetworkManager system-bus properties, while testsuite has no supported isolated state-injection contract. Do not use `/sys/class/power_supply` or GNOME proxy settings as substitutes. Next step: add a lab/image-owned simulation hook, then cover the upstream `/etc/uupd/config.json` contract. |

### Remaining quarantine breakdown

| Scenario | Suite | Blocked by |
|---|---|---|
| brew (×6) | developer | `brew-setup.service` masked in CI |
| ptyxis: `@brew` | developer | brew must be initialized first |
| ptyxis: `@input`, `@podman`, `@regression`, `@new_tab`, `@close` (×5) | developer | AT-SPI restart issue in CI — ptyxis reopens between scenarios but the new process isn't reliably accessible |
| VS Code extensions via Marketplace | dx | Flatpak marketplace not in RPM-installed VS Code |
| distrobox enter | dx | pulls `fedora:latest`; no pre-pull in CI, times out |
| JupyterLab | dx | not preinstalled in DX image |
| mise (×2) | dx | `brew-setup.service` masked — mise uses brew-installed shims |
| ujust report (×1) | smoke | `just` version change parses `{{.Repository}}` as template; awaiting image rebuild |
| Activities overview (×3) | smoke | GNOME 50 — `Main.overview.visible` always false in QEMU |
| screen lock (×1) | smoke | GNOME 50 headless — lock doesn't engage in 10s |
| MIME defaults PDF/PNG/video (×3) | smoke | Fedora system mimeapps.list sets Firefox as default; Flatpak apps don't override at system level |
| software GNOME Software scenarios (×8) | software | Bluefin uses Bazaar; upstream GNOME Software GUI coverage quarantined |
| common signing (×2) | common | pending signing policy enforcement |
| common flatpak model/state (×4) | common | flatpak-preinstall.service masked in CI; /var not preserved from OCI build |
| common dconf (×4) | common | gsettings/dconf schema defaults; Ptyxis palette is user-session state |
| common immutable (×2) | common | rpm-ostree/bootc status failing in fresh QEMU bootc install |
| common portals podman.socket (×1) | common | user socket not active in non-interactive CI session |
| common scripts ujust changelogs (×1) | common | glow not available (brew-setup.service masked in CI) |
| common services flatpak (×2) | common | flatpak-preinstall.service masked; /var/lib/flatpak not seeded |
| bootc pin | lifecycle | pin not supported on all images (race condition in some test environments) |
| bootc switch | lifecycle | switch target requires a valid alternate image ref in CI |

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

When activating: remove `@future`, update this file's coverage snapshot, update `docs/qa-review.md`.

## smoke vs vanilla-gnome

`smoke=failed` + `vanilla-gnome=passed` → Bluefin regression.  
`smoke=failed` + `vanilla-gnome=failed` → upstream GNOME issue.  
`vanilla-gnome` runs exclusively against `quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest` — the official upstream GNOME OS bootc image — so results are directly comparable to what GNOME ships.  
Comparison commands and manual inspection procedure → `docs/runbook.md`.
