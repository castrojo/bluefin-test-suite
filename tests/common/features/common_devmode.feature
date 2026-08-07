@common @bluefin
Feature: Bluefin developer mode via bctl (non-interactive)
  Validates the non-interactive devmode contract that resolves testsuite#500.
  `ujust toggle-devmode` (projectbluefin/common
  system_files/bluefin/usr/share/ublue-os/just/system.just) execs
  `bctl devmode --enable` whenever bluefinctl is present, before it ever reaches
  the interactive `gum choose` menu — so `bctl devmode --enable/--disable` is
  the same non-interactive entry point the recipe delegates to, and CI can
  drive it directly over SSH without simulating gum keystrokes.

  bluefinctl ships through the Homebrew preinstall set
  (system_files/shared/usr/share/ublue-os/homebrew/preinstall.d/bluefinctl.Brewfile
  in projectbluefin/common) and brew-setup.service is masked in QEMU CI, so
  `bctl` is absent there. Every scenario carries @requires_bctl, which skips
  with an explicit reason instead of failing on a missing binary — see
  docs/skills/test-authoring/behave/SKILL.md.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @requires_bctl
  Scenario: bctl provides a non-interactive devmode entry point
    * Run SSH command: "command -v bctl"
    * SSH command return code is "0"
    * SSH command output is not empty
    * Run SSH command: "bctl devmode --help"
    * SSH command return code is "0"
    * SSH command output contains "--enable"
    * SSH command output contains "--disable"

  @requires_bctl
  Scenario: bctl devmode reports current state without a GUI or prompt
    # Precondition, asserted rather than assumed: bluefinctl treats devmode as
    # active when the user is in ANY of docker/incus-admin/libvirt/dialout
    # (DEVMODE_GROUPS in bluefinctl/core/devmode.py). `grep -qxE` exits 1 when
    # none are present and 0 when one is, so the return-code assertion cannot
    # pass vacuously on an empty read or on an SSH transport failure (rc 255).
    * Run SSH command: "groups"
    * SSH command return code is "0"
    * SSH command output is not empty
    * Run SSH command: "groups | tr ' ' '\n' | grep -qxE 'docker|incus-admin|libvirt|dialout'"
    * SSH command return code is "1"
    # --disable on an already-inactive system takes the read-only branch in
    # bluefinctl (checks state, prints the result, returns) without calling
    # pkexec — see docs/skills/test-authoring/behave/SKILL.md "bctl devmode"
    # note for why this is the only mutation-free way to exercise the check.
    * Run SSH command: "bctl devmode --disable"
    * SSH command return code is "0"
    * SSH command output contains "Developer mode is already inactive"

  # Blocked on CI polkit, not on the recipe: bctl devmode --enable calls
  # `pkexec usermod` to add the docker/incus-admin/libvirt/dialout groups.
  # pkexec requires an authentication agent registered against a real login
  # session; a plain SSH connection has none, so the group-mutating branch
  # cannot be driven headlessly in this harness today. Tracked in
  # projectbluefin/testsuite#500. See
  # docs/skills/test-authoring/behave/SKILL.md for the full writeup.
  # Teardown is the @devmode_cleanup after_scenario hook in
  # tests/common/features/environment.py, not trailing steps, so a mid-scenario
  # failure cannot leak an enabled devmode into the next run.
  @pending @wip @requires_bctl @devmode_cleanup
  Scenario: bctl devmode --enable adds developer groups without a GUI prompt
    * Run SSH command: "bctl devmode --enable"
    * SSH command return code is "0"
    * Run SSH command: "groups"
    * SSH command return code is "0"
    * SSH command output is not empty
    * Run SSH command: "groups | tr ' ' '\n' | grep -qxE 'docker|incus-admin|libvirt|dialout'"
    * SSH command return code is "0"
