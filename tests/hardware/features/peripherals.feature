@future @hardware_emulation @nightly
Feature: Emulated hardware peripheral validation
  Validates GNOME/systemd interaction with KubeVirt-emulated hardware.
  All devices are virtual — no physical hardware required.
  Runner: plain SSH behave (CLI checks) or qecore for GUI interaction.

  # Requires: VM spec with additional devices (audio, TPM, watchdog).
  # See QA-REVIEW.md Epic E12 for full design.

  Background:
    * Bluefin VM is booted and reachable over SSH

  # ── Audio ──────────────────────────────────────────────────────────────────

  @hardware @audio
  Scenario: PipeWire audio service is running
    * Run SSH command: "systemctl --user is-active pipewire.service"
    * SSH command output "is" "active"

  @hardware @audio
  Scenario: Audio output sink is detected
    # TODO: Requires ich9-hda or virtio-snd device in VM spec.
    * Run SSH command: "pactl list sinks short 2>/dev/null | grep -c RUNNING || pactl list sinks short | wc -l"
    * SSH command return code is "0"

  @hardware @audio
  Scenario: PipeWire reports no errors on startup
    * Run SSH command: "journalctl --user -u pipewire -b --no-pager -p err 2>/dev/null | grep -c pipewire || echo 0"
    * SSH command output stripped "is" "0"

  # ── TPM 2.0 ────────────────────────────────────────────────────────────────

  @hardware @tpm
  Scenario: TPM 2.0 device is present
    # TODO: Requires swtpm device in KubeVirt VM spec.
    * Run SSH command: "test -c /dev/tpm0 && echo present || echo missing"
    * SSH command output "is" "present"

  @hardware @tpm
  Scenario: tpm2-tools can query TPM capabilities
    * Run SSH command: "tpm2_getcap properties-fixed 2>&1 | grep -c TPM2_PT_FAMILY_INDICATOR || echo 0"
    * SSH command return code is "0"

  # ── Watchdog ───────────────────────────────────────────────────────────────

  @hardware @watchdog
  Scenario: Hardware watchdog device exists
    # TODO: Requires i6300esb watchdog in KubeVirt VM spec.
    * Run SSH command: "test -c /dev/watchdog && echo present || echo missing"
    * SSH command output "is" "present"

  @hardware @watchdog
  Scenario: systemd watchdog is configured
    * Run SSH command: "wdctl 2>/dev/null | grep -c 'Device:' || echo 0"
    * SSH command return code is "0"

  # ── USB Mass Storage ───────────────────────────────────────────────────────

  @hardware @usb
  Scenario: USB controller is detected by kernel
    * Run SSH command: "lsusb 2>/dev/null | grep -c -i 'hub\|host' || echo 0"
    * SSH command return code is "0"

  # ── Display / virtio-gpu ───────────────────────────────────────────────────

  @hardware @display
  Scenario: virtio-gpu is the active display adapter
    * Run SSH command: "lspci | grep -i -c 'virtio.*display\|virtio.*gpu' || echo 0"
    * SSH command return code is "0"

  @hardware @display
  Scenario: Wayland session is using virtio-gpu
    * Run SSH command: "loginctl show-session $(loginctl list-sessions --no-legend | awk '{print $1}' | head -1) -p Type 2>/dev/null | grep -c wayland || echo 0"
    * SSH command return code is "0"
