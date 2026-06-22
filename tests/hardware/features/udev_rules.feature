@hardware_emulation
Feature: Custom udev rules integrity
  Verifies Bluefin-specific udev rules are installed and parse cleanly.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @hardware @udev
  Scenario: Bluefin custom udev rules pass syntax validation
    * Run SSH command: "for f in /usr/lib/udev/rules.d/50-framework16.rules /usr/lib/udev/rules.d/60-amd-s2idle-fixes.rules /usr/lib/udev/rules.d/90-apple-superdrive.rules /usr/lib/udev/rules.d/50-zsa.rules /usr/lib/udev/rules.d/70-wooting.rules /usr/lib/udev/rules.d/92-viia.rules; do [ -f \"$f\" ] || continue; if command -v udevadm >/dev/null 2>&1; then udevadm verify \"$f\" 2>&1 || exit 1; else echo skipped; fi; done; echo done"
    * SSH command return code is "0"
    * SSH command output contains "done"

  @hardware @udev
  Scenario: ZSA keyboard udev rule is installed
    * Run SSH command: "test -f /usr/lib/udev/rules.d/50-zsa.rules && echo present"
    * SSH command output "is" "present"

  @hardware @udev
  Scenario: Apple SuperDrive udev rule is installed
    * Run SSH command: "test -f /usr/lib/udev/rules.d/90-apple-superdrive.rules && echo present"
    * SSH command output "is" "present"
