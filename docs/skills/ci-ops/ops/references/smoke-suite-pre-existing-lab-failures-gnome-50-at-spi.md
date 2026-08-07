---
name: smoke-suite-pre-existing-lab-failures-gnome-50-at-spi
description: "Deep dive: smoke suite — pre-existing lab failures (GNOME 50 AT-SPI)"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Smoke Suite Pre Existing Lab Failures Gnome 50 At Spi

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

Additionally, in nested **container** lanes:

| Symptom | Root cause |
|---|---|
| `ModuleNotFoundError: No module named 'pkg_resources'` | `pkg_resources` is removed in setuptools 81+ and unbundled on Python 3.12+; the test stack still imports it. Fix by provisioning `setuptools` in the nested target |
| `User 'bluefin-test' does not have write permissions for '/dev/uinput'` | dogtail/qecore need uinput to synthesize input; the user is missing the owning group |
| `Cannot reach VM at 127.0.0.1 over SSH` | VM-only scenarios selected into a container lane, where no VM exists — a selection/tagging problem, not an infra fault |

**None of these failures indicate a bug in the PR under test.** They are visible in
smoke runs for unrelated PRs and for the post-merge smoke workflow. Tag scenarios
exposing these as `@quarantine` when the failure is a lab constraint, not a product bug.

**Flatpak scenarios:** Quarantine until lab runs OOBE before test execution.
The `@quarantine` tag is correct — when the lab is fixed, remove the tag and re-test.

---
