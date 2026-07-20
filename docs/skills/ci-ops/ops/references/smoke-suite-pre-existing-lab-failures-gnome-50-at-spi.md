---
name: smoke-suite-pre-existing-lab-failures-gnome-50-at-spi
description: "Deep dive: smoke suite — pre-existing lab failures (GNOME 50 AT-SPI)"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## smoke suite — pre-existing lab failures (GNOME 50 AT-SPI)

Many smoke suite scenarios fail in the lab on `bluefin:testing` for infrastructure
reasons unrelated to the PR being tested. These are expected until the lab image is
updated:

| Feature | Failure | Root cause |
|---|---|---|
| `bluefin_extensions.feature` | Extensions state=99 | Extensions not loaded — GNOME 50 changes to extension init |
| `bluefin_desktop.feature` | Shell.Eval rc=1 | QEMU guest agent not responding — AT-SPI unsafe_mode set fails |
| `gnome_shell.feature` | Shell.Eval rc=1 | Same — D-Bus Shell.Eval interface not responding |
| `gnome_notifications.feature` | Shell.Eval rc=1 | Same |
| `gnome_accessibility.feature` | AT-SPI daemon not running | AT-SPI registry not starting in KVM session |
| `gnome_apps.feature` | No launch candidate | OOTB Flatpaks not installed (no OOBE run) |
| `system_health.feature` | Root filesystem 5% free | VM disk too small (20GB VM vs ~17GB image) |

**None of these failures indicate a bug in the PR under test.** They are visible in
smoke runs for unrelated PRs and for the post-merge smoke workflow. Tag scenarios
exposing these as `@quarantine` when the failure is a lab constraint, not a product bug.

**Flatpak scenarios:** Quarantine until testing-lab runs OOBE before test execution.
The `@quarantine` tag is correct — when the lab is fixed, remove the tag and re-test.

---
