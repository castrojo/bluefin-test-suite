@installer @bluefin
Feature: Installer post-boot assertions for UEFI, Flatpak exclusion, and LUKS cmdline

  Validates post-install behavior after a fisherman (bootc-installer) to-filesystem install.
  Runner: plain SSH behave (no qecore — no GUI interaction needed).

  Background:
    * Bluefin VM is booted and reachable over SSH

  @installer @uefi
  Scenario: UEFI boot entry written to firmware (fisherman #2)
    # After a to-filesystem install, efibootmgr -v on the booted system must
    # show the installer-written entry. Without the /sys/firmware/efi/efivars
    # bind-mount in the podman run invocation, efibootmgr can't reach host UEFI
    # variables.
    * efibootmgr output contains BootCurrent entry
    * efibootmgr output contains BootXXXX entries

  @installer @flatpak
  Scenario: Installer Flatpaks excluded from target (fisherman #1)
    # CopyFlatpaks copies the system flatpak store to the installed system.
    # On the live ISO the tuna-installer app is in the system store and must
    # not appear on the installed target.
    * no installer Flatpaks appear in system flatpak list

  @installer @luks
  Scenario: LUKS cmdline UUID parseable with rd.luks.name= format (common#385)
    # After a LUKS install, /proc/cmdline should contain a parseable LUKS UUID
    # using either rd.luks.uuid= or rd.luks.name= format. Verifies the
    # luks-tpm2-autounlock fix will work on the installed system.
    * kernel cmdline contains rd.luks.name= entry
