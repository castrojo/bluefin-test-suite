@common @bluefin
Feature: Bluefin developer mode via bctl (non-interactive)
  Validates the non-interactive devmode contract that resolves testsuite#500.
  `ujust toggle-devmode` (projectbluefin/common
  system_files/bluefin/usr/share/ublue-os/just/system.just) execs
  `bctl devmode --enable` whenever bluefinctl is present, before it ever reaches
  the interactive `gum choose` menu — so `bctl devmode --enable/--disable` is
  the same non-interactive entry point the recipe delegates to, and CI can
  drive it directly over SSH without simulating gum keystrokes.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: bctl provides a non-interactive devmode entry point
    * Run SSH command: "command -v bctl"
    * SSH command return code is "0"
    * Run SSH command: "bctl devmode --help"
    * SSH command return code is "0"
    * SSH command output contains "--enable"
    * SSH command output contains "--disable"

  Scenario: bctl devmode reports current state without a GUI or prompt
    # A fresh VM has never run devmode setup, so groups must not include the
    # devmode set yet (docker/incus-admin/libvirt/dialout).
    * Run SSH command: "groups"
    * SSH command output does not contain "docker"
    # --disable on an already-inactive system takes the read-only branch in
    # bluefinctl (checks state, prints the result, returns) without calling
    # pkexec — see docs/skills/test-authoring/behave/SKILL.md "bctl devmode"
    # note for why this is the only mutation-free way to exercise the check.
    * Run SSH command: "bctl devmode --disable"
    * SSH command return code is "0"
    * SSH command output contains "already inactive"

  # Blocked on CI polkit, not on the recipe: bctl devmode --enable calls
  # `pkexec usermod` to add the docker/incus-admin/libvirt/dialout groups.
  # pkexec requires an authentication agent registered against a real login
  # session; a plain SSH connection has none, so the group-mutating branch
  # cannot be driven headlessly in this harness today. See
  # docs/skills/test-authoring/behave/SKILL.md for the full writeup.
  @pending @wip
  Scenario: bctl devmode --enable adds developer groups without a GUI prompt
    * Run SSH command: "bctl devmode --enable"
    * SSH command return code is "0"
    * Run SSH command: "groups"
    * SSH command output contains "docker"
    * Run SSH command: "bctl devmode --disable"
    * SSH command return code is "0"
