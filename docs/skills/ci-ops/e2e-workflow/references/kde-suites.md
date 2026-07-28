---
name: kde-suites
description: "KDE suite wiring in the reusable e2e.yml workflow."
metadata:
  type: reference
  audience: agents
  maturity: draft
---
# KDE Suites in the Reusable E2E Workflow

This reference describes how `e2e.yml` supports KDE/Plasma test suites. It is the
workflow counterpart to the behave test content in `tests/kde-*`; changes to either
must stay in sync.


## Supported suites

| Suite | Sharded | Runner mode | DUT session |
|---|---|---|---|
| `kde-smoke` | `-a` / `-b` | Host-side KDE runner container | KDE Plasma (SDDM autologin) |
| `kde-apps` | no | Host-side KDE runner container | KDE Plasma (future) |
| `kde-settings` | no | Host-side KDE runner container | KDE Plasma (future) |
| `kde-session` | no | Host-side KDE runner container | KDE Plasma (future) |

`kde-smoke` is auto-sharded into `kde-smoke-a` and `kde-smoke-b` by the matrix
resolver, mirroring `smoke` and `common`.


## KDE setup is gated to KDE suites only

All KDE-specific workflow logic uses `startsWith(steps.shard.outputs.suite_dir, 'kde')`.
It must **not** fire for `smoke`, `common`, `developer`, `dx`, `software`,
`vanilla-gnome`, `bazzite`, or `lifecycle`.

Gated workflow behavior includes:

- Pulling the KDE runner image (`ghcr.io/projectbluefin/testsuite-kde-runner`) instead of the GNOME runner image.
- Loading the runner container on the GitHub Actions runner (host-side), not into the VM.
- Writing SDDM autologin and KDE determinism environment variables at disk-prep time.
- Skipping the GNOME-only `gnome-ponytail-daemon` install.
- Preparing a KDE/Plasma `/tmp/session.env` (`XDG_SESSION_DESKTOP=kde`, Qt a11y env).
- Installing `selenium-webdriver-at-spi` + `inputsynth` on the DUT.
- Running behave in the host-side KDE runner container.

GNOME suite behavior is unchanged.


## Runner-image split

| Image | Purpose | Ships `inputsynth`? |
|---|---|---|
| `ghcr.io/projectbluefin/testsuite:runner` | GNOME/qecore orchestration inside the VM | yes (built in) |
| `ghcr.io/projectbluefin/testsuite-kde-runner` | KDE/Appium orchestration on the GHA runner | **no** |

The KDE runner image is **host-side only**. It contains pinned `behave`, `selenium`,
`Appium-Python-Client`, `lxml`, and `odiff`. It does **not** contain `inputsynth`,
because `inputsynth` links `PlasmaWaylandProtocols`' `fake-input.xml` and the
Plasma/Qt/KWin ABI differs across Fedora, Ubuntu/Neon, and Arch/KDE Linux.

`inputsynth` and the matching `selenium-webdriver-at-spi` server are installed on
the device-under-test at test time by `scripts/install-kde-webdriver.sh`.

This workflow depends on PR #640 for the `testsuite-kde-runner` image to exist.
Until that PR lands, a KDE suite job will fail at the image-pull step; this is
expected and documented in the PR description.


## Per-DUT webdriver install

The script `scripts/install-kde-webdriver.sh` runs inside the VM and:

1. Detects the distro family from `/etc/os-release`.
2. Performs a version-skew check on the Plasma version and skips the suite with a
defined reason if the version is below the supported baseline (`5.27 LTS` / `6.x`).
3. Prefers distro packages (`dnf`, `apt`, `pacman`) when available.
4. Falls back to a pinned source build of
   `github.com/KDE/selenium-webdriver-at-spi` at commit
   `d45a21e8f1b3591dc921f0be85f1ecd834cbe413`. No floating refs or unpinned
   downloads are used.

If the install emits `KDE_WEBDRIVER_SKIP=<reason>`, the workflow writes a single
skipped scenario to `results/results.json` and exits cleanly instead of producing
phantom failures.


## Version skew / skip behavior

KDE suites must **skip** rather than fail when the DUT cannot be tested reliably.
Current skip conditions:

- Plasma version below `5.27` or `6.0`.
- Distro family not in the supported set (`fedora`, `debian`/`ubuntu`/`neon`,
  `arch`/`kde-linux`).

The skip is surfaced in the job log, the GitHub Step Summary, and the behave JSON
output.
