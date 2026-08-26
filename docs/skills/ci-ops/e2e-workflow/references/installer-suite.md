---
name: installer-suite
description: "How the installer suite's three post-boot assertions gate themselves, and why a workflow-env gate made one of them unreachable."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Installer Suite

The `installer` suite (`tests/installer/features/installer_post_boot.feature`)
validates post-install behaviour after a fisherman (`bootc-installer`)
to-filesystem install: a UEFI boot entry in firmware, the installer's own
Flatpak excluded from the target, and a parseable LUKS UUID on the kernel
cmdline. It runs SSH-only — no qecore, no GUI — on the runner-side branch of the
behave step alongside `common` and `lifecycle`.

Tracked by projectbluefin/dakota#651; the source fixes it detects are
fisherman-side plus projectbluefin/common#385.

## Each assertion gates itself differently

| Assertion | Gate | Runs when |
|---|---|---|
| UEFI boot entry (`efibootmgr -v`) | step-level: skips if `efibootmgr` exits non-zero | the DUT booted via UEFI and `/sys` is reachable |
| Installer Flatpak excluded | none — always runs | every run |
| LUKS cmdline (`rd.luks.name=` / `rd.luks.uuid=`) | `before_scenario` probes the DUT | the target actually has a LUKS volume |

Only the Flatpak assertion is meaningful on the standard direct-kernel-boot
QEMU lane. The other two need a real installed target, which is why the suite
is dispatch-only in consuming repos rather than part of the smoke gate.

## The LUKS gate was unreachable, and what that teaches

The `@luks` scenario originally gated on a `LUKS_ENABLED` environment variable:

```python
context.luks_enabled = os.environ.get("LUKS_ENABLED", "false").lower() in (...)
...
if "luks" in scenario.tags and not context.luks_enabled:
    scenario.skip(...)
```

**Nothing ever set that variable.** The suite runs through the
`common|lifecycle|installer` branch of `e2e.yml`, which exports a fixed list —
`VM_IP`, `VM_USER`, `SSH_KEY`, `SSH_PORT`, `ZSTD_CHUNKED` — and the reusable
workflow exposed no input to add another. A downstream repo could not supply it
either. The scenario therefore skipped on every run since it landed, and a
skipped scenario reads as a green report: the projectbluefin/common#385
assertion was never once exercised.

The fix is a runtime probe, `target_uses_luks()`:

```
lsblk -rno TYPE | grep -qx crypt
```

A booted LUKS system always has an unlocked dm-crypt mapping, so `crypt` in the
`TYPE` column is a reliable signal. The result caches on the context, so one SSH
round trip covers the whole run. `LUKS_ENABLED` is still honoured as an explicit
override in both directions — an unset variable now means "probe", where it used
to collapse to "no LUKS".

**The general rule:** a scenario gated on an environment variable is only as
real as the plumbing that sets it. Before adding an env-var gate, grep for a
writer — `git grep MY_VAR` should find the workflow line that exports it, not
just the line that reads it. If no writer exists, prefer probing the DUT: a
probe cannot silently disagree with reality, and it activates on its own when
the condition it describes becomes true.

`tests/unit/test_installer_environment.py` pins this, including a guard that
fails if the gate reverts to reading an unset variable alone.
