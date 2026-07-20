> **Archived spike** — Learning captured in 2026-05 for issue #229 / epic #227. Issue/line references may be stale. Kept for historical context only.

# Spike: UEFI Boot via OVMF + bootc --bootloader systemd

> Issue: #229 | Epic: #227 (migration upgrade path validation)

## Problem

The existing `e2e.yml` uses direct kernel boot (`-kernel/-initrd/-append`) which
bypasses the bootloader entirely. This prevents testing VM reboots — after
`bootc switch`, the VM must reboot into the **new deployment**, but direct kernel
boot always boots the same extracted kernel/initrd regardless of what `bootc`
staged.

## Solution

Use OVMF (UEFI firmware) pflash boot instead of direct kernel boot. With
`bootc install to-disk --bootloader systemd`, the ESP gets a systemd-boot
installation that reads BLS (Boot Loader Specification) entries. After
`bootc switch` + reboot, systemd-boot picks the newly staged deployment's
BLS entry automatically.

## Spike Questions and Answers

### Q1: Does `bootc install to-disk --bootloader systemd` produce a bootable disk?

**To verify.** The `--bootloader systemd` flag tells bootc to install systemd-boot
instead of relying on bootupd (which may not be present in all images). The spike
workflow runs this and inspects whether the ESP contains a valid systemd-boot
binary and BLS entries.

Known: the existing `e2e.yml` already probes for `--bootloader` support (line 161)
and passes it when available. The comment at line 148-150 says bootc "fails at
the bootloader step" — this may be specific to older bootc versions without
`--bootloader systemd`.

### Q2: Where are the BLS entries?

With `bootc --bootloader systemd`, the typical disk layout is:
- `p1` — BIOS boot partition (small, unused for UEFI)
- `p2` — EFI System Partition (ESP) — contains `EFI/BOOT/BOOTX64.EFI` (systemd-boot)
  and `loader/entries/*.conf` (BLS entries)
- `p3` — Root filesystem (ostree)

The existing `gnome-e2e/action.yml` already mounts p2 and reads BLS entries from
`/loader/entries/` (line 170). The spike inspects all partitions to confirm.

### Q3: OVMF variant on ubuntu-latest

Ubuntu's `ovmf` package provides several variants:
- `OVMF_CODE.fd` / `OVMF_VARS.fd` — standard 2M variant
- `OVMF_CODE_4M.fd` / `OVMF_VARS_4M.fd` — 4M variant (more variable storage)
- `OVMF_CODE_4M.ms.fd` — 4M with Microsoft Secure Boot keys

The spike tries 4M first (more compatible with modern Fedora kernels), then falls
back to standard. The `ovmf` package is available via `apt install ovmf` on
ubuntu-latest.

### Q4: Does OVMF auto-detect the ESP?

**Expected: yes.** OVMF with empty VARS (no stored UEFI boot entries) scans the
disk for an ESP partition (GPT type `C12A7328-F81F-11D2-BA4B-00A0C93EC93B`) and
boots the fallback path `EFI/BOOT/BOOTX64.EFI`. This is the standard UEFI
fallback behavior. No `efibootmgr` or pre-stored NVRAM entries are needed.

### Q5: Does systemd-boot pick the staged deployment after bootc switch?

**Expected: yes.** `bootc switch` writes a new ostree deployment and generates a
new BLS entry. systemd-boot sorts BLS entries by version and boots the latest.
After reboot, `bootc status` should show the new image as the booted deployment.

## QEMU Flags

Key differences from direct kernel boot:

```bash
# Direct kernel boot (current e2e.yml):
-kernel ./vmlinuz -initrd ./initramfs.img -append "${KERNEL_ARGS}"

# UEFI boot via OVMF (this spike):
-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
-drive if=pflash,format=raw,file=./OVMF_VARS.fd
# No -kernel, -initrd, or -append
```

The OVMF_VARS.fd file must be a **writable copy** (not the original from
`/usr/share/OVMF/`) because UEFI firmware writes boot variables to it.

## Notes

- `bootc --bootloader systemd` may not be available in all bootc versions.
  The existing e2e.yml probes for it. If unavailable, the image cannot be
  UEFI-booted without manual bootloader installation.
- The kernel `selinux=0` parameter was previously injected via `-append`. With
  UEFI boot, kernel args come from the BLS entry's `options` line. To add CI
  args, modify the BLS `.conf` file on the ESP before first boot, or use
  `bootc kargs` after boot.
- systemd-boot `loader.conf` may need `timeout 0` to avoid a menu delay.
